"""
01Studio CanMV K230 - high-FPS concentric ring edge tracker.

Pipeline
--------
* VICAP CH0: YUV420SP -> display (hardware bound, zero-copy preview).
* VICAP CH2: GRAYSCALE -> cv_lite / radial refinement.
* cv_lite Hough circles: periodic coarse re-acquisition of both edges.
* Polar gradient + robust circle fit: every-frame sub-pixel refinement.
* Alpha-beta filter: low-jitter center/radius output with motion prediction.

Target used for the defaults: a dark annulus on a light background.  All
parameters that normally need tuning are grouped below.
"""

import gc
import math
import os
import time

import image
from media.sensor import *
from media.display import *
from media.media import *

try:
    import cv_lite
except ImportError:
    print("ERROR: cv_lite is not present in this firmware.")
    print("Flash the CanMV-K230 01Studio v1.8 (or newer) image.")
    raise


# ---------------------------------------------------------------------------
# Board / display configuration
# ---------------------------------------------------------------------------

# "LCD" = 01Studio ST7701 800x480 (recommended)
# "HDMI" = LT9611 1280x720
# "VIRT" = CanMV IDE virtual display (debug; not the fastest path)
DISPLAY_MODE = "LCD"

SENSOR_ID = 2
SENSOR_INPUT_WIDTH = 1280
SENSOR_INPUT_HEIGHT = 720
SENSOR_FPS = 90                 # Official cv_lite circle sample uses 720p90.
MIRROR_TO_IDE = False           # True is convenient for debug but costs display bandwidth.

MIRROR = False
VFLIP = False

DISPLAY_CHN = CAM_CHN_ID_0
ALGORITHM_CHN = CAM_CHN_ID_2

if DISPLAY_MODE == "LCD":
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480
    ALGORITHM_WIDTH = 320
    ALGORITHM_HEIGHT = 192       # Fast 5:3 analysis stream; CH0 stays 800x480.
    COMMON_CROP = (40, 0, 1200, 720)
elif DISPLAY_MODE == "HDMI":
    DISPLAY_WIDTH = 1280
    DISPLAY_HEIGHT = 720
    ALGORITHM_WIDTH = 320
    ALGORITHM_HEIGHT = 180       # Fast 16:9 analysis stream.
    COMMON_CROP = (0, 0, 1280, 720)
elif DISPLAY_MODE == "VIRT":
    DISPLAY_WIDTH = 320
    DISPLAY_HEIGHT = 192
    ALGORITHM_WIDTH = 320
    ALGORITHM_HEIGHT = 192
    COMMON_CROP = (40, 0, 1200, 720)
else:
    raise ValueError("DISPLAY_MODE must be LCD, HDMI, or VIRT")

IMAGE_SHAPE = [ALGORITHM_HEIGHT, ALGORITHM_WIDTH]  # cv_lite order is [H, W].


# ---------------------------------------------------------------------------
# Annulus detector configuration
# ---------------------------------------------------------------------------

DARK_RING = True                 # False for a light ring on a dark background.

# Global re-acquisition radius range.  Defaults cover the supplied image,
# whose inner/outer radius ratio is approximately 0.70.
SHORT_SIDE = min(ALGORITHM_WIDTH, ALGORITHM_HEIGHT)
OUTER_RADIUS_MIN = int(SHORT_SIDE * 0.20)
OUTER_RADIUS_MAX = int(SHORT_SIDE * 0.47)
INNER_OUTER_RATIO_MIN = 0.48
INNER_OUTER_RATIO_MAX = 0.88
INNER_OUTER_RATIO_HINT = 0.70

# cv_lite -> OpenCV HoughCircles parameters.  dp must be an integer in the
# CanMV binding even though desktop OpenCV accepts a float.
HOUGH_DP = 1
HOUGH_MIN_DIST = 10
HOUGH_CANNY_HIGH = 80
HOUGH_VOTE_THRESHOLD = 24
HOUGH_PERIOD = 180               # Reduce periodic Hough stalls; failures still reacquire immediately.
HOUGH_TRACK_RADIUS_BAND = 8      # Narrow range once tracking is established.

