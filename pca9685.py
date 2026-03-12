"""
PCA9685 MicroPython 通用驱动
支持：180°角度舵机、360°连续旋转舵机、普通PWM输出
适配所有主流舵机品牌（SG90、MG996R、FS90R 等）
"""

import time
from pcwi2c import *

# ==================== 寄存器地址定义 ====================
PCA9685_MODE1 = 0x00      # 模式寄存器1
PCA9685_MODE2 = 0x01      # 模式寄存器2
PCA9685_SUBADDR1 = 0x02      # I2C从地址1
PCA9685_SUBADDR2 = 0x03      # I2C从地址2
PCA9685_SUBADDR3 = 0x04      # I2C从地址3
PCA9685_ALLCALLADDR = 0x05      # 广播地址寄存器
PCA9685_LED0_ON_L = 0x06      # LED0开启计数值低8位
PCA9685_LED0_ON_H = 0x07      # LED0开启计数值高8位
PCA9685_LED0_OFF_L = 0x08      # LED0关闭计数值低8位
PCA9685_LED0_OFF_H = 0x09      # LED0关闭计数值高8位
PCA9685_ALL_LED_ON_L = 0xFA      # 所有通道开启计数值低8位
PCA9685_ALL_LED_ON_H = 0xFB      # 所有通道开启计数值高8位
PCA9685_ALL_LED_OFF_L = 0xFC      # 所有通道关闭计数值低8位
PCA9685_ALL_LED_OFF_H = 0xFD      # 所有通道关闭计数值高8位
PCA9685_PRE_SCALE = 0xFE      # 预分频寄存器（频率设置）
PCA9685_TESTMODE = 0xFF      # 测试模式寄存器

# ==================== MODE1寄存器位定义 ====================
PCA9685_MODE1_RESTART = 0x80      # 重新启动
PCA9685_MODE1_EXTCLK = 0x40      # 使用外部时钟
PCA9685_MODE1_AI = 0x20      # 自动递增（强烈建议启用）
PCA9685_MODE1_SLEEP = 0x10      # 睡眠模式
PCA9685_MODE1_SUB1 = 0x08      # 响应子地址1
PCA9685_MODE1_SUB2 = 0x04      # 响应子地址2
PCA9685_MODE1_SUB3 = 0x02      # 响应子地址3
PCA9685_MODE1_ALLCALL = 0x01      # 响应广播地址

# ==================== MODE2寄存器位定义 ====================
PCA9685_MODE2_OUTNE_0 = 0x01      # 输出使能配置位0
PCA9685_MODE2_OUTNE_1 = 0x02      # 输出使能配置位1
PCA9685_MODE2_OUTDRV = 0x04      # 输出模式：0=开漏，1=推挽
PCA9685_MODE2_OCH = 0x08      # 输出停止时状态
PCA9685_MODE2_INVRT = 0x10      # 输出极性反转

# ==================== 常量定义 ====================
PCA9685_OSC_CLOCK = 25000000   # 内部晶振频率 25MHz
PCA9685_MAX_VALUE = 4095       # 12位PWM最大值
PCA9685_PRESCALE_MIN = 3          # 最小预分频值
PCA9685_PRESCALE_MAX = 255        # 最大预分频值
PCA9685_FREQ_MIN = 24         # 最小频率（24Hz）
PCA9685_FREQ_MAX = 1526       # 最大频率（约1526Hz）

