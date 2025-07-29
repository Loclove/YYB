import math
import matplotlib.pyplot as plt

allpoints = [(227, 123), (205, 135), (185, 167), (134, 162), (194, 216), (217, 171), (217, 145), (195, 157), (170, 155), (199, 180), (210, 158), (192, 142), (179, 137), (235, 161), (186, 117), (254, 96), (207, 121), (231, 142), (169, 88), (268, 176)]
cx, cy = 204, 148

def polar_angle(point):
    x, y = point
    return math.atan2(y-cy, x-cx)

def distance(point1, point2):
    x1, y1 = point1
    x2, y2 = point2
    return math.hypot(x1 - x2, y1 - y2)

def ClockWiseSorting(sorted_list, centralpoint):
    # 保证每对点中更远的在前
    for i in range(0, len(sorted_list)-1, 2):
        if distance(centralpoint, sorted_list[i]) < distance(centralpoint, sorted_list[i+1]):
            sorted_list[i], sorted_list[i+1] = sorted_list[i+1], sorted_list[i]
    return sorted_list

# 计算每个点到中心的距离
distances = [(pt, distance(pt, (cx, cy))) for pt in allpoints]
sorted_distances = sorted(distances, key=lambda x: x[1])
points = [pair for pair, _ in sorted_distances[:10]]
outpoints = [pair for pair, _ in sorted_distances[10:]]

# 外圈点极角排序并分组
sorted_points = sorted(outpoints, key=polar_angle)
sorted_points = ClockWiseSorting(sorted_points, (cx, cy))

# 内圈点极角排序并分组
sorted_points2 = sorted(points, key=polar_angle)
sorted_points2 = ClockWiseSorting(sorted_points2, (220, 220))

# 绘制外圈点
for idx, point in enumerate(sorted_points):
    plt.annotate(idx, (point[0], point[1]))
    plt.plot(point[0], point[1], marker="o", markersize=5, markeredgecolor="red", markerfacecolor="red")

# 绘制内圈点
for idx, point in enumerate(sorted_points2):
    plt.annotate(idx+20, (point[0], point[1]))
    plt.plot(point[0], point[1], marker="o", markersize=5, markeredgecolor="lime", markerfacecolor="lime")

plt.axis("equal")
plt.show()