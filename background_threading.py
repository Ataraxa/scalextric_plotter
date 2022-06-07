import serial
import time
import threading
import struct
import itertools


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


class UpdatePlotThread(threading.Thread):
    """Main Thread:
    - Continuously run to update the data on the main window.
    - At each update iteration, if reset trigger is on, reset the angles then set the trigger
    to False"""

    def __init__(self, plot_obj):
        super(UpdatePlotThread, self).__init__()
        self.plot = plot_obj  # Set the target object
        self.serial_channel = SerialCommunication()  # Open serial communication

        # Reset-related attributes
        self.reset_trigger = threading.Event()  # Reset event used in the RUN loop
        self.rst_z = b'\xFF\xAA\x52'  # Hex command to reset Z-axis
        self.rst_xy = b'\xFF\xAA\x67'  # Hex command to reset XY-axis

        self.roll_offset = 0  # Here offset value should be stored when reset is triggered
        self.pitch_offset = 0
        self.yaw_offset = 0

        # Calibration-related attributes
        self.calibration_counter = threading.Event()

    def run(self):
        while True:

            # Preliminary block to reset if reset command is TRUE (before getting data)
            if self.reset_trigger.isSet():
                # print('RESET')
                # self.serial_channel.ser.write(self.rst_xy)
                # self.serial_channel.ser.write(self.rst_z)

                self.roll_offset += roll
                self.pitch_offset += pitch
                self.yaw_offset += yaw

                # self.plot.update_relay("Axis position reset successfully")
                self.reset_trigger.clear()

                self.plot.update_sys_info("Reset Successfully Performed")

            # Block to get data and update the main window (plot)
            roll, pitch, yaw = self.serial_channel.get_data()

            roll -= self.roll_offset
            pitch -= self.pitch_offset
            yaw -= self.yaw_offset

            self.plot.update((roll, pitch, yaw))

            # Block to add a point to the calibration counter on the main window
            if self.calibration_counter.isSet():
                self.plot.calibration_len += 1

            # Frequency defined here
            time.sleep(0.05)  # Number inside represents the PERIOD of the data_getter


class CalibrationThread(threading.Thread):
    def __init__(self, plot, update_thread):
        super(CalibrationThread, self).__init__()
        self.target = plot
        self.aux_thread = update_thread
        self.eqn_cst = {  # Constants and other useful data about the speed equation
            "roll": [0, 1, True],  # [0]: min val, [1]: max val, [2]: True if non-negligible
            "pitch": [0, 1, True],  # Same convention for other axes !
            "yaw": [0, 1, True],
        }

    def run(self):
        self.target.update_sys_info("Calibration has started")
        # TODO Finish the calibration function:
        # TODO - Add min and max to thread attributes DONE
        # TODO - Generate equation DONE
        size = len(list(self.target.data["roll_data"]))
        time.sleep(7)
        self.aux_thread.calibration_counter.clear()
        self.eqn_cst["roll"][0] = min(list(self.target.data["roll_data"])[-size:])
        self.eqn_cst["roll"][1] = max(list(self.target.data["roll_data"])[-size:])
        self.eqn_cst["pitch"][0] = min(list(self.target.data["pitch_data"])[-size:])
        self.eqn_cst["pitch"][1] = max(list(self.target.data["pitch_data"])[-size:])
        self.eqn_cst["yaw"][0] = min(list(self.target.data["yaw_data"])[-size:])
        self.eqn_cst["yaw"][1] = max(list(self.target.data["yaw_data"])[-size:])

        self.target.speed_eqn = self.gen_eqn()

        self.target.update_sys_info("Calibration Successful")

    # TODO Yep need to finish this
    def gen_eqn(self):
        roll_slope = self.eqn_cst["roll"][1]-self.eqn_cst["roll"][0]
        pitch_slope = self.eqn_cst["pitch"][1]-self.eqn_cst["pitch"][0]
        yaw_slope = self.eqn_cst["yaw"][1]-self.eqn_cst["yaw"][0]

        den_weight = (roll_slope + pitch_slope + yaw_slope)

        r_min = self.eqn_cst["roll"][0]
        p_min = self.eqn_cst["pitch"][0]
        y_min = self.eqn_cst["yaw"][0]

        def speed_eqn(roll, pitch, yaw):
            r_per = (roll-r_min)/roll_slope*100  # Percentage of completion of roll axis
            p_per = (pitch-p_min)/pitch_slope*100  # ^ but for pitch
            y_per = (yaw-y_min)/yaw_slope*100  # ^but for yaw

            speed = (r_per*roll_slope + p_per*pitch_slope + y_per*5)/den_weight

            return round(speed, 3)

        print(self.eqn_cst)
        return speed_eqn


class UpdateSpeedThread(threading.Thread):

    def __init__(self, plot):
        super(UpdateSpeedThread, self).__init__()
        self.target = plot

    def run(self):
        while True:
            time.sleep(3)
            self.target.speed += 1
            self.target.speed_lbl.setText(str(self.target.speed))