# Every-frame polar edge refinement.
RAY_COUNT = 24                   # Frees enough CPU for a wider fast-motion search window.
RADIAL_SEARCH = 10               # Handles about 10 algorithm pixels of motion per frame.
GRADIENT_HALF_WIDTH = 2          # Central-difference baseline in pixels.
MIN_EDGE_GRADIENT = 18           # Increase if texture causes false edges.
MIN_RAY_INLIERS = int(RAY_COUNT * 0.55)
MAX_FIT_RMS = 2.8

# Geometry / temporal gates.
PAIR_CENTER_GATE = 8.0
MAX_CENTER_JUMP = 48.0
MAX_RADIUS_JUMP = 16.0
MAX_MISSED_FRAMES = 2            # Fall back to a global search sooner after a fast jump.

# Alpha-beta temporal filter.  Larger alpha follows faster; smaller alpha is
# smoother. beta estimates velocity and reduces lag on moving targets.
FILTER_ALPHA_CENTER = 0.94
FILTER_BETA_CENTER = 0.20
FILTER_ALPHA_RADIUS = 0.72
FILTER_BETA_RADIUS = 0.10

# Runtime housekeeping.  Per-frame printing/GC causes visible frame-time spikes.
PRINT_PERIOD = 90
GC_PERIOD = 360
WARMUP_FRAMES = 6
OVERLAY_PERIOD = 1               # Refresh the tracking overlay on every processed frame.
VIRT_PREVIEW_PERIOD = 1          # Lowest latency when DISPLAY_MODE is VIRT.
DRAW_FPS = True                  # Left-top overlay contains FPS only.

# GC2093 on 01Studio v1.4 exposes set_auto_exposure() but its driver raises
# NotImplementedError.  Keep the firmware default so startup cannot fail.
AUTO_EXPOSURE = True
MANUAL_EXPOSURE_US = 8000


# Precompute polar directions once. This avoids trigonometry in the frame loop.
_DIRECTIONS = []
for _i in range(RAY_COUNT):
    _a = (2.0 * math.pi * _i) / RAY_COUNT
    _DIRECTIONS.append((math.cos(_a), math.sin(_a)))
del _i, _a


def _median(values):
    """Small-list median without ulab allocations."""
    if not values:
        return 0.0
    ordered = list(values)
    ordered.sort()
    n = len(ordered)
    middle = n >> 1
    if n & 1:
        return float(ordered[middle])
    return 0.5 * (ordered[middle - 1] + ordered[middle])


def _solve_3x3(matrix, vector):
    """Pivoted Gaussian elimination for a 3x3 system."""
    work = [
        [float(matrix[0][0]), float(matrix[0][1]), float(matrix[0][2]), float(vector[0])],
        [float(matrix[1][0]), float(matrix[1][1]), float(matrix[1][2]), float(vector[1])],
        [float(matrix[2][0]), float(matrix[2][1]), float(matrix[2][2]), float(vector[2])],
    ]

    for col in range(3):
        pivot = col
        pivot_abs = abs(work[col][col])
        for row in range(col + 1, 3):
            value_abs = abs(work[row][col])
            if value_abs > pivot_abs:
                pivot = row
                pivot_abs = value_abs
        if pivot_abs < 1.0e-9:
            return None
        if pivot != col:
            work[col], work[pivot] = work[pivot], work[col]

        divisor = work[col][col]
        for j in range(col, 4):
            work[col][j] /= divisor

        for row in range(3):
            if row == col:
                continue
            factor = work[row][col]
            if factor == 0.0:
                continue
            for j in range(col, 4):
                work[row][j] -= factor * work[col][j]

    return [work[0][3], work[1][3], work[2][3]]


