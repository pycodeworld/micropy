from pcwlib import LedRgb
from time import sleep_ms

"""
RGB LED 单色渐变示例
"""
led = LedRgb(38, 37, 36)  # R,G,B 引脚 GPIO38, GPIO37, GPIO36
try:
    while True:
        led.color(255, 0, 0)  # 红色
        sleep_ms(1000)
        led.color(0, 255, 0)
        sleep_ms(1000)
        led.color(0, 0, 255)
        sleep_ms(1000)
except KeyboardInterrupt:
    led.deinit()
