import time
from typing import Callable, Optional
from urllib.parse import urljoin

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoAlertPresentException,
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

from serverconfig.excel_loader import normalize_config_text

LogFn = Callable[[str], None]

LOGIN_ID = (By.ID, "admin_id")
LOGIN_PW = (By.ID, "passwd")
LOGIN_BUTTON = (By.ID, "login_btn")
LOGIN_OK_PATH = "/login/loginok"
MACHINE_PAGE = "/machine/log_control"
MAC_INPUT = (By.ID, "machine_no")
SEARCH_BUTTON = (By.CSS_SELECTOR, "input[type='button'][value='search']")
CONFIG_TEXTAREA = (By.CSS_SELECTOR, "textarea[id^='txt_config_memo_']")
EDIT_BUTTON = (By.XPATH, "//textarea[starts-with(@id,'txt_config_memo_')]/ancestor::tr//button[contains(., 'Edit')]")


class AutomationError(RuntimeError):
    pass


def config_line_key(line: str) -> Optional[str]:
    text = (line or "").strip()
    if not text or "=" not in text:
        return None
    return text.split("=", 1)[0].strip()


def merge_config(existing: str, incoming: str) -> str:
    command = normalize_config_text(incoming)
    command_lines = [line for line in command.split("\n") if line.strip() != ""]
    if not command_lines:
        return existing or ""

    replacement_keys = set()
    for line in command_lines:
        key = config_line_key(line)
        if key:
            replacement_keys.add(key)

    kept = []
    for line in (existing or "").replace("\r\n", "\n").split("\n"):
        key = config_line_key(line)
        if key and key in replacement_keys:
            continue
        kept.append(line)
    while kept and kept[-1] == "":
        kept.pop()

    if not kept:
        return "\n".join(command_lines) + "\n"
    return "\n".join(kept) + "\n" + "\n".join(command_lines) + "\n"


SAVE_CONFIG_JS = """
var seq = arguments[0];
var text = arguments[1];
var field = "txt_config_memo_" + seq;
var area = document.getElementById(field);
if (area) {
  area.value = text;
}
if (window.jQuery) {
  window.jQuery("#" + field).val(text);
}
var payload = "";
if (window.jQuery && window.jQuery("#work_form").length) {
  payload = window.jQuery("#work_form").serialize();
}
var encodedKey = encodeURIComponent(field) + "=";
if (payload.indexOf(field + "=") === -1 && payload.indexOf(encodedKey) === -1) {
  payload += (payload ? "&" : "") + encodedKey + encodeURIComponent(text);
}
payload += "&mode=edit_config&machine_seq=" + encodeURIComponent(seq);
var result = {ok: false, status: 0, body: ""};
window.jQuery.ajax({
  url: "/machine/log_control_prc",
  type: "POST",
  dataType: "text",
  async: false,
  data: payload,
  success: function(res) {
    result.ok = true;
    result.body = res;
  },
  error: function(xhr) {
    result.status = xhr.status;
    result.body = xhr.responseText || xhr.statusText || "";
  }
});
return result;
"""

DISMISS_POPUPS_JS = """
function labelOf(el) {
  return ((el.innerText || el.value || el.getAttribute("aria-label") || el.getAttribute("title") || "") + "")
    .replace(/\\s+/g, " ").trim();
}
function isDismissLabel(text) {
  var t = (text || "").toLowerCase();
  return t === "확인" || t === "닫기" || t === "닫기" || t === "ok" || t === "close" || t === "yes"
    || t.indexOf("확인") !== -1 || t.indexOf("닫기") !== -1 || t === "×" || t === "x";
}
function looksLikePopup(el) {
  if (!el || el === document.body || el === document.documentElement) return false;
  if (el.id === "wrapper" || el.id === "container" || el.id === "frm" || el.id === "work_form") return false;
  var cls = ((el.className && el.className.toString) ? el.className.toString() : "") + "";
  if (/modal|popup|layer|dialog|overlay|alert|swal|toast|lightbox|notice/i.test(cls)) return true;
  if (el.getAttribute("role") === "dialog" || el.tagName === "DIALOG") return true;
  var st = window.getComputedStyle(el);
  if (!st || st.display === "none" || st.visibility === "hidden") return false;
  var z = parseInt(st.zIndex, 10);
  if ((st.position === "fixed" || st.position === "absolute") && !isNaN(z) && z >= 50 && el.offsetWidth > 80 && el.offsetHeight > 40) {
    return true;
  }
  return false;
}
var selectors = [
  ".swal2-confirm", ".swal2-close", ".swal-button",
  ".layui-layer-btn0", ".layui-layer-close",
  ".ui-dialog-buttonset button", ".ui-dialog-titlebar-close",
  ".modal-footer button", ".modal-close", "[data-dismiss=modal]",
  ".popup_close", ".btn_close", ".close", "button.close"
];
for (var s = 0; s < selectors.length; s++) {
  var hits = document.querySelectorAll(selectors[s]);
  for (var h = 0; h < hits.length; h++) {
    if (hits[h].offsetParent !== null || hits[h].getClientRects().length) {
      hits[h].click();
      return "selector:" + selectors[s];
    }
  }
}
var candidates = document.querySelectorAll("div, section, article, dialog, aside, form");
for (var i = 0; i < candidates.length; i++) {
  var node = candidates[i];
  if (!looksLikePopup(node)) continue;
  var buttons = node.querySelectorAll("button, a, input[type=button], input[type=submit], [role=button]");
  for (var j = 0; j < buttons.length; j++) {
    if (isDismissLabel(labelOf(buttons[j]))) {
      buttons[j].click();
      return "popup-button";
    }
  }
}
return "none";
"""


