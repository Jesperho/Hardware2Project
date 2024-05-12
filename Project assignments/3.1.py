from machine import Pin
from led import Led
from fifo import Fifo
from time import sleep_ms


# Max value of PWM LED
LED_ON = 65535
STEP = 10
CLOCK_CYCLE = 150


class Led_handler:
    def __init__(self):
        # Push, inner and outer
        self.sw = Pin(12, Pin.IN, Pin.PULL_UP)
        self.a = Pin(10, Pin.IN, Pin.PULL_UP)
        self.b = Pin(11, Pin.IN, Pin.PULL_UP)

        self.state = True
        self.intensity = 100

        # One of the leds
        self.led = Led(pin=Pin(22), mode=Pin.OUT, brightness=100)
        self.led.on()

        # Fifo class
        self.fifo = Fifo(30)

        # Interrupt handler
        self.a.irq(handler=self.handler, trigger=Pin.IRQ_RISING, hard=True)

    # Tests only b value, is called when a has a rising edge
    def handler(self, var):
        if self.b():
            self.fifo.put(0)
        else:
            self.fifo.put(1)

    def adjust(self, direction):
        # Turning left
        if direction == 0:
            # Minus INTENSITY_STEP to the intensity unless 0, in which case 0
            self.intensity = self.intensity - STEP if self.intensity > 0 else 0
            self.led.brightness(self.intensity)
        # Turning right
        elif direction == 1:
            # Plus INTENSITY_STEP to the intensity unless 65535, in which case that
            self.intensity = self.intensity + STEP if self.intensity < 100 else 100
            self.led.brightness(self.intensity)


main = Led_handler()

while True:
    while main.fifo.has_data():
        value = main.fifo.get()
        # Adjust the intensity only if the
        if main.state:
            main.adjust(value)

    # Pushing rotary knob
    if not main.sw():
        main.led.toggle()
        # Flip a switch
        main.state = not main.state
        # Don't change the value if the knob is held down
        while not main.sw():
            sleep_ms(CLOCK_CYCLE)