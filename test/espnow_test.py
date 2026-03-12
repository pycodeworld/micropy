import network
import espnow
from machine import Pin, Timer
import time

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

print("="*50)
print("本机 ESP32 MAC 地址：", wlan.config("mac"))
print("="*50)

e = espnow.ESPNow()
e.active(True)
# 本机MAC：b'\xac\xa7\x04\xeem\xcc'
# 添加监听局域网其他ESP32的MAC列表
PEER_MAC_LIST = [b'\x1c\xdb\xd4v\xf1p']
for mac in PEER_MAC_LIST:
    e.add_peer(mac)

# 处理收到的消息


def recv_msg(e):
    mac, msg = e.irecv(0)
    if msg:
        print(f"\n 收到来自 {mac} 的消息：{msg.decode('utf-8')}")


# 注册消息回调函数
e.irq(recv_msg)

# 定时发送心跳消息


def send_msg(t):
    for mac in PEER_MAC_LIST:
        e.send(mac, "心跳消息！")


# 启动消息定时器
Timer(1).init(mode=Timer.PERIODIC, period=1000, callback=send_msg)