def _fit_circle_once(points, origin_x, origin_y):
    """Algebraic circle fit in centered coordinates for numerical stability."""
    n = len(points)
    if n < 6:
        return None

    suu = svv = suv = su = sv = 0.0
    suz = svz = sz = 0.0

    for point in points:
        u = point[0] - origin_x
        v = point[1] - origin_y
        z = u * u + v * v
        suu += u * u
        svv += v * v
        suv += u * v
        su += u
        sv += v
        suz += u * z
        svz += v * z
        sz += z

    solution = _solve_3x3(
        [[suu, suv, su], [suv, svv, sv], [su, sv, float(n)]],
        [-suz, -svz, -sz],
    )
    if solution is None:
        return None

    offset_x = -0.5 * solution[0]
    offset_y = -0.5 * solution[1]
    radius_sq = offset_x * offset_x + offset_y * offset_y - solution[2]
    if radius_sq <= 1.0:
        return None

    return (origin_x + offset_x, origin_y + offset_y, math.sqrt(radius_sq))


def _robust_circle_fit(points, seed_x, seed_y):
    """Two-pass MAD-like rejection; scratches/occlusion do not pull the circle."""
    first = _fit_circle_once(points, seed_x, seed_y)
    if first is None:
        return None

    cx, cy, radius = first
    residuals = []
    for point in points:
        distance = math.sqrt((point[0] - cx) ** 2 + (point[1] - cy) ** 2)
        residuals.append(abs(distance - radius))

    median_abs = _median(residuals)
    reject_limit = max(1.25, min(5.0, median_abs * 2.8 + 0.35))
    inliers = []
    for i in range(len(points)):
        if residuals[i] <= reject_limit:
            inliers.append(points[i])

    if len(inliers) < MIN_RAY_INLIERS:
        return None

    second = _fit_circle_once(inliers, seed_x, seed_y)
    if second is None:
        return None

    cx, cy, radius = second
    error_sum = 0.0
    for point in inliers:
        distance = math.sqrt((point[0] - cx) ** 2 + (point[1] - cy) ** 2)
        error = distance - radius
        error_sum += error * error
    rms = math.sqrt(error_sum / len(inliers))
    return (cx, cy, radius, len(inliers), rms, inliers)


def _gradient_score(img, center_x, center_y, cos_a, sin_a, radius, inner_edge):
    """Signed radial gradient with the expected annulus polarity."""
    inner_r = radius - GRADIENT_HALF_WIDTH
    outer_r = radius + GRADIENT_HALF_WIDTH

    x0 = int(center_x + inner_r * cos_a + 0.5)
    y0 = int(center_y + inner_r * sin_a + 0.5)
    x1 = int(center_x + outer_r * cos_a + 0.5)
    y1 = int(center_y + outer_r * sin_a + 0.5)

    if (x0 < 0 or x0 >= ALGORITHM_WIDTH or y0 < 0 or y0 >= ALGORITHM_HEIGHT or
            x1 < 0 or x1 >= ALGORITHM_WIDTH or y1 < 0 or y1 >= ALGORITHM_HEIGHT):
        return None

    gradient = img.get_pixel(x1, y1) - img.get_pixel(x0, y0)

    # Moving outward: dark annulus has a negative inner edge and positive outer edge.
    score = -gradient if inner_edge else gradient
    if not DARK_RING:
        score = -score
    return float(score)


def _sample_edge_points(img, center_x, center_y, radius, inner_edge):
    """Find one polarity-constrained edge peak on each radial ray."""
    points = []
    low_r = int(radius) - RADIAL_SEARCH
    high_r = int(radius) + RADIAL_SEARCH

    for direction in _DIRECTIONS:
        cos_a, sin_a = direction
        best_score = -1000000.0
        best_radius = 0

        for r in range(low_r, high_r + 1):
            score = _gradient_score(
                img, center_x, center_y, cos_a, sin_a, r, inner_edge
            )
            if score is not None and score > best_score:
                best_score = score
                best_radius = r

        if best_score < MIN_EDGE_GRADIENT:
            continue

        # Parabolic peak interpolation gives a fractional radial coordinate.
        refined_radius = float(best_radius)
        if best_radius > low_r and best_radius < high_r:
            left = _gradient_score(
                img, center_x, center_y, cos_a, sin_a, best_radius - 1, inner_edge
            )
            right = _gradient_score(
                img, center_x, center_y, cos_a, sin_a, best_radius + 1, inner_edge
            )
            if left is not None and right is not None:
                denominator = left - 2.0 * best_score + right
                if abs(denominator) > 1.0e-6:
                    delta = 0.5 * (left - right) / denominator
                    if delta < -0.5:
                        delta = -0.5
                    elif delta > 0.5:
                        delta = 0.5
                    refined_radius += delta

        points.append((
            center_x + refined_radius * cos_a,
            center_y + refined_radius * sin_a,
        ))

    return points


