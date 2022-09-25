from microdot import Microdot
from microdot import send_file
import network
import time
import secrets
import time
import neopixel
import os
import bitmapfont
from machine import Pin
import utime

def display(request):
    print('display')
    start = 0
    for y in range(YRES):
        for x in range(XRES):
            rgb = request[start] | (request[start + 1] << 8)
            r = rgb & 31
            g = (rgb >> 5) & 63
            b = rgb >> 11
            wall[mapPixel(x, y)] = (r<<1, g<<0, b<<1)
            start += 2
    wall.write()
    #print('displayed')

# Compute pixel array positiong from
# x,y coordinate
# TODO Fix for your type of chain positioning
def mapPixel(x, y):
    y = abs(y - YRES + 1) # text was upside down
    if x % 2 == 1:
        return (YRES * x) + y
    else:
        return YRES * x + YRES - 1 - y

# Alternative display code for screen with different internal routing
#def mapPixel(x, y):
#    if y % 2 == 1:
#        return XRES * y + x
#    else:
#        return XRES * y + XRES - 1 - x

# Light up a single pixel in the chain
def drawPixel(x,y, colour=(16,16,16)):
    if x >= XRES:
        return
    if y >= YRES:
        return
    wall[mapPixel(x, y)] = colour
    
# Show cached image (if exists)
def showCache():
    try:
        f = open("cache.dat", "rb")
        display(f.read())
    except OSError:
        print('No cache.dat')

# Clear out drawing array buffer
def clearBuffer(colour = (0,0,0)):
    for y in range(YRES):
        for x in range(XRES):
            wall[mapPixel(x, y)] = colour

# Clear pixel screen
def clearScreen(colour = (0,0,0)):
    clearBuffer(colour)
    wall.write()
    
# Scroll a message along the screen
def scrollText(message):
    with bitmapfont.BitmapFont(32, 8, drawPixel) as bf:
        message_width = bf.width(message)   # Message width in pixels.
        last = utime.ticks_ms()             # Last frame millisecond tick time.
        speed_ms = SPEED / 1000.0           # Scroll speed in pixels/ms.
        # Main loop:
        pos = 0
        while True:
            # Compute the time delta in milliseconds since the last frame.
            current = utime.ticks_ms()
            delta_ms = utime.ticks_diff(current, last)
            last = current
            # Compute position using speed and time delta.
            pos -= speed_ms*delta_ms
            if pos < -message_width:
                pos = XRES
                break
            # Clear the matrix and draw the text at the current position.
            clearBuffer()
            bf.text(message, int(pos), 0)
            # Update the matrix LEDs.
            wall.write()
            # Sleep a bit to give USB mass storage some processing time (quirk
            # of SAMD21 firmware right now).
            utime.sleep_ms(20)


SPEED          = 10.0    # Scroll speed in pixels per second.
XRES           = 32 # X resolution of neopixel array
YRES           = 8 # Y resolution of neopixel array
PIN            = 22 # PIN connected to screen
FRAMEBYTES = XRES * YRES * 2 # 16 bit image depth

wall = neopixel.NeoPixel(machine.Pin(PIN), XRES * YRES)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(secrets.networkName,secrets.networkPassword)

# Incrementally fill the screen up
# Useful for testing the array ordering
def snake():
    clearScreen()
    for x in range(XRES):
        for y in range(YRES):
            drawPixel(x,y)
            time.sleep(0.1)
            wall.write()
#snake()

showCache()

max_wait = 25 # Seconds to wait for WiFi
while max_wait > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    max_wait -= 1
    print('waiting for connection...')
    time.sleep(1)

if wlan.status() != 3:
    import machine
    led = machine.Pin("LED", machine.Pin.OUT)
    led.on() # LED on means the network connection failed
    raise RuntimeError('network connection failed')
else:
    print('connected')
    status = wlan.ifconfig()
    print( 'ip = ' + status[0] )
    scrollText(status[0]) # Show IP address on the screen


app = Microdot()

@app.route('/')
def hello(request):
    return send_file('static/index.html')

@app.route('/shutdown')
def shutdown(request):
    request.app.shutdown()
    return 'The server is shutting down...'

@app.route('/resolution', methods=['GET'])
def draw(request):
    return {
        'x': XRES,
        'y': YRES
    }

@app.route('/draw', methods=['GET'])
def draw(request):
    return send_file('cache.dat')

@app.route('/draw', methods=['POST'])
def draw(request):
    f = open("cache.dat", "wb")
    f.write(request.body)
    f.close()
    display(request.body)
    return 'success'

@app.route('/<path:path>')
def static(request, path):
    if '..' in path:
        # directory traversal is not allowed
        return 'Not found', 404
    return send_file('static/' + path)


app.run(debug=True, port=80)
