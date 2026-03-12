from pcwlib import TM1637
from time import sleep
tm1637 =  TM1637(42,2)
 
"""测试显示"""
print("开始TM1637测试...")

# 测试1: 全亮测试
print("测试1: 全亮")
tm1637.show_raw([0xFF, 0xFF, 0xFF, 0xFF])
sleep(1)

# 测试2: 数字滚动
print("测试2: 数字滚动")
for i in range(10):
    tm1637.show(str(i) * 4)
    sleep(0.3)

# 测试3: 显示"1234"
print("测试3: 显示1234")
tm1637.show("1234")
sleep(1)

# 测试4: 带小数点的数字
print("测试4: 显示12.34")
tm1637.show("12.34")
sleep(1)

# 测试5: 时间显示
print("测试5: 显示时间14:30")
tm1637.show_time(14, 30)
sleep(1)

# 测试6: 清空
print("测试6: 清空显示")
tm1637.clear()
sleep(0.5)

print("测试完成")
