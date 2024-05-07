from machine import ADC,Pin, I2C
from ssd1306 import SSD1306_I2C
from fifo import Fifo
import time,utime
from piotimer import Piotimer as Timer
from led import Led
import math
import framebuf
import micropython

import network
from umqtt.simple import MQTTClient
import urequests as requests 
import ujson
import json  # Add this line to import the json module

micropython.alloc_emergency_exception_buf(200)

class RotaryEncoder:
    def __init__(self, pin_a, pin_b, pin_sw, min_interval):
        self.pin_a = Pin(pin_a, Pin.IN, Pin.PULL_UP)
        self.pin_b = Pin(pin_b, Pin.IN, Pin.PULL_UP)
        self.pin_sw = Pin(pin_sw, Pin.IN, Pin.PULL_UP)
        self.Menu_State = False
        self.Rotation = Fifo(30) #FIFO queue to store rotation events
        self.min_interval = min_interval #Min. time b/w switch presses to avoid bouncing
        self.prev_press_time = 0
        self.sensitivity = 0
        self.pin_a.irq(trigger=Pin.IRQ_FALLING, handler=self.rotary_handler)
        self.pin_sw.irq(trigger=Pin.IRQ_FALLING, handler=self.toggle_handler)

    def rotary_handler(self, pin):
        if self.pin_b.value() and self.Menu_State:
            self.Rotation.put(1)
        elif not self.pin_b.value() and self.Menu_State:
            self.Rotation.put(0)

    def toggle_handler(self, pin):
        current_time = time.ticks_ms()
        if (time.ticks_diff(current_time, self.prev_press_time) > self.min_interval) and self.Menu_State:
            self.Rotation.put(2)
            self.prev_press_time = current_time


class MenuDisplay:
    def __init__(self, oled): #initializes with an OLED display object and LED pins
        self.oled = oled
        self.led_onboard = led_onboard
        self.options = ['Measure HR',"Kubios", 'Exit']
        self.options_state = ""
        self.current_row = 0

    def update(self):   #shows current state of each LED on the OLED
        self.oled.fill(0)
        self.oled.text("Choose an Option:",0,0,1)
        for i, state in enumerate(self.options):
            row_text = f"{i + 1}) {state} "
            if i == self.current_row:
                row_text += " <--"
            self.oled.text(row_text, 0, 20 + i * 10)
        self.oled.show()

    def next_opt(self): #navigates through LEDs
        self.current_row = (self.current_row + 1) % len(self.options)

    def prev_opt(self): #navigates through LEDs
        self.current_row = (self.current_row - 1) % len(self.options)

    def toggle_opt(self): #toggles the selected LED's state and updates its PWM signal
        options_index = self.current_row
        if options_index == 0:
            self.options_state = "HRV" 
        elif options_index == 1:
            self.options_state = "Kubios HRV"
        elif options_index == 2:
            self.options_state = "Exit"
            
    def Welcome_Text(self):
        self.oled.fill(1)
        self.led_onboard.on()
        self.oled.text("Welcome to", 24, 5, 0)
        self.oled.text("Pulse Pro", 24, 25, 0)
        self.oled.text("", 50, 45, 0)
        self.oled.show()
        time.sleep(3)

    def Press_Start(self):
        self.led_onboard.on()
        self.oled.fill(0)
        self.oled.text("Press the Button",0,0,1)
        self.oled.text("To Measure",0,12,1)
        self.oled.text("Your HeartBeat!!",0,24,1)
        self.oled.line(118, 48, 124, 53, 1)
        self.oled.line(118, 58, 124, 53, 1)
        self.oled.line(93, 53, 124, 53, 1)
        self.oled.show()

    def GoodBye(self):
        self.oled.fill(0)
        self.oled.show()
        self.oled.text("Goodbye!!!",25,26,1)
        self.oled.show()
        time.sleep(2)
        self.led_onboard.off()
        self.oled.fill(0)
        self.oled.show()
    

class HeartRateDetector:
    def __init__(self, oled, adc, encoder):
        self.oled = oled
        self.adc = adc
        self.encoder = encoder
        self.sensor_values = []
        self.collection_done = False
        
    def calculate_threshold(self, arr):
        mean = sum(arr) / len(arr)
        std_dev = math.sqrt(sum((x - mean) ** 2 for x in arr) / len(arr))
        threshold = mean + std_dev
        return threshold


    def detect_peaks(self, arr):
        peaks = []
        threshold = self.calculate_threshold(arr)
        for i in range(1, len(arr) - 1):
            if arr[i] > arr[i - 1] and arr[i] > arr[i + 1] and arr[i] > threshold:
                peaks.append(i)
                PPI.append(i)
        return peaks

    
    def calculate_heart_rate(self, sensor_values):
        peaks = self.detect_peaks(self.sensor_values)
        if len(peaks) < 2:
            return None
        time_between_peaks = (peaks[-1] - peaks[0]) / len(self.sensor_values)
        heart_rate = 60 / time_between_peaks
        return heart_rate

    def stop_collection(self, time):
        self.collection_done = True
        heart_rate = self.calculate_heart_rate(self.sensor_values)
        if heart_rate is not None and 30 < heart_rate < 150:
            self.oled.fill_rect(50, 14, 35, 14, 0)
            self.oled.show()
            hr = str(round(heart_rate))
            self.oled.text(hr, 52,15,1)
            self.oled.show()

    def collect_values(self):
        self.collection_done = False
        Timer.init(period = 3900, mode=machine.Timer.ONE_SHOT, callback = self.stop_collection)
        while not self.collection_done:
            if self.encoder.pin_sw.value() == 0:
                return False
            sensor_value = self.adc.read_u16()
            self.sensor_values.append(sensor_value)
            utime.sleep_ms(2)
        self.sensor_values.clear()
        return True


