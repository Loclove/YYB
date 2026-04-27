#include "shexiangtou.h"

uint8 Image_Use[gao][kuan]={0};        //压缩后的图像（不要使用）
uint8 Image_Bin[gao][kuan]={0};        //二值化的图像
uint8 Image_ZOP[gao][kuan]={0};        //0-1 值的图像(0黑1白)
uint8 Image_PZH[gao][kuan]={0};        //0-1 值的图像(0黑1白)

void camera_adj(void)
{
	suofang();
//	erzhihua();
	ips200_show_gray_image(0, 0 , Image_Bin[0], 100, 80, 100, 80, 0);
//	ips200_show_gray_image(120, 0 , Image_Bin[0], 100, 80, 100, 80, 0);
	
//	saoxian_eight(gao+kuan);
	
	saoxian_eight(150);
	
	qiuzhongxian();
		
}

void suofang(void)//Image_Bin[gao][kuan]={0} -->缩放+封边+二值化（此处的封边有微操）
{
	float x_suo=0,y_suo=0;
	x_suo=(float)MT9V03X_W/kuan;//188/(100-2)
	y_suo=(float)MT9V03X_H/gao ;//120/(80-2)
	
	for(uint8 i=1;i<gao-1;i++)//
	{
		for(uint8 j=1;j<kuan-1;j++)
		{
			Image_Use[i][j]=mt9v03x_image[(int)(i*y_suo)][(int)(x_suo*j)];
			if(Image_Use[i][j]>YUHZI)
			{
				Image_Bin[i][j]=255;
				Image_ZOP[i][j]=1;
			}	
			else
			{
				Image_Bin[i][j]=0;
				Image_ZOP[i][j]=0;
			}
		}
	}
//	ips200_show_float(200, 200 , x_suo, 2, 3);
//	ips200_show_float(200, 216, y_suo, 2, 3);
}
void erzhihua(void)
{
	for(uint8 i=1;i<gao-1;i++)
	{
		for(uint8 j=1;j<kuan-1;j++)
		{
			if(Image_Use[i][j]>YUHZI)
			{
				Image_Bin[i][j]=255;
				Image_ZOP[i][j]=1;
			}	
			else
			{
				Image_Bin[i][j]=0;
				Image_ZOP[i][j]=0;
			}
		}
	}
}

//寻找起点
uint8 r_start_point[2]={kuan,0};          		//右起始点 R_first_point[0]-->x   R_first_point[1]-->y
uint8 l_start_point[2]={0,0};             		//左起始点 L_first_point[0]-->x   L_first_point[1]-->y
uint8 zhongdian=0;
int r_seeds[8][2]={{0,1},{-1,1},{-1,0},{-1,-1},{0,-1},{1,-1},{1,0},{1,1}};//右线八个邻域：      //{-1, 1}{ 0, 1}{ 1, 1}

																								//{-1,-1}{ 0,-1}{1, -1}
																								//{ -1,0}       { 1, 0}//逆时针
int l_seeds[8][2]={{0,1},{1,1},{1,0},{1,-1},{0,-1},{-1,-1},{-1,0},{-1,1}};//左线八个邻域：      	//{ 1,-1}{ 0, 1}{ 1, 1}
int r_count=0,l_count=0;          				//右，左线长度
int r_grow_dir[gao*2]={0},l_grow_dir[gao*2]={0};//右，左线生长方向
int r_index[gao*2][2]={{0}},l_index[gao*2][2]={{0}},Middle[gao*2][2]={{0}};  //右，左线各点索引（右，左线x、y坐标）
int TS1[2]={0},TS2[2]={0};						//暂存变量

uint8 finish_first_scan_l=0,finish_first_scan_r=0,finish_first_scan_ok=0;//左右线首点扫线跳转标志位    
uint8 finish_other_scan_l=0,finish_other_scan_r=0,finish_other_scan_ok=0;//左右线除首点外扫线跳转标志位
uint8 finish_l=0,finish_r=0,finish_ok=0;//结束变量

