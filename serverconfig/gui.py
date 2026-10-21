from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from serverconfig import APP_TITLE
from serverconfig.excel_loader import ConfigWorkbook
from serverconfig.machines import CHECKBOX_TYPES, checkbox_type, excel_column, load_machines, machine_map
from serverconfig.settings_store import ACCOUNT_KEYS, SettingsStore
from serverconfig.worker import RunWorker


class SettingsDialog(QDialog):
    def __init__(self, store: SettingsStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("계정 설정")
        self.resize(520, 280)
        self.account_combo = QComboBox()
        for key in ACCOUNT_KEYS:
            self.account_combo.addItem(store.account(key)["name"], key)
        self.name_edit = QLineEdit()
        self.name_edit.setReadOnly(True)
        self.address_edit = QLineEdit()
        self.id_edit = QLineEdit()
        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.Password)
        form = QFormLayout()
        form.addRow("NAME", self.account_combo)
        form.addRow("표시 이름", self.name_edit)
        form.addRow("ADDRESS", self.address_edit)
        form.addRow("ID", self.id_edit)
        form.addRow("PW", self.pw_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.account_combo.currentIndexChanged.connect(self._load_selected)
        self._current_key = None
        self._load_selected()

    def _flush(self) -> None:
        if not self._current_key:
            return
        account = self.store.account(self._current_key)
        account["address"] = self.address_edit.text().strip()
        account["user_id"] = self.id_edit.text().strip()
        account["password"] = self.pw_edit.text()

    def _load_selected(self) -> None:
        self._flush()
        key = self.account_combo.currentData()
        self._current_key = key
        account = self.store.account(key)
        self.name_edit.setText(account["name"])
        self.address_edit.setText(account.get("address", ""))
        self.id_edit.setText(account.get("user_id", ""))
        self.pw_edit.setText(account.get("password", ""))

    def _save(self) -> None:
        self._flush()
        if not self.store.account("test_admin")["user_id"]:
            QMessageBox.warning(self, "확인", "Test Admin ID를 입력하세요.")
            return
        self.store.save()
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(980, 720)
        self.store = SettingsStore()
        self.machines = load_machines()
        self.machine_by_code = machine_map(self.machines)
        self.workbook = None
        self.excel_error = ""
        try:
            self.workbook = ConfigWorkbook()
        except Exception as exc:
            self.excel_error = str(exc)
        self.worker = None
        self._build_ui()
        self._fill_machines()
        self._fill_configs()
        self._refresh_preview()
        if self.excel_error:
            self._log("엑셀을 읽지 못했습니다: " + self.excel_error)
        else:
            self._log("엑셀 컨피그를 읽었습니다: " + str(self.workbook.path))
        self._log("계정 저장소: " + str(self.store.path))

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        top = QHBoxLayout()
        title = QLabel(APP_TITLE)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.set_button = QPushButton("⚙️ SET")
        self.set_button.clicked.connect(self._open_settings)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.set_button)
        layout.addLayout(top)

        row = QHBoxLayout()
        machine_box = QGroupBox("머신 선택")
        machine_layout = QVBoxLayout(machine_box)
        self.machine_combo = QComboBox()
        self.machine_combo.currentIndexChanged.connect(self._on_machine_changed)
        type_row = QHBoxLayout()
        self.type_checks = {}
        for name in CHECKBOX_TYPES:
            box = QCheckBox(name)
            box.stateChanged.connect(self._refresh_preview)
            self.type_checks[name] = box
            type_row.addWidget(box)
        type_row.addStretch()
        self.machine_name_label = QLabel("MACHINE NAME: -")
        machine_layout.addWidget(self.machine_combo)
        machine_layout.addLayout(type_row)
        machine_layout.addWidget(self.machine_name_label)
        row.addWidget(machine_box, 2)

        env_box = QGroupBox("운영 환경 선택")
        env_layout = QVBoxLayout(env_box)
        self.env_test = QRadioButton("테스트 어드민")
        self.env_live = QRadioButton("라이브 어드민")
        self.env_test.setChecked(True)
        env_group = QButtonGroup(self)
        env_group.addButton(self.env_test)
        env_group.addButton(self.env_live)
        env_layout.addWidget(self.env_test)
        env_layout.addWidget(self.env_live)
        row.addWidget(env_box)

        browser_box = QGroupBox("브라우저 선택")
        browser_layout = QVBoxLayout(browser_box)
        self.browser_chrome = QRadioButton("Chrome")
        self.browser_edge = QRadioButton("Edge")
        self.browser_chrome.setChecked(True)
        browser_group = QButtonGroup(self)
        browser_group.addButton(self.browser_chrome)
        browser_group.addButton(self.browser_edge)
        browser_layout.addWidget(self.browser_chrome)
        browser_layout.addWidget(self.browser_edge)
        row.addWidget(browser_box)

        config_box = QGroupBox("컨피그 선택")
        config_layout = QVBoxLayout(config_box)
        self.config_combo = QComboBox()
        self.config_combo.currentIndexChanged.connect(self._refresh_preview)
        self.reload_button = QPushButton("엑셀 다시 읽기")
        self.reload_button.clicked.connect(self._reload_excel)
        config_layout.addWidget(self.config_combo)
        config_layout.addWidget(self.reload_button)
        row.addWidget(config_box, 2)
        layout.addLayout(row)

        self.run_button = QPushButton("실행")
        self.run_button.setMinimumHeight(36)
        self.run_button.clicked.connect(self._on_run)
        layout.addWidget(self.run_button)

        splitter = QSplitter(Qt.Vertical)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("적용 컨피그 내용")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("실행 로그")
        splitter.addWidget(self.preview)
        splitter.addWidget(self.log_view)
        splitter.setSizes([280, 280])
        layout.addWidget(splitter, 1)

    def _fill_machines(self) -> None:
        self.machine_combo.blockSignals(True)
        self.machine_combo.clear()
        for item in self.machines:
            label = f"{item['code']}  {item['name']}  ({item['type']})"
            self.machine_combo.addItem(label, item["code"])
        self.machine_combo.blockSignals(False)
        self._on_machine_changed()

    def _fill_configs(self) -> None:
        self.config_combo.blockSignals(True)
        self.config_combo.clear()
        if self.workbook:
            for name in self.workbook.names:
                self.config_combo.addItem(name)
        self.config_combo.blockSignals(False)

    def _selected_machine(self):
        code = self.machine_combo.currentData()
        return self.machine_by_code.get(code)

    def _selected_types(self):
        return [name for name, box in self.type_checks.items() if box.isChecked()]

    def _on_machine_changed(self) -> None:
        machine = self._selected_machine()
        for box in self.type_checks.values():
            box.blockSignals(True)
            box.setChecked(False)
        if machine:
            target = checkbox_type(machine["type"])
            if target in self.type_checks:
                self.type_checks[target].setChecked(True)
            mac = machine.get("mac") or "(MAC 없음)"
            self.machine_name_label.setText(
                f"MACHINE NAME: {machine['name']}  |  IP: {machine['ip']}  |  MAC: {mac}"
            )
        for box in self.type_checks.values():
            box.blockSignals(False)
        self._refresh_preview()

    def _reload_excel(self) -> None:
        try:
            self.workbook = ConfigWorkbook()
            self.excel_error = ""
            self._fill_configs()
            self._refresh_preview()
            self._log("엑셀을 다시 읽었습니다.")
        except Exception as exc:
            self.excel_error = str(exc)
            QMessageBox.critical(self, "엑셀 오류", str(exc))
            self._log("엑셀 다시 읽기 실패: " + str(exc))

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.store, self)
        dialog.exec_()

    def _active_column(self):
        types = self._selected_types()
        if len(types) != 1:
            return None
        return excel_column(types[0])

    def _refresh_preview(self) -> None:
        if not self.workbook:
            self.preview.setPlainText(self.excel_error or "엑셀을 읽지 못했습니다.")
            return
        name = self.config_combo.currentText()
        column = self._active_column()
        if not name or not column:
            self.preview.setPlainText("머신 타입을 하나만 선택하세요.")
            return
        value, has_value = self.workbook.value(name, column)
        if not has_value:
            self.preview.setPlainText(f"[{name} / {column}] 셀이 비어 있습니다.")
            return
        self.preview.setPlainText(value)

    def _log(self, message: str) -> None:
        self.log_view.append(message)

    def _selected_browser(self) -> str:
        return "Edge" if self.browser_edge.isChecked() else "Chrome"

    def _account_key(self) -> str:
        return "live_admin" if self.env_live.isChecked() else "test_admin"

    def _on_run(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "실행 중", "이미 작업이 진행 중입니다.")
            return
        machine = self._selected_machine()
        if not machine:
            QMessageBox.warning(self, "확인", "MACHINE을 선택하세요.")
            return
        types = self._selected_types()
        if len(types) != 1:
            QMessageBox.warning(self, "확인", "머신 타입을 하나만 선택하세요.")
            return
        if not machine.get("mac"):
            QMessageBox.warning(self, "확인", f"{machine['name']}의 MAC이 규격서에 없습니다. machines.json을 보완하세요.")
            return
        if not self.workbook:
            QMessageBox.warning(self, "확인", "엑셀 컨피그를 읽지 못했습니다.")
            return
        config_name = self.config_combo.currentText()
        column = excel_column(types[0])
        config_text, has_value = self.workbook.value(config_name, column)
        if not has_value:
            QMessageBox.warning(self, "확인", "선택한 컨피그 셀이 비어 있습니다.")
            return
        account = self.store.account(self._account_key())
        if not account.get("user_id") or not account.get("password"):
            QMessageBox.warning(self, "확인", "SET에서 선택한 환경의 ID/PW를 저장하세요.")
            return
        url = account.get("address") or ""
        if not url:
            QMessageBox.warning(self, "확인", "어드민 ADDRESS가 없습니다.")
            return
        if self.env_live.isChecked():
            answer = QMessageBox.question(
                self,
                "라이브 환경 확인",
                f"라이브 어드민에 접속하여 컨피그를 적용합니다.\nURL: {url}\n머신: {machine['name']}\n계속할까요?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                self._log("라이브 실행을 취소했습니다.")
                return
        self._log("작업을 시작합니다.")
        self._log("MACHINE: " + machine["code"] + " / " + machine["name"] + " / " + machine["type"])
        self._log("환경: " + account["name"] + " / " + url)
        self._log("브라우저: " + self._selected_browser())
        self._log("컨피그: " + config_name + " / " + column)
        self.run_button.setEnabled(False)
        self.worker = RunWorker(
            self._selected_browser(),
            url,
            account["user_id"],
            account["password"],
            machine["mac"],
            config_text,
        )
        self.worker.log_message.connect(self._log)
        self.worker.finished_ok.connect(self._on_done)
        self.worker.failed.connect(self._on_fail)
        self.worker.finished.connect(self._restore_run_button)
        self.worker.start()

    def _on_done(self, message: str) -> None:
        self._log(message)
        QMessageBox.information(self, "완료", message)

    def _on_fail(self, message: str) -> None:
        self._log(message)
        QMessageBox.critical(self, "실패", message)

    def _restore_run_button(self) -> None:
        self.run_button.setEnabled(True)

    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.stop_browser()
            self.worker.wait(8000)
        event.accept()
