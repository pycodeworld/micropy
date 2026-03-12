import dht
from machine import Pin
from utime import sleep

sensor = dht.DHT11(Pin(16))
try:
    while True:
        sleep(2)  # DHT11两次读取之间至少需要1-2秒间隔
        sensor.measure() 
        temp = sensor.temperature() 
        humi = sensor.humidity()
        print(f"Temperature: {temp}°C, Humidity: {humi}%")
except OSError as e:
    print("Sensor read error:", e)