class HRVData:
    def __init__(self, oled):
        self.oled = oled
    
    def meanPPI_calculator(self, data):
        sumPPI = 0 
        for i in data:
            sumPPI += i
        rounded_PPI = round(sumPPI/len(data), 0)
        return int(rounded_PPI)

    def meanHR_calculator(self, meanPPI):
        rounded_HR = round(60*1000/meanPPI, 0)
        return int(rounded_HR)

    def SDNN_calculator(self, data, PPI):
        summary = sum((i - PPI) ** 2 for i in data)
        SDNN = (summary / (len(data) - 1)) ** 0.5
        rounded_SDNN = round(SDNN, 0)
        return int(rounded_SDNN)

    def RMSSD_calculator(self, data):
        summary = sum((data[i + 1] - data[i]) ** 2 for i in range(len(data) - 1))
        RMSSD = (summary / (len(data) - 1)) ** 0.5
        rounded_RMSSD = round(RMSSD, 0)
        return int(rounded_RMSSD)

    def display_HRV_values(self, mean_PPI, mean_HR, SDNN, RMSSD):
        self.oled.text(f'MeanPPI:{int(mean_PPI)} ms', 0, 0, 1)
        self.oled.text(f'MeanHR:{int(mean_HR)} bpm', 0, 15, 1)
        self.oled.text(f'SDNN:{int(SDNN)} ms', 0, 30, 1)
        self.oled.text(f'RMSSD:{int(RMSSD)} ms', 0, 45, 1)

# MQTT

SSID = "KMD658_Group_8"
PASSWORD = "27448052"
BROKER_IP = "192.168.8.253"
     
def connect_wlan():
    # Connecting to the group WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    Attempts = 0
    # Attempt to connect once per second
    while wlan.isconnected() == False and Attempts <= 200:
        Attempts +=1
 
def connect_mqtt():
    try:
        mqtt_client=MQTTClient("", BROKER_IP)
        mqtt_client.connect(clean_session=True)
        print("Connected to MQTT broker")
        return mqtt_client
    except Exception as e:
        print("Error connecting to MQTT broker:", e)
        return None    

def send_data():
    connect_wlan()

    try:
        #Try To Connect
        print(1)
        mqtt_client=connect_mqtt()
        print(2)
        try:
        
            # Sending Info Of Analysis by MQTT.
            topic = "HRV_Info"
            Info = [
                    f'MeanPPI: {mean_PPI} ms', 
                    f'MeanHR: {mean_HR} bpm',
                    f'SDNN: {SDNN} ms',
                    f'RMSSD: {RMSSD} ms',
                    ]
            for i in Info:
                mqtt_client.publish(topic, i)
                print(i)
            Space = "---------------"
            mqtt_client.publish(topic, Space)
            oled.fill(0)
            oled.text("The Infomation",0,28,1)
            oled.text("Has Been Sent!!!",0,38,1)
            oled.show()
            time.sleep(2)
                                           
                
        except Exception as e:
            #Unable To Send Info
            print(f"first exception: {e}")
            oled.fill(0)
            oled.text("Unable to Send",0,17,1)
            oled.text("Info,Try Again ",0,27,1)
            oled.text("Later Please...",0,37,1)
            oled.show()

        
    except Exception as e:
        #Unable To Connect
        print(f"second exception: {e}")
        oled.fill(0)
        oled.text("Connection Could",0,17,1)
        oled.text("Not be Made, Try",0,27,1)
        oled.text("Again Later..",0,37,1)
        oled.show()
        time.sleep(2)

i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)     
encoder = RotaryEncoder(10, 11, 12, 300)
On_btn = Pin(7,Pin.IN, Pin.PULL_UP)
back_btn= Pin(9,Pin.IN, Pin.PULL_UP)
led_onboard = Pin("LED", Pin.OUT)
led_onboard.off()
led = Led(22)
adc = machine.ADC(0)

start_state = True
begining = True
collect_state=True
work_state=True
back_menu = False

Timer = machine.Timer(-1)
PPI = [] # Peaks to peak interval

menu_display = MenuDisplay(oled) # class of display
run_heart_rate_detector = HeartRateDetector(oled, adc, encoder) # variable of class to run heart rate detection
HRV_values = HRVData(oled) # variable of class of HRV data

