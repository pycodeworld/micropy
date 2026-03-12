from machine import Pin, PWM, ADC, SPI
from time import sleep_ms, sleep_us, ticks_ms, ticks_us, ticks_diff
import math

import lcd_bus
import st7789
import lvgl
import gc
import task_handler

def version():
    return "1.0.3"


class IRQDev:
    def __init__(self, pin, handler=None, trigger=Pin.IRQ_FALLING, interval=500):
        self.handler = handler
        self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.handler = handler
        self.pin.irq(trigger=trigger, handler=self.callback)
        self.interval = interval  # 触发时间间隔
        self.last_time = 0

    def callback(self, pin):
        time = ticks_ms()
        if time - self.last_time < self.interval:
            return
        self.last_time = time
        if self.handler:
            self.handler(pin.value())

    def value(self):
        return self.pin.value()

    def deinit(self):
        """释放资源"""
        self.pin.deinit()


class PWMDev:
    def __init__(self, dev, freq=1000):
        if isinstance(dev, int):
            self.pin = Pin(dev, Pin.OUT)
            self.pwm = PWM(self.pin, freq=freq)
        else:
            self.pwm = dev
        self.off()  # 初始状态为关闭
        self._percent = 0

    # deprecated
    def set_percent(self, value=100):
        return self.percent(value)
    
    def percent(self, value=100):
        value = max(0, min(100, value))
        self._percent = value
        duty = int((value / 100) * 1023)
        self.pwm.duty(duty)
        return self._percent

    def value(self):
        return self._percent

    def on(self):
        return self.percent(100)

    def off(self):
        return self.percent(0)

    def fade(self, start=0, end=100, step=1, interval=10, duration=0):
        if start <= 0 or end >= 100 or start > end:
            print(f"渐变起始参数错误")
            return 
        if step < 0 or step >= end - start:
            print(f"渐变步长参数错误")
            return
        i = 0
        _percent = start
        _start = 0
        _end = end - start
        _run_time = 0  # 运行时间
        while _run_time < duration or duration <= 0:
            _percent = _start + i
            _percent %= 2 * _end
            _percent = _percent if _percent <= _end else 2 * _end - _percent
            self.percent(_start + _percent)
            i += step
            _run_time += interval
            sleep_ms(interval)

    def deinit(self):
        """释放PWM资源"""
        self.pwm.deinit()


class LedRgb:
    def __init__(self, red, green, blue):
        self.red = PWMDev(red)
        self.green = PWMDev(green)
        self.blue = PWMDev(blue)

    def set_color(self, red, green, blue):
        return self.color(red, green, blue)
    
    def color(self, red=100, green=100, blue=100):
        self.red.percent(int(red / 255 * 100))
        self.green.percent(int(green / 255 * 100))
        self.blue.percent(int(blue / 255 * 100))

    def on(self):
        self.set_color(255, 255, 255)

    def off(self):
        self.set_color(0, 0, 0)

    def deinit(self):
        self.red.deinit()
        self.green.deinit()
        self.blue.deinit()


class Servo360(PWMDev):
    def __init__(self, pin=-1):
        super().__init__(pin, 50)
        self._stop_speed = 0
        self._speed = 0

    # deprecated
    def set_calibrate(self, stop_speed=0):
        self.calibrate(stop_speed)
    
    def calibrate(self, stop_speed=0):
        """设置360°舵机的校准参数,停止点转速，不同舵机参数不同，需要根据实际情况调整"""
        self._stop_speed = stop_speed

    def _us_to_duty(self, us):
        """微秒转换为duty值"""
        return int(us / 20000 * 65535)

    def stop(self):
        self.speed(0)

    # deprecated
    def set_speed(self, value=100):
        self.speed(value)
    
    def speed(self, value=None):
        if value is None:
            return self._speed
        value = self._stop_speed + value
        value = max(-100, min(100, value))
        self._speed = value
        us = 1500 + (value / 100) * 1000
        self.pwm.duty_u16(self._us_to_duty(us))

    def forward(self, speed=100):
        """顺时针旋转 (0-100速度)"""
        self.speed(speed)

    def backward(self, speed=100):
        """逆时针旋转 (0-100速度)"""
        self.speed(-speed)

    def deinit(self):
        """释放资源"""
        self.pwm.deinit()


