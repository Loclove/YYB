# OpenMV 阈值调节界面
# 基于K230代码改写的OpenMV版本

import sensor, image, time, lcd, ustruct
import gc
import ujson

# 初始化摄像头
sensor.reset()
sensor.set_pixformat(sensor.RGB565)    # 设置像素格式为RGB565
sensor.set_framesize(sensor.QVGA)      # 设置分辨率为QVGA (320x240)
sensor.skip_frames(time = 2000)        # 跳过前面的帧，等待设置生效
sensor.set_auto_gain(False)            # 关闭自动增益
sensor.set_auto_whitebal(False)        # 关闭自动白平衡

# 初始化LCD显示
lcd.init()
lcd.clear()

# 显示参数
DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240

# 按键参数优化
BTN_WIDTH = 45
BTN_HEIGHT = 25
BTN_MARGIN = 8
BTN_Y_TOP = DISPLAY_HEIGHT - 2 * (BTN_HEIGHT + BTN_MARGIN)
BTN_Y_BOTTOM = DISPLAY_HEIGHT - BTN_HEIGHT - BTN_MARGIN

# 中文标签（OpenMV支持的字符）
btn_labels_bottom = ["L_min", "L_max", "A_min", "A_max", "B_min", "B_max"]
btns_bottom = []

# 创建底部按键
for i in range(6):
    x = BTN_MARGIN + i * (BTN_WIDTH + BTN_MARGIN)
    if x + BTN_WIDTH > DISPLAY_WIDTH:  # 确保按键不超出屏幕
        break
    btns_bottom.append({
        "label": btn_labels_bottom[i],
        "rect": (x, BTN_Y_BOTTOM, BTN_WIDTH, BTN_HEIGHT),
        "callback": None
    })

# 创建顶部按键
btns_top = [
    {"label": "+", "rect": (BTN_MARGIN, BTN_Y_TOP, BTN_WIDTH, BTN_HEIGHT), "callback": None},
    {"label": "-", "rect": (BTN_MARGIN*2 + BTN_WIDTH, BTN_Y_TOP, BTN_WIDTH, BTN_HEIGHT), "callback": None},
    {"label": "SW", "rect": (BTN_MARGIN*3 + BTN_WIDTH*2, BTN_Y_TOP, BTN_WIDTH, BTN_HEIGHT), "callback": None},
    {"label": "SAV", "rect": (BTN_MARGIN*4 + BTN_WIDTH*3, BTN_Y_TOP, BTN_WIDTH, BTN_HEIGHT), "callback": None}
]

all_btns = btns_top + btns_bottom

# 文件操作函数
def read_threshold():
    """读取阈值文件"""
    try:
        with open('threshold.txt', 'r') as f:
            threshold_str = f.read().strip()
            return eval(threshold_str)
    except:
        print("使用默认阈值")
        return [30, 100, -64, -8, -32, 32]  # 默认红色阈值

def write_threshold(threshold):
    """保存阈值到文件"""
    try:
        with open('threshold.txt', 'w') as f:
            f.write(str(threshold))
        print("阈值已保存:", threshold)
    except Exception as e:
        print("保存失败:", e)

# 初始化阈值和状态变量
xunji_threshold = read_threshold()
threshold_index = 0
binary_flag = False
fps = 0

# 按键回调函数
def btn_plus_callback():
    """增加当前参数"""
    global threshold_index
    xunji_threshold[threshold_index] += 2
    # 限制范围
    if threshold_index in [0, 1]:  # L通道 0-100
        xunji_threshold[threshold_index] = min(100, xunji_threshold[threshold_index])
    else:  # A,B通道 -128到127
        xunji_threshold[threshold_index] = min(127, xunji_threshold[threshold_index])
    print("阈值:", xunji_threshold)

def btn_minus_callback():
    """减少当前参数"""
    global threshold_index
    xunji_threshold[threshold_index] -= 2
    # 限制范围
    if threshold_index in [0, 1]:  # L通道 0-100
        xunji_threshold[threshold_index] = max(0, xunji_threshold[threshold_index])
    else:  # A,B通道 -128到127
        xunji_threshold[threshold_index] = max(-128, xunji_threshold[threshold_index])
    print("阈值:", xunji_threshold)

def btn_switch_image_callback():
    """切换显示模式"""
    global binary_flag
    binary_flag = not binary_flag
    print("二值化模式:", binary_flag)

def btn_write_threshold_callback():
    """保存阈值"""
    write_threshold(xunji_threshold)

# 参数选择回调函数
def select_param(index):
    """选择要调节的参数"""
    global threshold_index
    threshold_index = index
    param_names = ["L_min", "L_max", "A_min", "A_max", "B_min", "B_max"]
    print(f"选择参数: {param_names[index]}")

# 绑定回调函数
btns_top[0]["callback"] = btn_plus_callback
btns_top[1]["callback"] = btn_minus_callback
btns_top[2]["callback"] = btn_switch_image_callback
btns_top[3]["callback"] = btn_write_threshold_callback

for i, btn in enumerate(btns_bottom):
    btn["callback"] = lambda idx=i: select_param(idx)

# 触摸检测函数（OpenMV模拟触摸，可用按键或串口代替）
def check_touch():
    """检查触摸输入（这里用键盘模拟）"""
    # OpenMV没有内置触摸屏，这里可以用串口或其他方式替代
    # 返回模拟的触摸坐标，实际使用时需要根据具体硬件修改
    return None

