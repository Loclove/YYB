#ifndef SHEXIANGTOUY_H
#define SHEXIANGTOUY_H

#include "zf_common_headfile.h"

#define kuan		100
#define gao			80
#define YUHZI		240
#define QIANZHAN	35

extern uint8 Image_Use[gao][kuan];        //压缩后的图像（不要使用）
extern uint8 Image_Bin[gao][kuan];        //二值化的图像
extern uint8 Image_ZOP[gao][kuan];        //0-1 值的图像(0白1黑)
extern uint8 Image_PZH[gao][kuan];        //0-1 值的图像(0白1黑)
extern uint8 Image_P00[gao][kuan];        //0-1 值的图像(0白1黑)

extern uint8 zuo[gao],you[gao],zhongxian[gao];

extern uint8 cro_b_l,cro_b_r,jiaodian,zanshi,zanshi1;//左右线越界次数
extern int r_count,l_count,actual_line_r,actual_line_l;


	
void camera_adj(void);
void suofang(void);
void erzhihua(void);
void jiangzao(void);
void huadian(uint8 x,uint8 y,const uint16 color);
uint8 shu_zhong_point(uint8 hang,uint8 xianshi);
void shu_zhong_point_xianshi(uint8 canshu,uint8 zuo_dian,uint8 you_dian,uint8 hang);
uint8 jiyi_saoxian(uint8 last_zhongdian,uint8 hang);

void ImagePerspective_Init(void);
void jiaohuan(void);

void find_first_point(uint8 line);
void saoxian_eight(int count);
void qiuzhongxian(void);

	
#endif