uint8 jiaodian=0,zanshi=0,zanshi1=0;
uint8 cro_b_l_flag=0,cro_b_r_flag=0;			//左右每扫一个点得越界标志位
uint8 cro_b_l=0,cro_b_r=0;						//左右线越界次数
int cro_b_p_l[10][2]={0},cro_b_p_r[10][2]={0};	//越界点
//uint8 cro_b_re_l=0,cro_b_re_r=0;				//退回几号越界点
int cro_b_line_l[10]={0},cro_b_line_r[10]={0};	//第n次越界时边线长度
int actual_line_l=0,actual_line_r=0;			//使用来计算时实际的左右线长度

void find_first_point(uint8 line)//找八邻域起始点(自动更新起始点)
{
    zhongdian=(r_start_point[0]+l_start_point[0])/2;

	huadian(zhongdian,line,RGB565_CYAN);
    for(uint8 i=zhongdian;i<kuan;i--)
    {
        if(Image_ZOP[line][i]==0 && Image_ZOP[line][i+1]==1)
        {
            l_start_point[0]=i;     //x
            l_start_point[1]=line;  //y
            break;
        }
        if(i==0)
        {
            l_start_point[0]=0;
            l_start_point[1]=line;  //y
			break;
        }
    }

    for(uint8 i=zhongdian;i<kuan;i++)
    {
        if(Image_ZOP[line][i]==0 && Image_ZOP[line][i-1]==1)
        {
            r_start_point[0]=i;     //x
            r_start_point[1]=line;  //y
            break;
        }
        if(i==kuan-1)
        {
            r_start_point[0]=kuan-1;
            r_start_point[1]=line;
			break;
        }
    }
}


