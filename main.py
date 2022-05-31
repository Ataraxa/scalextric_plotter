from PyQt5 import QtWidgets
import background_threads
import plot_gui_class
import sys


class GyroObject(object):
    """App class"""
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.plot = plot_gui_class.AnglePlots()
        # self.plot.show()


if __name__ == '__main__':
    my_gyro = GyroObject()
    update_thread = background_threads.UpdateThread(my_gyro.plot)
    update_thread.start()

    sys.exit(my_gyro.app.exec_())
