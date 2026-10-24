from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import (
    QApplication,
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
    QListView,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from serverconfig import APP_TITLE
from serverconfig.excel_loader import ConfigWorkbook
from serverconfig.machines import (
    CHECKBOX_TYPES,
    checkbox_type,
    excel_column,
    load_machines,
    machine_label,
    machine_location,
    machine_map,
)
from serverconfig.settings_store import ACCOUNT_KEYS, SettingsStore
from serverconfig.worker import RunWorker

CONFIG_PLACEHOLDER = "적용할 컨피그를 선택하세요"
MACHINE_PLACEHOLDER = "적용할 머신을 선택하세요"


COMBO_ITEM_HEIGHT = 24
COMBO_ITEM_SPACING = 3
LOCATION_ROLE = Qt.UserRole + 1
LOCATION_COL_X = 168


class TallComboDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width(), max(size.height(), COMBO_ITEM_HEIGHT))


class MachineComboDelegate(TallComboDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        widget = opt.widget
        style = widget.style() if widget is not None else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, widget)

        machine_text = index.data(Qt.DisplayRole) or ""
        location = (index.data(LOCATION_ROLE) or "").strip()
        painter.setPen(opt.palette.color(QPalette.Text))

        item_rect = opt.rect
        left_rect = QRect(item_rect.left() + 8, item_rect.top(), LOCATION_COL_X - 8, item_rect.height())
        painter.drawText(left_rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextSingleLine, machine_text)
        if location:
            loc_rect = QRect(
                item_rect.left() + LOCATION_COL_X,
                item_rect.top(),
                max(0, item_rect.width() - LOCATION_COL_X - 8),
                item_rect.height(),
            )
            painter.drawText(loc_rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextSingleLine, "(" + location + ")")

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(max(size.width(), LOCATION_COL_X + 90), size.height())


def style_select_combo(combo: QComboBox, machine: bool = False) -> None:
    view = QListView()
    view.setSpacing(COMBO_ITEM_SPACING)
    view.setUniformItemSizes(True)
    combo.setView(view)
    combo.setItemDelegate(MachineComboDelegate(combo) if machine else TallComboDelegate(combo))
    combo.setStyleSheet(
        "QComboBox QAbstractItemView::item {"
        f" min-height: {COMBO_ITEM_HEIGHT}px;"
        " padding-top: 4px; padding-bottom: 4px;"
        " }"
    )

ACCOUNT_LABELS = {
    "test_admin": "테스트 어드민",
    "live_admin": "라이브 어드민",
}


def korean_buttons(box: QMessageBox) -> None:
    yes = box.button(QMessageBox.Yes)
    no = box.button(QMessageBox.No)
    if yes:
        yes.setText("예")
    if no:
        no.setText("아니오")