class Servo(PWMDev):
    def __init__(self, pin=-1, atype=180):
        super().__init__(pin, 50)
        self.atype = atype
        self._angle = 0

    def _us_to_duty(self, us):
        return int(us / 20000 * 65535)

    # deprecated
    def set_angle(self, angle=0):
        return self.angle(angle)

    def angle(self, value=None):
        if value is None:
            return self._angle
        self._angle = max(0, min(self.atype, value))
        us = 500 + self._angle * 2000 / self.atype
        self.pwm.duty_u16(self._us_to_duty(us))


class Motor:
    def __init__(self, in1, in2):
        self.in1 = PWMDev(in1)
        self.in2 = PWMDev(in2)
        self._speed = 0

    # deprecated
    def set_speed(self, speed):
        self.speed(speed)
    
    def speed(self, value=None):
        if value is None:
            return self._speed
        value = max(0, min(100, value))
        self._speed = value
        duty = int(value * 65535 / 100)
        self.in1.pwm.duty_u16(duty if value > 0 else 0)
        self.in2.pwm.duty_u16(duty if value < 0 else 0)

    def forward(self, speed=50):
        self.speed(speed)

    def backward(self, speed=50):
        self.speed(-speed)

    def coast(self):
        self.speed(0)

    def brake(self):
        self.in1.pwm.duty_u16(65535)
        self.in2.pwm.duty_u16(65535)

    def deinit(self):
        self.in1.deinit()
        self.in2.deinit()


class RotaryEncoder:
    def __init__(self, clk, dt, sw, counter_handler, sw_handler):
        self.clk = IRQDev(clk, self.encoder_callback, Pin.IRQ_RISING | Pin.IRQ_FALLING, 1)
        self.dt = IRQDev(dt, self.encoder_callback, Pin.IRQ_RISING | Pin.IRQ_FALLING, 1)
        self.sw = IRQDev(sw, sw_handler)
        self.counter_handler = counter_handler

        self.states = [
            [0, -1, 1, 0],
            [1, 0, 0, -1],
            [-1, 0, 0, 1],
            [0, 1, -1, 0],
        ]
        # 计数器变量
        self.counter = 0
        self.last_state = 0

    def encoder_callback(self, pin):
        current_state = (self.clk.value() << 1) | self.dt.value()
        change = self.states[self.last_state][current_state]
        self.counter += change
        self.last_state = current_state
        if self.counter_handler:
            self.counter_handler(self.counter)

    def deinit(self):
        self.clk.deinit()
        self.dt.deinit()
        self.sw.deinit()


class ToyStick:
    def __init__(self, x, y, sw, sw_handler):
        self.xpin = ADC(Pin(x))
        self.ypin = ADC(Pin(y))
        self.sw = IRQDev(sw, sw_handler)

        self.x_center = 0
        self.y_center = 0
        # 校准中心位置
        for i in range(10):
            self.x_center += self.xpin.read()
            self.y_center += self.ypin.read()
            sleep_ms(10)
        self.x_center //= 10
        self.y_center //= 10

    def percent(self):
        x, y = 0, 0
        if self.xpin.read() > self.x_center:
            x = (self.xpin.read() - self.x_center) * \
                100 // (4095 - self.x_center)
        else:
            x = -(self.x_center - self.xpin.read()) * \
                100 // (self.x_center - 0)

        if self.ypin.read() > self.y_center:
            y = (self.ypin.read() - self.y_center) * \
                100 // (4095 - self.y_center)
        else:
            y = -(self.y_center - self.ypin.read()) * \
                100 // (self.y_center - 0)

        # 如果接近中间值设为0，防止抖动
        x = 0 if abs(x) < 5 else x
        y = 0 if abs(y) < 5 else y
        return (x, y)

    def deinit(self):
        """释放资源"""
        self.xpin.deinit()
        self.ypin.deinit()
        self.sw.deinit()


