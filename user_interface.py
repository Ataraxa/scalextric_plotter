from PyQt5 import QtWidgets
import pyqtgraph as pg
from PyQt5.QtCore import pyqtSlot
import background_threading
from collections import deque


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Scalextric Python GUI")

        # Connecting to a plot object to get data
        self.target_plot = PlotData(self)

        # Create the grid property manager
        layout = QtWidgets.QGridLayout()

        # Creating the buttons
        rst_btn = QtWidgets.QPushButton("Reset")  # Creating the RESET button
        rst_btn.clicked.connect(self.target_plot.reset)  # Connecting it to the correct function

        cal_btn = QtWidgets.QPushButton("Calibrate")
        cal_btn.clicked.connect(self.target_plot.start_cal)
        
        # Creating the labels
        self.sys_info_lbl = QtWidgets.QLabel(f"System Info: {self.target_plot.sys_info}")
        self.speed_lbl = QtWidgets.QLabel(f"Current Speed: {self.target_plot.speed}")
        self.eqn_lbl = QtWidgets.QLabel(f"Speed Equation: N/A")
        
        # Create the table
        self.data_tbl = QtWidgets.QTableWidget(3, 3)

        # Add widgets to layout
        layout.addWidget(rst_btn, 1, 1)
        layout.addWidget(cal_btn, 2, 1)
        layout.addWidget(self.sys_info_lbl, 3, 1)
        layout.addWidget(self.speed_lbl, 4, 1)
        layout.addWidget(self.eqn_lbl, 5, 1)
        layout.addWidget(self.data_tbl, 6, 1)
        layout.addWidget(self.target_plot.plot, 0, 2, 0, 2)

        # Add grid to the main window
        self.setLayout(layout)


class PlotData(object):
    def __init__(self, target_gui):
        super(PlotData, self).__init__()

        # Create a plot object
        self.plot = pg.PlotWidget()

        # Options for the plot widget
        # self.plot.setAutoVisible(y=1.0)
        # self.plot.enableAutoRange(axis='y', enable=True)
        self.plot.addLegend()

        # System Info for debugging
        self.sys_info = "Plot Initialised"
        self.target_gui = target_gui

        # Attributes for storage of important properties and objects
        self.data = {}  # Data to be updated
        self.plots = {}  # Collection of the individual plot objects

        # Small variables for calibration
        self.calibration_len = 0  # Number of points recorded during the calibration part

        # Attribute related to speed calculation
        self.speed = 0
        self.speed_eqn = lambda a, b, c: 0

        # Creating the final window
        self._setup_plot()

        # Initialising the update threads
        self.update_thread = background_threading.UpdatePlotThread(self)
        self.update_thread.start()

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

        self.plots["roll"] = draw_roll
        self.plots["pitch"] = draw_pitch
        self.plots["yaw"] = draw_yaw

        # Block to add legend to graph. CPU usage stonks...
        # self.legend = pg.LegendItem(offset=(0., .5))
        # self.legend.setParentItem(self.analog_plot.graphicsItem())
        # self.legend.addItem(self.analog_plot, 'HHH')

        self.data["roll_data"] = deque([0]*100)
        self.data["pitch_data"] = deque([0]*100)
        self.data["yaw_data"] = deque([0]*100)

    def reset(self):
        self.update_thread.reset_trigger.set()  # TODO correct the threading part here
        self.update_sys_info("System Info: Reset Initiated")

    def start_cal(self):
        """Called when calibration should happen. Simply starts a parallel thread that dynamically creates
        a new function"""

        self.reset()
        self.update_thread.calibration_counter.set()
        calibration_thread = background_threading.CalibrationThread(self, self.update_thread)
        calibration_thread.start()

    def update_sys_info(self, message):
        self.target_gui.sys_info_lbl.setText(f"System Info:{message}")

    def update(self, data):

        # TODO Update the update_function to fit new data structure deque (DONE?)
        new_roll_point = data[0]
        new_pitch_point = data[1]
        new_yaw_point = data[2]

        self.data["roll_data"].popleft()
        self.data["roll_data"].append(new_roll_point)
        self.data["pitch_data"].popleft()
        self.data["pitch_data"].append(new_pitch_point)
        self.data["yaw_data"].popleft()
        self.data["yaw_data"].append(new_yaw_point)

        self.plots["roll"].setData(self.data["roll_data"])
        self.plots["pitch"].setData(self.data["pitch_data"])
        self.plots["yaw"].setData(self.data["yaw_data"])
        
        speed = self.speed_eqn(new_roll_point, new_pitch_point, new_yaw_point)
        self.target_gui.speed_lbl.setText(f"Current speed: {speed} %")
