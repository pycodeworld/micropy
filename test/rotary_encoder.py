from pcwlib import RotaryEncoder
from machine import PWM

led = PWM(7)
led.duty(0)
light = 0  # 保存上次亮度


def brightness(count):
    global light
    light = max(0, min(count, 1023))
    led.duty(light)


def toggle(t):
    led.duty(light - led.duty())  # 反转亮度


encoder = RotaryEncoder(4, 5, 6, brightness, toggle)