# 3Pin无源蜂鸣器，设置音量和声音频率
class BuzzerSig(PWMDev):
    def __init__(self, pin=-1):
        super().__init__(pin)
        self._volume = 32768
        self.pwm.duty_u16(0)

    def volume(self, vol):
        self._volume = max(0, min(65535, vol))
        self.pwm.duty_u16(self._volume)

    def play(self, freq, duration_ms=0):
        """播放指定频率和持续时间的声音，duration_ms=0表示一直鸣响"""
        if freq > 0:
            self.pwm.freq(freq)
            self.pwm.duty_u16(self._volume)
            if duration_ms > 0:
                sleep_ms(duration_ms)
                self.pwm.duty_u16(0)  # 关闭蜂鸣器
        else:
            sleep_ms(duration_ms)

    def stop(self):
        self.pwm.duty_u16(0)

    def deinit(self):
        self.stop()
        self.pwm.deinit()


class UltrasonicEcho:
    def __init__(self, echo, trig):
        self.echo = Pin(echo, Pin.IN)
        self.trig = Pin(trig, Pin.OUT)

        self.SOUND_SPEED = 343.2  # 声速，单位：米/秒 (20°C空气)
        self.temperature = 20.0  # 默认20°C
        self.last_time = 0  # 两次读值不能间隔过短

    def set_temperature(self, temp_celsius=20):
        self.temperature = temp_celsius
        # 计算当前温度下的声速
        self.SOUND_SPEED = 331.3 * math.sqrt(1 + temp_celsius / 273.15)

    def distance(self):
        """单位cm， 两次读值间隔5ms以上"""
        if ticks_ms() - self.last_time < 5:
            print("读值过快")
            return -1

        # 1. 发送触发信号
        self.trig.value(0)
        sleep_us(2)
        self.trig.value(1)
        sleep_us(10)
        self.trig.value(0)

        # 2. 等待回波开始，并记录高电平持续时间
        while self.echo.value() == 0:
            pass  # 等待变为高电平
        start = ticks_us()  # 记录开始时间

        while self.echo.value() == 1:
            pass  # 等待高电平结束
        end = ticks_us()  # 记录结束时间

        # 3. 计算距离
        duration = ticks_diff(end, start)  # 计算高电平时间（微秒）
        distance_cm = (duration * self.SOUND_SPEED / 10000) / 2
        self.last_time = ticks_ms()  # 更新上次读取时间
        return distance_cm


