from PyQt5 import QtWidgets
import sys
import user_interface


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main = user_interface.MainWindow()
    availableGeometry = main.screen().availableGeometry()
    # main.resize(availableGeometry.width() / 1.66, availableGeometry.height() / 1.75)
    main.resize(availableGeometry.width(), availableGeometry.height())

    main.show()
    sys.exit(app.exec_())
