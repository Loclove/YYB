# Untitled - By: 姚彦博 - Thu Jul 17 2025

import sensor
import time
from pyb import UART

uart = UART(3, 115200)
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQQVGA)
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

clock = time.clock()

thresholds = [(0, 20, -10, 10, -10, 10)]
last_error_bottom = 0
integral_bottom = 0
last_error_theta = 0
integral_bottom_theta = 0  # Initialize integral for x-coordinate
def pid_control(error, last_error, integral, Kp, Ki, Kd):
    """PID control function."""
    integral += error
    derivative = error - last_error
    output = Kp * error + Ki * integral + Kd * derivative
    last_error = error
    return output, last_error, integral

def get_endpoint(line):
    """Calculate the endpoints of a line."""
    x1, y1, x2, y2 = line.line()
    if y1>y2:
        return(x1,y1)
    else:
        return(x2,y2)

def theta_change(theta):
    if theta > 90:
        theta = theta - 180
        return theta
    else:
        return theta

while True:
    clock.tick()
    img = sensor.snapshot()
    img.binary(thresholds)  # Apply binary thresholding to the image
    img.open(1)
    img.gaussian(1)#边缘光滑没有噪点
    line = img.get_regression([(100, 100)], robust=True)  # Get line regression 优化取样
    if line and line.magnitude() > 10:  # 表示直线的长度大于10像素,滤去光线产生的伪信号
        img.draw_line(line.line(), color=(255, 0, 0), thickness=2)  # Draw the detected line
        uart.write("Line detected: {}\n".format(line.line()))  # Send line data over UART
        bottom_x,bottom_y = get_endpoint(line)  # Get the endpoint of the line
        error_x= bottom_x - img.width() // 2  # Calculate the error from the center of the image
        output_bottom, last_error_bottom, integral_bottom = pid_control(error_x, last_error_bottom, integral_bottom, 0.6, 0.01, 0.1)  # PID control for x-coordinate
        output_theta, last_error_theta, integral_bottom_theta = pid_control(theta_change(line.theta()), last_error_theta, integral_bottom_theta, 0.52, 0, 0.15)
        output = output_bottom + output_theta


        if(output > 100):
           output=100
        elif(output < -100):
           output=-100
        output = int(output)  # Convert output to integer
        uart.write(bytes(128+ output))  # Send control output over UART
    else:
        uart.write(bytes([0]))  # Send no line detected message over UART
    print(clock.fps())
