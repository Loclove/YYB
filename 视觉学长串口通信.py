# This work is licensed under the MIT license.
# Copyright (c) 2013-2023 OpenMV LLC. All rights reserved.
# https://github.com/openmv/openmv/blob/master/LICENSE
#
# Hello World Example
#
# Welcome to the OpenMV IDE! Click on the green run arrow button below to run the script!

import sensor,ustruct
import time
from pyb import UART

thressholds =(28, 92, -35, -56, -105, 87)

uart=UART(1,115200)
uart.init(115200,bits=8,parity=None,stop=1)  # Initialize UART1 with 115200 baud rate.

def ouruart(y):
    global uart;
    data=ustrust.pack("<bbbb",
                 0xC2,
                 0xC1,
                 y,
                 0xb5)
    uart.write(data);# Send data over UART.
    print('发送')

def inuart(flag):
    while uart.any():
        a=uart.read(1)
        a = ustruct.unpack('B', a)
        a=hex(a)
        if a==hex(0xc2) and uart.any():
            b=uart.read(1)
            b = ustruct.unpack('B', b)
            b=hex(b)
            if b==hex(0x21):
                c=uart.read(1)
                c = ustruct.unpack('B', c)
                c=hex(c)
                c=int(c)
                if uart.any():
                    d=uart.read(1)
                    d = ustruct.unpack('B', d)
                    d=hex(d)
                    if d==hex(0xb5):
                        flag=c
                        e=uart.read()
                        return flag
sensor.reset()  # Reset and initialize the sensor.
sensor.set_pixformat(sensor.RGB565)  # Set pixel format to RGB565 (or GRAYSCALE)
sensor.set_framesize(sensor.VGA)
sensor.skip_frames(time=2000)  # Wait for settings take effect.
clock = time.clock()  # Create a clock object to track the FPS.
sensor.set_auto_gain(False)  # Disable auto gain control.
sensor.set_auto_whitebal(False)  # Disable auto white balance.
clock=time.clock()

flag=0x00
while True:
    clock.tick()  # Update the FPS clock.
    img = sensor.snapshot()  # Take a picture and return the image.
    for blob in img.find_blobs([thressholds], pixels_threshold=200, area_threshold=200, merge=True):
       radio=blob.w()/blob.h()  # Calculate the aspect ratio of the blob.
       if radio>=0.5 and radio<=1.5:
           img.draw_rectangle(blob.rect())
           img.draw_cross(blob.cx(), blob.cy())
           outuart(blob.cy())  # Send the y-coordinate of the blob center over UART.
           print("坐标",blob.cy())
    if uart.any():
        flag_m=inuart(flag)
        print('接收', flag_m)
    print(clock.fps())  # Print the FPS.
