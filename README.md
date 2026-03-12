# micropy

#### 项目描述
基于micropython的智能硬件库，接口参考文档：https://www.pycodeworld.com/pysmart/doc/pysmart.html。


### 目录结构

| 文件/目录 | 描述 |
| --------- | ----------- |
| pcwlib.py | 基础封装包括: Pin中断, PWM封装, Servo舵机（连续/角度），Motor马达，RotaryEncoder 旋转编码器，ToyStick 摇杆，蜂鸣器，超声传感器，TM1637 数码显示屏，ST7789屏幕，I2C |
| pca9685.py | PCA9685 16通道PWM驱动 |
| lx16.py | LX-16 舵机驱动 |
| song | 蜂鸣器音乐库 | 
| test | 测试代码 |

### I2C 控制器

ESP32 <---> PWM \
ESP32 <---> I2C <---> PWM

1. 直连控制
```
from pcwlib import Servo360
servo = Servo360(9)
servo.forward(50) 
```

2. I2C控制
```
from pcwlib import Servo360
from machine import 

i2c = I2C(0, scl=Pin(10), sda=Pin(9), freq=1000)
controller = PCA9685(i2c, address=0x40)
servo = Servo360(I2CDev(controller, 0))
servo.forward(50) 
```

### 项目依赖
1. pcwlib.py 依赖lvgl库。项目：https://github.com/lvgl-micropython/lvgl_micropython


### 帮助文档
1. 前往https://www.pycodeworld.com/pysmart/doc/pysmart.html 了解固件烧录方法。
2. 案例及作品展示：https://www.pycodeworld.com/pysmart/works。 
