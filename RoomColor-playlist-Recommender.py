#####################################
# Created by Danesvarmen Rasanderan
# github.com/DanesvarmenRasanderan
#####################################
from machine import UART, Pin, ADC, Timer, PWM
import utime
import time
from math import log
from gpio_lcd import GpioLcd

#----------Details-----------
SSID = "XXXXXXXX"
Password = "XXXXXXXX"
base_url = "https://api.thingspeak.com/apps/thinghttp/send_request?api_key=XXXXXXXX"
ThingspeakAPI = "XXXXXXXXXX"
#-----------------------------

# Initialize Pin
resetSw = Pin(2, Pin.IN)
selectSw = Pin(3, Pin.IN)
Ldr = ADC(Pin(27))
TempSensor = ADC(4)
led_onboard = machine.Pin(25, Pin.OUT)
LedPin = [20, 19, 18]
PwmLed = [PWM(Pin(LedPin[0])),PWM(Pin(LedPin[1])),PWM(Pin(LedPin[2]))]
uart0 = UART(0, rx=Pin(17), tx=Pin(16), baudrate=115200)
print(uart0)

lcd = GpioLcd(rs_pin=Pin(8),
              enable_pin=Pin(9),
              d4_pin=Pin(10),
              d5_pin=Pin(11),
              d6_pin=Pin(12),
              d7_pin=Pin(13),
              num_lines=2, num_columns=16)

# Initialize Value
count = 0
mode = 0
ok = 0
err = 0
Timer = Timer()
modeState = ""
done = 0  # 1 means send, 0 not send
led_onboard.value(0)

PwmLed[0].freq(1000)
PwmLed[1].freq(1000)
PwmLed[2].freq(1000)

degree = bytearray([0x07,0x05,0x07,0x00,0x00,0x00,0x00,0x00])

PlaylistLink = {'Sad' : "open.spotify.com/playlist/26Nw4MJdwBSfSUe67ziwRj?si=6d9aba07e7024d5a",
                'Love' : "open.spotify.com/playlist/4pqdXECBpzbBQNBQ7IrPi2?si=75865975ef32430b",
                'Energy' : "open.spotify.com/playlist/37i9dQZF1DX0vHZ8elq0UK?si=2aad36175d3a4eb0",
                'Romance' : "open.spotify.com/playlist/37i9dQZF1DWTyTgrZFIX3S?si=057b37766a8e4ec4",
                'Purity' : "open.spotify.com/playlist/2NTny8jD3vJcjS7HtYOk9s?si=979f2cadd6554dd4",
                'Envy' : "open.spotify.com/playlist/7s1RmqTPmvfKGSOWzLcRU5?si=bd4f21c569eb481c"}


def playlistRecommend(modeSt,currentmode):
    global mode, done

    end_time= time.time() + 10
    while (selectSw.value() == 0) and (done == 0):
        if time.time() > end_time:
            submitdataESP01(PlaylistLink[modeSt],modeSt)
            submitdataESP01(PlaylistLink[modeSt],modeSt)
            done = 1
            print("Playlist Selected")
            break

        if mode != currentmode:
            break


def blinkLEDOnboard():
    led_onboard.value(0)
    utime.sleep(0.1)
    led_onboard.value(1)
    utime.sleep(0.1)
    led_onboard.value(0)

def sendCMD_waitResp(cmd, uart=uart0, timeout=2000):
    print("CMD: " + cmd)
    uart.write(cmd)
    waitResp(uart, timeout)
    print()

def waitResp(uart=uart0, timeout=2000):
    global ok
    global err
    prvMills = utime.ticks_ms()
    resp = b""
    while (utime.ticks_ms()-prvMills)<timeout:
        if uart.any():
            resp = b"".join([resp, uart.read(1)])
    print("resp:")
    try:
        print(resp.decode())
        blinkLEDOnboard()
        ok=ok+1
    except UnicodeError:
        print(resp)
        err=err+1


def initializeESP01():                                                                    # The timeout=x can be adjusted
    sendCMD_waitResp("AT\r\n", timeout=3000)                                              # Test AT startup
    sendCMD_waitResp("AT+CWMODE=1\r\n")                                                   # Set the Wi-Fi mode = Station mode
    sendCMD_waitResp("AT+CWJAP={},{}\r\n".format(SSID, Password), timeout=5000)           # Connect to AP
    sendCMD_waitResp("AT+CIPMUX=0\r\n", timeout=1000)
    sendCMD_waitResp("AT+CIPMUX=1\r\n", timeout=1000)


def submitdataESP01(PlaylistURL, mode):

    sendCMD_waitResp("AT+CIPSTART=3,\"TCP\",\"api.thingspeak.com\",80\r\n", timeout=5000)


    Http = ("GET /apps/thinghttp/send_request?api_key={}&mode=*{}*&message={}".format(ThingspeakAPI,mode,PlaylistURL) + "\r\n")

    HttpLen = len(Http)
    PlaylistLen = len(PlaylistURL)
    totalLen = HttpLen + PlaylistLen

    sendCMD_waitResp("AT+CIPSEND=3," + str(totalLen) + "\r\n" , timeout=5000)
    sendCMD_waitResp(Http , timeout=100)
    sendCMD_waitResp("\r\n", timeout=1000)

    print('Playlist send to ThingHttp-twilio')


