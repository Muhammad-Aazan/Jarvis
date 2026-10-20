
import os
import subprocess
import webbrowser
from pathlib import Path

import psutil

# Sirf approved apps aur websites launch hongi.
APP_PATHS = {
    "notepad": [
        str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "notepad.exe")
    ],
    "calculator": [
        str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "calc.exe")
    ],
    "cmd": [
        str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "cmd.exe")
    ],
    "powershell": [
        "powershell.exe"
    ],
    "vscode": [
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
    ],
    "antigravity": [
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "antigravity" / "Antigravity.exe"),
    ],
}

WEBSITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
}


def open_app(name):
    """Launch an approved application."""
    name = name.lower().strip()

    if name not in APP_PATHS:
        raise ValueError(
            f"App '{name}' allowed list mein nahi hai. "
            f"Available apps: {', '.join(APP_PATHS)}"
        )

    for app_path in APP_PATHS[name]:
        if os.path.isfile(app_path):
            subprocess.Popen([app_path], shell=False)
            return f"{name.title()} launch ho gaya."

    # Windows registered apps ke liye fallback.
    if name in {"notepad", "calculator"}:
        executable = APP_PATHS[name][0]
        subprocess.Popen([executable], shell=False)
        return f"{name.title()} launch command bhej di."

    raise FileNotFoundError(
        f"{name.title()} ka executable nahi mila. "
        "APP_PATHS mein uska correct path add karo."
    )


def open_website(name):
    """Open an approved website."""
    name = name.lower().strip()

    if name not in WEBSITES:
        raise ValueError(
            f"Website allowed list mein nahi hai: {', '.join(WEBSITES)}"
        )

    webbrowser.open(WEBSITES[name])
    return f"{name.title()} browser mein open ho raha hai."


def list_running_apps():
    """Return visible window process names when available."""
    running = []

    for process in psutil.process_iter(["pid", "name"]):
        try:
            name = process.info.get("name") or ""
            if name:
                running.append({
                    "pid": process.info["pid"],
                    "name": name,
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return running


def find_processes(name):
    """Find running processes by executable name."""
    query = name.lower().strip()
    matches = []

    if not query:
        return matches

    for process in psutil.process_iter(["pid", "name"]):
        try:
            process_name = process.info.get("name") or ""
            if query in process_name.lower():
                matches.append({
                    "pid": process.info["pid"],
                    "name": process_name,
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return matches


def close_app(name):
    """
    Close an app only if exactly one matching process is found.
    This requests a graceful termination first; it does not force-kill.
    """
    name = name.lower().strip()

    if name not in APP_PATHS:
        raise ValueError("Sirf APP_PATHS mein listed apps close kar sakte ho.")

    process_names = {
        "notepad": {"notepad.exe"},
        "calculator": {"calculator.exe", "calc.exe"},
        "cmd": {"cmd.exe"},
        "powershell": {"powershell.exe"},
        "vscode": {"code.exe"},
        "antigravity": {"antigravity.exe"},
    }

    allowed_names = process_names.get(name, set())
    matches = []

    for process in psutil.process_iter(["pid", "name"]):
        try:
            process_name = (process.info.get("name") or "").lower()
            if process_name in allowed_names:
                matches.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not matches:
        return f"{name.title()} ka running process nahi mila."

    if len(matches) > 1:
        return (
            f"{name.title()} ke {len(matches)} processes chal rahe hain. "
            "Galat window close hone se bachane ke liye action cancel kiya."
        )

    try:
        matches[0].terminate()
        return f"{name.title()} ko close request bhej di."
    except (psutil.NoSuchProcess, psutil.AccessDenied) as error:
        return f"App close nahi ho saka: {error}"