def _radial_refine(img, seed):
    """Refine both boundaries and enforce a common center."""
    seed_x, seed_y, seed_inner_r, seed_outer_r = seed[0:4]

    inner_points = _sample_edge_points(
        img, seed_x, seed_y, seed_inner_r, True
    )
    outer_points = _sample_edge_points(
        img, seed_x, seed_y, seed_outer_r, False
    )
    if len(inner_points) < MIN_RAY_INLIERS or len(outer_points) < MIN_RAY_INLIERS:
        return None

    inner_fit = _robust_circle_fit(inner_points, seed_x, seed_y)
    outer_fit = _robust_circle_fit(outer_points, seed_x, seed_y)
    if inner_fit is None or outer_fit is None:
        return None

    ix, iy, _, inner_count, inner_rms, inner_inliers = inner_fit
    ox, oy, _, outer_count, outer_rms, outer_inliers = outer_fit

    if math.sqrt((ix - ox) ** 2 + (iy - oy) ** 2) > PAIR_CENTER_GATE:
        return None
    if inner_rms > MAX_FIT_RMS or outer_rms > MAX_FIT_RMS:
        return None

    # Weight the cleaner fit more, then recompute both radii about this shared center.
    inner_weight = inner_count / (0.5 + inner_rms)
    outer_weight = outer_count / (0.5 + outer_rms)
    weight_sum = inner_weight + outer_weight
    center_x = (ix * inner_weight + ox * outer_weight) / weight_sum
    center_y = (iy * inner_weight + oy * outer_weight) / weight_sum

    inner_distances = []
    for point in inner_inliers:
        inner_distances.append(math.sqrt(
            (point[0] - center_x) ** 2 + (point[1] - center_y) ** 2
        ))
    outer_distances = []
    for point in outer_inliers:
        outer_distances.append(math.sqrt(
            (point[0] - center_x) ** 2 + (point[1] - center_y) ** 2
        ))

    inner_radius = _median(inner_distances)
    outer_radius = _median(outer_distances)

    if abs(center_x - seed_x) > RADIAL_SEARCH + 3:
        return None
    if abs(center_y - seed_y) > RADIAL_SEARCH + 3:
        return None
    if abs(inner_radius - seed_inner_r) > RADIAL_SEARCH + 2:
        return None
    if abs(outer_radius - seed_outer_r) > RADIAL_SEARCH + 2:
        return None

    ratio = inner_radius / outer_radius
    if ratio < INNER_OUTER_RATIO_MIN or ratio > INNER_OUTER_RATIO_MAX:
        return None

    inlier_fraction = min(inner_count, outer_count) / float(RAY_COUNT)
    fit_penalty = 1.0 / (1.0 + 0.25 * (inner_rms + outer_rms))
    quality = min(1.0, inlier_fraction * fit_penalty)
    return (center_x, center_y, inner_radius, outer_radius, quality)


