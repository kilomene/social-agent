"""Driver abstraction: Playwright as the engine, simulated for tests.

Playwright is imported lazily (inside PlaywrightDriver.start) so the
whole repo keeps working — tests, exams, CLI — on machines where
Playwright isn't installed. Anything that needs a real browser calls
require_playwright() first, which raises a clear error pointing at
browser/SETUP.md.
"""

SETUP_DOC = "browser/SETUP.md"

try:
    import playwright  # noqa: F401
    BROWSER_OK = True
except ImportError:
    BROWSER_OK = False


class BrowserUnavailable(RuntimeError):
    """Raised when a real browser is needed but Playwright is missing."""


def require_playwright():
    if not BROWSER_OK:
        raise BrowserUnavailable(
            "Playwright is not installed. The agent drives platforms through"
            " a real browser — install it with:\n"
            "  pip install playwright && playwright install chromium\n"
            "Full instructions: browser/SETUP.md")


class Driver:
    """Abstract browser driver. Methods return small result dicts."""

    name = "abstract"

    def start(self, profile_dir, headed=True):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def goto(self, url):
        raise NotImplementedError

    def click(self, selector):
        raise NotImplementedError

    def fill(self, selector, text):
        raise NotImplementedError

    def press(self, key):
        raise NotImplementedError

    def scroll(self, selector=None, direction="down", amount=600):
        raise NotImplementedError

    def upload(self, selector, file_path):
        raise NotImplementedError

    def screenshot(self, path):
        raise NotImplementedError

    def get_text(self, selector=None):
        raise NotImplementedError

    def wait_for(self, selector, timeout_ms=15000):
        raise NotImplementedError

    def current_url(self):
        raise NotImplementedError

    @property
    def actions(self):
        """Recorded primitive calls (useful for tests/dry runs)."""
        return []


class PlaywrightDriver(Driver):
    """Real driver: persistent Chromium context per account profile."""

    name = "playwright"

    def __init__(self):
        self._pw = None
        self._ctx = None
        self._page = None
        self._actions = []

    def start(self, profile_dir, headed=True):
        require_playwright()
        from playwright.sync_api import sync_playwright
        import os
        os.makedirs(profile_dir, exist_ok=True)
        self._pw = sync_playwright().start()
        self._ctx = self._pw.chromium.launch_persistent_context(
            profile_dir, headless=not headed,
            viewport={"width": 1366, "height": 900},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0 Safari/537.36"),
            locale="en-US",
        )
        pages = self._ctx.pages
        self._page = pages[0] if pages else self._ctx.new_page()
        self._record("start", profile_dir=profile_dir, headed=headed)
        return {"ok": True, "profile_dir": profile_dir, "headed": headed}

    def stop(self):
        self._record("stop")
        try:
            if self._ctx:
                self._ctx.close()
        finally:
            if self._pw:
                self._pw.stop()
            self._ctx, self._pw, self._page = None, None, None

    def _record(self, op, **kw):
        self._actions.append({"op": op, **kw})

    def _need_page(self):
        if not self._page:
            raise BrowserUnavailable("driver not started")

    def goto(self, url):
        self._need_page()
        self._page.goto(url, wait_until="domcontentloaded")
        self._record("goto", url=url)
        return {"ok": True, "url": self._page.url}

    def click(self, selector):
        self._need_page()
        self._page.click(selector, timeout=15000)
        self._record("click", selector=selector)
        return {"ok": True}

    def fill(self, selector, text):
        self._need_page()
        self._page.fill(selector, text, timeout=15000)
        self._record("fill", selector=selector, chars=len(text))
        return {"ok": True}

    def press(self, key):
        self._need_page()
        self._page.keyboard.press(key)
        self._record("press", key=key)
        return {"ok": True}

    def scroll(self, selector=None, direction="down", amount=600):
        self._need_page()
        if selector:
            self._page.hover(selector, timeout=15000)
            self._page.mouse.wheel(0, amount if direction == "down" else -amount)
        else:
            self._page.evaluate(
                f"window.scrollBy(0, {amount if direction == 'down' else -amount})")
        self._record("scroll", selector=selector, direction=direction)
        return {"ok": True}

    def upload(self, selector, file_path):
        self._need_page()
        self._page.set_input_files(selector, file_path, timeout=30000)
        self._record("upload", selector=selector, file=file_path)
        return {"ok": True}

    def screenshot(self, path):
        self._need_page()
        self._page.screenshot(path=path, full_page=False)
        self._record("screenshot", path=path)
        return {"ok": True, "path": path}

    def get_text(self, selector=None):
        self._need_page()
        if selector:
            text = self._page.inner_text(selector, timeout=15000)
        else:
            text = self._page.inner_text("body", timeout=15000)
        self._record("get_text", selector=selector, chars=len(text))
        return {"ok": True, "text": text}

    def wait_for(self, selector, timeout_ms=15000):
        self._need_page()
        self._page.wait_for_selector(selector, timeout=timeout_ms)
        self._record("wait_for", selector=selector)
        return {"ok": True}

    def current_url(self):
        self._need_page()
        return self._page.url

    @property
    def actions(self):
        return list(self._actions)


class SimulatedDriver(Driver):
    """Offline stand-in: records calls, returns canned responses.

    Used by tests, exams, and --simulate runs. Never touches the network.
    """

    name = "simulated"

    def __init__(self, logged_in=True, pages=None):
        self._actions = []
        self._started = False
        self._logged_in = logged_in
        self._url = "about:blank"
        self._pages = pages or {}  # url -> body text

    def start(self, profile_dir, headed=True):
        import os
        os.makedirs(profile_dir, exist_ok=True)
        self._started = True
        self._actions.append({"op": "start", "profile_dir": profile_dir,
                              "headed": headed, "simulated": True})
        return {"ok": True, "profile_dir": profile_dir, "headed": headed,
                "simulated": True}

    def stop(self):
        self._started = False
        self._actions.append({"op": "stop"})

    def _need(self):
        if not self._started:
            raise BrowserUnavailable("simulated driver not started")

    def goto(self, url):
        self._need()
        self._url = url
        self._actions.append({"op": "goto", "url": url})
        return {"ok": True, "url": url}

    def click(self, selector):
        self._need()
        self._actions.append({"op": "click", "selector": selector})
        return {"ok": True}

    def fill(self, selector, text):
        self._need()
        self._actions.append({"op": "fill", "selector": selector,
                              "chars": len(text)})
        return {"ok": True}

    def press(self, key):
        self._need()
        self._actions.append({"op": "press", "key": key})
        return {"ok": True}

    def scroll(self, selector=None, direction="down", amount=600):
        self._need()
        self._actions.append({"op": "scroll", "selector": selector,
                              "direction": direction})
        return {"ok": True}

    def upload(self, selector, file_path):
        self._need()
        self._actions.append({"op": "upload", "selector": selector,
                              "file": file_path})
        return {"ok": True}

    def screenshot(self, path):
        self._need()
        # a real screenshot can't exist offline; record the intent
        self._actions.append({"op": "screenshot", "path": path})
        return {"ok": True, "path": path, "simulated": True}

    def get_text(self, selector=None):
        self._need()
        text = self._pages.get(self._url, "")
        self._actions.append({"op": "get_text", "selector": selector,
                              "chars": len(text)})
        return {"ok": True, "text": text}

    def wait_for(self, selector, timeout_ms=15000):
        self._need()
        self._actions.append({"op": "wait_for", "selector": selector})
        return {"ok": True}

    def current_url(self):
        self._need()
        return self._url

    @property
    def actions(self):
        return list(self._actions)

    @property
    def logged_in(self):
        return self._logged_in
