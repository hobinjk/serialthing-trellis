import sys
import time
import board
import busio
import adafruit_trellis_express
import adafruit_adxl34x

properties_data = [
    """{"name":"accel-x","type":"number","value":0}""",
    """{"name":"accel-y","type":"number","value":0}""",
    """{"name":"accel-z","type":"number","value":0}""",
    """{"name":"pressed","type":"string","value":""}""",
    """{"name":"palette","type":"number","value":0,"min":0,"max":1}""",
    """{"name":"color","type":"string","value":"#ffa400"}""",
]


SOH = 1
STX = 2
ETX = 3
EOT = 4


def lrc(data):
    c = 0
    for d in data:
        c += d
    return ((c ^ 0xff) + 1) & 0xff


def send(data_str):
    data = bytes(data_str, 'utf-8')
    buf = [SOH, len(data) & 0xff, 0, STX]
    buf.extend(data)
    buf.extend([ETX, lrc(data), EOT])
    sys.stdout.write(bytes(buf))


def send_property_changed(prop, value):
    send('{"messageType":"propertyChanged","data":{"id":"neotrellis-0","name":"' + prop + '","value":' + value + '}}')


def on_message(msg):
    if "getAdapter" in msg:
        send("""{"messageType":"adapter","data":{"id":"neotrellis","name":"Adafruit NeoTrellis M4","thingCount":1}}""")
    elif "getThingByIdx" in msg:
        send("""{"messageType":"thing","data":{"id":"neotrellis-0","name":"Adafruit NeoTrellis M4","type":"thing","description":"","propertyCount":6}}""")
    elif "getPropertyByIdx" in msg:
        pi_str = "propertyIdx\":"
        pi_i = msg.index(pi_str)
        idx_s = ''
        for c in msg[pi_i + len(pi_str):]:
            if c == '}':
                break
            idx_s += c
        idx = int(idx_s)
        send("""{"messageType":"property","data":""" + properties_data[idx] + "}")
    elif "setProperty" in msg:
        if "palette" in msg:
            val_str = "value\":"
            val_i = msg.index(val_str)
            v_s = ''
            for c in msg[val_i + len(val_str):]:
                if c == ',':
                    break
                v_s += c
            v = int(v_s)
            palette = v
            write_palette(palette)
            send_property_changed("palette", str(palette))


# Our keypad + neopixel driver
trellis = adafruit_trellis_express.TrellisM4Express(rotation=90)

# Our accelerometer
i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
accelerometer = adafruit_adxl34x.ADXL345(i2c)


# Input a value 0 to 255 to get a color value.
def wheel(palette, pos):
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if palette == 0:
        if pos < 85:
            return(int(pos * 3), int(255 - pos*3), 0)
        elif pos < 170:
            pos -= 85
            return(int(255 - pos*3), 0, int(pos * 3))
        else:
            pos -= 170
            return(0, int(pos * 3), int(255 - pos*3))
    elif palette == 1:
        return (pos, pos, pos)


def triplet_to_hex(rgb):
    return "#%0.2x%0.2x%0.2x" % rgb


def write_palette(new_palette):
    global palette
    palette = new_palette
    for i in range(32):
        pixel_index = (i * 256 // 32)
        trellis.pixels._neopixel[i] = wheel(palette, pixel_index & 255)
    trellis.pixels._neopixel.show()


trellis.pixels._neopixel.brightness = 0.25
palette = 0
write_palette(0)

# currently pressed buttons
current_press = set()

while True:
    if len(set(trellis.pressed_keys)) > 0:
        break
    time.sleep(0.1)
    # try:
    #     sys.stdin.read(1)
    #     break
    # except Exception:
    #     pass

# on_message("getAdapter")
# on_message("getThingByIdx")
# on_message("getPropertyByIdx propertyIdx\":0}")
# on_message("getPropertyByIdx propertyIdx\":1}")
# on_message("getPropertyByIdx propertyIdx\":2}")
# on_message("getPropertyByIdx propertyIdx\":3}")
# on_message("getPropertyByIdx propertyIdx\":4}")
# on_message("getPropertyByIdx propertyIdx\":5}")

write_palette(1)

send_property_changed("palette", str(palette))

accel_i = 0

while True:
    try:
        msg = sys.stdin.readline()
        if len(msg) > 1:
            on_message(msg)
            continue
    except Exception as e:
        print(e)
        pass

    # print(sys.stdin.read(1))
    # Check for pressed buttons
    pressed = set(trellis.pressed_keys)
    # send(pressed)
    if pressed != current_press:
        send_property_changed("pressed", '"' + str(trellis.pressed_keys) + '"')
        new_press = pressed - current_press
        if len(new_press) > 0:
            down = new_press.pop()
            x = down[1]
            y = 3 - down[0]
            i = x + y * 8
            pixel_index = (i * 256 // 32)
            send_property_changed("color", '"' + triplet_to_hex(wheel(palette, pixel_index & 255)) + '"')
        current_press = pressed

    accel_i += 1
    if accel_i > 10:
        accel_i = 0
        # Check accelerometer tilt!
        accel_x = accelerometer.acceleration[1]
        accel_y = accelerometer.acceleration[0]
        accel_z = accelerometer.acceleration[2]
        send_property_changed("accel-x", str(accel_x))
        send_property_changed("accel-y", str(accel_y))
        send_property_changed("accel-z", str(accel_z))

    time.sleep(0.1)
