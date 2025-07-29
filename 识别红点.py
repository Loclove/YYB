import sensor,time

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA)
sensor.skip_frames(time=2000)
#sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
clock = time.clock()

red_thresholds = [(52, 100, 24, 127, -49, 41), (29, 73, 19, 127, -57, 89)]
rect_threshold = (78, 255)


def detect_red_point(img):
    blobs = img.find_blobs(red_thresholds, merge=True)
    for blob in blobs:
        img.draw_rectangle(blob.rect(), color=(255, 0, 0))
        img.draw_cross(blob.cx(), blob.cy(), color=(0, 0, 0))
        print("Red point:", blob.cx(), blob.cy())
    return img

def detect_rectangles(img):
    img_gray = img.to_grayscale(copy=True)
    img_bin = img_gray.binary([rect_threshold])
    rects = img_bin.find_rects(threshold=10000)
    for r in rects:
        for i in range(4):
            a = r.corners()[i]
            b = r.corners()[(i+1)%4]
            img.draw_line(a[0], a[1], b[0], b[1], color=(0,255,0))
        cx = sum([pt[0] for pt in r.corners()]) // 4
        cy = sum([pt[1] for pt in r.corners()]) // 4
        img.draw_cross(cx, cy, color=(255,0,0))
        print("Rect center:", cx, cy)
    return img

while(True):
    clock.tick()
    img = sensor.snapshot()
    img = detect_red_point(img)
    #img = detect_rectangles(img)
    print(clock.fps())
