
import time
import image
import os, sys, gc
from media.sensor import *
from media.display import *
from media.media import *
import nncase_runtime as nn
import ulab.numpy as np
import random
from libs.PlatTasks import DetectionApp
from libs.PipeLine import PipeLine
from libs.Utils import *
from machine import UART, FPIOA, TOUCH, Pin, Timer
import _thread
import ujson

# 定义ALIGN_UP函数
def ALIGN_UP(x, align):
    return ((x + align - 1) // align) * align

# 定义摄像头通道常量
CAM_CHN_ID_0 = 0
CAM_CHN_ID_1 = 1
CAM_CHN_ID_2 = 2



DISPLAY_WIDTH = ALIGN_UP(800, 16)
DISPLAY_HEIGHT = 480
AI_RGB888P_WIDTH = ALIGN_UP(800, 16)
AI_RGB888P_HEIGHT = 480
Track_WIDTH = 800
Track_HEIGHT = 480

sensor = Sensor()
sensor.reset()

#sensor.set_hmirror(False)
#sensor.set_vflip(False)

sensor.set_framesize(width = DISPLAY_WIDTH, height = DISPLAY_HEIGHT,chn=CAM_CHN_ID_0)
sensor.set_pixformat(Sensor.YUV420SP,chn=CAM_CHN_ID_0)

sensor.set_framesize(width = AI_RGB888P_WIDTH , height = AI_RGB888P_HEIGHT, chn=CAM_CHN_ID_1)
sensor.set_pixformat(Sensor.RGBP888, chn=CAM_CHN_ID_1)

sensor.set_framesize(width=Track_WIDTH, height=Track_HEIGHT,chn=CAM_CHN_ID_2) 
sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_2) 


sensor_bind_info = sensor.bind_info(x = 0, y = 0, chn = CAM_CHN_ID_0)
osd_img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.ARGB8888)
Display.init(Display.ST7701, width=DISPLAY_WIDTH,height=DISPLAY_HEIGHT,osd_num=1, to_ide=True)
sensor._set_chn_fps(chn = CAM_CHN_ID_0, fps = Display.fps())
MediaManager.init()
sensor.run()

osd_img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.ARGB8888)

# 优化按键尺寸以适应中文显示
BTN_WIDTH = 120
BTN_HEIGHT = 45
BTN_MARGIN = 15
BTN_Y_TOP = DISPLAY_HEIGHT - 2 * (BTN_HEIGHT + BTN_MARGIN)  
BTN_Y_BOTTOM = DISPLAY_HEIGHT - BTN_HEIGHT - BTN_MARGIN     

# 使用中文标签，更直观
btn_labels_bottom = ["L最小", "L最大", "A最小", "A最大", "B最小", "B最大"]
btns_bottom = []
for i in range(6):
    x = BTN_MARGIN + i * (BTN_WIDTH + BTN_MARGIN)
    btns_bottom.append({
        "label": btn_labels_bottom[i],
        "rect": (x, BTN_Y_BOTTOM, BTN_WIDTH, BTN_HEIGHT),
        "callback": None  
    })

btns_top = [
    {"label": "+增加", "rect": (BTN_MARGIN, BTN_Y_TOP, BTN_WIDTH, BTN_HEIGHT), "callback": None},
    {"label": "-减少", "rect": (BTN_MARGIN*2 + BTN_WIDTH, BTN_Y_TOP, BTN_WIDTH, BTN_HEIGHT), "callback": None},
    {"label": "图像切换", "rect": (BTN_MARGIN*3 + BTN_WIDTH*2, BTN_Y_TOP, BTN_WIDTH, BTN_HEIGHT), "callback": None},
    {"label": "保存阈值", "rect": (BTN_MARGIN*4 + BTN_WIDTH*3, BTN_Y_TOP, BTN_WIDTH, BTN_HEIGHT), "callback": None}
]

all_btns = btns_top + btns_bottom

def read_threshold():
    """读取阈值"""
    f = open('/data/threshold.txt', 'r')  
    threshold = f.read().strip()  
    f.close()
    return threshold

def write_threshold(value):
    """写入阈值"""
    f = open('/data/threshold.txt', 'w')  
    f.write(str(value))  
    f.close()

