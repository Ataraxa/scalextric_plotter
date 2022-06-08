from PyQt5 import QtWidgets
import pyqtgraph as pg
from PyQt5.QtCore import pyqtSlot
import background_threading
from collections import deque


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Scalextric Python GUI")

        # Creating the labels
        self.sys_info_lbl = QtWidgets.QLabel(f"System Info: Initialised")
        self.speed_lbl = QtWidgets.QLabel(f"Current Speed: 0 %")
        self.eqn_lbl = QtWidgets.QLabel(f"Speed Equation: N/A")

        # Connecting to a plot object to get data
        self.aux_plot = CalibrationPlot(self)
        self.target_plot = PlotData(self, self.aux_plot)

        # Create the grid property manager
        layout = QtWidgets.QGridLayout()

        # Creating the buttons
        rst_btn = QtWidgets.QPushButton("Reset")  # Creating the RESET button
        rst_btn.clicked.connect(self.target_plot.reset)  # Connecting it to the correct function
        
        # cal_btn = QtWidgets.QPushButton("Calibrate")
        # cal_btn.clicked.connect(self.target_plot.start_cal)

        # TODO Keep that idea in mind
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

        # Add widgets to layout
        layout.addWidget(rst_btn, 1, 1)
        # layout.addWidget(cal_btn, 2, 1)
        layout.addWidget(self.cal_max_btn, 2, 1)
        layout.addWidget(self.cal_min_btn, 2, 0)
        layout.addWidget(self.sys_info_lbl, 3, 1)
        layout.addWidget(self.speed_lbl, 4, 1)
        layout.addWidget(self.eqn_lbl, 5, 1)
        layout.addWidget(self.data_tbl, 7, 1)
        layout.addWidget(self.target_plot.plot, 0, 4, 0, 4)
        layout.addWidget(self.axis_sel, 6, 1)

        # Add grid to the main window
        self.setLayout(layout)


class PlotData(object):
    def __init__(self, target_gui, aux_plot):
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

        self.aux_plot = aux_plot

        # Attributes for storage of important properties and objects
        self.data = {}  # Data to be updated
        self.plots = {}  # Collection of the individual plot objects

        # Small variables for calibration
        self.min_pos = (0, 0, 0)
        self.max_pos = (0, 0, 0)
        self.calibration_len = 0  # Number of points recorded during the calibration part

        # Attribute related to speed calculation
        self.speed = 0
        self.speed_eqn = lambda a, b, c: 0

        # Creating the final window
        self._setup_plot()

        # Initialising the update threads
        self.update_thread = background_threading.UpdatePlotThread(self, aux_plot)
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
        draw_speed = self.plot.plot(pen='g', name='Speed')

        self.plots["roll"] = draw_roll
        self.plots["pitch"] = draw_pitch
        self.plots["yaw"] = draw_yaw
        self.plots["speed"] = draw_speed

        # Block to add legend to graph. CPU usage stonks...
        # self.legend = pg.LegendItem(offset=(0., .5))
        # self.legend.setParentItem(self.analog_plot.graphicsItem())
        # self.legend.addItem(self.analog_plot, 'HHH')

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

        self.reset()
        self.aux_plot.data_reset()
        self.update_thread.calibration_counter.set()
        r_start = self.data["roll_data"][-1]
        p_start = self.data["pitch_data"][-1]
        y_start = self.data["yaw_data"][-1]
        self.min_pos = (r_start, p_start, y_start)

        self.target_gui.data_tbl.setItem(0, 1, QtWidgets.QTableWidgetItem(f"{r_start}"))
        self.target_gui.data_tbl.setItem(1, 1, QtWidgets.QTableWidgetItem(f"{p_start}"))
        self.target_gui.data_tbl.setItem(2, 1, QtWidgets.QTableWidgetItem(f"{y_start}"))

        # calibration_thread = background_threading.CalibrationThread(self, self.update_thread, self.aux_plot)
        # calibration_thread.start()

    def end_cal(self):
        self.update_thread.calibration_counter.clear()

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

        self.data["speed"].popleft()
        self.data["speed"].append(speed)
        self.plots["speed"].setData(self.data["speed"])


# DO NOT USE !!
class CalibrationPlot(object):
    def __init__(self, target_gui):
        super(CalibrationPlot, self).__init__()

        self.plot = pg.PlotWidget()

        self.target_gui = target_gui

        self.data = {}
        self.plots = {}

        self._setup_plot()

    def _setup_plot(self):
        self.plot.setYRange(-180, 180)
        self.plot.setXRange(0, 140)
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

        self.data["roll_data"] = deque()
        self.data["pitch_data"] = deque()
        self.data["yaw_data"] = deque()

    def data_reset(self):
        self.data["roll_data"] = deque()
        self.data["pitch_data"] = deque()
        self.data["yaw_data"] = deque()

    def update(self, data):

        # TODO Update the update_function to fit new data structure deque (DONE?)
        new_roll_point = data[0]
        new_pitch_point = data[1]
        new_yaw_point = data[2]

        self.data["roll_data"].append(new_roll_point)
        self.data["pitch_data"].append(new_pitch_point)
        self.data["yaw_data"].append(new_yaw_point)

        self.plots["roll"].setData(self.data["roll_data"])
        self.plots["pitch"].setData(self.data["pitch_data"])
        self.plots["yaw"].setData(self.data["yaw_data"])