while True:
    if (On_btn.value() == 0 or back_btn.value()== 0) and start_state:
        if begining:
            menu_display.Welcome_Text() # call welcome display function
            encoder.current_row = 0 # make arrow appear in first option
            begining = False # donot show welcome page
        menu_display.update() # show options
        encoder.Menu_State = True # allow encoder to navigate arrow in options
        while encoder.Menu_State: # until it is on menu display
            while encoder.Rotation.has_data(): # until encoder is not pressed
                rotation_action = encoder.Rotation.get() # selected option
                if rotation_action == 1: 
                    menu_display.next_opt()
                elif rotation_action == 0:  
                    menu_display.prev_opt()
                elif encoder.pin_sw.value() == 0:  
                    menu_display.toggle_opt()
# HRV options                     
                    if menu_display.options_state == "HRV" or menu_display.options_state == "Kubios HRV":
                        encoder.Menu_State = False
                        menu_display.Press_Start()
                        time.sleep(0.5)
                        while work_state: # starte detecting hear rate
                            if encoder.pin_sw.value() == 0:
                                time.sleep(1)
                                oled.fill(0)
                                oled.text("BPM",50,5,1)
                                oled.text("--",52,15,1)
                                oled.text("Press button to",0,40,1 )
                                oled.text("continue to HRV",0,50,1)
                                oled.show()
                                while collect_state:
                                    if back_btn.value() == 0:
                                        back_menu = True
                                        break
                                    
                                    collect_state= run_heart_rate_detector.collect_values() # get values of collected heart rate beats
                                work_state = False
                        if back_menu:
                            menu_display.options_state = ""
                            time.sleep(1)
                            encoder.Menu_State = True
                            work_state = True
                            collect_state=True
                            back_menu = False
                            break
                            
                        Timer.deinit() # stopping the timer to collect HRV
                        oled.fill(0) # fill zero
                        oled.show() # makes the display blank
# calculate HRV Values                        
                        mean_PPI = HRV_values.meanPPI_calculator(PPI)
                        mean_HR = HRV_values.meanHR_calculator(mean_PPI)
                        SDNN = HRV_values.SDNN_calculator(PPI, mean_PPI)
                        RMSSD = HRV_values.RMSSD_calculator(PPI)

# Display HRV Values
                        HRV_values.display_HRV_values(mean_PPI, mean_HR, SDNN, RMSSD) # Display HRV Values
                        oled.show()
                        PPI.clear() # clear PPI data
                        time.sleep(0.75)
                        
                        while True:
                            if encoder.pin_sw.value() == 0: # 
                                break
                        oled.fill(0)
                        oled.text("Sending Info to ",0,28,1)
                        oled.text("The Server... ",10,38,1)
                        oled.show()
                        time.sleep(2)
                        
                        # connect to MQTT
                        
                        send_data()
                        
                        
#                         if len(PPI) >= 10 and menu_display.options_state == "Kubios HRV":
#                             oled.text("Analyzing PPI",0,12,1)
#                             oled.text("Using The Kubios",0,22,1)
#                             oled.text("Cloud Server",0,32,1)
#                             oled.text("Please Wait...",0,52,1)
#                             oled.show()
#                             time.sleep(2)
#                             
#                             try:
#                                 response = requests.post(
#                                     url = TOKEN_URL, 
#                                     data = 'grant_type=client_credentials&client_id={}'.format(CLIENT_ID), 
#                                     headers = {'Content-Type':'application/x-www-form-urlencoded'}, 
#                                     auth = (CLIENT_ID, CLIENT_SECRET)
#                                 )
#                                 
#                                 response_json = response.json()  # Parse JSON response into a python dictionary 
#                                 access_token = response_json["access_token"]  # Parse access token
#                                 HRV_Info= {
#                                     "type": "RRI",
#                                     "data": PPI,
#                                     "analysis": {"type": "readiness"}
#                                 }
#                                 
#                                 # Make the readiness analysis with the given data
#                                 response = requests.post(
#                                     url = "https://analysis.kubioscloud.com/v2/analytics/analyze",
#                                     headers = {"Authorization": "Bearer {}".format(access_token), "X-Api-Key": APIKEY},
#                                     json = HRV_Info
#                                 )
#                                 
#                                 #Get The Response and Make It A Nested Dictonary
#                                 response = response.json()
#                             
                            
                            
                        
                        # Resting states for Menu options, HRV values, ADC Values 
                        menu_display.options_state = ""
                        time.sleep(1)
                        encoder.Menu_State = True
                        work_state = True
                        collect_state=True
                        
                    elif menu_display.options_state == "Exit":
                        encoder.Menu_State = False
                        oled.fill(0)
                        oled.show()
                        oled.text("Do you want to",0,0,1)
                        oled.text("turn off the device?",0,9,1)
                        menu_display.options_state = ""
                        oled.show()       
                        while True:
                            if On_btn.value() == 0:
                                begining=True      
                                menu_display.GoodBye()
                                break
                            if back_btn.value() == 0:
                                work_state = True
                                menu_display.update()
                                break
                        encoder.Menu_State = True
                        start_state = True

                    if encoder.Menu_State:
                        break
                menu_display.update()
                if begining:
                    break
            if begining:
                break