class TM1637:
    def __init__(self, clk_pin, dio_pin, brightness=7, segments_num=4):
        self.clk = Pin(clk_pin, Pin.OUT)
        self.dio = Pin(dio_pin, Pin.OUT)
        self.brightness = brightness & 0x07  # 亮度0-7，最大7
        self.segments_num = segments_num

        self.digits = [
            0x3F,  # 0: 数字0
            0x06,  # 1: 数字1
            0x5B,  # 2: 数字2
            0x4F,  # 3: 数字3
            0x66,  # 4: 数字4
            0x6D,  # 5: 数字5
            0x7D,  # 6: 数字6
            0x07,  # 7: 数字7
            0x7F,  # 8: 数字8
            0x6F,  # 9: 数字9
            0x77,  # 10: A
            0x7C,  # 11: b
            0x39,  # 12: C
            0x5E,  # 13: d
            0x79,  # 14: E
            0x71,  # 15: F
            0x6F,  # 16: G # 同 9
            0x76,  # 17: H
            0x30,  # 18: I
            0x1E,  # 19: J
            0x75,  # 20: K
            0x38,  # 21: L
            0x37,  # 22: M
            0x54,  # 23: N
            0x3F,  # 24: O (与0复用)
            0x73,  # 25: P
            0x67,  # 26: Q
            0x50,  # 27: R
            0x6D,  # 28: S (与5复用)
            0x78,  # 29: T
            0x3E,  # 30: U
            0x1C,  # 31: V
            0x2A,  # 32: W
            0x76,  # 33: X (与H复用)
            0x6E,  # 34: Y
            0x5B,  # 35: Z (与2复用)
            0x00,  # 36: 空格/无显示
            0x40,  # 37: - 负号
            0x08,  # 38: _ 下划线
            0x63,  # 39: ° 温度符号(兼容显示)
        ]
        self._init_display()

    def _delay(self):
        sleep_us(2)

    def _start(self):
        self.dio.value(1)
        self.clk.value(1)
        self._delay()
        self.dio.value(0)
        self._delay()
        self.clk.value(0)
        self._delay()

    def _stop(self):
        self.clk.value(0)
        self._delay()
        self.dio.value(0)
        self._delay()
        self.clk.value(1)
        self._delay()
        self.dio.value(1)
        self._delay()

    def _write_byte(self, data):
        for i in range(8):
            self.clk.value(0)
            self._delay()
            self.dio.value((data >> i) & 0x01)
            self._delay()
            self.clk.value(1)
            self._delay()
        # 等待ACK应答
        self.clk.value(0)
        self._delay()
        self.dio.value(1)
        self._delay()
        self.clk.value(1)
        self._delay()
        ack = self.dio.value()
        self.clk.value(0)
        self._delay()
        return ack == 0

    def _init_display(self):
        """初始化TM1637，带重试机制，提高稳定性"""
        for attempt in range(3):
            try:
                self._start()
                self._write_byte(0x40)  # 自动地址+普通模式
                self._stop()
                self.clear()  # 初始化后清空屏幕
                self._start()
                self._write_byte(0x88 | self.brightness)  # 开显示+亮度
                self._stop()
                return True
            except:
                sleep_ms(10)
        print("TM1637 初始化失败！")
        return False

    def clear(self):
        self.show_raw([0x00]*self.segments_num)

    def show_raw(self, segments):
        """直接写入段码数据，底层调用"""
        sn = self.segments_num
        segments = segments[:sn] + [0]*(sn-len(segments))  # 强制补满4位
        self._start()
        self._write_byte(0x40)
        self._stop()
        self._start()
        self._write_byte(0xC0)
        for seg in segments:
            self._write_byte(seg)
        self._stop()
        self._start()
        self._write_byte(0x88 | self.brightness)
        self._stop()

    def set_brightness(self, level):
        """设置亮度，范围 0(最暗) ~7(最亮)"""
        self.brightness = max(0, min(7, level))
        self._start()
        self._write_byte(0x88 | self.brightness)
        self._stop()

    def show_number(self, num):
        """显示纯数字（整数/负数都支持）"""
        self.show(str(num))

    def show_hex(self, value):
        """显示4位十六进制数 0000~FFFF"""
        if value < 0:
            value = 0
        if value > 0xFFFF:
            value = 0xFFFF
        hex_str = "{:04X}".format(value)
        self.show(hex_str)

    def show_time(self, hour, minute):
        """显示时间 带冒号 例：12:30"""
        self.show("{:02}{:02}".format(hour, minute), colon=True)

    def show(self, text, colon=False):
        segments = []
        add_dot = False  # 标记：下一个循环，给【上一个字符】加小数点
        text = str(text).upper()

        for char in text:
            if char == '.':
                add_dot = True
                continue
            if char == ':':
                colon = True
                continue

            # 匹配当前字符的段码
            seg_code = 0x00
            if char.isdigit():
                seg_code = self.digits[int(char)]
            elif 'A' <= char <= 'Z':
                seg_code = self.digits[ord(char) - ord('A') + 10]
            elif char == '-':
                seg_code = self.digits[37]
            elif char == '_':
                seg_code = self.digits[38]
            elif char == ' ':
                seg_code = self.digits[36]
            elif char == '°':
                seg_code = self.digits[39]

            if add_dot and len(segments) > 0:
                segments[-1] |= 0x80  # 只修改上一个字符的bit7 → 只亮小数点
                add_dot = False       # 用完立即重置，杜绝误触发

            if len(segments) < 4:
                segments.append(seg_code)
            else:
                break

        # 冒号处理
        if colon and len(segments) >= 2:
            segments[1] |= 0x80

        self.show_raw(segments)

    def show_at(self, pos, char, has_dot=False):
        if not 0 <= pos <= 3:
            return  # 位置越界直接返回
        
        current_segs = [0]*4
        char = str(char).upper()
        seg_code = 0x00

        # 匹配字符编码
        if char.isdigit():
            seg_code = self.digits[int(char)]
        elif 'A' <= char <= 'Z':
            seg_code = self.digits[ord(char)-ord('A')+10]
        elif char == '-':
            seg_code = self.digits[37]
        elif char == ' ':
            seg_code = self.digits[36]

        if has_dot:
            seg_code |= 0x80
        current_segs[pos] = seg_code
        self.show_raw(current_segs)


