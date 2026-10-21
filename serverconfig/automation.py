from typing import Callable, Optional

from selenium import webdriver
from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    UnexpectedAlertPresentException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

LogFn = Callable[[str], None]

LOGIN_ID = (By.ID, "admin_id")
LOGIN_PW = (By.ID, "passwd")
LOGIN_BUTTON = (By.ID, "login_btn")
LOGIN_OK_PATH = "/login/loginok"

MACHINE_MENU_CANDIDATES = [
    (By.LINK_TEXT, "Machine"),
    (By.PARTIAL_LINK_TEXT, "Machine"),
    (By.XPATH, "//a[contains(translate(., 'machine', 'MACHINE'), 'MACHINE')]"),
    (By.CSS_SELECTOR, "a[href*='machine']"),
]

MAC_INPUT_CANDIDATES = [
    (By.ID, "macAddr"),
    (By.NAME, "macAddr"),
    (By.CSS_SELECTOR, "input[name*='mac' i], input[id*='mac' i]"),
    (By.XPATH, "//th[contains(., 'Mac Addr') or contains(., 'MAC')]/following::input[1]"),
    (By.XPATH, "//td[contains(., 'Mac Addr')]/following::input[1]"),
]

SEARCH_CANDIDATES = [
    (By.XPATH, "//input[@type='submit' and (contains(@value,'earch') or contains(@value,'Search'))]"),
    (By.XPATH, "//button[contains(., 'Search') or contains(., 'search')]"),
    (By.XPATH, "//a[contains(., 'Search') or contains(., 'search')]"),
    (By.CSS_SELECTOR, "input[value='Search'], input[value='search']"),
]

CONFIG_AREA_CANDIDATES = [
    (By.XPATH, "//*[contains(., 'Config')]/following::textarea[last()]"),
    (By.CSS_SELECTOR, "textarea"),
]

EDIT_CANDIDATES = [
    (By.XPATH, "//input[@type='button' or @type='submit'][contains(@value,'EDIT') or contains(@value,'Edit')]"),
    (By.XPATH, "//button[contains(., 'EDIT') or contains(., 'Edit')]"),
    (By.XPATH, "//a[contains(., 'EDIT') or contains(., 'Edit')]"),
]


class AutomationError(RuntimeError):
    pass


