from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph import GraphicsLayoutWidget
from threading import Thread, Event
from collections import deque
import serial
from PyQt5.QtGui import QPixmap
import time


# Root window with all widgets
class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Scalextric Python GUI")


        # Creating the labels
        self.sys_info_lbl = QtWidgets.QLabel(f"System Info: Choose you axis")
        self.speed_lbl = QtWidgets.QLabel(f"Current Speed: 0 %")
        self.eqn_lbl = QtWidgets.QLabel(f"Speed Equation: N/A")

        # Connecting to a plot object to get data
        self.target_plot = PlotData(self)

        # Create the grid property manager
        layout = QtWidgets.QGridLayout()

        # Creating the buttons
        rst_btn = QtWidgets.QPushButton("Reset")  # Creating the RESET button
        rst_btn.clicked.connect(self.target_plot.reset)  # Connecting it to the correct function

        self.cal_min_btn = QtWidgets.QPushButton("Start Calibration")
        self.cal_min_btn.clicked.connect(self.target_plot.start_cal)

        self.cal_max_btn = QtWidgets.QPushButton("End Calibration")
        self.cal_max_btn.clicked.connect(self.target_plot.end_cal)

        # Create the table
        self.data_tbl = QtWidgets.QTableWidget(3, 5)
        self.data_tbl.setItem(0, 0, QtWidgets.QTableWidgetItem("Roll"))
        self.data_tbl.setItem(1, 0, QtWidgets.QTableWidgetItem("Pitch"))
        self.data_tbl.setItem(2, 0, QtWidgets.QTableWidgetItem("Yaw"))

        # Create the drop-down menu to select axis
        self.axis_sel = QtWidgets.QComboBox()
        self.axis_sel.addItem("Roll: x-axis")
        self.axis_sel.addItem("Pitch: y-axis")
        self.axis_sel.addItem("Yaw: z-axis")

        # LOGO
        self.pixmap = QPixmap('logo.png')
        self.pix_lbl = QtWidgets.QLabel(self)
        self.pix_lbl.setPixmap(self.pixmap)
        # Add widgets to layout
        # layout.addWidget(rst_btn, 1, 1)
        # layout.addWidget(cal_btn, 2, 1)
        layout.addWidget(self.cal_max_btn, 4, 1)
        layout.addWidget(self.cal_min_btn, 3, 1)
        layout.addWidget(self.sys_info_lbl, 1, 1)
        layout.addWidget(self.speed_lbl, 5, 1)
        # layout.addWidget(self.eqn_lbl, 5, 1)
        # layout.addWidget(self.data_tbl, 7, 1)
        layout.addWidget(self.target_plot.plot, 0, 4, 0, 4)
        layout.addWidget(self.axis_sel, 2, 1)
        layout.addWidget(self.pix_lbl, 0, 1)

        # Add grid to the main window
        self.setLayout(layout)


