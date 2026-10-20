
import time
from pathlib import Path

import pyautogui
import pyperclip

# JARVIS mouse/keyboard safety settings
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = BASE_DIR / "screenshots"

SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Only commonly used keyboard shortcuts are permitted.
ALLOWED_SHORTCUTS = {
    "copy": ("ctrl", "c"),
    "paste": ("ctrl", "v"),
    "cut": ("ctrl", "x"),
    "select_all": ("ctrl", "a"),
    "save": ("ctrl", "s"),
    "undo": ("ctrl", "z"),
    "redo": ("ctrl", "y"),
    "find": ("ctrl", "f"),
    "new_tab": ("ctrl", "t"),
    "close_tab": ("ctrl", "w"),
    "switch_window": ("alt", "tab"),
    "minimize": ("win", "down"),
    "maximize": ("win", "up"),
    "lock_pc": ("win", "l"),
}


def get_screen_size():
    """Return screen width and height."""
    width, height = pyautogui.size()
    return {"width": width, "height": height}


def _validate_coordinates(x, y):
    """Reject invalid or out-of-screen coordinates."""
    if isinstance(x, bool) or isinstance(y, bool):
        raise ValueError("Coordinates must be numbers.")

    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        raise ValueError("Coordinates must be numbers.")

    width, height = pyautogui.size()

    if not (0 <= x < width and 0 <= y < height):
        raise ValueError(
            f"Coordinates must be within the screen: "
            f"x=0-{width - 1}, y=0-{height - 1}"
        )


def move_mouse(x, y, duration=0.2):
    """Move the mouse to a screen coordinate."""
    _validate_coordinates(x, y)

    if not 0 <= duration <= 2:
        raise ValueError("Duration must be between 0 and 2 seconds.")

    pyautogui.moveTo(x, y, duration=duration)
    return f"Mouse moved to ({x}, {y})."


def click_mouse(x=None, y=None, button="left", clicks=1):
    """Click at a position, or click the current mouse position."""
    if button not in {"left", "right", "middle"}:
        raise ValueError("Button must be left, right, or middle.")

    if clicks not in {1, 2}:
        raise ValueError("Only single and double clicks are allowed.")

    if (x is None) != (y is None):
        raise ValueError("Provide both x and y, or neither.")

    if x is not None:
        _validate_coordinates(x, y)
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
    else:
        pyautogui.click(button=button, clicks=clicks)

    return f"{button.title()} click completed."


def scroll_mouse(direction="down", amount=3):
    """Scroll the current window."""
    if direction not in {"up", "down"}:
        raise ValueError("Direction must be up or down.")

    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("Scroll amount must be an integer.")

    if not 1 <= amount <= 10:
        raise ValueError("Scroll amount must be between 1 and 10.")

    pyautogui.scroll(amount if direction == "up" else -amount)
    return f"Scrolled {direction} by {amount} steps."


def type_text(text):
    """Paste plain text into the currently focused application."""
    if not isinstance(text, str):
        raise ValueError("Text must be a string.")

    if not text:
        return "Nothing to type."

    if len(text) > 2000:
        raise ValueError("Text is too long. Maximum is 2000 characters.")

    # Clipboard paste supports Unicode and Urdu more reliably
    # than simulated individual key presses.
    previous_clipboard = None

    try:
        previous_clipboard = pyperclip.paste()
    except Exception:
        pass

    pyperclip.copy(text)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")

    # Restore the clipboard after the paste operation.
    if previous_clipboard is not None:
        time.sleep(0.2)
        try:
            pyperclip.copy(previous_clipboard)
        except Exception:
            pass

    return f"Typed {len(text)} characters."


def press_shortcut(name):
    """Run a predefined keyboard shortcut by its name."""
    shortcut = ALLOWED_SHORTCUTS.get(name.lower().strip())

    if shortcut is None:
        allowed = ", ".join(sorted(ALLOWED_SHORTCUTS))
        raise ValueError(f"Shortcut not allowed. Available: {allowed}")

    pyautogui.hotkey(*shortcut)
    return f"Shortcut executed: {name}."


def press_key(key):
    """Press one key from a restricted list."""
    allowed_keys = {
        "enter", "esc", "tab", "space", "backspace", "delete",
        "up", "down", "left", "right", "home", "end",
        "pageup", "pagedown", "f5"
    }

    key = key.lower().strip()

    if key not in allowed_keys:
        raise ValueError("This key is not in the allowed key list.")

    pyautogui.press(key)
    return f"Key pressed: {key}."


def take_screenshot(filename=None):
    """Save a screenshot in the project's screenshots folder."""
    if filename is None:
        filename = time.strftime("screenshot_%Y%m%d_%H%M%S.png")

    # Prevent paths outside the screenshots directory.
    if (
        not isinstance(filename, str)
        or Path(filename).name != filename
        or not filename.lower().endswith(".png")
    ):
        raise ValueError("Use a simple PNG filename, without folder paths.")

    output_path = SCREENSHOT_DIR / filename
    image = pyautogui.screenshot()
    image.save(output_path)

    return str(output_path)


def get_mouse_position():
    """Return the current mouse position."""
    point = pyautogui.position()
    return {"x": point.x, "y": point.y}
