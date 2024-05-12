from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
from fifo import Fifo
from filefifo import Filefifo
import micropython
import time

#Init class encoder
class Encoder:
    def __init__(self, rot_a, rot_b, rot_c):
        self.a = Pin(rot_a, mode=Pin.IN, pull=Pin.PULL_UP)
        self.b = Pin(rot_b, mode=Pin.IN, pull=Pin.PULL_UP)
        self.c = Pin(rot_c, mode=Pin.IN, pull=Pin.PULL_UP)  
        self.last_pressed_time = 0
        self.fifo = Fifo(30, 'i')
        self.a.irq(handler=self.handle_rotation, trigger=Pin.IRQ_RISING, hard=True)
        self.c.irq(handler=self.switch, trigger=Pin.IRQ_FALLING, hard=True)

    def handle_rotation(self, pin):     # triggered on rising edge and updates the FIFO 
        self.fifo.put(1 if self.b.value() != self.a.value() else -1)

    def switch(self, pin):    #  triggered on falling edge and updates the FIFO
        current_time = time.ticks_ms()
        if current_time - self.last_pressed_time >= 200:
            self.last_pressed_time = current_time
            self.fifo.put(0)

i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)
rot = Encoder(10, 11, 12)
data_reader = Filefifo(10, name='capture_250Hz_02.txt') #use filefifo to read the values 

data = [data_reader.get() for _ in range(1000)] # read 1000 data points from the capture-02 file
minimum, maximum = min(data), max(data)

def scale_data(value, min_val, max_val): # function to scale the data to fit within the OLED display
    return int(((value - min_val) / (max_val - min_val)) * 63)

samples = [scale_data(val, minimum, maximum) for val in data]

def display_samples(samples, display_position):
    oled.fill(0) # clear display
    for pixel_index in range(128): #iterate through samples based on oled screen
        sample_index = pixel_index + display_position
        if sample_index < len(samples):
            oled.pixel(pixel_index, 63 - samples[sample_index], 1)
    oled.show()

current_position, max_position = 0, len(samples) - 128

while True:
    while rot.fifo.has_data():
        encoder_value = rot.fifo.get()
        if encoder_value == 1 and current_position < max_position: # if the encoder is rotated clockwise and there is space to move to the right
            #it increments the current_position var
            current_position += 5
        elif encoder_value == -1 and current_position > 0: # counter clockwise
            current_position -= 5
    display_samples(samples, current_position)