//八领域正式开始扫线
void saoxian_eight(int count)//左右线寻线最长长度
{
	finish_first_scan_l=0;finish_first_scan_r=0;finish_first_scan_ok=0;//左右线首点扫线跳转标志位    
	finish_other_scan_l=0;finish_other_scan_r=0;finish_other_scan_ok=0;//左右线除首点外扫线跳转标志位
	finish_l=0;finish_r=0;finish_ok=0;//结束变量
	
	cro_b_l=0;cro_b_r=0;			//越界清零
	jiaodian=0;						//交点清零
	cro_b_l_flag=0;					//越界清零
	cro_b_r_flag=0;					//越界清零
	
    find_first_point(gao-2);
                          
    r_index[0][0]=r_start_point[0];	//将起始点X坐标给r_index[0][0]
    r_index[0][1]=r_start_point[1]; //将起始点Y坐标给r_index[0][1]
	r_count=1; 						//
	                      
    l_index[0][0]=l_start_point[0];	//将起始点X坐标给l_index[0][0]
    l_index[0][1]=l_start_point[1];	//将起始点Y坐标给l_index[0][1]
	l_count=1; 						//
	
	/*首点越界判断*/
	if(l_index[0][0]==0     ){cro_b_l++;cro_b_l_flag=1;cro_b_line_l[cro_b_l]=l_count;}//判断左线首点是否越界
	if(r_index[0][0]==kuan-1){cro_b_r++;cro_b_r_flag=1;cro_b_line_r[cro_b_r]=r_count;}//判断右线首点是否越界

	cro_b_l_flag=0;
	cro_b_r_flag=0;
    for(uint8 j=3;j<8-1 && !finish_first_scan_ok;j++)//首点扫线
    {				
		if(TS1[0]==kuan-1 /*&& TS1[1]>0*/){Image_ZOP[ TS1[1]-1 ][ TS1[0] ] =0;}//右线边缘限制,防止超出范围和丢线时继续向上扫线。2026.4.13怎么说呢，靠！写的真烂，当时太忙了，没有检查，这个地方应该是不需要的，已经做了封边处理，八领域算法不会跑超出图片区域（肯定还有好几处有细节问题，本人已经没有机会在比赛里面解决那些问题了，祝比赛前的你多加加油，别像本人一样稀里糊涂地上赛场。愿我的思路能够帮到你，也愿你能够取得满意度成绩，更愿你能够在比赛中学到比比赛本身重要的东西，加油！！！）
        if(TS2[0]==0      /*&& TS2[1]>0*/){Image_ZOP[ TS2[1]-1 ][ TS2[0] ] =0;}//左线边缘限制,防止超出范围和丢线时继续向上扫线
			
		if(!finish_first_scan_r)
		{
			TS1[0]=r_index[0][0] + r_seeds[j][0];	//x:中心点x坐标移动
			TS1[1]=r_index[0][1] + r_seeds[j][1];	//y:中心点y坐标移动	
			if( Image_ZOP[ TS1[1] ][ TS1[0] ] ==0 )
			{
				r_grow_dir[0]=j;            		//得出右线第一个生长方向
				r_index[1][0]=TS1[0];       		//索引跳到下一个点(x)
				r_index[1][1]=TS1[1];      			//索引跳到下一个点(y)
				r_count++;
				finish_first_scan_r=1;
				if(r_index[1][0]==kuan-1 && r_index[0][0]!=kuan-1)
				{
					cro_b_r++;
					cro_b_r_flag=1;
					cro_b_line_r[cro_b_r]=r_count;
				}
			}
		}
		if(!finish_first_scan_l)
		{
			TS2[0]=l_index[0][0] + l_seeds[j][0];	//x
			TS2[1]=l_index[0][1] + l_seeds[j][1];	//y	
			if( Image_ZOP[ TS2[1] ][ TS2[0] ] ==0 )
			{
				l_grow_dir[0]=j;            		//得出左线第一个生长方向
				l_index[1][0]=TS2[0];       		//索引跳到下一个点(x)
				l_index[1][1]=TS2[1];       		//索引跳到下一个点(y)
				l_count++;
				finish_first_scan_l=1;
				if(l_index[1][0]==0 && l_index[0][0]!=0)
				{
					cro_b_l++;
					cro_b_l_flag=1;
					cro_b_line_l[cro_b_l]=l_count;
				}
			}			
		}
		if(finish_first_scan_l && finish_first_scan_r){finish_first_scan_ok=1;}//首行扫线向第二行扫线完成
    }
    if(finish_first_scan_ok)//首点向第二点跳转完成，进行其余行扫线
    {		
        for(int i=1;i<count && !finish_ok;i++)//寻找左右边线,除去按行扫线(第一次八邻域扫线)得到的点，//i为中心点，j为邻域点
        {
			cro_b_l_flag=0;
			cro_b_r_flag=0;
			finish_other_scan_l=0;finish_other_scan_r=0;finish_other_scan_ok=0;//左右线除首点外扫线跳转标志位
			/*未做封边处理时需要以下处理，实际上本算法在缩放时就已经做好封边出处理*///封边处理     
//				 if(TS1[0]==kuan-1 && TS1[1]>0     && Image_ZOP[ TS1[1]-1 ][ TS1[0]   ] ==1){Image_ZOP[ TS1[1]-1 ][ TS1[0]   ] =0;}//右线右边缘限制,防止超出范围和丢线时继续向上扫线
//			else if(TS1[0]==kuan-2 && TS1[1]>0     && Image_ZOP[ TS1[1]   ][ TS1[0]+1 ] ==1){Image_ZOP[ TS1[1]   ][ TS1[0]+1 ] =0;}//右线右边缘限制,防止超出范围和丢线时继续向上扫线
//			else if(TS1[0]> 0      && TS1[1]==0    && Image_ZOP[ TS1[1]   ][ TS1[0]-1 ] ==1){Image_ZOP[ TS1[1]   ][ TS1[0]-1 ] =0;}//右线上边缘限制,防止超出范围和丢线时继续向左扫线
//			else if(TS1[0]> 0      && TS1[1]==1    && Image_ZOP[ TS1[1]-1 ][ TS1[0]   ] ==1){Image_ZOP[ TS1[1]-1 ][ TS1[0]   ] =0;}//右线上边缘限制,防止超出范围和丢线时继续向左扫线
//			else if(TS1[0]==0      && TS1[1]<gao-1 && Image_ZOP[ TS1[1]+1 ][ TS1[0]   ] ==1){Image_ZOP[ TS1[1]+1 ][ TS1[0]   ] =0;}//右线左边缘限制,防止超出范围和丢线时继续向下扫线
//			else if(TS1[0]==1      && TS1[1]<gao-1 && Image_ZOP[ TS1[1]   ][ TS1[0]-1 ] ==1){Image_ZOP[ TS1[1]   ][ TS1[0]-1 ] =0;}//右线左边缘限制,防止超出范围和丢线时继续向下扫线	 
//
//				 if(TS2[0]==0      && TS2[1]>0     && Image_ZOP[ TS2[1]-1 ][ TS2[0]   ] ==1){Image_ZOP[ TS2[1]-1 ][ TS2[0]   ] =0;}//左线左边缘限制,防止超出范围和丢线时继续向上扫线
//			else if(TS2[0]==1      && TS2[1]>0     && Image_ZOP[ TS2[1]   ][ TS2[0]-1 ] ==1){Image_ZOP[ TS2[1]   ][ TS2[0]-1 ] =0;}//左线左边缘限制,防止超出范围和丢线时继续向上扫线
//			else if(TS2[0]< kuan-1 && TS2[1]==0    && Image_ZOP[ TS2[1]   ][ TS2[0]+1 ] ==1){Image_ZOP[ TS2[1]   ][ TS2[0]+1 ] =0;}//左线上边缘限制,防止超出范围和丢线时继续向右扫线
//			else if(TS2[0]< kuan-1 && TS2[1]==1    && Image_ZOP[ TS2[1]-1 ][ TS2[0]   ] ==1){Image_ZOP[ TS2[1]-1 ][ TS2[0]   ] =0;}//左线上边缘限制,防止超出范围和丢线时继续向右扫线
//			else if(TS2[0]==kuan-1 && TS2[1]<gao-1 && Image_ZOP[ TS2[1]+1 ][ TS2[0]   ] ==1){Image_ZOP[ TS2[1]+1 ][ TS2[0]   ] =0;}//左线右边缘限制,防止超出范围和丢线时继续向下扫线
//			else if(TS2[0]==kuan-2 && TS2[1]<gao-1 && Image_ZOP[ TS2[1]   ][ TS2[0]+1 ] ==1){Image_ZOP[ TS2[1]   ][ TS2[0]+1 ] =0;}//左线右边缘限制,防止超出范围和丢线时继续向下扫线
				
            r_grow_dir[i]=(((r_grow_dir[i-1]-2)>0) ? (r_grow_dir[i-1]-2) : 6+r_grow_dir[i-1]);//根据上一次生长方向确定下一次开始判断的点//grow_R_dir[i-2]表示上一次生长方向
			l_grow_dir[i]=(((l_grow_dir[i-1]-2)>0) ? (l_grow_dir[i-1]-2) : 6+l_grow_dir[i-1]);//根据上一次生长方向确定下一次开始判断的点//grow_R_dir[i-2]表示上一次生长方向
            
			if(TS1[1]>=gao-1)finish_other_scan_r=1;	//扫到最下面一行停止扫线
			if(TS2[1]>=gao-1)finish_other_scan_l=1;	//扫到最下面一行停止扫线
				
			for(uint8 j=r_grow_dir[i],m=l_grow_dir[i],k=0; k<8 && (!finish_other_scan_l || !finish_other_scan_r); j++,m++,k++)//最多循环8次
            {		
				if(!finish_other_scan_r)
				{
					j=j%8;//循环扫
					TS1[0]=r_index[i][0] +  r_seeds[j][0];	//x
					TS1[1]=r_index[i][1] +  r_seeds[j][1];	//y
				
					if( Image_ZOP[ TS1[1] ][ TS1[0] ] == 0 )
					{
						r_grow_dir[i]=j;        //得出生长方向
						r_index[i+1][0]=TS1[0]; //索引跳到下一个点(x)
						r_index[i+1][1]=TS1[1]; //索引跳到下一个点(y)
						r_count++;
						finish_other_scan_r=1;
						//每生长一次方向判断一次是否越界，若越界则记住此次越界的线长
							 if(r_index[i+1][0]==kuan-1 && r_index[i  ][0]!=kuan-1){cro_b_r++;cro_b_r_flag=1;cro_b_line_r[cro_b_r]=r_count;}//右进越界
						else if(r_index[i+1][1]==0      && r_index[i  ][1]!=0     ){cro_b_r++;cro_b_r_flag=1;cro_b_line_r[cro_b_r]=r_count;}//上进越界
						else if(r_index[i+1][0]==0      && r_index[i  ][0]!=0     ){cro_b_r++;cro_b_r_flag=1;cro_b_line_r[cro_b_r]=r_count;}//左进越界
						
//						ips200_draw_point(r_index[i+1][0],r_index[i+1][1], RGB565_RED);
					}					
				}
				if(!finish_other_scan_l)
				{
					m=m%8;//循环扫

					TS2[0]=l_index[i][0] +  l_seeds[m][0];//x
					TS2[1]=l_index[i][1] +  l_seeds[m][1];//y
					
					
					if( Image_ZOP[ TS2[1] ][ TS2[0] ] ==0 )
					{
						l_grow_dir[i]=m;        //得出生长方向
						l_index[i+1][0]=TS2[0]; //索引跳到下一个点(x)
						l_index[i+1][1]=TS2[1]; //索引跳到下一个点(y)
						l_count++;
						finish_other_scan_l=1;
						//每生长一次方向判断一次是否越界，若越界则记住此次越界的线长
							 if(l_index[i+1][0]==0      && l_index[i  ][0]!=0     ){cro_b_l++;cro_b_l_flag=1;cro_b_line_l[cro_b_l]=l_count;}//右进越界
						else if(l_index[i+1][1]==0      && l_index[i  ][1]!=0     ){cro_b_l++;cro_b_l_flag=1;cro_b_line_l[cro_b_l]=l_count;}//上进越界
						else if(l_index[i+1][0]==kuan-1 && l_index[i  ][0]!=kuan-1){cro_b_l++;cro_b_l_flag=1;cro_b_line_l[cro_b_l]=l_count;}//左进越界
						
//						ips200_draw_point(l_index[i+1][0],l_index[i+1][1], RGB565_BLUE);
					}
				}
				if(finish_other_scan_l && finish_other_scan_r)//左右每找完一对点后判断是否相交
				{
					if(																			//此处条件并没有给多
					   (r_index[i  ][0]==l_index[i+1][0] && r_index[i  ][1]==l_index[i+1][1]) ||
					   (r_index[i+1][0]==l_index[i+1][0] && r_index[i+1][1]==l_index[i+1][1]))
					{
						jiaodian=1;//找到交点
//						huadian(l_index[i][0],l_index[i][1],RGB565_GREEN);
					}				
				}
            }			
			if(jiaodian)//相交后找越界来判别实际使用的边线长度
			{
				if(cro_b_l_flag==1)						//相交后左线先越界
				{
					actual_line_l=l_count;				//左线保持不变			
					actual_line_r=cro_b_line_r[cro_b_r];//右线退回之前的越界点
					break;
				}
				else if(cro_b_r_flag==1)				//相交后右线先越界
				{                                       
					actual_line_l=cro_b_line_l[cro_b_l];//左线退回之前的越界点	
					actual_line_r=r_count;              //右线保持不变
					break;
				}
				else if(r_count==148)					//相交后两线不越界，两边保持原长
				{
					actual_line_l=l_count;
					actual_line_r=r_count;
					break;
				}
			}
			else if(r_count==149)						//两线不相交，两边保持原长
			{
				actual_line_l=l_count;
				actual_line_r=r_count;
				break;
			}
        }		
    }
}

