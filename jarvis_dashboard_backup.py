import os
import json
import threading
import subprocess
import webbrowser
import shutil
import platform
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import tkinter as tk
from tkinter import scrolledtext, messagebox

from openai import OpenAI

# ---------------- CONFIG ----------------

MODEL = "openai/gpt-oss-20b"
API_KEY = os.environ.get("GROQ_API_KEY")

client = (
    OpenAI(
        api_key=API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )
    if API_KEY else None
)

BASE_DIR = Path(__file__).resolve().parent
MEMORY_FILE = BASE_DIR / "jarvis_memory.json"
HOME = Path.home()

SYSTEM_PROMPT = """
You are JARVIS, a helpful Windows desktop assistant.
Reply naturally and concisely. Understand follow-up questions using
the conversation history.

You can use the provided tools to perform PC tasks.
Only use tools when the user requests an action.
Never claim an action succeeded unless its tool result confirms it.
Never ask for or reveal passwords, API keys, or private credentials.
Do not try to bypass security, access other people's data, or disable
security software. Do not invent tool results.
If a requested task is not supported by your tools, explain that honestly.
"""

# Only these applications can be launched by name.
APP_COMMANDS = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "file explorer": ["explorer.exe"],
    "explorer": ["explorer.exe"],
    "paint": ["mspaint.exe"],
    "task manager": ["taskmgr.exe"],
    "command prompt": ["cmd.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "settings": ["cmd.exe", "/c", "start", "", "ms-settings:"],
    "vscode": ["code"],
    "visual studio code": ["code"],
    "chrome": ["chrome"],
    "edge": ["msedge"],
}

# ---------------- MEMORY ----------------

def load_memory():
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [
                item for item in data
                if isinstance(item, dict)
                and item.get("role") in ("user", "assistant")
                and isinstance(item.get("content"), str)
            ][-100:]
    except (OSError, ValueError):
        pass
    return []


conversation = load_memory()


def save_memory():
    try:
        MEMORY_FILE.write_text(
            json.dumps(conversation[-100:], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except OSError as exc:
        print("Memory save error:", exc)


# ---------------- SAFE PATHS ----------------

def resolve_user_path(raw_path):
    """Allow access only to paths inside the current user's home folder."""
    path = Path(raw_path).expanduser()

    if not path.is_absolute():
        path = HOME / path

    path = path.resolve()
    path.relative_to(HOME.resolve())
    return path


# ---------------- PC TOOLS ----------------

def open_app(app_name):
    name = app_name.strip().lower()
    command = APP_COMMANDS.get(name)

    if not command:
        return (
            f"'{app_name}' is not in the approved application list. "
            "Currently supported: " + ", ".join(APP_COMMANDS.keys())
        )

    try:
        subprocess.Popen(command, shell=False)
        return f"Launch request sent for {app_name}."
    except (OSError, ValueError) as exc:
        return f"Could not launch {app_name}: {exc}"


def open_website(url):
    url = url.strip()

    if "://" not in url:
        url = "https://" + url

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return "Please provide a valid HTTP or HTTPS website URL."

    webbrowser.open(url)
    return f"Opened website: {url}"


def open_folder(path):
    try:
        target = resolve_user_path(path)

        if not target.exists():
            return "That path does not exist."

        if not target.is_dir():
            return "That path is a file, not a folder."

        os.startfile(str(target))
        return f"Opened folder: {target}"

    except (ValueError, OSError, RuntimeError):
        return "That folder could not be opened. Use a path inside your user folder."


def list_folder(path=""):
    try:
        target = resolve_user_path(path or str(HOME))

        if not target.is_dir():
            return "The requested folder does not exist."

        entries = []
        for item in list(target.iterdir())[:80]:
            kind = "Folder" if item.is_dir() else "File"
            entries.append(f"{kind}: {item.name}")

        return "\n".join(entries) if entries else "This folder is empty."

    except (ValueError, OSError, RuntimeError):
        return "Cannot list that folder. Access is restricted to your user folder."


def search_files(query):
    """Search common user folders; stop after a bounded number of entries."""
    query = query.strip().lower()

    if not query:
        return "Enter a filename to search for."

    search_roots = [
        HOME / "Desktop",
        HOME / "Documents",
        HOME / "Downloads",
    ]

    found = []
    scanned = 0
    max_scan = 12000

    for root in search_roots:
        if not root.is_dir():
            continue

        for current, dirs, files in os.walk(root, onerror=lambda _e: None):
            # Avoid scanning hidden/system directories.
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d.lower() not in ("node_modules", ".git", "__pycache__")
            ]

            for name in dirs + files:
                scanned += 1

                if query in name.lower():
                    found.append(str(Path(current) / name))

                if len(found) >= 30 or scanned >= max_scan:
                    break

            if len(found) >= 30 or scanned >= max_scan:
                break

        if len(found) >= 30 or scanned >= max_scan:
            break

    if not found:
        return "No matching files found in Desktop, Documents, or Downloads."

    suffix = "\n(Search limit reached.)" if scanned >= max_scan else ""
    return "\n".join(found) + suffix


def get_system_info():
    return (
        f"Operating system: {platform.system()} {platform.release()}\n"
        f"Computer: {platform.node()}\n"
        f"Python: {platform.python_version()}\n"
        f"User folder: {HOME}"
    )


# ---------------- AI TOOL DEFINITIONS ----------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an approved Windows application by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Application name, e.g. Notepad or VS Code."
                    }
                },
                "required": ["app_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Open a website in the default browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"}
                },
                "required": ["url"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_folder",
            "description": "Open a folder inside the current user's home folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Folder path, e.g. Desktop or Downloads."
                    }
                },
                "required": ["path"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_folder",
            "description": "List files and subfolders in a user's folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search filenames in Desktop, Documents and Downloads.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get basic information about this computer.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        }
    }
]

