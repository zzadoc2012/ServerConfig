import sys

from PyQt5.QtWidgets import QApplication, QMessageBox

from serverconfig.gui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    try:
        window = MainWindow()
    except Exception as exc:
        QMessageBox.critical(None, "시작 실패", str(exc))
        return 1
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
