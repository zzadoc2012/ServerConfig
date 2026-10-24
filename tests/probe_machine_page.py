import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from selenium.webdriver.common.by import By

from serverconfig.automation import AdminAutomation
from serverconfig.settings_store import SettingsStore


def summarize_inputs(driver):
    rows = driver.execute_script(
        """
        return [...document.querySelectorAll('input,button,a,textarea,select,frame,iframe')].slice(0,120).map(el => ({
          tag: el.tagName,
          type: el.type || '',
          id: el.id || '',
          name: el.name || '',
          value: (el.value || '').slice(0,40),
          text: (el.innerText || el.textContent || '').trim().slice(0,40),
          href: (el.getAttribute('href') || '').slice(0,80)
        }));
        """
    )
    return rows


def dump_context(auto, label):
    driver = auto.driver
    print("===", label, "===")
    print("url:", driver.current_url)
    print("title:", driver.title)
    print("frames", driver.execute_script("return window.frames.length"))
    for row in summarize_inputs(driver):
        blob = " ".join(f"{k}={v}" for k, v in row.items() if v)
        if any(key in blob.lower() for key in ("mac", "machine", "search", "config", "frame", "log")):
            print(" ", blob)


def search_frames(auto):
    driver = auto.driver
    driver.switch_to.default_content()
    dump_context(auto, "default")
    frames = driver.find_elements(By.CSS_SELECTOR, "frame, iframe")
    print("frame_count", len(frames))
    for index, frame in enumerate(frames):
        name = frame.get_attribute("name") or frame.get_attribute("id") or ""
        src = frame.get_attribute("src") or ""
        print("frame", index, "name=", name, "src=", src)
        driver.switch_to.default_content()
        driver.switch_to.frame(frame)
        dump_context(auto, "frame " + str(index))
        nested = driver.find_elements(By.CSS_SELECTOR, "frame, iframe")
        for nested_index, nested_frame in enumerate(nested):
            print(
                " nested",
                nested_index,
                nested_frame.get_attribute("name"),
                nested_frame.get_attribute("src"),
            )
            driver.switch_to.frame(nested_frame)
            dump_context(auto, "nested " + str(index) + "." + str(nested_index))
            driver.switch_to.parent_frame()
        driver.switch_to.default_content()


def main() -> None:
    store = SettingsStore()
    account = store.account("test_admin")
    if not account.get("user_id") or not account.get("password"):
        raise SystemExit("no credentials")
    auto = AdminAutomation("Chrome", print)
    try:
        auto.start()
        auto._open(account["address"])
        auto._login(account["user_id"], account["password"])
        search_frames(auto)
        auto.driver.get("https://test-admin.phoenixdarts.com/machine/log_control")
        print("opened log_control")
        search_frames(auto)
        print("page_html_len", len(auto.driver.page_source))
        html = auto.driver.page_source
        Path(ROOT / "tests" / "log_control_snippet.html").write_text(html[:20000], encoding="utf-8")
        for row in summarize_inputs(auto.driver):
            print("ALL", " ".join(f"{k}={v}" for k, v in row.items() if v))
    finally:
        auto.close()


if __name__ == "__main__":
    main()