def _select_outer_circle(flat_circles, prediction):
    """Choose the strongest plausible outer circle from cv_lite's flat list."""
    if not flat_circles:
        return None

    best = None
    best_score = 1.0e30
    frame_center_x = ALGORITHM_WIDTH * 0.5
    frame_center_y = ALGORITHM_HEIGHT * 0.5

    candidate_index = 0
    for i in range(0, len(flat_circles) - 2, 3):
        x = float(flat_circles[i])
        y = float(flat_circles[i + 1])
        r = float(flat_circles[i + 2])
        if r < OUTER_RADIUS_MIN or r > OUTER_RADIUS_MAX:
            continue
        if x - r < 2 or y - r < 2:
            continue
        if x + r >= ALGORITHM_WIDTH - 2 or y + r >= ALGORITHM_HEIGHT - 2:
            continue

        if prediction is not None:
            dx = x - prediction[0]
            dy = y - prediction[1]
            center_error = math.sqrt(dx * dx + dy * dy)
            radius_error = abs(r - prediction[3])
            score = center_error * 2.0 + radius_error + candidate_index * 0.5
        else:
            # OpenCV returns high-vote circles first; center distance is only a tie-breaker.
            dx = x - frame_center_x
            dy = y - frame_center_y
            score = candidate_index * 10.0 + math.sqrt(dx * dx + dy * dy) * 0.03

        if score < best_score:
            best_score = score
            best = (x, y, r)
        candidate_index += 1

    return best


def _select_inner_circle(flat_circles, outer, prediction):
    """Pair an inner Hough circle with the selected outer boundary."""
    if not flat_circles or outer is None:
        return None

    outer_x, outer_y, outer_r = outer
    target_r = (prediction[2] if prediction is not None
                else outer_r * INNER_OUTER_RATIO_HINT)
    best = None
    best_score = 1.0e30
    candidate_index = 0

    for i in range(0, len(flat_circles) - 2, 3):
        x = float(flat_circles[i])
        y = float(flat_circles[i + 1])
        r = float(flat_circles[i + 2])
        ratio = r / outer_r
        if ratio < INNER_OUTER_RATIO_MIN or ratio > INNER_OUTER_RATIO_MAX:
            continue

        dx = x - outer_x
        dy = y - outer_y
        center_error = math.sqrt(dx * dx + dy * dy)
        if center_error > PAIR_CENTER_GATE:
            continue

        score = center_error * 4.0 + abs(r - target_r) + candidate_index * 0.5
        if score < best_score:
            best_score = score
            best = (x, y, r)
        candidate_index += 1

    return best


def _hough_seed(img_np, prediction):
    """Run separate radius-band Hough passes; minDist would suppress concentric
    circles if both boundaries were requested in a single call.
    """
    if prediction is None:
        outer_min = OUTER_RADIUS_MIN
        outer_max = OUTER_RADIUS_MAX
    else:
        outer_min = max(OUTER_RADIUS_MIN,
                        int(prediction[3] - HOUGH_TRACK_RADIUS_BAND))
        outer_max = min(OUTER_RADIUS_MAX,
                        int(prediction[3] + HOUGH_TRACK_RADIUS_BAND))

    if outer_max <= outer_min + 2:
        return None

    outer_values = cv_lite.grayscale_find_circles(
        IMAGE_SHAPE, img_np,
        HOUGH_DP, HOUGH_MIN_DIST,
        HOUGH_CANNY_HIGH, HOUGH_VOTE_THRESHOLD,
        outer_min, outer_max,
    )
    outer = _select_outer_circle(outer_values, prediction)
    outer_values = None
    if outer is None:
        return None

    inner_min = max(6, int(outer[2] * INNER_OUTER_RATIO_MIN))
    inner_max = min(int(outer[2] * INNER_OUTER_RATIO_MAX), int(outer[2]) - 5)
    if prediction is not None:
        inner_min = max(inner_min,
                        int(prediction[2] - HOUGH_TRACK_RADIUS_BAND))
        inner_max = min(inner_max,
                        int(prediction[2] + HOUGH_TRACK_RADIUS_BAND))
    if inner_max <= inner_min + 2:
        return None

    inner_values = cv_lite.grayscale_find_circles(
        IMAGE_SHAPE, img_np,
        HOUGH_DP, HOUGH_MIN_DIST,
        HOUGH_CANNY_HIGH, HOUGH_VOTE_THRESHOLD,
        inner_min, inner_max,
    )
    inner = _select_inner_circle(inner_values, outer, prediction)
    inner_values = None
    if inner is None:
        return None

    # The radial stage will impose one robust shared center.
    center_x = 0.5 * (outer[0] + inner[0])
    center_y = 0.5 * (outer[1] + inner[1])
    return (center_x, center_y, inner[2], outer[2], 0.38)