class PlotData(GraphicsLayoutWidget):

    data_acquired = pyqtSignal()

    def __init__(self, target_gui):
        super().__init__()

        # Create a plot object
        self.plot = pg.PlotWidget()

        # Options for the plot widget
        # self.plot.setAutoVisible(y=1.0)
        # self.plot.enableAutoRange(axis='y', enable=True)
        self.plot.addLegend()

        # Connect to main window
        self.target_gui = target_gui

        # Connection to serial port
        self.ser = self.serial_connect()
        self.data_acquired.connect(self.update_data)

        # Attributes for storage of important properties and objects
        self.data = {}  # Data to be updated
        self.plots = {}  # Collection of the individual plot objects
        self.new_frame = (0, 0, 0)

        # Small variables for calibration
        self.min_pos = (0, 0, 0)
        self.max_pos = (0, 0, 0)

        # Attribute related to speed calculation
        self.speed = 0
        self.speed_eqn = lambda a, b, c: 0

        # Creating the final window
        self._setup_plot()

        # Initialising the update threads
        self.threadkill = Event()
        self.thread = Thread(target=self.generate_data, args=(self.data_acquired.emit, self.threadkill))
        self.thread.start()

    # Kill our data acquisition thread when shutting down
    def closeEvent(self, close_event):
        self.threadkill.set()

    # Slot to receive acquired data and update plot
    @pyqtSlot()
    def update_data(self):
        self.plots["roll"].setData(self.data["roll_data"])
        self.plots["pitch"].setData(self.data["pitch_data"])
        self.plots["yaw"].setData(self.data["yaw_data"])

        self.target_gui.speed_lbl.setText(f"Current speed: {self.speed} %")

    def _setup_plot(self):
        """Function called to create all the relevant data structures"""

        # Creating and setting up the ROOT of the window
        # self.plot = self.addPlot(title=f"Orientation")  # Root object of the GUI
        self.plot.setYRange(-180, 180)
        self.plot.setXRange(0, 100)
        self.plot.showGrid(x=True, y=True, alpha=0.5)
        x_axis = self.plot.getAxis("bottom")
        y_axis = self.plot.getAxis("left")

        x_axis.setLabel(text="Time (s)")
        y_axis.setLabel(text="Angle (°)")

        # Add individual plots
        draw_roll = self.plot.plot(pen='c', name='Roll')
        draw_pitch = self.plot.plot(pen='y', name='Pitch')
        draw_yaw = self.plot.plot(pen='r', name='Yaw')
        draw_speed = self.plot.plot(pen='g', name='Speed')

        self.plots["roll"] = draw_roll
        self.plots["pitch"] = draw_pitch
        self.plots["yaw"] = draw_yaw
        self.plots["speed"] = draw_speed

        self.data["roll_data"] = deque([0]*100)
        self.data["pitch_data"] = deque([0]*100)
        self.data["yaw_data"] = deque([0]*100)
        self.data["speed"] = deque([0]*100)

    def reset(self):
        self.update_thread.reset_trigger.set()  # TODO correct the threading part here
        self.update_sys_info("System Info: Reset Initiated")

    def start_cal(self):
        """Called when calibration should happen. Simply starts a parallel thread that dynamically creates
        a new function"""

        # self.reset()
        r_start = self.data["roll_data"][-1]
        p_start = self.data["pitch_data"][-1]
        y_start = self.data["yaw_data"][-1]
        self.min_pos = (r_start, p_start, y_start)

        self.target_gui.data_tbl.setItem(0, 1, QtWidgets.QTableWidgetItem(f"{r_start}"))
        self.target_gui.data_tbl.setItem(1, 1, QtWidgets.QTableWidgetItem(f"{p_start}"))
        self.target_gui.data_tbl.setItem(2, 1, QtWidgets.QTableWidgetItem(f"{y_start}"))

    def end_cal(self):
        r_end = self.data["roll_data"][-1]
        p_end = self.data["pitch_data"][-1]
        y_end = self.data["yaw_data"][-1]
        self.max_pos = (r_end, p_end, y_end)

        self.target_gui.data_tbl.setItem(0, 2, QtWidgets.QTableWidgetItem(f"{r_end}"))
        self.target_gui.data_tbl.setItem(1, 2, QtWidgets.QTableWidgetItem(f"{p_end}"))
        self.target_gui.data_tbl.setItem(2, 2, QtWidgets.QTableWidgetItem(f"{y_end}"))

        self.speed_eqn = self._gen_eqn()

    def _gen_eqn(self):
        # TODO Use case syntax instead of shitty if/elif
        # Getting th right equation for the right choice of axis
        if self.target_gui.axis_sel.currentIndex() == 0:  # If axis selected is x-axis (roll)
            r_weight = 1
            p_weight = 0
            y_weight = 0

        elif self.target_gui.axis_sel.currentIndex() == 1:  # If axis selected is y-axis (pitch)
            r_weight = 0
            p_weight = 1
            y_weight = 0

        elif self.target_gui.axis_sel.currentIndex() == 2:  # If axis selected is z-axis (yaw)
            r_weight = 0
            p_weight = 0
            y_weight = 1

        def speed_eqn(r, p, y):
            r_per = ((r-self.min_pos[0])/(self.max_pos[0]-self.min_pos[0]))*100
            p_per = ((p-self.min_pos[1])/(self.max_pos[1]-self.min_pos[1]))*100
            y_per = ((y-self.min_pos[2])/(self.max_pos[2]-self.min_pos[2]))*100

            speed = r_per*r_weight + p_per*p_weight + y_per*y_weight

            return speed

        return speed_eqn

    def update_sys_info(self, message):
        self.target_gui.sys_info_lbl.setText(f"System Info:{message}")

    def generate_data(self, callback, threadkill):
        while not threadkill.is_set():

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
                self.new_frame = (roll, pitch, yaw)

                self.data["roll_data"].popleft()
                self.data["roll_data"].append(self.new_frame[0])
                self.data["pitch_data"].popleft()
                self.data["pitch_data"].append(self.new_frame[1])
                self.data["yaw_data"].popleft()
                self.data["yaw_data"].append(self.new_frame[2])

                self.speed = round(self.speed_eqn(self.new_frame[0], self.new_frame[1], self.new_frame[2]), 3)
                clamp = lambda n: max(min(100, n), 0)
                self.speed = clamp(self.speed)
                callback()
                time.sleep(0.001)

    @staticmethod
    def serial_connect():
        try:
            ser = serial.Serial(port="COM5", baudrate=115200)
        except serial.serialutil.SerialException:
            print("Connection Failed")
            ser = None
        ser.reset_input_buffer()
        return ser


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        sys.exit(app.exec_())