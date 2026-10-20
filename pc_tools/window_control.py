
import pygetwindow as gw


def list_windows():
    """List windows with visible titles."""
    results = []

    for window in gw.getAllWindows():
        title = window.title.strip()

        if title:
            results.append({
                "title": title,
                "active": window.isActive,
                "minimized": window.isMinimized,
                "maximized": window.isMaximized,
            })

    return results


def find_window(title):
    """Find windows whose titles contain the given text."""
    query = title.strip().lower()

    if not query:
        raise ValueError("Window title enter karo.")

    matches = [
        window for window in gw.getAllWindows()
        if query in window.title.lower() and window.title.strip()
    ]

    return matches


def focus_window(title):
    """Activate a matching window, only when the match is unique."""
    matches = find_window(title)

    if not matches:
        return f"'{title}' naam ki window nahi mili."

    if len(matches) > 1:
        names = [window.title for window in matches[:10]]
        return f"Multiple windows mili hain; specific title use karo: {names}"

    window = matches[0]

    try:
        if window.isMinimized:
            window.restore()

        window.activate()
        return f"Window focus karne ki request bhej di: {window.title}"
    except Exception as error:
        return f"Window activate nahi ho saki: {error}"


def minimize_window(title):
    """Minimize one uniquely matched window."""
    matches = find_window(title)

    if len(matches) != 1:
        return f"Ek unique matching window nahi mili: {len(matches)} matches."

    try:
        matches[0].minimize()
        return f"Window minimize kar di: {matches[0].title}"
    except Exception as error:
        return f"Window minimize nahi ho saki: {error}"


def maximize_window(title):
    """Maximize one uniquely matched window."""
    matches = find_window(title)

    if len(matches) != 1:
        return f"Ek unique matching window nahi mili: {len(matches)} matches."

    try:
        matches[0].maximize()
        return f"Window maximize kar di: {matches[0].title}"
    except Exception as error:
        return f"Window maximize nahi ho saki: {error}"


def close_window(title):
    """
    Ask Windows to close a uniquely matched window.
    Unsaved work dialogs may appear; no forced process termination.
    """
    matches = find_window(title)

    if len(matches) != 1:
        return f"Ek unique matching window nahi mili: {len(matches)} matches."

    try:
        matches[0].close()
        return f"Window close request bhej di: {matches[0].title}"
    except Exception as error:
        return f"Window close nahi ho saki: {error}"
