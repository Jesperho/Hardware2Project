import time
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C


move_left = Pin(9, Pin.IN, Pin.PULL_UP)    #  GPIO for SW0 or Rotary encoder 10
move_right = Pin(7, Pin.IN, Pin.PULL_UP)  #  GPIO for SW2 or Rotary encoder 10


i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)


ufo_position = oled_width // 2 - 8  


def draw_ufo(position):
    oled.fill(0)  # Clear the screen
    oled.text("<=>", position, oled_height - 8)
    oled.show()

# Draw the UFO initially
draw_ufo(ufo_position)

# Main loop
while True:
    # Read button states
    move_left_pressed = not move_left.value()  # Button to move UFO left
    move_right_pressed = not move_right.value()  # Button to move UFO right

    # If left button is pressed and UFO is not at the left edge, move it left
    if move_left_pressed and ufo_position > 0:
        ufo_position -= 1
    # If right button is pressed and UFO is not at the right edge, move it right
    elif move_right_pressed and ufo_position < oled_width - 16:
        ufo_position += 1

    # Draw the UFO at its current position
    draw_ufo(ufo_position)

    # Add a small delay to avoid flickering
    time.sleep(0.05)


