import sensor, image, time, math
from pyb import LED
from pyb import UART

thresholds = [(30, 100, 127, 12, -128, 127)]

sensor.reset() #初始化设置
sensor.set_pixformat(sensor.RGB565) #设置为彩色
sensor.set_framesize(sensor.QQVGA) #设置清晰度
sensor.skip_frames(time = 2000) #跳过前2000ms的图像
#sensor.set_auto_gain(False) # must be turned off for color tracking
sensor.set_auto_whitebal(False) # must be turned off for color tracking
clock = time.clock() #创建一个clock便于计算FPS，看看到底卡不卡

uart = UART(3, 9600)
flag1=0
flag2=0
q=[0]*20
cx=0
cy=0
while(True): #不断拍照
    clock.tick()
    img = sensor.snapshot().lens_corr(1.8) #拍摄一张照片，lens_corr函数用于非鱼眼畸变矫正，默认设置参数为1.8
    i=0
        #img = sensor.snapshot().lens_corr(1.8) #拍摄一张照片，lens_corr函数用于非鱼眼畸变矫正，默认设置参数为1.8
        #readflag=0
    for blob in img.find_blobs(thresholds,pixels_threshold=20,area_threshold=20):
            #print(blob.solidity())
            if blob.solidity()>0.50 and flag1<6:
                flag1=flag1+1
                img.draw_rectangle(blob.rect(),color = (255, 0, 0))
               # print([blob.cx(),blob.cy()]);
                cx=cx+blob.cx()
                cy=cy+blob.cy()

        for r in img.find_rects(threshold = 30000):
            #print(r)
            if r.w() > 30 and r.h() > 30 and r.w() <70 and r.h() < 70 and flag2<6:
                flag2=flag2+1
                img.draw_rectangle(r.rect(), color = (0, 0, 255))
                for p in r.corners():
                    img.draw_circle(p[0], p[1], 5, color = (0, 255, 0))
                    q[i]=q[i]+p[0]
                    i=i+1
                    q[i]=q[i]+p[1]
                    i=i+1
        print([0xA5,cx,cy,q[0], q[1],q[2], q[3],q[4],q[5],q[6], q[7],0xA6])
        if flag1>=5 and flag2>=5:
            readflag=0
            cx=cx//flag1
            cy=cy//flag1
            q[0]=q[0]//flag2
            q[1]=q[1]//flag2
            q[2]=q[2]//flag2
            q[3]=q[3]//flag2
            q[4]=q[4]//flag2
            q[5]=q[5]//flag2
            q[6]=q[6]//flag2
            q[7]=q[7]//flag2
            a = bytearray([0xA5,cx,cy,q[0], q[1],q[2], q[3],q[4],q[5],q[6], q[7],0xA6])
            #a = bytearray([0xA5,100,0x5A])
            uart.write(a)
            print([0xA5,cx,cy,q[0], q[1],q[2], q[3],q[4],q[5],q[6], q[7],0xA6])
            q=[0]*20
            cx=0
            cy=0
            flag1=0
            flag2=0
    #print("FPS %f" % clock.fps())
