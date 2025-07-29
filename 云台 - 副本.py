
import sensor, image, time

sensor.reset()  

sensor.set_pixformat(sensor.RGB565)  
sensor.set_framesize(sensor.QQVGA)   
sensor.set_contrast(3)               
# 设置对比度+3（增强明暗对比，提升识别率）
# *************************** 图像镜像设置 ***************************
 # （根据摄像头物理安装方向调整，不需要可注释）
sensor.set_vflip(True)   # 垂直翻转：适用于摄像头倒置安装的情况
sensor.set_hmirror(True) # 水平镜像：适用于需要镜像显示的场景
# *************************** 数字模板配置 ***************************
 num_quantity = 8    
# 定义要识别的数字范围（1-8）
num_model = []       
# 创建空列表存储模板图像
# 加载预存数字模板（需提前准备1.pgm~8.pgm文件）
for n in range(1, num_quantity+1):
 # 加载PGM格式模板（建议使用白底黑字40像素高度图片）
num_model.append(image.Image(str(n) + '.pgm'))  # 将模板图像存入列表
# *************************** 性能监测配置 ***************************
 clock = time.clock()  # 创建帧率计算时钟对象
# *************************** 图像缓冲区配置 ***************************
 # 分配模板匹配专用缓冲区（优化处理速度）
img_to_matching = sensor.alloc_extra_fb(35, 45, sensor.GRAYSCALE)  # 35x45灰度缓冲
区
# 说明：该缓冲区用于存储缩放后的待匹配区域图像
# *************************** 算法参数设置 ***************************
 threshold = (0, 70)  # 灰度阈值范围：0-70（用于检测深色数字区域）
scale = 1            
# 图像缩放比例初始化值
# *************************** 主循环处理逻辑 ***************************
 while(True):
 # 【阶段1】帧率计算与图像采集
clock.tick()  # 开始帧计时（必须在循环开头调用）
img = sensor.snapshot()  # 捕获一帧RGB565彩色图像（160x120像素）
# 【阶段2】创建灰度处理副本
img_gray = img.to_grayscale(copy=True)  # 生成灰度副本（保持原图不变）
# 注意：所有图像处理操作在灰度副本上进行以保证算法稳定性
# 【阶段3】色块检测
blobs = img_gray.find_blobs([threshold])  # 在灰度图像中查找符合阈值的色块
    
    # 【阶段4】候选区域处理
    if blobs:  # 如果检测到有效色块
        # 遍历所有检测到的色块（blobs对象包含多个blob）
        for blob in blobs:
            # 色块有效性过滤条件（排除噪声干扰）
            if blob.pixels() > 50 and 100 > blob.h() > 10 and blob.w() > 3:
                # 【步骤4.1】在彩色图像上绘制检测框
                # 绘制绿色预备框（比实际区域大4像素）
                img.draw_rectangle(
                    blob.x()-2, blob.y()-2,  # 起点坐标（左上角）
                    blob.w()+4, blob.h()+4,   # 框体尺寸（宽度+高度）
                    color=(0, 255, 0)        # 颜色：纯绿色
                )
                # 在色块左上角显示当前缩放比例（调试信息，白色文字）
                img.draw_string(blob[0], blob[1], str(round(scale, 2)), color=
 (255, 255, 255))
                
                # 【步骤4.2】计算缩放比例
                scale = 40 / blob.h()  # 根据色块高度计算缩放比例（模板高度为40像素）
                
                # 【步骤4.3】提取待匹配区域
                img_to_matching.draw_image(
                    img_gray,  # 源图像（使用灰度副本保证处理一致性）
                    0, 0,     # 目标位置（缓冲区左上角）
                    roi=(  # 源图像感兴趣区域（Region of Interest）
                        blob.x()-2,      # x起点（左扩2像素）
                        blob.y()-2,      # y起点（上扩2像素）
                        blob.w()+4,      # 宽度（左右各扩2像素）
                        blob.h()+4       # 高度（上下各扩2像素）
                    ),
                    x_scale=scale,  # 水平缩放比例
                    y_scale=scale   # 垂直缩放比例
                )
                
                # 【阶段5】模板匹配识别
                # 遍历所有数字模板进行匹配
                for n in range(0, num_quantity):
                    # 执行模板匹配（核心识别函数）
                    r = img_to_matching.find_template(
                        num_model[n],  # 当前数字模板（n对应数字1-8）
                        0.7,           # 相似度阈值（0.0-1.0，越大匹配越严格）
                        step=2,        # 搜索步长（2表示隔行扫描，加快速度）
                        search=image.SEARCH_EX  # 搜索模式：穷举搜索（精度最高）
                    )
                    
                    if r:  # 如果匹配结果有效（相似度超过阈值）
                        # 【步骤5.1】在彩色图像上绘制橙色确认框
                        img.draw_rectangle(
                            blob[0:4],          # 矩形参数（x,y,w,h）
                            color=(255, 100, 0) # 橙色边框（BGR格式）
                        )
                        # 【步骤5.2】显示识别结果（核心修改点）
                        img.draw_string(
                            blob[0], blob[1],   # 显示位置（色块左上角）
                            str(n+1),          # 显示内容（识别到的数字）
                            scale=5,            # 字体放大倍数（原始5倍）
                            color=(255, 0, 0)   # 字体颜色：纯红色（BGR格式）
                            )
                             # 【新增】输出识别结果：数字ID,X坐标,Y坐标
                            print("DETECT: num={}, x={}, y={}".format(n+1, 
                            blob.cx(), blob.cy()))
                             # 【阶段6】显示帧率信息
                            # 在画面左上角显示当前帧率（白色文字）
                            img.draw_string(0, 0, str(round(clock.fps(), 2)), color=(255, 255, 255))
                             # *************************** 注意事项 ***************************
                             """
                             1. 必须准备数字模板：在存储卡根目录放置1.pgm~8.pgm文件
                            2. 模板建议规格：白底黑字、高度40像素、PGM格式
                            3. 实际显示效果：- 绿色框：初步检测区域- 橙色框：成功匹配区域- 红色数字：识别结果- 白色文字：帧率信息
                            4. 性能参数：QQVGA分辨率下典型帧率15-30fps（取决于处理复杂度）
                            5. 调试技巧：可通过调整threshold阈值和scale计算优化识别效果
                            """