class _AlphaBetaAxis:
    def __init__(self, alpha, beta):
        self.alpha = alpha
        self.beta = beta
        self.value = 0.0
        self.velocity = 0.0
        self.ready = False

    def reset(self):
        self.value = 0.0
        self.velocity = 0.0
        self.ready = False

    def start(self, measurement):
        self.value = float(measurement)
        self.velocity = 0.0
        self.ready = True

    def prediction(self):
        if not self.ready:
            return None
        return self.value + self.velocity

    def update(self, measurement, quality):
        if not self.ready:
            self.start(measurement)
            return
        predicted = self.value + self.velocity
        innovation = float(measurement) - predicted
        # Large innovations get less smoothing so a fast drag does not lag.
        quality_scale = 0.82 + 0.18 * quality
        alpha_boost = min(0.24, abs(innovation) * 0.025)
        beta_boost = min(0.12, abs(innovation) * 0.012)
        adaptive_alpha = min(0.96, self.alpha * quality_scale + alpha_boost)
        adaptive_beta = min(0.35, self.beta * quality_scale + beta_boost)
        self.value = predicted + adaptive_alpha * innovation
        self.velocity += adaptive_beta * innovation

    def coast(self):
        if self.ready:
            self.value += self.velocity
            self.velocity *= 0.92


class RingTracker:
    """Coherent four-state filter so a bad frame cannot update only one radius."""
    def __init__(self):
        self.fx = _AlphaBetaAxis(FILTER_ALPHA_CENTER, FILTER_BETA_CENTER)
        self.fy = _AlphaBetaAxis(FILTER_ALPHA_CENTER, FILTER_BETA_CENTER)
        self.fi = _AlphaBetaAxis(FILTER_ALPHA_RADIUS, FILTER_BETA_RADIUS)
        self.fo = _AlphaBetaAxis(FILTER_ALPHA_RADIUS, FILTER_BETA_RADIUS)
        self.misses = 0
        self.last_quality = 0.0

    def reset(self):
        self.fx.reset()
        self.fy.reset()
        self.fi.reset()
        self.fo.reset()
        self.misses = 0
        self.last_quality = 0.0

    def valid(self):
        return self.fx.ready

    def prediction(self):
        if not self.valid():
            return None
        return (
            self.fx.prediction(), self.fy.prediction(),
            self.fi.prediction(), self.fo.prediction(),
        )

    def state(self):
        if not self.valid():
            return None
        return (
            self.fx.value, self.fy.value,
            self.fi.value, self.fo.value,
            self.last_quality,
        )

    def _geometry_ok(self, measurement):
        x, y, inner_r, outer_r = measurement[0:4]
        if outer_r < OUTER_RADIUS_MIN or outer_r > OUTER_RADIUS_MAX:
            return False
        if inner_r <= 4 or inner_r >= outer_r - 4:
            return False
        ratio = inner_r / outer_r
        if ratio < INNER_OUTER_RATIO_MIN or ratio > INNER_OUTER_RATIO_MAX:
            return False
        if x - outer_r < 0 or y - outer_r < 0:
            return False
        if x + outer_r >= ALGORITHM_WIDTH or y + outer_r >= ALGORITHM_HEIGHT:
            return False
        return True

    def update(self, measurement):
        if measurement is None or not self._geometry_ok(measurement):
            return False

        if self.valid():
            predicted = self.prediction()
            dx = measurement[0] - predicted[0]
            dy = measurement[1] - predicted[1]
            if math.sqrt(dx * dx + dy * dy) > MAX_CENTER_JUMP:
                return False
            if abs(measurement[2] - predicted[2]) > MAX_RADIUS_JUMP:
                return False
            if abs(measurement[3] - predicted[3]) > MAX_RADIUS_JUMP:
                return False

        quality = max(0.0, min(1.0, float(measurement[4])))
        self.fx.update(measurement[0], quality)
        self.fy.update(measurement[1], quality)
        self.fi.update(measurement[2], quality)
        self.fo.update(measurement[3], quality)
        self.misses = 0
        self.last_quality = quality
        return True

    def miss(self):
        if not self.valid():
            return
        self.fx.coast()
        self.fy.coast()
        self.fi.coast()
        self.fo.coast()
        self.misses += 1
        self.last_quality *= 0.85
        if self.misses > MAX_MISSED_FRAMES:
            self.reset()


