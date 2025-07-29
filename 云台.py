# Untitled - By: 姚彦博 - Wed Jul 16 2025

import sensor,time,math,json
from pyb import UART

def init_camera():  # Initialize the camera sensor
    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.QQVGA)
    sensor.skip_frames(time=2000)
    sensor.set_auto_gain(False)
    sensor.set_auto_whitebal(False)
    return sensor

def init_uart():  # Initialize the UART communication
    uart = UART(3, 115200)
    return uart

def find_max_blob(blobs):  # Find the largest blob in the list of blobs
    max_blob = None
    max_area = 0
    for blob in blobs:
        if blob.area() > max_area:
            max_area = blob.area()
            max_blob = blob
    return max_blob

def pack_data(x,y):
    x=max(0, min(x, 160))
    y=max(0, min(y, 120))
    data=bytearray([0x2c,7,x,y,3,4,0x5b])
    return data

def main():
    sensor=init_camera()
    uart=init_uart()
    clock=time.clock()  # Create a clock object to manage the frame rate
    threshold=(15, 75, 20, 90, 0, 60)
    while True:
        clock.tick()  # Update the clock
        img = sensor.snapshot()  # Capture an image
        img.lens_corr(1.8)  # Apply lens correction


        blobs = img.find_blobs([threshold], pixels_threshold=100, area_threshold=100, merge=True)  # Find blobs in the image

        if blobs:
            max_blob = find_max_blob(blobs)  # Find the largest blob
            if max_blob:
                img.draw_rectangle(max_blob.rect(),color=(255,0,0),thickness=2)
                img.draw_cross(max_blob.cx(), max_blob.cy(), color=(255,0,0), thickness=2)

                try:
                    data=pack_data(max_blob.cx(), max_blob.cy())
                    uart.write(data)  # Send the data over UART
                    print("Sent data:", data)
                except Exception as e:
                    print("UART write error:",e)
        else:
            try:
               default_data=bytearray([0x2c,7,80,60,3,4,0x5b])
               uart.write(default_data)  # Send default data if no blobs found
               print("Sent default data",default_data)
            except Exception as e:
                print("UART write error:",e)

if __name__ == "__main__":
    main()  # Start the main function

