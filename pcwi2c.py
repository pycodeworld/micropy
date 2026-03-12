class I2Controller:
    def __init__(self, pwm_max=4095):
        self.pwm_max = pwm_max

    def duty(self, value):
        raise NotImplementedError("duty(value) must be implemented")

    def freq(self, value):
        raise NotImplementedError("freq(value) must be implemented")


class I2CDev:
    def __init__(self, controller: I2Controller, channel: int):
        self.controller = controller
        self.channel = channel

    # 10位占空比值
    def duty(self, value: int):
        self.controller.duty(self.channel, int(
            value*self.controller.pwm_max/1023))

    # 16位占空比值
    def duty_u16(self, value: int):
        self.controller.duty(self.channel, int(
            value*self.controller.pwm_max/65535))

    def on(self):
        self.controller.duty(self.channel, self.controller.pwm_max)

    def off(self):
        self.controller.duty(self.channel, 0)

    # pin方法
    def value(self, val=None):
        if val == None:
            self.read()
        self.off() if val == 0 else self.on()

    def freq(self, val):
        return self.controller.freq(val)

    # pwm方法
    def read(self):
        return self.controller.duty(self.channel)
    
    def deinit(self):
        self.off()