def Switch(pin):
    global count, mode, done

    if count <= 7:
        if selectSw.value() == 1:
            count += 1
            mode += 1
            done = 0

    else:
        count = 0
        mode =0
        done = 0

    utime.sleep(0.5)
    return mode, done


def resetSwitch(pin):
    global count, mode, done

    count = 0
    mode = 0
    done = 0
    PwmLed[0].duty_u16(0)
    PwmLed[1].duty_u16(0)
    PwmLed[2].duty_u16(0)

    print("reset ok")
    return mode, done


def display(timer):
    lux, temp = stat()
    mode = Switch('')
    global modeState

    lcd.clear()
    lcd.move_to(2,0)
    lcd.putstr("Mode :")
    lcd.putstr(modeState)
    utime.sleep(1)

    lcd.clear()
    lcd.putstr("Temp : {}".format(temp))
    lcd.custom_char(0, degree)
    lcd.putchar(chr(0))
    lcd.putstr("C")
    lcd.move_to(0,1)
    lcd.putstr("Lux  : {}% ".format(lux))


def stat():
    luxdata = []
    tempdata = []
    lux = 0
    temp = 0

    for i in range(10):
        tempReading = TempSensor.read_u16()
        convertionVal =3.3/(65535)
        tempVal = (tempReading * convertionVal)
        tempVal = 27 - (tempVal - 0.706)/ 0.001721
        tempval = round(tempVal, 2)
        tempdata.append(tempval)

    for i in range(10):
        temp += tempdata[i]

    temp = temp/10
    temp = round(temp, 2)


    for i in range(10):
        ldrReading = Ldr.read_u16()
        luxVal = ldrReading/65535 * 100
        luxVal = round(luxVal, 1)
        luxdata.append(luxVal)

    for i in range(10):
        lux += luxdata[i]

    lux = lux/10
    lux = round(lux, 2)

    #print("Lux: {}%".format(lux))
    #print("Temperature: {} C".format(temp))

    return lux, temp


def fading():
    for i in range(0,65025, 20):
        PwmLed[0].duty_u16(i)
        PwmLed[1].duty_u16(i)
        PwmLed[2].duty_u16(i)
        utime.sleep(0.001)

    utime.sleep(2)

    for i in range(65025,0, -20):
        PwmLed[0].duty_u16(i)
        PwmLed[1].duty_u16(i)
        PwmLed[2].duty_u16(i)
        utime.sleep(0.001)

    utime.sleep(2)


def colorSelector(color):

    if color == "red":
        PwmLed[0].duty_u16(65025)
        PwmLed[1].duty_u16(0)
        PwmLed[2].duty_u16(0)
    elif color == "green" :
        PwmLed[0].duty_u16(0)
        PwmLed[1].duty_u16(65025)
        PwmLed[2].duty_u16(0)
    elif color == "blue" :
        PwmLed[0].duty_u16(0)
        PwmLed[1].duty_u16(0)
        PwmLed[2].duty_u16(65025)
    elif color == "white" :
        PwmLed[0].duty_u16(65025)
        PwmLed[1].duty_u16(65025)
        PwmLed[2].duty_u16(65025)
    elif color == "yellow" :
        PwmLed[0].duty_u16(65025)
        PwmLed[1].duty_u16(65025)
        PwmLed[2].duty_u16(0)
    elif color == "purple" :
        PwmLed[0].duty_u16(65025)
        PwmLed[1].duty_u16(0)
        PwmLed[2].duty_u16(65025)
    elif color == "orange" :
        PwmLed[0].duty_u16(65025)
        PwmLed[1].duty_u16(5000)
        PwmLed[2].duty_u16(0)


initializeESP01()
Timer.init(period=15000, mode=Timer.PERIODIC, callback=display)

while True:

    resetSw.irq(trigger = Pin.IRQ_RISING, handler = resetSwitch)
    selectSw.irq(trigger = Pin.IRQ_RISING, handler = Switch)


    if mode == 0:
        PwmLed[0].duty_u16(0)
        PwmLed[1].duty_u16(0)
        PwmLed[2].duty_u16(0)
        modeState = "OFF"
    elif mode == 1 :
        colorSelector("white")
        modeState = "Purity"

        playlistRecommend(modeState,1)

    elif mode == 2 :
        colorSelector("red")
        modeState = "Love"

        playlistRecommend(modeState,2)

    elif mode == 3 :
        colorSelector("blue")
        modeState = "Sad"

        playlistRecommend(modeState,3)

    elif mode == 4 :
        colorSelector("orange")
        modeState = "Energy"

        playlistRecommend(modeState,4)

    elif mode == 5 :
        colorSelector("purple")
        modeState = "Romance"

        playlistRecommend(modeState,5)

    elif mode == 6:
        colorSelector("green")
        modeState = "Envy"

        playlistRecommend(modeState,6)

    elif mode == 7:
        fading()

    utime.sleep(0.001)
    #print(modeState)
    #print(mode)
