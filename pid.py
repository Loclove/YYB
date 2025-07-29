from pyb import millis              
from math import pi, isnan          
class PID:                          
    _kp = _ki = _kd = _integrator = _imax = 0         # 类变量，分别为比例、积分、微分系数，积分累计值，积分最大值
    _last_error = _last_derivative = _last_t = 0       
    _RC = 1/(2 * pi * 20)                              # 微分低通滤波器的时间常数，20Hz 截止频率

    def __init__(self, p=0, i=0, d=0, imax=0):         # 构造函数，初始化 PID 参数
        self._kp = float(p)                            # 设置比例系数
        self._ki = float(i)                            # 设置积分系数
        self._kd = float(d)                            # 设置微分系数
        self._imax = abs(imax)                         # 设置积分最大绝对值，防止积分饱和
        self._last_derivative = float('nan')           # 上一次微分值初始化为 NaN

    def get_pid(self, error, scaler):                  # 计算 PID 输出的主函数
        tnow = millis()                               # 获取当前时间（毫秒）
        dt = tnow - self._last_t                      # 计算距离上次调用的时间差
        output = 0                                    # 初始化输出值
        if self._last_t == 0 or dt > 1000:            # 如果是第一次调用或时间间隔太长
            dt = 0                                    # 时间差置零
            self.reset_I()                            # 重置积分项
        self._last_t = tnow                           # 更新上次调用时间
        delta_time = float(dt) / float(1000)          # 将时间差转换为秒
        output += error * self._kp                    # 计算比例项并加到输出

        if abs(self._kd) > 0 and dt > 0:              # 如果设置了微分系数且时间差大于0
            if isnan(self._last_derivative):          # 如果上次微分为 NaN（首次进入）
                derivative = 0                        # 微分项置零
                self._last_derivative = 0             # 上次微分也置零
            else:
                derivative = (error - self._last_error) / delta_time   # 计算误差变化率
            # 低通滤波处理微分项，减少噪声影响
            derivative = self._last_derivative + \
                         ((delta_time / (self._RC + delta_time)) * \
                          (derivative - self._last_derivative))
            self._last_error = error                  # 保存本次误差
            self._last_derivative = derivative        # 保存本次微分
            output += self._kd * derivative           # 微分项加到输出

        output *= scaler                             # 对输出进行缩放

        if abs(self._ki) > 0 and dt > 0:             # 如果设置了积分系数且时间差大于0
            self._integrator += (error * self._ki) * scaler * delta_time   # 积分项累加
            if self._integrator < -self._imax:       
                self._integrator = -self._imax
            elif self._integrator > self._imax:     
                self._integrator = self._imax
            output += self._integrator               

        return output                              

    def reset_I(self):                              
        self._integrator = 0
        self._last_derivative = float('nan')