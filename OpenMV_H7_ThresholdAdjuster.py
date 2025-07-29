# OpenMV H7 阈值调节器
# 适用于OpenMV H7摄像头模块
# 基于你的K230代码改写

import sensor, image, time, lcd
import gc, pyb
import json

# ==================== 初始化设置 ====================

# 摄像头初始化
sensor.reset()                      # 重置摄像头
sensor.set_pixformat(sensor.RGB565) # 设置像素格式为RGB565 (或sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)   # 设置分辨率QVGA (320x240)
sensor.skip_frames(time = 2000)     # 等待设置生效
sensor.set_auto_gain(False)         # 关闭自动增益
sensor.set_auto_whitebal(False)     # 关闭自动白平衡
clock = time.clock()                # 创建时钟对象

# LCD显示初始化
lcd.init()
lcd.clear(color=(0, 0, 0))

# ==================== 界面参数配置 ====================

# 显示尺寸
DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240

# 按键布局参数
BTN_WIDTH = 48
BTN_HEIGHT = 28
BTN_MARGIN = 6
BTN_Y_TOP = DISPLAY_HEIGHT - 2 * (BTN_HEIGHT + BTN_MARGIN) - 10
BTN_Y_BOTTOM = DISPLAY_HEIGHT - BTN_HEIGHT - BTN_MARGIN

# 按键标签
btn_labels_bottom = ["L-", "L+", "A-", "A+", "B-", "B+"]
btn_labels_top = ["+", "-", "SW", "SAVE"]

# ==================== 数据管理 ====================

# 默认LAB阈值 (适用于红色物体检测)
default_threshold = [30, 100, 15, 127, 15, 127]  # (L_min, L_max, A_min, A_max, B_min, B_max)

def load_threshold():
    """从文件加载阈值"""
    try:
        with open("threshold.json", "r") as f:
            data = json.load(f)
            return data.get("threshold", default_threshold)
    except:
        print("使用默认阈值")
        return default_threshold

def save_threshold(threshold):
    """保存阈值到文件"""
    try:
        data = {"threshold": threshold}
        with open("threshold.json", "w") as f:
            json.dump(data, f)
        print("阈值已保存:", threshold)
        return True
    except Exception as e:
        print("保存失败:", e)
        return False

# ==================== 全局变量 ====================

current_threshold = load_threshold()
selected_param = 0  # 当前选中的参数索引 (0-5)
binary_mode = False
fps_counter = 0
save_feedback = 0  # 保存反馈计时器

# ==================== 按键控制系统 ====================

class Button:
    def __init__(self, x, y, w, h, label, action=None):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.label = label
        self.action = action
        self.pressed = False
    
    def draw(self, img, selected=False):
        """绘制按键"""
        # 选择颜色
        if selected:
            bg_color = (255, 140, 0)    # 橙色高亮
            border_color = (255, 215, 0)
        elif self.pressed:
            bg_color = (255, 255, 0)    # 按下时黄色
            border_color = (255, 0, 0)
        else:
            if self.label in ["+", "-"]:
                bg_color = (34, 139, 34)    # 绿色
            elif self.label == "SW":
                bg_color = (255, 69, 0) if binary_mode else (75, 0, 130)
            elif self.label == "SAVE":
                bg_color = (220, 20, 60)    # 深红色
            else:
                bg_color = (70, 130, 180)   # 钢蓝色
            border_color = (255, 255, 255)
        
        # 绘制按键背景
        img.draw_rectangle(self.x, self.y, self.w, self.h, 
                         color=bg_color, fill=True)
        
        # 绘制边框
        img.draw_rectangle(self.x, self.y, self.w, self.h, 
                         color=border_color, thickness=2)
        
        # 绘制文字 (居中)
        text_len = len(self.label)
        text_x = self.x + (self.w - text_len * 6) // 2
        text_y = self.y + (self.h - 8) // 2
        img.draw_string(text_x, text_y, self.label, 
                       color=(255, 255, 255), scale=1)
    
    def is_pressed(self, x, y):
        """检查点击位置是否在按键内"""
        return (self.x <= x <= self.x + self.w and 
                self.y <= y <= self.y + self.h)

# 创建按键对象
buttons = []

# 底部参数选择按键
for i in range(6):
    x = BTN_MARGIN + i * (BTN_WIDTH + BTN_MARGIN)
    if x + BTN_WIDTH <= DISPLAY_WIDTH:
        btn = Button(x, BTN_Y_BOTTOM, BTN_WIDTH, BTN_HEIGHT, 
                    btn_labels_bottom[i])
        buttons.append(btn)

# 顶部功能按键
for i in range(4):
    x = BTN_MARGIN + i * (BTN_WIDTH + BTN_MARGIN + 8)
    if x + BTN_WIDTH <= DISPLAY_WIDTH:
        btn = Button(x, BTN_Y_TOP, BTN_WIDTH, BTN_HEIGHT, 
                    btn_labels_top[i])
        buttons.append(btn)

# ==================== 控制函数 ====================

def adjust_threshold(param_index, delta):
    """调节阈值参数"""
    global current_threshold
    
    current_threshold[param_index] += delta
    
    # 限制参数范围
    if param_index in [0, 1]:  # L通道: 0-100
        current_threshold[param_index] = max(0, min(100, current_threshold[param_index]))
    else:  # A, B通道: -128 到 127
        current_threshold[param_index] = max(-128, min(127, current_threshold[param_index]))
    
    print("阈值更新:", current_threshold)