TOTAL_STEPS = 8


class AdminAutomation:
    def __init__(self, browser: str, log: LogFn) -> None:
        self.browser = browser
        self.log = log
        self.driver: Optional[WebDriver] = None

    def _step(self, number: int, message: str) -> None:
        self.log(f"{number}/{TOTAL_STEPS} {message}")

    def start(self) -> None:
        self._step(1, "백그라운드 브라우저를 준비합니다.")
        try:
            options = self._browser_options()
            if self.browser == "Edge":
                self.driver = webdriver.Edge(options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
        except Exception as exc:
            raise AutomationError(
                "WebDriver 초기화에 실패했습니다. Chrome/Edge와 맞는 브라우저가 설치돼 있는지 확인하세요. 원문: "
                + str(exc)
            ) from exc

    def _browser_options(self):
        options = EdgeOptions() if self.browser == "Edge" else ChromeOptions()
        options.page_load_strategy = "eager"
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--log-level=3")
        options.add_argument("--disable-save-password-bubble")
        options.add_argument(
            "--disable-features=PasswordLeakDetection,PasswordManagerOnboarding,SafetyHub,SafeBrowsingEnhancedProtection"
        )
        options.add_experimental_option(
            "prefs",
            {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.password_manager_leak_detection": False,
            },
        )
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        return options

    def close(self) -> None:
        if self.driver is None:
            return
        try:
            self.driver.quit()
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
        self._step(8, "작업을 완료했습니다.")

    def _open(self, url: str) -> None:
        self._step(2, "어드민에 접속합니다.")
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
        self._step(3, "로그인합니다.")
        try:
            WebDriverWait(driver, 20).until(self._login_finished)
        except TimeoutException as exc:
            still_login = bool(driver.find_elements(*LOGIN_ID))
            if still_login:
                raise AutomationError("로그인에 실패했거나 추가 인증이 필요합니다. 브라우저에서 직접 확인하세요.") from exc
        if driver.find_elements(*LOGIN_ID):
            raise AutomationError("로그인 페이지에 남아 있습니다. 계정 정보를 확인하세요.")
        self._step(4, "로그인했습니다.")

    def _login_finished(self, driver: WebDriver) -> bool:
        self._accept_alert_if_present()
        return LOGIN_OK_PATH not in driver.current_url and driver.find_elements(*LOGIN_ID) == []

    def _open_machine_page(self) -> None:
        target = urljoin(self.driver.current_url, MACHINE_PAGE)
        self._step(5, "Machine 페이지로 이동합니다.")
        self.driver.get(target)
        self._wait_ready(MAC_INPUT, timeout=12)
        if MACHINE_PAGE not in self.driver.current_url:
            raise AutomationError("Machine 페이지로 이동하지 못했습니다. 현재 URL: " + self.driver.current_url)

    def _wait_ready(self, locator, timeout: float) -> None:
        deadline = time.time() + timeout
        last_error = None
        while time.time() < deadline:
            self._accept_alert_if_present()
            clicked = self.driver.execute_script(DISMISS_POPUPS_JS)
            try:
                element = WebDriverWait(self.driver, 0.2).until(EC.element_to_be_clickable(locator))
                if element:
                    return
            except TimeoutException as exc:
                last_error = exc
            if clicked and clicked != "none":
                continue
            time.sleep(0.05)
        raise AutomationError("Machine 페이지의 Mac Addr 입력란을 열지 못했습니다.") from last_error

    def _dismiss_blocking_popups(self, drain_seconds: float = 2) -> None:
        deadline = time.time() + drain_seconds
        idle_since = None
        while time.time() < deadline:
            dismissed = self._accept_alert_if_present()
            clicked = self.driver.execute_script(DISMISS_POPUPS_JS)
            if dismissed or (clicked and clicked != "none"):
                idle_since = None
                continue
            if idle_since is None:
                idle_since = time.time()
            elif time.time() - idle_since >= 0.2:
                return
            time.sleep(0.05)

    def _search_mac(self, mac: str) -> None:
        mac_value = mac.replace(":", "").replace("-", "").replace(" ", "").strip()
        mac_input = WebDriverWait(self.driver, 8).until(EC.element_to_be_clickable(MAC_INPUT))
        try:
            mac_input.clear()
            mac_input.send_keys(mac_value)
        except (ElementClickInterceptedException, ElementNotInteractableException):
            self._dismiss_blocking_popups(drain_seconds=2)
            mac_input = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(MAC_INPUT))
            mac_input.clear()
            mac_input.send_keys(mac_value)
        entered = (mac_input.get_attribute("value") or "").replace(":", "").replace("-", "").replace(" ", "")
        if entered.upper() != mac_value.upper():
            self.driver.execute_script("arguments[0].value = arguments[1];", mac_input, mac_value)
            entered = (mac_input.get_attribute("value") or "").replace(":", "").replace("-", "").replace(" ", "")
        if entered.upper() != mac_value.upper():
            raise AutomationError("Mac Addr에 MAC이 입력되지 않았습니다.")
        self._step(6, "머신을 검색합니다.")
        search = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(SEARCH_BUTTON))
        try:
            search.click()
        except ElementClickInterceptedException:
            self._dismiss_blocking_popups(drain_seconds=2)
            search = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(SEARCH_BUTTON))
            search.click()
        if not self._wait_search_results(timeout=8):
            self.driver.execute_script("list_load(1);")
        if not self._wait_search_results(timeout=20):
            raise AutomationError("search 이후 머신 목록이 나오지 않았습니다.")
        if not self.driver.find_elements(*CONFIG_TEXTAREA):
            desc = ""
            if self.driver.find_elements(By.ID, "desc"):
                desc = self.driver.find_element(By.ID, "desc").text.strip()
            raise AutomationError("해당 MAC으로 머신을 찾지 못했습니다. " + desc)

    def _wait_search_results(self, timeout: int) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.find_elements(*CONFIG_TEXTAREA)
                or (
                    d.find_elements(By.ID, "desc")
                    and d.find_element(By.ID, "desc").text.strip() != ""
                )
            )
            return True
        except TimeoutException:
            return False

    def _apply_config(self, config_text: str) -> None:
        areas = self.driver.find_elements(*CONFIG_TEXTAREA)
        if not areas:
            raise AutomationError("검색 결과의 Config 입력란을 찾지 못했습니다.")
        area = areas[0]
        area_id = area.get_attribute("id") or ""
        if not area_id.startswith("txt_config_memo_"):
            raise AutomationError("Config 입력란 ID를 확인하지 못했습니다.")
        machine_seq = area_id.replace("txt_config_memo_", "", 1)
        existing = area.get_attribute("value") or ""
        merged = merge_config(existing, config_text)
        self._step(7, "선택한 설정을 저장합니다.")
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});"
            "arguments[0].value = arguments[1];"
            "if (window.jQuery) { window.jQuery(arguments[0]).val(arguments[1]); }",
            area,
            merged,
        )
        edit = self._first_visible([EDIT_BUTTON], timeout=10)
        if edit is None:
            raise AutomationError("Edit 버튼을 찾지 못했습니다.")
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", edit)
        edit.click()
        if not self._accept_alert_matching(("Sure", "Edit", "확인"), timeout=8):
            self.driver.execute_script(
                "window.confirm = function(){ return true; }; edit_config(arguments[0]);",
                machine_seq,
            )
        if self._accept_alert_matching(("Success",), timeout=12):
            return
        result = self.driver.execute_script(SAVE_CONFIG_JS, machine_seq, merged)
        if not result or not result.get("ok"):
            detail = ""
            if result:
                detail = str(result.get("status") or "") + " " + str(result.get("body") or "")
            raise AutomationError("Config 저장을 확인하지 못했습니다. " + detail.strip())

    def _accept_alert_if_present(self, keywords=()) -> bool:
        try:
            alert = self.driver.switch_to.alert
        except NoAlertPresentException:
            return False
        except UnexpectedAlertPresentException:
            self.driver.switch_to.alert.accept()
            return True
        text = alert.text or ""
        if keywords and not any(word.lower() in text.lower() for word in keywords):
            alert.accept()
            return False
        alert.accept()
        return True

    def _accept_alerts(self) -> None:
        self._accept_alert_if_present()

    def _accept_alert_matching(self, keywords, timeout: int) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._accept_alert_if_present(keywords):
                return True
            time.sleep(0.05)
        return False

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