class AdminAutomation:
    def __init__(self, browser: str, log: LogFn) -> None:
        self.browser = browser
        self.log = log
        self.driver: Optional[WebDriver] = None

    def start(self) -> None:
        self.log("브라우저를 시작합니다: " + self.browser)
        try:
            if self.browser == "Edge":
                options = EdgeOptions()
                options.add_argument("--start-maximized")
                self.driver = webdriver.Edge(options=options)
            else:
                options = ChromeOptions()
                options.add_argument("--start-maximized")
                self.driver = webdriver.Chrome(options=options)
        except Exception as exc:
            raise AutomationError(
                "WebDriver 초기화에 실패했습니다. Chrome/Edge와 맞는 브라우저가 설치돼 있는지 확인하세요. 원문: "
                + str(exc)
            ) from exc

    def close(self) -> None:
        if self.driver is None:
            return
        try:
            self.driver.quit()
            self.log("브라우저를 종료했습니다.")
        except Exception as exc:
            self.log("브라우저 종료 중 오류: " + str(exc))
        finally:
            self.driver = None

    def run(self, url: str, user_id: str, password: str, mac: str, config_text: str) -> None:
        if not self.driver:
            raise AutomationError("브라우저가 준비되지 않았습니다.")
        self._open(url)
        self._login(user_id, password)
        self._open_machine_page()
        self._search_mac(mac)
        self._apply_config(config_text)
        self.log("컨피그 적용 절차를 완료했습니다.")

    def _open(self, url: str) -> None:
        self.log("접속: " + url)
        self.driver.get(url)
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(LOGIN_ID))

    def _login(self, user_id: str, password: str) -> None:
        driver = self.driver
        wait = WebDriverWait(driver, 20)
        user_box = wait.until(EC.element_to_be_clickable(LOGIN_ID))
        pw_box = wait.until(EC.element_to_be_clickable(LOGIN_PW))
        if not user_box.is_displayed() or not pw_box.is_displayed():
            raise AutomationError("로그인 입력란이 표시되지 않습니다.")
        user_box.clear()
        user_box.send_keys(user_id)
        pw_box.clear()
        pw_box.send_keys(password)
        login_btn = wait.until(EC.presence_of_element_located(LOGIN_BUTTON))
        login_btn.click()
        self.log("로그인 버튼을 클릭했습니다.")
        self._accept_alerts()
        try:
            WebDriverWait(driver, 20).until(lambda d: LOGIN_OK_PATH not in d.current_url and d.find_elements(*LOGIN_ID) == [])
        except TimeoutException as exc:
            still_login = bool(driver.find_elements(*LOGIN_ID))
            if still_login:
                raise AutomationError("로그인에 실패했거나 추가 인증이 필요합니다. 브라우저에서 직접 확인하세요.") from exc
        if driver.find_elements(*LOGIN_ID):
            raise AutomationError("로그인 페이지에 남아 있습니다. 계정 정보를 확인하세요.")
        self.log("로그인 성공으로 판단했습니다. 현재 URL: " + driver.current_url)

    def _open_machine_page(self) -> None:
        self.log("Machine 메뉴를 찾는 중입니다. 로그인 이후 식별자는 페이지 구조에 따라 다를 수 있습니다.")
        element = self._first_visible(MACHINE_MENU_CANDIDATES, timeout=15)
        if element is None:
            raise AutomationError(
                "Machine 메뉴를 찾지 못했습니다. 로그인 후 화면에서 메뉴 식별자를 확인해 주세요."
            )
        element.click()
        self.log("Machine 메뉴를 클릭했습니다.")

    def _search_mac(self, mac: str) -> None:
        mac_input = self._first_visible(MAC_INPUT_CANDIDATES, timeout=15)
        if mac_input is None:
            raise AutomationError("Mac Addr 입력란을 찾지 못했습니다. 실제 DOM 확인이 필요합니다.")
        mac_input.clear()
        mac_input.send_keys(mac)
        self.log("MAC을 입력했습니다.")
        search = self._first_visible(SEARCH_CANDIDATES, timeout=10)
        if search is None:
            raise AutomationError("Search 버튼을 찾지 못했습니다. 실제 DOM 확인이 필요합니다.")
        search.click()
        self.log("Search를 클릭했습니다.")

    def _apply_config(self, config_text: str) -> None:
        area = self._first_visible(CONFIG_AREA_CANDIDATES, timeout=15)
        if area is None:
            raise AutomationError("Config 입력 영역을 찾지 못했습니다. 실제 DOM 확인이 필요합니다.")
        area.clear()
        area.send_keys(config_text)
        self.log("선택한 컨피그 내용을 붙여 넣었습니다.")
        edit = self._first_visible(EDIT_CANDIDATES, timeout=10)
        if edit is None:
            raise AutomationError("EDIT 버튼을 찾지 못했습니다. 실제 DOM 확인이 필요합니다.")
        edit.click()
        self.log("EDIT를 클릭했습니다.")
        self._accept_alerts()
        self._click_confirm_buttons()
        self.log("확인/Success 팝업 처리를 시도했습니다.")

    def _accept_alerts(self) -> None:
        for _ in range(3):
            try:
                WebDriverWait(self.driver, 2).until(EC.alert_is_present())
                alert = self.driver.switch_to.alert
                self.log("브라우저 알림을 확인했습니다.")
                alert.accept()
            except TimeoutException:
                return
            except UnexpectedAlertPresentException:
                self.driver.switch_to.alert.accept()

    def _click_confirm_buttons(self) -> None:
        confirm_candidates = [
            (By.XPATH, "//button[contains(., '확인') or contains(., 'OK') or contains(., 'Success')]"),
            (By.XPATH, "//input[@type='button' or @type='submit'][contains(@value,'확인') or contains(@value,'OK')]"),
            (By.XPATH, "//a[contains(., '확인')]"),
        ]
        for _ in range(2):
            button = self._first_visible(confirm_candidates, timeout=3)
            if button is None:
                return
            button.click()

    def _first_visible(self, candidates, timeout: int):
        last_error = None
        for locator in candidates:
            try:
                element = WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(locator))
                if element.is_displayed():
                    return element
            except (
                TimeoutException,
                NoSuchElementException,
                ElementNotInteractableException,
                StaleElementReferenceException,
            ) as exc:
                last_error = exc
                continue
        if last_error:
            self.log("요소 탐색 실패: " + type(last_error).__name__)
        return None
