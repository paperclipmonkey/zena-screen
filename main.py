# Control an LED array to show a message coming in over HTTP POST
    # Saves the last image to show on reboot
    # Shows the IP address on boot
    # HTTP file server (mostly working)

import network
import socket
import time
import gc
import neopixel
import os
import bitmapfont
from machine import Pin
import utime
import re
import math

headerLineRegex = re.compile("[\r\n]")
headerPathRegex = re.compile("\s")
headerPathFiletypeRegex = re.compile("\.")

SPEED          = 10.0    # Scroll speed in pixels per second.
ssid           = '####' # YOUR WIFI SSID
password       = '####' # YOUR WIFI PASSWORD
xres           = 32 # X resolution of neopixel array
yres           = 8 # Y resolution of neopixel array
pin            = 22 # PIN connected to screen
frameBytes = xres * yres * 2 # 16 bit image depth

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

wall = neopixel.NeoPixel(machine.Pin(pin), xres * yres)
wall.write()

def display(request):
    #print('display')
    for i in range(len(request) - 3):
        # cr + lf + cr + lf
        if(request[i] == 13 and request[i + 1] == 10 and request[i + 2] == 13 and request[i + 3] == 10):
            # found frame start
            start = i + 4;
            for y in range(yres):
                for x in range(xres):
                    rgb = request[start] | (request[start + 1] << 8)
                    r = rgb & 31
                    g = (rgb >> 5) & 63
                    b = rgb >> 11
                    wall[mapPixel(x, y)] = (r<<1, g<<0, b<<1)
                    start += 2
            wall.write()
            print('drawn')


# Compute pixel array positiong from
# x,y coordinate
# TODO Fix for your type of chain positioning
def mapPixel(x, y):
    y = abs(y - yres + 1) # text was upside down
    if x % 2 == 1:
        return (yres * x) + y
    else:
        return yres * x + yres - 1 - y

# Alternative display code for screen with different internal routing
#def mapPixel(x, y):
#    if y % 2 == 1:
#        return xres * y + x
#    else:
#        return xres * y + xres - 1 - x

# Light up a single pixel in the chain
def drawPixel(x,y, colour=(16,16,16)):
    if x >= xres:
        return
    if y >= yres:
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
    for y in range(yres):
        for x in range(xres):
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
                pos = xres
                break
            # Clear the matrix and draw the text at the current position.
            clearBuffer()
            bf.text(message, int(pos), 0)
            # Update the matrix LEDs.
            wall.write()
            # Sleep a bit to give USB mass storage some processing time (quirk
            # of SAMD21 firmware right now).
            utime.sleep_ms(20)

showCache()

# Incrementally fill the screen up
# Useful for testing the array ordering
def snake():
    clearScreen()
    for x in range(xres):
        for y in range(yres):
            drawPixel(x,y)
            time.sleep(0.1)
            wall.write()
#snake()

max_wait = 25 # Seconds to wait for WiFi
while max_wait > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    max_wait -= 1
    print('waiting for connection...')
    time.sleep(1)

if wlan.status() != 3:
    raise RuntimeError('network connection failed')
else:
    print('connected')
    status = wlan.ifconfig()
    print( 'ip = ' + status[0] )
    scrollText(status[0]) # Show IP address on the screen

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()
s.bind(addr)
s.listen(1)

print('listening on', addr)
    
showCache() # Default state is showing previous image

# Listen for connections
while True:
    try:
        cl, addr = s.accept()
        # print('client connected from', addr)
        request = cl.recv(8196)
        # print(request)
        if len(request) >= 1:
            if request[0] == 80: # 'P' for post
                for i in range(len(request) - 3):
                    if(request[i] == 13 and request[i + 1] == 10 and request[i + 2] == 13 and request[i + 3] == 10):
                        # found frame start
                        # print('found start at %d' % i)
                        start = i + 4;
                        while (len(request) - start < frameBytes):
                            request += cl.recv(8196)
                        # Save to file so we can show it on next reboot
                        f = open("cache.dat", "wb")
                        f.write(request)
                        f.close()
                        display(request)
                        cl.send('HTTP/1.0 200 OK\r\nAccess-Control-Allow-Origin:*\r\n')
                        break
            # Kept for posterity. The file web server mostly works but garbles
            # up long non-binary responses (> ~4kb)
            if request[0] == 71: # 'G' for GET
                headers = headerLineRegex.split(request)
                parsedPath = headerPathRegex.split(headers[0])
                path = parsedPath[1].decode('UTF-8')
                binaryFiles = ['woff', 'woff2', 'png', 'jpg']
                contentTypes = {
                    'woff': 'font/woff',
                    'woff2': 'font/woff2',
                    'png': 'image/png',
                    'jpg': 'image/jpg',
                    'js': 'text/javascript',
                    'css': 'text/css',
                    'html': 'text/html',
                }
                print('GET: ' + path)
                if(path == '/'):
                    path = 'index.html'
                
                fileType = headerPathFiletypeRegex.split(path)
                if fileType[-1] in binaryFiles:
                    print("Binary file")
                    try:
                        f = open("/web/" + path, "rb")
                        contentType = contentTypes.get(fileType[-1])
                        cl.send('HTTP/1.0 200 OK\r\n' + contentType + '\r\n\r\n')
                        while True:
                            buffer = f.read(1024)
                            if buffer:
                                cl.send(buffer)
                            else:
                                break
                        #cl.send(f.read())
                    except OSError:
                        cl.send('HTTP/1.0 404 OK\r\nContent-type: text/html\r\n\r\nFile Not Found')

                else:
                    print("Non-Binary file")
                    try:
                        f = open("/web/" + path, "r")
                        #fileSize = os.size("/web/" + path) # Filesize not available in Pico Micropython ?
                        contentType = contentTypes.get(fileType[-1])
                        #'\r\ncontent-length: ' + fileSize + 
                        cl.send('HTTP/1.0 200 OK\r\nContent-type: ' + contentType + '\r\n\r\n')
                        while True:
                            buffer = f.read(9192)
                            if buffer:
                                cl.send(buffer)
                            else:
                                break
                    except OSError:
                        cl.send('HTTP/1.0 404 OK\r\nContent-type: text/html\r\n\r\nFile Not Found')
        cl.close()
        #del request
        #del cl
        #del addr
        #gc.collect()

    except OSError as e:
        cl.close()
        print('connection closed')
