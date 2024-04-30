import time
from machine import UART, Pin, I2C, Timer, ADC
from ssd1306 import SSD1306_I2C

button = Pin(9, Pin.IN, Pin.PULL_UP)
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)

oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

oled.fill(0)

text_height = 8 
current_y = 0

while True:
    text = input("Enter text: ")
    
    if current_y + text_height > oled_height:
        oled.scroll(0, -text_height)
        current_y -= text_height
        
        oled.fill_rect(0, current_y, oled_width, text_height, 0)
    
    # Display the text
    oled.text(text, 0, current_y)
    oled.show()
    
    # Move to the next line
    current_y += text_height
