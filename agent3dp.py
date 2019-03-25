import serial
import json
import numpy as np
import re
from time import time
from time import sleep
import threading


class Agent3DP:
    def __init__(self, device_path, config_filename="printer_config/prusai3_hictop.json"):
        with open(config_filename, 'r') as f:
            self.config = json.load(f)

        self.printer = serial.Serial(device_path, self.config["baud"])

        self.r = np.zeros(3)
        self.r0 = np.zeros(3)
        self.fan_speed = 0

        self.th = None
        self.is_printing = False
        self.is_abort = False
        self.print_state = 0
        self.eta_seconds = -1
        self.printing_time = -1
        self.send_window = 10

    def send(self, gcode, endline='\r\n'):
        self.printer.write(gcode.encode('utf-8'))
        if endline is not None:
            self.printer.write(endline.encode('utf-8'))

    def receive(self):
        return self.printer.readline().decode('utf-8')

    def autohome(self, axis=(1, 1, 1)):
        axis_str = ''
        pos_tmp = [None, None, None]
        if axis[0] == 1:
            axis_str += 'X '
            pos_tmp[0] = 0.
        if axis[1] == 1:
            axis_str += 'Y '
            pos_tmp[1] = 0.
        if axis[2] == 1:
            axis_str += 'Z'
            pos_tmp[0] = 0.

        self._setValidPos(pos_tmp[0], pos_tmp[1], pos_tmp[2])
        self.send('G28 ' + axis_str)

    def move(self, x=0, y=0, z=0):
        self._setValidPos(x, y, z)

        self._putnozzle()

    def movediff(self, dx, dy, dz):
        self.move(self.r[0] + dx, self.r[1] + dy, self.r[2] + dz)

    def setBedTemperature(self, t):
        if t < 0:
            t = 0
        elif t > self.config['lim_bed_temp']:
            t = self.config['lim_bed_temp']

        self.send('M140 S' + str(t))

    def setNozzleTemperature(self, t):
        if t < 0:
            t = 0
        elif t > self.config['lim_nozzle_temp']:
            t = self.config['lim_nozzle_temp']

        self.send('M104 S' + str(t) + ' T0 ')

    def setFanSpeed(self, speed):
        self.send('M106 S' + str(speed))
        self.fan_speed = speed

    def stopFan(self):
        self.send('M107')
        self.fan_speed = 0

    def startPrint(self, filename, callback=None):
        if self.is_printing:
            return
        self.th = threading.Thread(
                    target=self.__printProc,
                    name="printer_thread",
                    args=(filename, callback)
                    )
        self.th.setDaemon(True)

        self.is_printing = True
        self.th.start()

    def abortPrint(self, safety=True):
        if self.is_printing:
            self.is_abort = True
            self.th.join()
            if safety:
                self.startPrint('termination.gcode')
                self.waitComplete()

    def waitComplete(self):
        self.th.join()

    def getDirectionVector(self):
        dr = self.r - self.r0
        norm = np.linalg.norm(dr)
        if norm == 0:
            return None
        return dr / norm

    def _setValidPos(self, x, y, z):
        self.r0 = self.r.copy()

        if x is not None:
            if x < 0:
                self.r[0] = 0
            elif x <= self.config["lim_x"]:
                self.r[0] = x
            else:
                self.r[0] = self.config["lim_x"]

        if y is not None:
            if y < 0:
                self.r[1] = 0
            elif y <= self.config["lim_y"]:
                self.r[1] = y
            else:
                self.r[1] = self.config["lim_y"]

        if z is not None:
            if z < 0:
                self.r[2] = 0
            elif z <= self.config["lim_z"]:
                self.r[2] = z
            else:
                self.r[2] = self.config["lim_z"]

    def _putnozzle(self):
        self.send("G0 X{} Y{} Z{}".format(self.r[0], self.r[1], self.r[2]))

    def __printProc(self, filename, callback):
        sleep(3.0)
        # start_t = time()

        self.is_printing = True

        with open(filename, 'r') as f:
            for i in range(10):
                gcode = f.readline()
                if re.match('^;TIME:[0-9]+.*$', gcode):
                    self.eta_seconds = int(re.findall('[0-9]+', gcode)[0])
                    if callback is not None:
                        callback(self)
                    break

            f.seek(0)
            count = self.send_window
            for gcode in f:
                if not re.match('^;', gcode):
                    print('SEND: ', gcode, end='')
                    self.send(gcode, endline=None)
                    
                    res = '  '
                    while res[0:2] != 'ok':
                        res = self.receive()

                        if self.is_abort:
                            self.is_printing = False
                            self.eta_seconds = -1
                            return
                        if callback is not None:
                            callback(self)

                    print('RESEIVE:', res, end='')


        self.is_printing = False
        self.eta_seconds = -1


if __name__ == '__main__':
    def testCallback(printer):
        # print('ETA[sec]: ', printer.eta_seconds)
        lefttime = printer.eta_seconds - printer.printing_time
        print('Time Left: ', lefttime)

    printer = Agent3DP('/dev/ttyACM0')
    printer.startPrint(filename='./tmp/test.gcode', callback=testCallback)
    try:
        printer.waitComplete()
    except KeyboardInterrupt:
        printer.abortPrint()
