from machine import Pin, PWM, Timer
from fifo import Fifo
import time

class Encoder:
    def __init__(self, rot_a, rot_b):
        self.a = Pin(rot_a, mode=Pin.IN, pull=Pin.PULL_UP)
        self.b = Pin(rot_b, mode=Pin.IN, pull=Pin.PULL_UP)
        self.fifo = Fifo(30, typecode='i')
        self.a.irq(handler=self.handler, trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING)

    def handler(self, pin):
        if self.b.value():
            self.fifo.put(1)
        else:
            self.fifo.put(-1)

class Button:
    def __init__(self, pin):
        self.button = Pin(pin, mode=Pin.IN, pull=Pin.PULL_UP)
        self.last_press_time = 0
    
    def pressed(self):
        now = time.ticks_ms()
        if not self.button.value() and now - self.last_press_time > 200:  # Debounce threshold: 200 ms
            self.last_press_time = now
            return True
        return False

# Setup
led = PWM(Pin(20), freq=1000)
led.duty(0)  # Start with LED off
brightness = 0
led_state = False

rot = Encoder(10, 11,12)
button = Button(12)  # Assume the button pin is 12, adjust as needed

while True:
    # Button press handling
    if button.pressed():
        led_state = not led_state
        if not led_state:
            led.duty(0)
    
    # Encoder handling
    if led_state and rot.fifo.has_data():
        turn = rot.fifo.get()
        brightness += turn * 1023 // 100  # Scale turn to PWM range
        brightness = max(0, min(1023, brightness))  # Constrain to valid PWM range
        led.duty(brightness)

    time.sleep(0.01)  # Small delay to avoid hogging CPU