#xunji_threshold = [29, 46, 14, 58, 5, 44]
xunji_threshold = read_threshold()
xunji_threshold = eval(xunji_threshold)
threshold_index = 0
def btn_plus_callback():
    global threshold_index
    xunji_threshold[threshold_index] = xunji_threshold[threshold_index] + 2
    print(xunji_threshold)

def btn_minus_callback():
    global threshold_index
    xunji_threshold[threshold_index] = xunji_threshold[threshold_index] - 2
    print(xunji_threshold)

def btn_l_min_callback():
    global threshold_index
    threshold_index = 0
    print("L_min button pressed")


def btn_l_max_callback():
    global threshold_index
    threshold_index = 1
    """L_max按键回调函数"""
    print("L_max button pressed")

def btn_a_min_callback():
    global threshold_index
    threshold_index = 2
    """A_min按键回调函数"""
    print("A_min button pressed")

def btn_a_max_callback():
    global threshold_index
    threshold_index = 3
    """A_max按键回调函数"""
    print("A_max button pressed")

def btn_b_min_callback():
    global threshold_index
    threshold_index = 4
    """B_min按键回调函数"""
    print("B_min button pressed")

def btn_b_max_callback():
    global threshold_index
    threshold_index = 5
    """B_max按键回调函数"""
    print("B_max button pressed")

binary_flag = 0
def btn_switch_image_callback():
    global binary_flag
    binary_flag = not binary_flag
    print("1")

def btn_write_threshold():
    write_threshold(xunji_threshold)

btns_top[0]["callback"] = btn_plus_callback     # 增加按钮
btns_top[1]["callback"] = btn_minus_callback    # 减少按钮
btns_top[2]["callback"] = btn_switch_image_callback    # 切换按钮
btns_top[3]["callback"] = btn_write_threshold    # 更新阈值按钮
btns_bottom[0]["callback"] = btn_l_min_callback # L_min
btns_bottom[1]["callback"] = btn_l_max_callback # L_max
btns_bottom[2]["callback"] = btn_a_min_callback # A_min
btns_bottom[3]["callback"] = btn_a_max_callback # A_max
btns_bottom[4]["callback"] = btn_b_min_callback # B_min
btns_bottom[5]["callback"] = btn_b_max_callback # B_max

def draw_buttons():
    # 绘制下方六个阈值按键
    for i, btn in enumerate(btns_bottom):
        x, y, w, h = btn["rect"]
        
        # 根据当前选中状态设置颜色
        if i == threshold_index:
            # 选中状态：橙色高亮
            bg_color = (255, 140, 0)  # 橙色
            border_color = (255, 215, 0)  # 金色边框
            text_color = (255, 255, 255)  # 白色文字
        else:
            # 未选中状态：蓝色
            bg_color = (70, 130, 180)  # 钢蓝色
            border_color = (255, 255, 255)  # 白色边框
            text_color = (255, 255, 255)  # 白色文字
        
        # 绘制按键背景（填充）
        osd_img.draw_rectangle(x, y, w, h, color=bg_color, thickness=-1)
        # 绘制按键边框
        osd_img.draw_rectangle(x, y, w, h, color=border_color, thickness=3)
        
        # 计算文字居中位置
        text_x = x + (w - len(btn["label"]) * 10) // 2
        text_y = y + (h - 20) // 2
        
        # 绘制按键文字
        osd_img.draw_string_advanced(text_x, text_y, 18, btn["label"], color=text_color)

    # 绘制上方四个功能按键
    for i, btn in enumerate(btns_top):
        x, y, w, h = btn["rect"]
        
        # 根据按键类型设置不同颜色
        if btn["label"] in ["+增加", "-减少"]:
            bg_color = (34, 139, 34)  # 森林绿
            border_color = (0, 255, 0)  # 亮绿色边框
        elif btn["label"] == "图像切换":
            if binary_flag:
                bg_color = (255, 69, 0)  # 红橙色（切换状态）
            else:
                bg_color = (75, 0, 130)  # 靛紫色（正常状态）
            border_color = (255, 255, 255)
        else:  # 保存阈值按键
            bg_color = (220, 20, 60)  # 深红色
            border_color = (255, 192, 203)  # 粉色边框
        
        text_color = (255, 255, 255)  # 统一白色文字
        
        # 绘制按键背景
        osd_img.draw_rectangle(x, y, w, h, color=bg_color, thickness=-1)
        # 绘制按键边框
        osd_img.draw_rectangle(x, y, w, h, color=border_color, thickness=3)
        
        # 计算文字居中位置
        text_x = x + (w - len(btn["label"]) * 9) // 2
        text_y = y + (h - 20) // 2
        
        # 绘制按键文字
        osd_img.draw_string_advanced(text_x, text_y, 18, btn["label"], color=text_color)
    
    Show_threshold(osd_img)

