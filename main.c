/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "tim.h"
#include "gpio.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "OLED.h"
#include "Key.h"
#include "Encoder.h"
#include "Motor.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
uint16_t i;
int16_t PWML,PWMR;
uint8_t KeyNum;
int16_t Speed;
int16_t Location;

float TargetL=13,ActualL,OutL,TargetR=13,ActualR,OutR;
float Kp=0.1,Ki=0.05,Kd;
float ErrorL0,ErrorL1,ErrorIntL,ErrorR0,ErrorR1,ErrorIntR;
/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_TIM1_Init();
  MX_TIM3_Init();
  MX_TIM4_Init();
  MX_TIM8_Init();
  /* USER CODE BEGIN 2 */
	OLED_Init();
	HAL_TIM_Base_Start_IT(&htim3);
	HAL_TIM_Encoder_Start(&htim1,TIM_CHANNEL_1|TIM_CHANNEL_2);	//ÓÒÂÖ±àÂëÆ÷
	HAL_TIM_Encoder_Start(&htim8,TIM_CHANNEL_1|TIM_CHANNEL_2);	//×óÂÖ±àÂëÆ÷
	HAL_TIM_PWM_Start(&htim4,TIM_CHANNEL_1);				//×óÂÖPWM
	HAL_TIM_PWM_Start(&htim4,TIM_CHANNEL_2);				//ÓÒÂÖPWM
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
		//OLED_ShowString(L_X1,H_Y1,"Hello!",OLED_8X16);
		OLED_Printf(0,0,OLED_8X16,"Speed Control");
		OLED_Printf(0,16,OLED_8X16,"Tar:%+04.0f",TargetL);
		OLED_Printf(0,32,OLED_8X16,"Act:%+04.0f",ActualL);
		OLED_Printf(0,48,OLED_8X16,"Out:%+04.0f",OutL);
		OLED_Printf(64,16,OLED_8X16,"Tar:%+04.0f",TargetR);
		OLED_Printf(64,32,OLED_8X16,"Act:%+04.0f",ActualR);
		OLED_Printf(64,48,OLED_8X16,"Out:%+04.0f",OutR);
		//OLED_Printf(64,16,OLED_8X16,"Out:%+04.0f",Out);
		OLED_Update();
		//Ñ²Ïß²¿·Ö
			if(M==1)
			{
					Motor_SetLPWM(OutL);
					Motor_SetRPWM(OutR);
			}
			if(L1==1)
			{
					Motor_SetLPWM(OutL-5);
					Motor_SetRPWM(OutR+5);
			}
			if(L2==1)
			{
					Motor_SetLPWM(OutL-10);
					Motor_SetRPWM(OutR+10);
			}			
			if(L3==1)
			{
					Motor_SetLPWM(OutL-15);
					Motor_SetRPWM(OutR+15);
			}
			if(R1==1)
			{
					Motor_SetLPWM(OutL+5);
					Motor_SetRPWM(OutR-5);
			}
			if(R2==1)
			{
					Motor_SetLPWM(OutL+10);
					Motor_SetRPWM(OutR-10);
			}
			if(R3==1)
			{
					Motor_SetLPWM(OutL+15);
					Motor_SetRPWM(OutR-15);
			}
		//µç»ú±Õ»·¿ØÖÆ
//		KeyNum=Key_GetNum();
//		if(KeyNum==1)
//		{
//				TargetL+=10;
//				//if(PWML>100){PWML=100;}
//		}
//		if(KeyNum==2)
//		{
//				TargetL-=10;
//				//if(PWML<-100){PWML=-100;}
//		}		
//		if(KeyNum==3)
//		{
//				TargetR+=10;
//		}
//		if(KeyNum==4)
//		{
//				TargetR-=10;
//		}
		//Motor_SetLPWM(PWML);
		}
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLM = 4;
  RCC_OscInitStruct.PLL.PLLN = 168;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
  RCC_OscInitStruct.PLL.PLLQ = 4;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5) != HAL_OK)
  {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
		static int count;
		if(htim==&htim3)
		{
				Key_Tick();
				count++;
				if(count>=40)
				{
						count=0;
						
						ActualL=Encoder_GetL();
						ActualR=Encoder_GetR();
					
						ErrorL1=ErrorL0;
						ErrorL0=TargetL-ActualL;
						ErrorR1=ErrorR0;
						ErrorR0=TargetR-ActualR;
			
						ErrorIntL+=ErrorL0;
						ErrorIntR+=ErrorR0;
		
						OutL=Kp*ErrorL0+Ki*ErrorIntL+Kd*(ErrorL0-ErrorL1);
						OutR=Kp*ErrorR0+Ki*ErrorIntR+Kd*(ErrorR0-ErrorR1);
					
						if(OutL>100){OutL=100;}
						if(OutL<-100){OutL=-100;}
						if(OutR>100){OutR=100;}
						if(OutR<-100){OutR=-100;}
						
//						Motor_SetLPWM(OutL);
//						Motor_SetRPWM(OutR);
				}
		}
}

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
