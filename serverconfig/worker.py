from PyQt5.QtCore import QThread, pyqtSignal

from serverconfig.automation import AdminAutomation, AutomationError


class RunWorker(QThread):
    log_message = pyqtSignal(str)
    finished_ok = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, browser: str, url: str, user_id: str, password: str, mac: str, config_text: str) -> None:
        super().__init__()
        self.browser = browser
        self.url = url
        self.user_id = user_id
        self.password = password
        self.mac = mac
        self.config_text = config_text
        self._automation: AdminAutomation = None

    def run(self) -> None:
        automation = AdminAutomation(self.browser, self.log_message.emit)
        self._automation = automation
        try:
            automation.start()
            automation.run(self.url, self.user_id, self.password, self.mac, self.config_text)
            self.finished_ok.emit("작업을 완료했습니다.")
        except AutomationError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit("예상하지 못한 오류: " + str(exc))
        finally:
            automation.close()

    def stop_browser(self) -> None:
        if self._automation:
            self._automation.close()