float zuo_bili=0,you_bili=0;				//左右线步进比例
float zuo_qianjing=0,you_qianjing=0;		//沿左右线前进长度，左右线平均数
void qiuzhongxian(void)//求中线
{
	int pingjun;
	zuo_qianjing=0;
	you_qianjing=0;
	
	pingjun=(l_count+r_count)/2;	
	zuo_bili=(float)actual_line_l/pingjun;
	you_bili=(float)actual_line_r/pingjun;
	
//	ips200_show_float(0, gao, zuo_bili, 3, 3);
//	ips200_show_float(0, gao+16*1, you_bili, 3, 3);
//	ips200_show_int(0, 80+16*2,pingjun, 5); 
//	ips200_show_int(0, 80+16*3,l_count, 5); 
//	ips200_show_int(0, 80+16*4,r_count, 5); 
	
	for(uint8 i=0;i<pingjun;i++)
	{
		zuo_qianjing+=zuo_bili;
		you_qianjing+=you_bili;
		
//		ips200_show_float(0, gao+16*7, zuo_qianjing, 3, 3);
//		ips200_show_float(0, gao+16*7, you_qianjing, 3, 3);
		
		Middle[i][0]=(l_index[(int)zuo_qianjing][0]+r_index[(int)you_qianjing][0])/2;
		Middle[i][1]=(l_index[(int)zuo_qianjing][1]+r_index[(int)you_qianjing][1])/2;
		
//		ips200_show_int(0, 80+16*5,Middle[i][0], 5); 
//		ips200_show_int(0, 80+16*6,Middle[i][1], 5); 
		
		ips200_draw_point(Middle[i][0],Middle[i][1],RGB565_PURPLE );
		
//		if(Middle[i][0]<239 && Middle[i][0]>0 && Middle[i][1]<359 && Middle[i][1]>0)
//		{
//			ips200_draw_point(Middle[i][0],Middle[i][1],RGB565_PURPLE );
//		}
		
		
	}
	 
	
}
void huadian(uint8 x,uint8 y,const uint16 color)
{
	if(x>0 && x<kuan-1 && y>0 && y<gao-1) 
	{
		ips200_draw_point(x  , y  , color);
		ips200_draw_point(x  , y-1, color);
		ips200_draw_point(x  , y+1, color);
		ips200_draw_point(x-1, y  , color);
		ips200_draw_point(x+1, y  , color);
		ips200_draw_point(x-1, y-1, color);
		ips200_draw_point(x+1, y-1, color);
		ips200_draw_point(x-1, y+1, color);
		ips200_draw_point(x+1, y+1, color);
	}	
	else if(x==0 && y==0)
	{
		ips200_draw_point(x  , y  , color);
		ips200_draw_point(x+1, y  , color);
		ips200_draw_point(x  , y+1, color);
		ips200_draw_point(x+1, y+1, color);
	}
	else if(x==0 && y>0 && y<gao-1)
	{
		ips200_draw_point(x  , y-1, color);
		ips200_draw_point(x+1, y-1, color);		
		ips200_draw_point(x  , y  , color);
		ips200_draw_point(x+1, y  , color);
		ips200_draw_point(x  , y+1, color);
		ips200_draw_point(x+1, y+1, color);
	}
	else if(x==0 && y==gao-1)
	{
		ips200_draw_point(x  , y  , color);
		ips200_draw_point(x+1, y  , color);
		ips200_draw_point(x  , y-1, color);
		ips200_draw_point(x+1, y-1, color);
	}
	else if(x>0 && x<kuan-1 && y==gao-1)
	{
		ips200_draw_point(x-1, y-1, color);
		ips200_draw_point(x  , y-1, color);		
		ips200_draw_point(x+1, y-1, color);
		ips200_draw_point(x-1, y  , color);
		ips200_draw_point(x  , y  , color);
		ips200_draw_point(x+1, y  , color);
	}
	else if(x==kuan-1 && y==gao-1)
	{
		ips200_draw_point(x-1, y-1, color);
		ips200_draw_point(x  , y-1, color);
		ips200_draw_point(x-1, y  , color);
		ips200_draw_point(x  , y  , color);
	}
	else if(x==kuan-1 && y>0 && y<gao-1)
	{
		ips200_draw_point(x-1, y-1, color);
		ips200_draw_point(x  , y-1, color);		
		ips200_draw_point(x-1, y  , color);
		ips200_draw_point(x  , y  , color);
		ips200_draw_point(x-1, y+1, color);
		ips200_draw_point(x  , y+1, color);
	}
	else if(x==kuan-1 && y==0)
	{
		ips200_draw_point(x-1, y  , color);
		ips200_draw_point(x  , y  , color);
		ips200_draw_point(x-1, y+1, color);
		ips200_draw_point(x  , y+1, color);
	}
	if(x>0 && x<kuan-1 && y==0)
	{
		ips200_draw_point(x-1, y  , color);
		ips200_draw_point(x  , y  , color);		
		ips200_draw_point(x+1, y  , color);
		ips200_draw_point(x-1, y+1, color);
		ips200_draw_point(x  , y+1, color);
		ips200_draw_point(x+1, y+1, color);
	}	
}