def _draw_overlay(osd_img, state, fps):
    osd_img.clear()
    if DRAW_FPS:
        osd_img.draw_string_advanced(
            8, 8, 20, "FPS: %.1f" % fps, color=(0, 255, 80)
        )
    if state is None:
        Display.show_image(osd_img, 0, 0, Display.LAYER_OSD3)
        return

    center_x, center_y, inner_r, outer_r, _ = state
    scale_x = DISPLAY_WIDTH / float(ALGORITHM_WIDTH)
    scale_y = DISPLAY_HEIGHT / float(ALGORITHM_HEIGHT)
    radius_scale = 0.5 * (scale_x + scale_y)
    draw_x = int(center_x * scale_x + 0.5)
    draw_y = int(center_y * scale_y + 0.5)
    draw_inner = int(inner_r * radius_scale + 0.5)
    draw_outer = int(outer_r * radius_scale + 0.5)

    osd_img.draw_circle(draw_x, draw_y, draw_outer,
                        color=(0, 255, 80), thickness=2)
    osd_img.draw_circle(draw_x, draw_y, draw_inner,
                        color=(0, 220, 255), thickness=2)
    osd_img.draw_cross(draw_x, draw_y, color=(255, 64, 64), size=12, thickness=2)
    Display.show_image(osd_img, 0, 0, Display.LAYER_OSD3)


def _draw_virtual(img, state, fps):
    """IDE fallback: draw directly on grayscale; physical modes use zero-copy CH0."""
    if DRAW_FPS:
        img.draw_string_advanced(4, 4, 16, "FPS: %.1f" % fps)
    if state is not None:
        center_x, center_y, inner_r, outer_r, _ = state
        x = int(center_x + 0.5)
        y = int(center_y + 0.5)
        img.draw_circle(x, y, int(outer_r + 0.5), color=255, thickness=2)
        img.draw_circle(x, y, int(inner_r + 0.5), color=180, thickness=2)
        img.draw_cross(x, y, color=255, size=10, thickness=2)
    Display.show_image(img)


def _configure_pipeline():
    sensor = Sensor(
        id=SENSOR_ID,
        width=SENSOR_INPUT_WIDTH,
        height=SENSOR_INPUT_HEIGHT,
        fps=SENSOR_FPS,
    )
    sensor.reset()
    sensor.set_hmirror(MIRROR)
    sensor.set_vflip(VFLIP)

    # Use one explicit acquisition crop for both channels. CanMV's crop=True
    # chooses a crop from each output size independently, which misaligns OSD.
    # Scaling this shared crop preserves one field of view on CH0 and CH2.
    if DISPLAY_MODE != "VIRT":
        sensor.set_framesize(
            width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT,
            chn=DISPLAY_CHN, crop=COMMON_CROP,
        )
        sensor.set_pixformat(Sensor.YUV420SP, chn=DISPLAY_CHN)
        bind_info = sensor.bind_info(x=0, y=0, chn=DISPLAY_CHN)
        Display.bind_layer(**bind_info, layer=Display.LAYER_VIDEO1)

    sensor.set_framesize(
        width=ALGORITHM_WIDTH, height=ALGORITHM_HEIGHT,
        chn=ALGORITHM_CHN, crop=COMMON_CROP,
    )
    sensor.set_pixformat(Sensor.GRAYSCALE, chn=ALGORITHM_CHN)

    if DISPLAY_MODE == "LCD":
        Display.init(
            Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT,
            to_ide=MIRROR_TO_IDE,
        )
    elif DISPLAY_MODE == "HDMI":
        Display.init(
            Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT,
            to_ide=MIRROR_TO_IDE,
        )
    else:
        Display.init(
            Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT,
            fps=60, to_ide=True, quality=50,
        )

    MediaManager.init()
    sensor.run()
    if not AUTO_EXPOSURE:
        try:
            if hasattr(sensor, "set_auto_exposure"):
                try:
                    sensor.set_auto_exposure(
                        False, exposure_us=MANUAL_EXPOSURE_US
                    )
                except TypeError:
                    sensor.set_auto_exposure(False, MANUAL_EXPOSURE_US)
            elif hasattr(sensor, "auto_exposure"):
                sensor.auto_exposure(False)
                if hasattr(sensor, "exposure"):
                    sensor.exposure(MANUAL_EXPOSURE_US)
            else:
                print("manual exposure API unavailable; using firmware default")
        except Exception as error:
            # Some v1.4 sensor drivers publish the method but do not implement it.
            print("manual exposure unsupported; using firmware default:", repr(error))

    osd_img = None
    if DISPLAY_MODE != "VIRT":
        osd_img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.ARGB8888)
    return sensor, osd_img