class ST7789Screen:
    def __init__(self, host=2, sck=12, mosi=13, rst=8, dc=9, cs=10, blk=11, width=240, height=240):
        self.dc = dc
        self.cs = cs
        self.rst = rst
        self.backlight = blk
        self.width = width
        self.height = height
        self.sck = sck
        self.mosi = mosi

        self._reset()

        spi_bus = SPI.Bus(host=host, mosi=mosi, sck=sck)

        display_bus = lcd_bus.SPIBus(
            spi_bus=spi_bus,
            dc=dc,
            cs=cs,
            freq=40000000)

        self.st = st7789.ST7789(
            data_bus=display_bus,
            display_width=width,
            display_height=height,
            backlight_pin=blk,
            backlight_on_state=st7789.STATE_HIGH,
            reset_state=st7789.STATE_LOW,
            color_space=lvgl.COLOR_FORMAT.RGB565,
            color_byte_order=st7789.BYTE_ORDER_BGR,
            rgb565_byte_swap=True,
        )

        self.st.init()
        self.st.set_power(True)
        self.screen = lvgl.screen_active()
        self.set_screen_color()

        backlight_pwm = PWM(Pin(blk), freq=1000)
        backlight_pwm.duty_u16(int(65535))

        self.labels = []
        self.current_label_index = 0
        self.current_scroll_y = 0

    def _reset(self):
        gc.collect()
        Pin(self.sck, Pin.OUT, value=0)
        Pin(self.mosi, Pin.OUT, value=0)
        Pin(self.cs, Pin.OUT, value=1)
        Pin(self.dc, Pin.OUT, value=0)
        Pin(self.rst, Pin.OUT, value=1)
        sleep_ms(20)

        Pin(self.rst, Pin.OUT, value=0) 
        sleep_ms(50)                   
        Pin(self.rst, Pin.OUT, value=1)
        sleep_ms(100)

        lvgl.init()
        sleep_ms(10)
        self.timer = None

    def set_screen_color(self, color=0xFFFFFF):
        self.screen.set_style_bg_color(lvgl.color_hex(color), 0)

    def clear(self, force=False):
        for label in self.labels:
            label.set_text("")
            if force:
                label.deinit()
        if force:
            self.labels = []
            gc.collect()
        self.current_label_index = 0

    def show(self, text, x=0, y=0,  mode=3, color=0x000000, size=24):
        if self.current_label_index < len(self.labels):
            label = self.labels[self.current_label_index]
        else:
            label = lvgl.label(self.screen)
            self.labels.append(label)

        label.set_style_text_color(lvgl.color_hex(color), 0)  # 黑色文字
        if size not in [16, 24, 32]:
            size = 24
        font_name = "font_puhui_{}".format(size)  # 字体文件
        font = getattr(lvgl, font_name, None)
        label.set_style_text_font(font, 0)
        label.align(lvgl.ALIGN.TOP_LEFT, x, y)
        label.set_width(self.width)
        label.set_long_mode(mode)  # 0自动换行 1点省略 2左右滚动 3单向循环滚动 4裁切超出不显示
        label.set_text(text)
        self.current_label_index += 1
        return label

    def auto_scroll(self, interval_ms):
        if self.timer:
            lvgl.timer_del(self.timer)

        def _scroll(timer):
            first = self.labels[0].get_text()
            for i in range(1, len(self.labels)):
               self.labels[i-1].set_text(self.labels[i].get_text())
            self.labels[-1].set_text(first)

        self.timer = lvgl.timer_create(_scroll, interval_ms, None)

    def display(self):
        task_handler.TaskHandler()