fps = 0
def Show_str(img):
    # 显示FPS，使用更美观的样式
    fps_text = f"帧率: {fps:.1f} FPS"
    
    # 绘制半透明背景
    text_width = len(fps_text) * 12
    img.draw_rectangle(DISPLAY_WIDTH - text_width - 15, 5, text_width + 10, 30, color=(0, 0, 0, 150), thickness=-1)
    
    # 绘制FPS文字
    img.draw_string_advanced(DISPLAY_WIDTH - text_width - 10, 10, 20, fps_text, color=(0, 255, 255))

def Show_help_info(img):
    """显示操作提示信息"""
    help_text = "操作说明: 先选择参数，再点击+/-调节"
    help_y = DISPLAY_HEIGHT - 3 * (BTN_HEIGHT + BTN_MARGIN) - 25
    
    # 绘制提示背景
    img.draw_rectangle(10, help_y, len(help_text) * 10 + 10, 25, color=(25, 25, 112, 100), thickness=-1)
    img.draw_string_advanced(15, help_y + 5, 16, help_text, color=(255, 255, 255))

def Show_threshold(img):
    # 显示当前阈值，使用更美观的格式
    threshold_text = f"当前阈值: L[{xunji_threshold[0]},{xunji_threshold[1]}] A[{xunji_threshold[2]},{xunji_threshold[3]}] B[{xunji_threshold[4]},{xunji_threshold[5]}]"
    
    # 绘制半透明背景
    img.draw_rectangle(5, 5, len(threshold_text) * 12 + 10, 35, color=(0, 0, 0, 128), thickness=-1)
    
    # 绘制阈值文字
    img.draw_string_advanced(10, 10, 24, threshold_text, color=(255, 215, 0))
    
    # 显示当前选中的参数
    param_names = ["L最小", "L最大", "A最小", "A最大", "B最小", "B最大"]
    current_param = f"当前调节: {param_names[threshold_index]} = {xunji_threshold[threshold_index]}"
    
    # 绘制当前参数背景
    img.draw_rectangle(5, 50, len(current_param) * 12 + 10, 30, color=(139, 69, 19, 128), thickness=-1)
    img.draw_string_advanced(10, 55, 20, current_param, color=(255, 255, 255))

clock = time.clock()
tp = TOUCH(0)

while True:
    clock.tick()
    osd_img.clear()

    osd_img = sensor.snapshot(chn=CAM_CHN_ID_2)


    points = tp.read()

    if points: 
        x, y = points[0].x, points[0].y

        # 检查按键点击
        for btn in all_btns:
            bx, by, bw, bh = btn["rect"]
            if (bx <= x <= bx + bw) and (by <= y <= by + bh):
                
                # 绘制按键按下效果 - 使用亮黄色高亮
                osd_img.draw_rectangle(bx, by, bw, bh, color=(255, 255, 0), thickness=-1)
                osd_img.draw_rectangle(bx, by, bw, bh, color=(255, 0, 0), thickness=4)
                
                # 计算文字居中位置
                text_x = bx + (bw - len(btn["label"]) * 9) // 2
                text_y = by + (bh - 20) // 2
                
                # 绘制按下状态的文字（黑色）
                osd_img.draw_string_advanced(text_x, text_y, 18, btn["label"], color=(0, 0, 0))

                # 执行按键回调
                if btn["callback"]:
                    btn["callback"]()

                time.sleep_ms(150)  # 减少延迟，提高响应性
                break
    if binary_flag == 1:
        osd_img.binary([xunji_threshold])
    
    # 绘制所有界面元素
    draw_buttons()
    Show_str(osd_img)
    Show_help_info(osd_img)
    Display.show_image(osd_img)

    time.sleep_ms(1)  
    fps = clock.fps()

