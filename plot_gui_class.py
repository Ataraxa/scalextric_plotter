import numpy as np
import threading
import time
import pyqtgraph as pg
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot


class AnglePlots(pg.GraphicsLayoutWidget):
    """Class that represents the plot object"""

    def __init__(self):
        super(AnglePlots, self).__init__()

        self.data = {}  # Data to be updated
        self.plots = {}  # Collection of the individual plot objects

        self.period = 1  # Variable used for resetting the time window
        self.speed = 0  # Crap
        self.update_speed_period = 0  # Crap

        self. roll_offset = 0  # To reset the angles
        self.pitch_offset = 0  # ^
        self.yaw_offset = 0  # ^

        self.calibr_coef = {  # ??
            "min_roll": 0,
            "max_roll": 1,
            "min_pitch": 0,
            "max_pitch": 1,
            "min_yaw": 0,
            "max_yaw": 1,

        }

        self._setup_plot()
        self._setup_gui()

    def _setup_plot(self):
        """"""
        self.analog_plot = self.addPlot(title=f"Orientation")
        self.analog_plot.setYRange(-180, 360)
        self.analog_plot.setXRange(0, 30)
        self.analog_plot.showGrid(x=True, y=True, alpha=0.5)
        x_axis = self.analog_plot.getAxis("bottom")
        y_axis = self.analog_plot.getAxis("left")

        x_axis.setLabel(text="Time (s)")
        y_axis.setLabel(text="Angle (°)")

        draw_roll = self.analog_plot.plot(pen='c')
        draw_pitch = self.analog_plot.plot(pen='y')
        draw_yaw = self.analog_plot.plot(pen='r')

        self.plots["roll"] = draw_roll
        self.plots["pitch"] = draw_pitch
        self.plots["yaw"] = draw_yaw

        # Block to add legend to graph. CPU usage stonks...
        # self.legend = pg.LegendItem(offset=(0., .5))
        # self.legend.setParentItem(self.analog_plot.graphicsItem())
        # self.legend.addItem(self.analog_plot, 'HHH')

        self.data["roll_data"] = np.array([], dtype=float)
        self.data["pitch_data"] = np.array([], dtype=float)
        self.data["yaw_data"] = np.array([], dtype=float)
        self.data["time"] = np.array([], dtype=float)

    def _setup_gui(self):
        # General Window Features
        self.setWindowTitle('Graph')

        # Interaction buttons
        reset_btn = QtWidgets.QPushButton('Reset angles', self)
        reset_btn.setToolTip('Click to reset all angles')
        reset_btn.move(150, 70)
        reset_btn.clicked.connect(self._reset)

        calibration_btn = QtWidgets.QPushButton('Calibrate', self)
        calibration_btn.setToolTip('Click to enter calibration mode')
        calibration_btn.move(150, 105)
        calibration_btn.clicked.connect(self._start_cal)

        # Dynamic Labels
        self.speed_lbl = pg.TextItem()
        self.speed_lbl.setText(str(self.speed))
        self.analog_plot.addItem(self.speed_lbl)

        self.rnd_info = pg.TextItem(text='HI THERE', anchor=(0, 1), border='y')
        self.analog_plot.addItem(self.rnd_info)

        self.show()

    @pyqtSlot()
    def _start_cal(self):
        self._reset()
        starting_index = self.data["roll_data"].size - 1
        calibration_rec_thread = CalibrationThread(plot=self, starting_index=starting_index)
        calibration_rec_thread.start()

    def end_recording(self, starting_index):
        last_index = self.data["roll_data"].size - 1

        self.calibr_coef["min_roll"] = np.amin(self.data["roll_data"][starting_index:last_index])
        self.calibr_coef["max_roll"] = np.amax(self.data["roll_data"][starting_index:last_index])
        self.calibr_coef["min_pitch"] = np.amin(self.data["pitch_data"][starting_index:last_index])
        self.calibr_coef["max_pitch"] = np.amax(self.data["pitch_data"][starting_index:last_index])
        self.calibr_coef["min_yaw"] = np.amin(self.data["yaw_data"][starting_index:last_index])
        self.calibr_coef["max_yaw"] = np.amax(self.data["yaw_data"][starting_index:last_index])

        # print(self.calibr_coef)

    @pyqtSlot()
    def _reset(self):
        self.roll_offset = self.data["roll_data"][-1]+self.roll_offset
        self.pitch_offset = self.data["pitch_data"][-1]+self.pitch_offset
        self.yaw_offset = self.data["yaw_data"][-1]+self.yaw_offset

    def update(self, time_point, data):
        new_roll_point = data[0]-self.roll_offset
        new_pitch_point = data[1]-self.pitch_offset
        new_yaw_point = data[2]-self.yaw_offset % 180 + 90

        new_roll = np.append(self.data["roll_data"], new_roll_point)
        new_pitch = np.append(self.data["pitch_data"], new_pitch_point)
        new_yaw = np.append(self.data["yaw_data"], new_yaw_point)
        new_time = np.append(self.data["time"], time_point-(30*(self.period-1)))

        self.plots["roll"].setData(new_time, new_roll)
        self.plots["pitch"].setData(new_time, new_pitch)
        self.plots["yaw"].setData(new_time, new_yaw)

        r_max = self.calibr_coef["max_roll"]
        r_min = self.calibr_coef["min_roll"]
        p_max = self.calibr_coef["max_pitch"]
        p_min = self.calibr_coef["min_pitch"]
        y_max = self.calibr_coef["max_yaw"]
        y_min = self.calibr_coef["min_yaw"]

        # roll_coeff = (new_roll_point-r_max)/(r_min-r_max)
        # pitch_coeff = (new_pitch_point-p_max)/(p_min-p_max)
        # yaw_coeff = (new_yaw_point-y_max)/(y_min-y_max)
        # self.speed = (abs(roll_coeff)*(r_min-r_max) + abs(pitch_coeff)*(p_min-p_max)) / ((r_min-r_max) + (p_min-p_max))
        # print(f"Speed: {self.speed*100}%")

            # self.speed = (roll_coeff + pitch_coeff + yaw_coeff)/300
            # self.speed_lbl.setText(f"Speed: {self.speed*100}%")

        if new_time[-1] > 30:
            self.data["roll_data"] = np.array([], dtype=float)
            self.data["pitch_data"] = np.array([], dtype=float)
            self.data["yaw_data"] = np.array([], dtype=float)
            self.data["time"] = np.array([], dtype=float)
            self.period += 1
        else:
            self.data["roll_data"] = new_roll
            self.data["pitch_data"] = new_pitch
            self.data["yaw_data"] = new_yaw
            self.data["time"] = new_time


class CalibrationThread(threading.Thread):
    def __init__(self, plot, starting_index):
        super(CalibrationThread, self).__init__()
        self.target = plot
        self.starting_index = starting_index

    def run(self):
        time.sleep(5)
        self.target.end_recording(self.starting_index)
