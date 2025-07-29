#https://space.bilibili.com/438224522
#b站up主 洛基的魔方

DIV_TIME=15 #细分多少次
light=(25, 100, -126, -13, -128, 127) #绿色激光点阈值


import sensor
import time
import image
import pyb
from machine import UART

#只能用于openmv H7Plus 更便宜的版本会报堆栈溢出
#openmv需放在距离矩形90cm-100cm处运行效果最佳
#若距离无法满足要求 手动修改下面两个不同位置的判断
#if r.magnitude()>50000: 中50000的数值
#该数值对应的是寻找的矩形的最小面积



def find_max(blobs):
    max_size=0
    for blob in blobs:
        if blob.pixels() > max_size:
            max_blob=blob
            max_size = blob.pixels()
    return max_blob


def draw_rect(rect,color):
    img.draw_line(rect[0][0], rect[0][1], rect[1][0], rect[1][1], color)
    img.draw_line(rect[1][0], rect[1][1], rect[2][0], rect[2][1], color)
    img.draw_line(rect[2][0], rect[2][1], rect[3][0], rect[3][1], color)
    img.draw_line(rect[3][0], rect[3][1], rect[0][0], rect[0][1], color)
    return


sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_vflip(True)
sensor.set_hmirror(True)
sensor.set_framesize(sensor.QVGA)
sensor.set_brightness(-3)
sensor.set_contrast(3)
sensor.set_auto_exposure(False,exposure_us=120000)

clock = time.clock()

flag=0   #goto作用
first_rect_corners=[]
outside_rect_corners=[]
temp_size=0
min_id = 0
while flag ==0:
    clock.tick()
    img = sensor.snapshot()
    corner=[]
    if True:
        rect_time=0
        for r in img.find_rects(threshold=100):
            if r.magnitude()>50000:
                first_rect_corners=r.corners()
                #img.draw_rectangle(r.rect(), color=(255, 255, 255))
                temp_size=r.magnitude()
                print(r.magnitude())
                for p in r.corners():
                    #img.draw_circle(p[0], p[1], 5, color=(255, 255, 255))
                    corner.append(p[0])
                    corner.append(p[1])
                print(corner)
                flag=1
                break

flag=0
corner=[]

while flag==0:
    img = sensor.snapshot()
    for r in img.find_rects(threshold=100):
        if r.magnitude()>50000:
            temp_corner=r.corners()
            min_value = 1000
            for i in range(4):
             #寻找第二个矩形框 两个分别来自不同矩形的点 距离最小值有限定
             #以免寻找到同一个矩形上
                temp = abs(temp_corner[0][0] - first_rect_corners[i][0])
                if temp < min_value:
                    min_id = i
                    min_value = temp
            if min_value>2:
                outside_rect_corners=r.corners()
                print(r.magnitude())
                for p in r.corners():
                    corner.append(p[0])
                    corner.append(p[1])
                print(corner)
                flag=1
                break

#由于寻找矩形返回的两个矩形点集可能顺序不一样 在此矫正
if True:
    mid_corner=[]
    for i in range(4):
        temp=i+min_id
        if temp>3:
            temp-=4
        temp1=[]
        for j in range(2):
            temp1.append(int((first_rect_corners[temp][j]+outside_rect_corners[i][j])/2))
        mid_corner.append(temp1)

    print(mid_corner)

sensor.set_pixformat(sensor.RGB565)
#mid_corner=[[86,144],[147,172],[184,87],[126,63]]

dif=[]
flag=0
mid_pos = [[[0 for _ in range(2)] for _ in range(DIV_TIME)] for _ in range(4)]
for xy in range(2):
    dif = [0] * 4
    dif[0] = mid_corner[1][xy] - mid_corner[0][xy]
    dif[1] = mid_corner[2][xy] - mid_corner[1][xy]
    dif[2] = mid_corner[3][xy] - mid_corner[2][xy]
    dif[3] = mid_corner[0][xy] - mid_corner[3][xy]
    if dif[0]>dif[1]:
        flag=1
    temp = DIV_TIME

    for num in range(DIV_TIME):
        for id in range(4):
            temp = DIV_TIME
            if flag==1:
                if id%2==0:
                    temp = DIV_TIME-5
            div=dif[id]/temp
            if num >=temp:
                mid_pos[id][num][xy] = -1
            elif num == 0:
                mid_pos[id][num][xy] = int(mid_corner[id][xy])
            else:
                mid_pos[id][num][xy] = int(mid_corner[id][xy] + div * (num))

id=0
num=0
error=5
while True:
    img = sensor.snapshot()
    draw_rect(first_rect_corners,(255,0,0))
    draw_rect(outside_rect_corners,(0,255,100))
    blobs = img.find_blobs([light],merge=True)
    max_blob=[]
    if blobs:
        max_blob=find_max(blobs)
        img.draw_cross(max_blob[5], max_blob[6],[0,0,255])
        if(abs(mid_pos[id][num][0]-max_blob[5])<error and abs(mid_pos[id][num][1]-max_blob[6])<error):
            num+=1
            if num >DIV_TIME-1 or mid_pos[id][num][0]==-1 :
                id+=1
                num=0
                if id==4:
                    id=0
        #uart.write(str(mid_pos[id][num][0]-max_blob[5])+" "+str(mid_pos[id][num][1]-max_blob[6])+"#\n")
    #draw_rect(mid_corner,(255,0,0))
    #上方代码是画出去中值的矩形 可删去注释
    for i in mid_pos:
        for dot in i:
            if dot[0]==-1:
                continue
            #下面的代码是画出细分的点 可以删掉注释
            #img.draw_circle(int(dot[0]), int(dot[1]), 1, color=(255, 255, 255))
    img.draw_circle(mid_pos[id][num][0], mid_pos[id][num][1], 3, color=(0,255,255))






