from pcwlib import Motor
import time

# 初始化电机驱动
# 方式1: 只有方向控制（全速或停止）
motor = Motor(47, 48)
motor.forward()  # 全速正转
time.sleep(2)
motor.coast()  # 滑行停止
time.sleep(2)
motor.backward()
time.sleep(2)
motor.coast()  # 滑行停止
time.sleep(2)
motor.deinit()