FUNCTIONS = {
    "open_app": open_app,
    "open_website": open_website,
    "open_folder": open_folder,
    "list_folder": list_folder,
    "search_files": search_files,
    "get_system_info": get_system_info,
}


def ask_jarvis(user_text):
    if not client:
        return (
            "GROQ_API_KEY nahi mili. CMD mein setx GROQ_API_KEY "
            "\"YOUR_KEY\" chalao, phir CMD dobara kholo."
        )

    # Keep the latest messages to control request size.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *conversation[-20:],
        {"role": "user", "content": user_text},
    ]

    try:
        # A maximum of three tool rounds per request.
        for _ in range(3):
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=1000,
            )

            message = response.choices[0].message
            if not message.tool_calls:
                return message.content or "Bhai, mujhe koi response nahi mila."

            # Preserve the tool-call message in this API request.
            messages.append(message.model_dump(exclude_none=True))

            for tool_call in message.tool_calls:
                name = tool_call.function.name

                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                    function = FUNCTIONS.get(name)

                    if function is None:
                        result = "This tool is not allowed."
                    else:
                        result = function(**arguments)

                except Exception as exc:
                    result = f"Action failed: {exc}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result)[:5000],
                })

        return "Bhai, ek request mein bohat saare actions ho gaye. Dobara try karo."

    except Exception as exc:
        print("Groq API error:", repr(exc))
        return f"AI error: {exc}"


# ---------------- DASHBOARD ----------------

root = tk.Tk()
root.title("JARVIS AI Assistant")
root.geometry("950x700")
root.minsize(650, 500)
root.configure(bg="#07111d")

BG = "#07111d"
PANEL = "#0d1d2c"
CYAN = "#36d9ff"
WHITE = "#e8f7ff"
MUTED = "#8ba8ba"

header = tk.Frame(root, bg=BG)
header.pack(fill="x", padx=22, pady=(18, 10))

tk.Label(
    header,
    text="J.A.R.V.I.S.",
    font=("Segoe UI", 25, "bold"),
    fg=CYAN,
    bg=BG
).pack(anchor="w")

status_text = (
    "GROQ CONNECTED  •  MEMORY ENABLED"
    if client else
    "API KEY MISSING"
)

status = tk.Label(
    header,
    text=status_text,
    font=("Consolas", 10),
    fg=MUTED,
    bg=BG
)
status.pack(anchor="w", pady=(3, 0))

chat = scrolledtext.ScrolledText(
    root,
    wrap=tk.WORD,
    font=("Segoe UI", 11),
    bg=PANEL,
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat",
    padx=15,
    pady=15,
    state="disabled"
)
chat.pack(fill="both", expand=True, padx=22, pady=10)

chat.tag_config("user", foreground=CYAN, font=("Segoe UI", 11, "bold"))
chat.tag_config("jarvis", foreground="#76f7b0", font=("Segoe UI", 11, "bold"))
chat.tag_config("body", foreground=WHITE)

def show_message(speaker, text):
    chat.configure(state="normal")
    tag = "user" if speaker == "YOU" else "jarvis"
    chat.insert(tk.END, f"{speaker}\n", tag)
    chat.insert(tk.END, f"{text}\n\n", "body")
    chat.configure(state="disabled")
    chat.see(tk.END)


for item in conversation:
    show_message("YOU" if item["role"] == "user" else "JARVIS", item["content"])

if not conversation:
    show_message(
        "JARVIS",
        "Online, bhai! Ask me a question or tell me to open an app, "
        "website, folder, or search for a file."
    )


input_frame = tk.Frame(root, bg=BG)
input_frame.pack(fill="x", padx=22, pady=(4, 20))

entry = tk.Entry(
    input_frame,
    font=("Segoe UI", 12),
    bg=PANEL,
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat"
)
entry.pack(side="left", fill="x", expand=True, ipady=13, padx=(0, 10))

send_button = tk.Button(
    input_frame,
    text="SEND",
    font=("Segoe UI", 10, "bold"),
    bg=CYAN,
    fg="#00121d",
    activebackground="#78e8ff",
    relief="flat",
    padx=24,
    pady=10,
    cursor="hand2"
)
send_button.pack(side="right")


def send_message(event=None):
    user_text = entry.get().strip()

    if not user_text:
        return

    entry.delete(0, tk.END)
    entry.configure(state="disabled")
    send_button.configure(state="disabled")
    status.configure(text="JARVIS IS THINKING...", fg=CYAN)

    show_message("YOU", user_text)

    def worker():
        reply = ask_jarvis(user_text)

        def finish():
            conversation.append({"role": "user", "content": user_text})
            conversation.append({"role": "assistant", "content": reply})
            del conversation[:-100]
            save_memory()

            show_message("JARVIS", reply)
            entry.configure(state="normal")
            send_button.configure(state="normal")
            status.configure(
                text="GROQ CONNECTED  •  MEMORY ENABLED",
                fg=MUTED
            )
            entry.focus_set()

        root.after(0, finish)

    threading.Thread(target=worker, daemon=True).start()


send_button.configure(command=send_message)
entry.bind("<Return>", send_message)
entry.focus_set()


def on_close():
    save_memory()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()