# 绘制函数
def draw_buttons(img):
    """绘制所有按键"""
    # 绘制底部参数选择按键
    for i, btn in enumerate(btns_bottom):
        x, y, w, h = btn["rect"]
        
        # 根据选中状态设置颜色
        if i == threshold_index:
            # 选中状态：橙色
            bg_color = (255, 140, 0)
            border_color = (255, 215, 0)
        else:
            # 未选中状态：蓝色
            bg_color = (70, 130, 180)
            border_color = (255, 255, 255)
        
        # 绘制按键
        img.draw_rectangle(x, y, w, h, color=bg_color, fill=True)
        img.draw_rectangle(x, y, w, h, color=border_color, thickness=2)
        
        # 绘制文字（居中）
        text_x = x + (w - len(btn["label"]) * 6) // 2
        text_y = y + (h - 8) // 2
        img.draw_string(text_x, text_y, btn["label"], color=(255, 255, 255), scale=1)
    
    # 绘制顶部功能按键
    for i, btn in enumerate(btns_top):
        x, y, w, h = btn["rect"]
        
        # 根据按键类型设置颜色
        if btn["label"] in ["+", "-"]:
            bg_color = (34, 139, 34)  # 绿色
        elif btn["label"] == "SW":
            bg_color = (255, 69, 0) if binary_flag else (75, 0, 130)  # 切换状态颜色
        else:  # 保存按键
            bg_color = (220, 20, 60)  # 红色
        
        # 绘制按键
        img.draw_rectangle(x, y, w, h, color=bg_color, fill=True)
        img.draw_rectangle(x, y, w, h, color=(255, 255, 255), thickness=2)
        
        # 绘制文字
        text_x = x + (w - len(btn["label"]) * 6) // 2
        text_y = y + (h - 8) // 2
        img.draw_string(text_x, text_y, btn["label"], color=(255, 255, 255), scale=1)

def show_threshold_info(img):
    """显示阈值信息"""
    # 显示当前阈值
    threshold_text = "T:L%d-%d A%d-%d B%d-%d" % (
        xunji_threshold[0], xunji_threshold[1],
        xunji_threshold[2], xunji_threshold[3],
        xunji_threshold[4], xunji_threshold[5]
    )
    
    # 绘制背景
    img.draw_rectangle(2, 2, len(threshold_text) * 6 + 4, 12, 
                      color=(0, 0, 0), fill=True)
    
    # 绘制阈值文字
    img.draw_string(4, 4, threshold_text, color=(255, 215, 0), scale=1)
    
    # 显示当前选中参数
    param_names = ["L_min", "L_max", "A_min", "A_max", "B_min", "B_max"]
    current_text = "Now: %s=%d" % (param_names[threshold_index], 
                                   xunji_threshold[threshold_index])
    
    # 绘制当前参数背景
    img.draw_rectangle(2, 16, len(current_text) * 6 + 4, 12,
                      color=(139, 69, 19), fill=True)
    img.draw_string(4, 18, current_text, color=(255, 255, 255), scale=1)

def show_fps(img):
    """显示帧率"""
    fps_text = "FPS: %.1f" % fps
    text_width = len(fps_text) * 6
    
    # 右上角显示FPS
    img.draw_rectangle(DISPLAY_WIDTH - text_width - 4, 2, text_width + 2, 12,
                      color=(0, 0, 0), fill=True)
    img.draw_string(DISPLAY_WIDTH - text_width - 2, 4, fps_text, 
                   color=(0, 255, 255), scale=1)

def show_help(img):
    """显示帮助信息"""
    help_text = "Select param, then +/-"
    help_y = DISPLAY_HEIGHT - 3 * (BTN_HEIGHT + BTN_MARGIN) - 15
    
    img.draw_rectangle(2, help_y, len(help_text) * 6 + 4, 12,
                      color=(25, 25, 112), fill=True)
    img.draw_string(4, help_y + 2, help_text, color=(255, 255, 255), scale=1)

# 主循环
clock = time.clock()
print("OpenMV阈值调节器启动...")
print("控制说明:")
print("- 底部按键选择参数")
print("- +/- 调节数值")
print("- SW 切换显示模式")
print("- SAV 保存阈值")

while True:
    clock.tick()
    
    # 获取图像
    img = sensor.snapshot()
    
    # 应用图像处理
    if binary_flag:
        # 应用LAB阈值分割
        blobs = img.find_blobs([xunji_threshold], pixels_threshold=200, area_threshold=200)
        
        # 绘制检测到的色块
        for blob in blobs:
            img.draw_rectangle(blob.rect(), color=(255, 0, 0), thickness=2)
            img.draw_cross(blob.cx(), blob.cy(), size=5, color=(0, 255, 0))
    
    # 绘制界面元素
    draw_buttons(img)
    show_threshold_info(img)
    show_fps(img)
    show_help(img)
    
    # 显示图像
    lcd.display(img)
    
    # 检查输入（这里可以添加按键或串口控制）
    # 由于OpenMV没有触摸屏，可以通过以下方式控制：
    # 1. 使用GPIO按键
    # 2. 使用串口命令
    # 3. 使用IDE的串口终端输入命令
    
    # 简单的串口控制示例（可选）
    try:
        import pyb
        if pyb.USB_VCP().any():
            cmd = pyb.USB_VCP().read().decode().strip()
            if cmd == '0': select_param(0)
            elif cmd == '1': select_param(1)
            elif cmd == '2': select_param(2)
            elif cmd == '3': select_param(3)
            elif cmd == '4': select_param(4)
            elif cmd == '5': select_param(5)
            elif cmd == '+': btn_plus_callback()
            elif cmd == '-': btn_minus_callback()
            elif cmd == 's': btn_switch_image_callback()
            elif cmd == 'w': btn_write_threshold_callback()
    except:
        pass
    
    # 内存管理
    if clock.fps() < 10:  # 如果帧率过低，清理内存
        gc.collect()
    
    # 更新FPS
    fps = clock.fps()

print("程序结束")
