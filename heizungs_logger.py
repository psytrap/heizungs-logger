import serial
import serial.tools.list_ports
import argparse
import json
import time
import board
import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd
import datetime
import dateutil.tz
import sys
import os.path


STARTUP_DELAY = 3.0
CONVERSION_DELAY = 5.0
RATE=20
LCD_COLUMNS = 16
LCD_ROWS = 2
i2c = board.I2C()
lcd = character_lcd.Character_LCD_RGB_I2C(i2c, LCD_COLUMNS, LCD_ROWS)
lcd.clear()
lcd.color = [100, 0, 0]


parser = argparse.ArgumentParser()
parser.add_argument("--list", help="List available serial devices", action="store_true")
parser.add_argument("--log_directory", help="Directory to place the logs", type=str)
parser.add_argument("--port", help="Send message to the serial port", type=str)
args = parser.parse_args()

if args.list is True:
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        print("{}: {} [{}]".format(port, desc, hwid))
    exit()

if args.port is None:
    print("No port defined")
    print()
    parser.print_help()
    exit()

if args.log_directory is not None:
   log_directory = args.log_directory
else:
   log_directory = "./"

with serial.Serial(args.port, 9600, timeout=1) as ser:
    time.sleep(STARTUP_DELAY)
    while True:
        next = datetime.datetime.utcnow() + datetime.timedelta(seconds=RATE)
        try:
            ser.reset_input_buffer()
            time.sleep(.1)
            str(ser.write(b'x'))
            ser.flush()
            time.sleep(CONVERSION_DELAY)
            line = ser.readline()
            data = line.decode("utf-8").strip().split(" ")
            print(data)
            lcd.clear()
            lcd.cursor_position(0,0)
            lcd.message = data[1]
            lcd.cursor_position(6,0)
            lcd.message = data[2]
            lcd.cursor_position(12,0)
            lcd.message = data[6]

            lcd.cursor_position(0,1)
            lcd.message = data[3]
            lcd.cursor_position(6,1)
            lcd.message = data[4]
            lcd.cursor_position(12,1)
            lcd.message = data[7]

            after =  datetime.datetime.utcnow() #tz=dateutil.tz.tzlocal())
            delta = next - after
            print(delta.total_seconds())
            time.sleep(delta.total_seconds())
            date = next.astimezone(dateutil.tz.tzlocal()).isoformat()
            print(date)
            data.append(date)
            filename = os.path.join(log_directory, "LOG-" + next.astimezone(dateutil.tz.tzlocal()).date().isoformat() + ".json")
            with open(filename, 'a') as file:
                print(str(data), file=file)
            next = next + datetime.timedelta(seconds=RATE)
        except KeyboardInterrupt:
            sys.exit(0)