# 舵机通用常量
SERVO_DEFAULT_FREQ = 50         # 舵机标准频率50Hz
# 90/180/270°舵机脉冲范围（ms）
SERVO_MIN_PULSE = 0.5
SERVO_MAX_PULSE = 2.5
# 360°舵机默认校准值（可根据实际舵机调整）
SERVO_360_DEFAULT_STOP = 307        # 默认停止点
SERVO_360_DEFAULT_RANGE = 30        # 默认转速范围

 
class PCA9685(I2Controller):
    """
    初始化PCA9685
    参数:
        i2c: machine.I2C对象
        address: PCA9685的I2C地址（默认0x40）
        calibrate: 是否启用频率校准（推荐True）
    """
    def __init__(self, i2c, address=0x40, calibrate=True):

        self.i2c = i2c
        self.addr = address
        self.calibrate = calibrate

        # 舵机校准参数缓存（按通道存储）
        self.servo_calibrates = {'atype': '360'}

        # 检查设备是否存在
        if not self._ping():
            raise ValueError(f"PCA9685 not found at address 0x{address:02X}")

        # 复位到默认状态
        self.reset()

    def _ping(self):
        """检查设备是否存在"""
        try:
            self.i2c.writeto(self.addr, b'')
            return True
        except:
            return False

    def _write_reg(self, reg, value):
        """写入单个字节到寄存器"""
        self.i2c.writeto_mem(self.addr, reg, bytes([value]))

    def _write_regs(self, reg, data):
        """写入多个字节到寄存器（自动递增模式）"""
        self.i2c.writeto_mem(self.addr, reg, bytes(data))

    def _read_reg(self, reg):
        """读取单个字节寄存器"""
        return self.i2c.readfrom_mem(self.addr, reg, 1)[0]

    def _read_regs(self, reg, len=1):
        """读取多个字节寄存器"""
        return self.i2c.readfrom_mem(self.addr, reg, len)

    def reset(self):
        """复位设备到默认状态"""
        # 启用自动递增，退出睡眠
        self._write_reg(PCA9685_MODE1, PCA9685_MODE1_AI)
        # 推挽输出，输出停止时保持电平
        self._write_reg(PCA9685_MODE2, PCA9685_MODE2_OUTDRV |
                        PCA9685_MODE2_OCH)
        time.sleep_ms(10)
        # 关闭所有通道
        self.all_off()

    def sleep(self, enable=True):
        """设置睡眠模式（修改频率前必须启用）"""
        mode = self._read_reg(PCA9685_MODE1)
        if enable:
            mode |= PCA9685_MODE1_SLEEP
        else:
            mode &= ~PCA9685_MODE1_SLEEP
        self._write_reg(PCA9685_MODE1, mode)
        time.sleep_us(500)

    def restart(self):
        """重新启动（从睡眠中唤醒）"""
        mode = self._read_reg(PCA9685_MODE1)
        mode &= ~PCA9685_MODE1_SLEEP
        mode |= PCA9685_MODE1_RESTART
        self._write_reg(PCA9685_MODE1, mode)
        time.sleep_us(500)
        mode &= ~PCA9685_MODE1_RESTART
        self._write_reg(PCA9685_MODE1, mode)

    def freq(self, freq=None):
        """获取/设置PWM频率"""
        if freq is None:
            prescale = self._read_reg(PCA9685_PRE_SCALE)
            return PCA9685_OSC_CLOCK / 4096 / (prescale + 1)

        if freq < PCA9685_FREQ_MIN or freq > PCA9685_FREQ_MAX:
            raise ValueError(
                f"频率必须在 {PCA9685_FREQ_MIN}~{PCA9685_FREQ_MAX}Hz 之间")

        # 计算预分频值
        prescale = int(PCA9685_OSC_CLOCK / 4096 / freq + 0.5) - 1

        # 频率校准
        if self.calibrate:
            prescale = int(prescale * 0.915)

        # 限制范围
        prescale = max(PCA9685_PRESCALE_MIN, min(PCA9685_PRESCALE_MAX, prescale))

        # 应用设置
        self.sleep(True)
        self._write_reg(PCA9685_PRE_SCALE, prescale)
        self.restart()


    def _duty(self, channel, off_value, on_value=0):
        """原始PWM设置（直接设置ON/OFF计数值）"""
        if channel < 0 or channel > 15:
            raise ValueError("通道号必须在0~15之间")

        on_value = max(0, min(PCA9685_MAX_VALUE, on_value))
        off_value = max(0, min(PCA9685_MAX_VALUE, off_value))

        reg_base = PCA9685_LED0_ON_L + 4 * channel
        self._write_regs(reg_base, [
            on_value & 0xFF,
            (on_value >> 8) & 0xFF,
            off_value & 0xFF,
            (off_value >> 8) & 0xFF
        ])

    def duty(self, channel, value=None):
        if value is not None:
            return self._duty(channel, value)
            
        # 读取当前占空比
        reg_base = PCA9685_LED0_ON_L + 4 * channel
        off_l = self._read_reg(reg_base + 2)
        off_h = self._read_reg(reg_base + 3)
        return (off_h << 8) | off_l

    def all_duty(self, value):
        """同时设置所有通道占空比"""
        if value < 0 or value > PCA9685_MAX_VALUE:
            raise ValueError(f"值须在0~{PCA9685_MAX_VALUE}之间")

        self._write_regs(PCA9685_ALL_LED_ON_L, [0x00, 0x00])
        self._write_regs(PCA9685_ALL_LED_OFF_L, [
            value & 0xFF,
            (value >> 8) & 0x0F
        ])

    def all_off(self):
        """关闭所有通道"""
        self._write_regs(PCA9685_ALL_LED_ON_L, [0x00, 0x00])
        self._write_regs(PCA9685_ALL_LED_OFF_L, [0x00, 0x00])


    def deinit(self):
        self.all_off()

 
    def __repr__(self):
        try:
            f = self.freq()
            return f"PCA9685(addr=0x{self.addr:02X}, freq={f:.1f}Hz)"
        except:
            return f"PCA9685(addr=0x{self.addr:02X})"
