import machine
import utime

# Define the LED and button pins
led = machine.PWM(machine.Pin(25))
button = machine.Pin(20, machine.Pin.IN, machine.Pin.PULL_UP)

# Define the initial brightness and the increment
brightness = 0
increment = 10

# Define the last button press time (for debouncing)
last_press_time = utime.ticks_ms()

# Function to update the LED brightness
def update_led_brightness():
    global brightness
    led.duty_u16(brightness)

# Function to handle button presses
def handle_button_press():
    global brightness, last_press_time

    # Debouncing
    if utime.ticks_diff(utime.ticks_ms(), last_press_time) < 200:
        return

    # Check if the button is pressed
    if button.value() == 0:
        # Increase the brightness
        brightness += increment

        # If the brightness exceeds the maximum, reset it
        if brightness > 65025:
            brightness = 0

        # Update the LED brightness
        update_led_brightness()

        # Update the last button press time
        last_press_time = utime.ticks_ms()

# Main loop
while True:
    handle_button_press()
    utime.sleep(0.01)