def toggle_binary_mode():
    """切换二值化显示模式"""
    global binary_mode
    binary_mode = not binary_mode
    print("二值化模式:", "开启" if binary_mode else "关闭")

def save_current_threshold():
    """保存当前阈值"""
    global save_feedback
    if save_threshold(current_threshold):
        save_feedback = 30  # 显示保存成功30帧
    else:
        save_feedback = -30  # 显示保存失败30帧

# ==================== 界面绘制 ====================

def draw_info_panel(img):
    """绘制信息面板"""
    # 阈值信息背景
    img.draw_rectangle(2, 2, DISPLAY_WIDTH-4, 45, color=(0, 0, 0), fill=True)
    img.draw_rectangle(2, 2, DISPLAY_WIDTH-4, 45, color=(255, 255, 255), thickness=1)
    
    # 当前阈值显示
    threshold_text = "LAB: [%d,%d] [%d,%d] [%d,%d]" % tuple(current_threshold)
    img.draw_string(5, 5, threshold_text, color=(255, 215, 0), scale=1)
    
    # 当前选中参数
    param_names = ["L_min", "L_max", "A_min", "A_max", "B_min", "B_max"]
    current_text = "Editing: %s = %d" % (param_names[selected_param], 
                                        current_threshold[selected_param])
    img.draw_string(5, 18, current_text, color=(0, 255, 255), scale=1)
    
    # FPS显示
    fps_text = "FPS: %.1f" % fps_counter
    img.draw_string(5, 31, fps_text, color=(0, 255, 0), scale=1)
    
    # 保存反馈
    if save_feedback > 0:
        img.draw_string(200, 31, "SAVED!", color=(0, 255, 0), scale=1)
        save_feedback -= 1
    elif save_feedback < 0:
        img.draw_string(200, 31, "ERROR!", color=(255, 0, 0), scale=1)
        save_feedback += 1

def draw_help_info(img):
    """绘制操作说明"""
    help_y = BTN_Y_TOP - 20
    img.draw_rectangle(2, help_y, DISPLAY_WIDTH-4, 15, color=(25, 25, 112), fill=True)
    img.draw_string(5, help_y + 3, "Select param, then +/- to adjust", 
                   color=(255, 255, 255), scale=1)

def draw_all_buttons(img):
    """绘制所有按键"""
    for i, btn in enumerate(buttons):
        # 底部按键 (参数选择)
        if i < 6:
            selected = (i == selected_param)
            btn.draw(img, selected)
        # 顶部按键 (功能)
        else:
            btn.draw(img)

# ==================== 图像处理 ====================

def process_image(img):
    """处理图像"""
    if binary_mode:
        # 应用LAB颜色阈值分割
        blobs = img.find_blobs([current_threshold], 
                              pixels_threshold=100, 
                              area_threshold=100, 
                              merge=True)
        
        # 绘制检测结果
        for blob in blobs:
            # 绘制边界框
            img.draw_rectangle(blob.rect(), color=(255, 0, 0), thickness=2)
            
            # 绘制中心点
            img.draw_cross(blob.cx(), blob.cy(), size=8, color=(0, 255, 0), thickness=2)
            
            # 显示面积信息
            img.draw_string(blob.x(), blob.y()-10, "Area:%d" % blob.pixels(), 
                          color=(255, 255, 0), scale=1)

# ==================== 输入处理 ====================

def handle_button_input():
    """处理按键输入 (使用OpenMV的按键或串口)"""
    global selected_param
    
    # 检查板载按键 (如果存在)
    try:
        if pyb.Switch().value():
            # 按键按下时切换参数
            selected_param = (selected_param + 1) % 6
            pyb.delay(200)  # 防抖动
            return True
    except:
        pass
    
    # 串口命令控制
    try:
        if pyb.USB_VCP().any():
            cmd = pyb.USB_VCP().read().decode().strip()
            
            # 参数选择命令
            if cmd in ['0', '1', '2', '3', '4', '5']:
                selected_param = int(cmd)
                print(f"选择参数 {selected_param}")
                
            # 调节命令
            elif cmd == '+':
                adjust_threshold(selected_param, 2)
                
            elif cmd == '-':
                adjust_threshold(selected_param, -2)
                
            # 功能命令
            elif cmd == 's':
                toggle_binary_mode()
                
            elif cmd == 'w':
                save_current_threshold()
                
            elif cmd == 'r':
                # 重置为默认值
                current_threshold[:] = default_threshold[:]
                print("重置为默认阈值")
                
            elif cmd == 'h':
                # 显示帮助
                print("=== OpenMV 阈值调节器 ===")
                print("命令:")
                print("0-5: 选择参数")
                print("+/-: 增减数值") 
                print("s: 切换显示模式")
                print("w: 保存阈值")
                print("r: 重置阈值")
                print("h: 显示帮助")
                
            return True
    except:
        pass
    
    return False

# ==================== 主程序循环 ====================

def main():
    """主程序"""
    global fps_counter
    
    print("=== OpenMV 阈值调节器启动 ===")
    print("发送 'h' 查看控制帮助")
    
    while True:
        clock.tick()
        
        # 获取图像
        img = sensor.snapshot()
        
        # 处理图像
        process_image(img)
        
        # 绘制界面
        draw_info_panel(img)
        draw_help_info(img)
        draw_all_buttons(img)
        
        # 处理输入
        handle_button_input()
        
        # 显示图像
        lcd.display(img)
        
        # 更新FPS
        fps_counter = clock.fps()
        
        # 内存管理
        if fps_counter < 15:
            gc.collect()

# ==================== 启动程序 ====================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print("程序异常:", e)
    finally:
        print("程序结束")