class SettingsDialog(QDialog):
    def __init__(self, store: SettingsStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("계정 설정")
        self.resize(520, 280)
        self.account_combo = QComboBox()
        for key in ACCOUNT_KEYS:
            self.account_combo.addItem(ACCOUNT_LABELS[key], key)
        self.name_edit = QLineEdit()
        self.name_edit.setReadOnly(True)
        self.address_edit = QLineEdit()
        self.id_edit = QLineEdit()
        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.Password)
        form = QFormLayout()
        form.addRow("계정", self.account_combo)
        form.addRow("표시 이름", self.name_edit)
        form.addRow("주소", self.address_edit)
        form.addRow("아이디", self.id_edit)
        form.addRow("비밀번호", self.pw_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("저장")
        buttons.button(QDialogButtonBox.Cancel).setText("취소")
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
        self.name_edit.setText(ACCOUNT_LABELS.get(key, account["name"]))
        self.address_edit.setText(account.get("address", ""))
        self.id_edit.setText(account.get("user_id", ""))
        self.pw_edit.setText(account.get("password", ""))

    def _save(self) -> None:
        self._flush()
        if not self.store.account("test_admin")["user_id"]:
            QMessageBox.warning(self, "확인", "테스트 어드민 아이디를 입력하세요.")
            return
        self.store.save()
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(980, 720)
        self.store = SettingsStore()
        self.machines = []
        self.machine_by_code = {}
        self.workbook = None
        self.excel_error = ""
        self.worker = None
        self._current_mac = ""
        self._build_ui()
        self._reload_source_data()
        self._fill_machines()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        top = QHBoxLayout()
        title = QLabel(APP_TITLE)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.set_button = QPushButton("⚙️ 설정")
        self.set_button.clicked.connect(self._open_settings)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.set_button)
        layout.addLayout(top)

        row = QHBoxLayout()
        machine_box = QGroupBox("머신 선택")
        machine_layout = QVBoxLayout(machine_box)
        self.machine_combo = QComboBox()
        style_select_combo(self.machine_combo, machine=True)
        self.machine_combo.currentIndexChanged.connect(self._on_machine_changed)
        type_row = QHBoxLayout()
        self.type_checks = {}
        for name in CHECKBOX_TYPES:
            box = QCheckBox(name)
            box.setEnabled(False)
            self.type_checks[name] = box
            type_row.addWidget(box)
        type_row.addStretch()
        info_row = QHBoxLayout()
        self.machine_name_label = QLabel("위치: -")
        self.machine_name_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.copy_mac_button = QPushButton("Copy")
        self.copy_mac_button.setFixedWidth(56)
        self.copy_mac_button.setEnabled(False)
        self.copy_mac_button.clicked.connect(self._copy_mac)
        info_row.addWidget(self.machine_name_label, 1)
        info_row.addWidget(self.copy_mac_button)
        machine_layout.addWidget(self.machine_combo)
        machine_layout.addLayout(type_row)
        machine_layout.addLayout(info_row)
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
        self.browser_chrome = QRadioButton("크롬")
        self.browser_edge = QRadioButton("엣지")
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
        style_select_combo(self.config_combo)
        self.config_combo.currentIndexChanged.connect(self._refresh_preview)
        config_layout.addWidget(self.config_combo)
        row.addWidget(config_box, 2)
        layout.addLayout(row)

        self.run_button = QPushButton("실행")
        self.run_button.setMinimumHeight(36)
        self.run_button.clicked.connect(self._on_run)
        layout.addWidget(self.run_button)

        splitter = QSplitter(Qt.Vertical)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("적용할 컨피그를 선택하면 여기에 상세 내역이 표시됩니다.")
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
        self.machine_combo.addItem(MACHINE_PLACEHOLDER, None)
        for item in self.machines:
            self.machine_combo.addItem(f"{item['type']} {item['code']}", item["code"])
            self.machine_combo.setItemData(self.machine_combo.count() - 1, machine_location(item), LOCATION_ROLE)
        self.machine_combo.setCurrentIndex(0)
        self.machine_combo.blockSignals(False)
        self._on_machine_changed()

    def _fill_configs(self, keep_selection: bool = False) -> None:
        previous = self._selected_config_name() if keep_selection else None
        self.config_combo.blockSignals(True)
        self.config_combo.clear()
        self.config_combo.addItem(CONFIG_PLACEHOLDER, None)
        column = self._active_column()
        names = []
        if self.workbook and column:
            names = self.workbook.names_for_column(column)
            for name in names:
                self.config_combo.addItem(name, name)
        if previous and previous in names:
            self.config_combo.setCurrentIndex(self.config_combo.findData(previous))
        else:
            self.config_combo.setCurrentIndex(0)
        self.config_combo.blockSignals(False)
        self._refresh_preview()

    def _selected_machine(self):
        code = self.machine_combo.currentData()
        return self.machine_by_code.get(code)

    def _selected_types(self):
        return [name for name, box in self.type_checks.items() if box.isChecked()]

    def _on_machine_changed(self) -> None:
        machine = self._selected_machine()
        for box in self.type_checks.values():
            box.setChecked(False)
        self._current_mac = ""
        if machine:
            target = checkbox_type(machine["type"])
            if target in self.type_checks:
                self.type_checks[target].setChecked(True)
            mac = (machine.get("mac") or "").strip()
            self._current_mac = mac
            mac_text = mac or "(MAC 없음)"
            location = machine_location(machine) or "-"
            self.machine_name_label.setText(
                f"위치: {location}  |  IP: {machine['ip']}  |  MAC: {mac_text}"
            )
        else:
            self.machine_name_label.setText("위치: -")
        self.copy_mac_button.setEnabled(bool(self._current_mac))
        self._fill_configs()

    def _copy_mac(self) -> None:
        if not self._current_mac:
            QMessageBox.information(self, "확인", "복사할 MAC이 없습니다.")
            return
        QApplication.clipboard().setText(self._current_mac)
        self._log("MAC 주소를 클립보드에 복사했습니다.")

    def _reload_source_data(self, machines: bool = True, excel: bool = True) -> None:
        if machines:
            try:
                self.machines = load_machines()
                self.machine_by_code = machine_map(self.machines)
                self._log("내장 머신 목록을 읽었습니다. (" + str(len(self.machines)) + "대)")
            except Exception as exc:
                self.machines = []
                self.machine_by_code = {}
                self._log("머신 목록을 읽지 못했습니다: " + str(exc))
        if excel:
            try:
                self.workbook = ConfigWorkbook()
                self.excel_error = ""
                self._log("내장 엑셀 컨피그를 읽었습니다.")
            except Exception as exc:
                self.workbook = None
                self.excel_error = str(exc)
                self._log("엑셀을 읽지 못했습니다: " + self.excel_error)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.store, self)
        dialog.exec_()

    def _active_column(self):
        types = self._selected_types()
        if len(types) != 1:
            return None
        return excel_column(types[0])

    def _selected_config_name(self):
        name = self.config_combo.currentData()
        if not name:
            return None
        return name

    def _refresh_preview(self) -> None:
        if not self.workbook:
            self.preview.clear()
            return
        name = self._selected_config_name()
        if not name:
            self.preview.clear()
            return
        column = self._active_column()
        if not column:
            self.preview.clear()
            return
        value, has_value = self.workbook.value(name, column)
        if not has_value:
            self.preview.clear()
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
            QMessageBox.warning(self, "확인", "머신을 선택하세요.")
            return
        types = self._selected_types()
        if len(types) != 1:
            QMessageBox.warning(self, "확인", "머신 타입을 하나만 선택하세요.")
            return
        if not machine.get("mac"):
            QMessageBox.warning(self, "확인", f"{machine_label(machine)}의 MAC이 없습니다. 머신 목록을 보완하세요.")
            return
        if not self.workbook:
            QMessageBox.warning(self, "확인", "엑셀 컨피그를 읽지 못했습니다.")
            return
        config_name = self._selected_config_name()
        if not config_name:
            QMessageBox.warning(self, "확인", "적용할 컨피그를 선택하세요.")
            return
        column = excel_column(types[0])
        config_text, has_value = self.workbook.value(config_name, column)
        if not has_value:
            QMessageBox.warning(self, "확인", "선택한 컨피그 셀이 비어 있습니다.")
            return
        account = self.store.account(self._account_key())
        if not account.get("user_id") or not account.get("password"):
            QMessageBox.warning(self, "확인", "설정에서 선택한 환경의 아이디와 비밀번호를 저장하세요.")
            return
        url = account.get("address") or ""
        if not url:
            QMessageBox.warning(self, "확인", "어드민 주소가 없습니다.")
            return
        if self.env_live.isChecked():
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Question)
            box.setWindowTitle("라이브 환경 확인")
            box.setText(
                f"라이브 어드민에 접속하여 컨피그를 적용합니다.\n주소: {url}\n머신: {machine_label(machine)}\n계속할까요?"
            )
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.setDefaultButton(QMessageBox.No)
            korean_buttons(box)
            answer = box.exec_()
            if answer != QMessageBox.Yes:
                self._log("라이브 실행을 취소했습니다.")
                return
        self.log_view.clear()
        self._log("머신: " + machine_label(machine))
        self._log("환경: " + ACCOUNT_LABELS.get(self._account_key(), account["name"]))
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
        QMessageBox.information(self, "완료", "작업을 완료했습니다.")

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
