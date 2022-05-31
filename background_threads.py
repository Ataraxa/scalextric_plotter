import serial
import time
import threading


class SerialCommunication(object):
    def __init__(self, port="COM3", baudrate=115200):
        try:
            self.ser = serial.Serial(port="COM5", baudrate=115200)
        except serial.serialutil.SerialException:
            print("Connection Failed")
        self.tri_angles = (0, 0, 0)
        self.ser.reset_input_buffer()

    def get_data(self):
        while True:
            buf = bytearray()
            for i in range(11):
                buf.extend(self.ser.read())

            if str(buf.hex()[0:3]) != "555":
                self.ser.reset_input_buffer()
                # print(f"{str(buf[0:3].hex())} -> Corrupt Data. Reset...")

            elif buf.hex()[0:4] == "5553":
                hex_buf = buf.hex()
                rollL = int(hex_buf[4:6], 16)
                rollH = int(hex_buf[6:8], 16)
                pitchL = int(hex_buf[8:10], 16)
                pitchH = int(hex_buf[10:12], 16)
                yawL = int(hex_buf[12:14], 16)
                yawH = int(hex_buf[14:16], 16)

                roll = ((((rollH << 8) | rollL)/32768)*180)
                if roll > 180:
                    roll -= 360
                pitch = ((((pitchH << 8) | pitchL)/32768)*180)
                if pitch > 180:
                    pitch -= 360
                yaw = ((((yawH << 8) | yawL)/32768)*180)
                if yaw > 180:
                    yaw -= 360

                self.ser.reset_input_buffer()
                self.tri_angles = (roll, pitch, yaw)
                break
        return self.tri_angles


class UpdateThread(threading.Thread):
    def __init__(self, plot_obj):
        super(UpdateThread, self).__init__()
        self.plot = plot_obj
        self.t0 = time.time()
        self.serial_channel = SerialCommunication()

    def run(self):
        while True:
            ser_data = self.serial_channel.get_data()
            t1 = time.time()
            elapsed_time = t1 - self.t0
            # print(elapsed_time)
            # print(ser_data)
            self.plot.update(elapsed_time, ser_data)
            time.sleep(0.1)  # Frequency defined here
