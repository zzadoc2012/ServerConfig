import sys

from PyQt5.QtCore import QLibraryInfo, QLocale, QTranslator
from PyQt5.QtWidgets import QApplication, QMessageBox

from serverconfig.gui import MainWindow


def install_korean_qt(app: QApplication) -> None:
    QLocale.setDefault(QLocale(QLocale.Korean, QLocale.SouthKorea))
    translator = QTranslator(app)
    translations = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    if translator.load(QLocale(QLocale.Korean), "qtbase", "_", translations):
        app.installTranslator(translator)
    app.setProperty("qt_ko_translator", translator)


def main() -> int:
    app = QApplication(sys.argv)
    install_korean_qt(app)
    try:
        window = MainWindow()
    except Exception as exc:
        QMessageBox.critical(None, "시작 실패", str(exc))
        return 1
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