def run():
    sensor = None
    osd_img = None
    display_ready = False
    media_ready = False

    try:
        sensor, osd_img = _configure_pipeline()
        display_ready = True
        media_ready = True

        # Give AE and the sensor pipeline a few frames to settle.
        for _ in range(WARMUP_FRAMES):
            warmup = sensor.snapshot(chn=ALGORITHM_CHN)
            warmup = None

        tracker = RingTracker()
        clock = time.clock()
        frame_number = 0

        while True:
            os.exitpoint()
            clock.tick()

            img = sensor.snapshot(chn=ALGORITHM_CHN)
            if img == -1:
                tracker.miss()
                continue

            prediction = tracker.prediction()
            hough_seed = None
            hough_attempted = False

            # Run expensive Hough only periodically while tracked.  The display
            # channel keeps streaming in hardware regardless of detector time.
            if (prediction is None or tracker.misses > 0 or
                    (frame_number % HOUGH_PERIOD) == 0):
                hough_attempted = True
                img_np = img.to_numpy_ref()
                hough_seed = _hough_seed(img_np, prediction)
                img_np = None

            seed = hough_seed if hough_seed is not None else prediction
            measurement = None
            if seed is not None:
                measurement = _radial_refine(img, seed)

            # If normal tracking just failed, reacquire in this same frame
            # instead of coasting until the next Hough refresh.
            if (measurement is None and not hough_attempted and
                    prediction is not None):
                img_np = img.to_numpy_ref()
                hough_seed = _hough_seed(img_np, prediction)
                img_np = None
                if hough_seed is not None:
                    measurement = _radial_refine(img, hough_seed)

            # A valid Hough pair is a conservative fallback if a scratch or
            # glare leaves too few radial inliers in this frame.
            if measurement is None and hough_seed is not None:
                measurement = hough_seed

            if not tracker.update(measurement):
                tracker.miss()

            state = tracker.state()
            fps = clock.fps()

            if DISPLAY_MODE == "VIRT":
                if (frame_number % VIRT_PREVIEW_PERIOD) == 0:
                    _draw_virtual(img, state, fps)
            elif (frame_number % OVERLAY_PERIOD) == 0:
                _draw_overlay(osd_img, state, fps)

            if (frame_number % PRINT_PERIOD) == 0:
                if state is None:
                    print("ring: searching, fps=%.1f" % fps)
                else:
                    print(
                        "ring: cx=%.2f cy=%.2f ri=%.2f ro=%.2f "
                        "thickness=%.2f q=%.2f fps=%.1f" % (
                            state[0], state[1], state[2], state[3],
                            state[3] - state[2], state[4], fps,
                        )
                    )

            img = None
            frame_number += 1
            if (frame_number % GC_PERIOD) == 0:
                gc.collect()

    except KeyboardInterrupt:
        print("user stopped")
    except BaseException as error:
        print("runtime error:", repr(error))
    finally:
        if isinstance(sensor, Sensor):
            sensor.stop()
        if display_ready:
            Display.deinit()
        os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
        time.sleep_ms(100)
        if media_ready:
            MediaManager.deinit()


if __name__ == "__main__":
    run()

