"""
JARVIS - Desktop AI Assistant Engine
Fixed & Enhanced Version
"""

import io
import os
import json
import subprocess
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly
import pyttsx3

from groq import Groq


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
MEMORY_FILE = BASE_DIR / "jarvis_memory.json"

# API Key — loaded from .env file (never hardcode secrets!)
from dotenv import load_dotenv
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Best available Groq chat model
GROQ_MODEL = "openai/gpt-oss-120b"

# Groq Whisper model for cloud STT (fast and accurate)
GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"

# Mic config – Device 1 = Realtek Microphone (MME, 2-channel, 44100 Hz)
MIC_DEVICE        = 1
MIC_SAMPLE_RATE   = 44100
MIC_CHANNELS      = 2
RECORD_SECONDS    = 6   # How long to record per voice press

# Silence threshold – if audio is quieter than this, skip transcription
SILENCE_THRESHOLD = 0.003

SYSTEM_PROMPT = """\
You are JARVIS, an intelligent and friendly desktop AI assistant created for this user.
- Respond naturally, concisely and helpfully.
- The user may speak in English, Urdu, or Roman Urdu. Respond in the same language they use.
- When the user asks you to open apps or websites, confirm naturally.
- Do NOT claim to perform a computer action unless the code actually executed it.
- Keep responses short unless the user explicitly asks for detail.
- Current date/time: {datetime}
"""


# =========================================================
# GROQ CLIENT (singleton)
# =========================================================

_groq_client = None
_groq_lock = threading.Lock()


def get_groq_client():
    global _groq_client
    with _groq_lock:
        if _groq_client is None:
            _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


# =========================================================
# MEMORY
# =========================================================

def load_memory():
    if not MEMORY_FILE.exists():
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_memory(messages):
    try:
        messages = messages[-100:]
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print("Memory save error:", e)


def clear_memory():
    global conversation
    conversation = []
    try:
        MEMORY_FILE.write_text("[]", encoding="utf-8")
    except OSError:
        pass


conversation = load_memory()


# =========================================================
# GROQ AI CHAT
# =========================================================

def ask_ai(user_message, status_callback=None):
    """
    Sends user message to Groq and returns the AI response.
    Conversation history is persisted in jarvis_memory.json.
    """
    def set_status(msg):
        if status_callback:
            try:
                status_callback(msg)
            except Exception:
                pass

    client = get_groq_client()
    set_status("Thinking...")

    system_with_time = SYSTEM_PROMPT.format(
        datetime=datetime.now().strftime("%A, %d %B %Y  %I:%M %p")
    )

    messages = [{"role": "system", "content": system_with_time}]
    messages.extend(conversation[-20:])
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_completion_tokens=800,
        )
        answer = response.choices[0].message.content or "Sorry, mujhe response nahi mila."
    except Exception as e:
        answer = f"AI Error: {e}"

    conversation.append({"role": "user",      "content": user_message})
    conversation.append({"role": "assistant",  "content": answer})
    save_memory(conversation)

    return answer


# =========================================================
# TEXT TO SPEECH
# =========================================================

_tts_engine = None
_tts_lock   = threading.Lock()


def _build_tts_engine():
    """Create a fresh pyttsx3 engine (called inside the TTS lock)."""
    engine = pyttsx3.init()
    engine.setProperty("rate",   170)
    engine.setProperty("volume", 1.0)

    # Prefer a natural-sounding voice if available
    voices = engine.getProperty("voices")
    for voice in voices:
        if "david" in voice.name.lower() or "mark" in voice.name.lower():
            engine.setProperty("voice", voice.id)
            break

    return engine


def _strip_emojis(text):
    """Remove emoji/non-ASCII characters for TTS compatibility."""
    import re
    # Remove emoji unicode ranges
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub("", text).strip()


def speak(text):
    """
    Speaks text using Windows TTS (pyttsx3).
    Runs synchronously – call from a daemon thread so the UI stays responsive.
    """
    global _tts_engine

    if not text:
        return

    # Strip emojis so pyttsx3 doesn't choke or say weird things
    clean_text = _strip_emojis(text)
    if not clean_text:
        return

    with _tts_lock:
        try:
            if _tts_engine is None:
                _tts_engine = _build_tts_engine()

            _tts_engine.say(clean_text)
            _tts_engine.runAndWait()

        except Exception as e:
            print("TTS error:", e)
            # Reset engine so next call gets a clean one
            try:
                _tts_engine.stop()
            except Exception:
                pass
            _tts_engine = None


# =========================================================
# VOICE RECORDING + GROQ CLOUD WHISPER TRANSCRIPTION
# =========================================================

def record_audio(status_callback=None):
    """
    Records audio from the selected microphone.
    Returns raw PCM bytes (WAV format) ready for the Groq API,
    or None if the recording is silent / failed.
    """
    def set_status(msg):
        if status_callback:
            try:
                status_callback(msg)
            except Exception:
                pass

    try:
        set_status("🎙 Listening… speak now")

        audio = sd.rec(
            int(RECORD_SECONDS * MIC_SAMPLE_RATE),
            samplerate=MIC_SAMPLE_RATE,
            channels=MIC_CHANNELS,
            dtype="float32",
            device=MIC_DEVICE,
        )
        sd.wait()

        if audio is None or audio.size == 0:
            set_status("No audio captured.")
            return None

        # Stereo → mono
        mono = audio.mean(axis=1).astype(np.float32)

        # Check silence
        peak = float(np.max(np.abs(mono)))
        if peak < SILENCE_THRESHOLD:
            set_status("Too quiet – please speak louder.")
            return None

        # Resample 44100 → 16000 Hz (required by Whisper)
        audio_16k = resample_poly(mono, up=160, down=441).astype(np.float32)

        # Convert float32 → 16-bit PCM WAV bytes for Groq API
        import wave
        pcm_int16 = (audio_16k * 32767).clip(-32768, 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)      # 16-bit
            wf.setframerate(16000)
            wf.writeframes(pcm_int16.tobytes())

        return buf.getvalue()

    except Exception as e:
        set_status(f"Recording failed: {e}")
        print("Recording error:", repr(e))
        return None


def transcribe_audio(wav_bytes, status_callback=None):
    """
    Sends WAV bytes to Groq Whisper and returns the transcript string.
    """
    def set_status(msg):
        if status_callback:
            try:
                status_callback(msg)
            except Exception:
                pass

    set_status("Transcribing…")

    try:
        client = get_groq_client()

        # Groq expects a file-like object with a name attribute
        audio_file = io.BytesIO(wav_bytes)
        audio_file.name = "audio.wav"

        result = client.audio.transcriptions.create(
            model=GROQ_WHISPER_MODEL,
            file=audio_file,
            response_format="text",
            language=None,   # auto-detect (English / Urdu / Roman Urdu)
        )

        # result is a plain string when response_format="text"
        transcript = str(result).strip()
        return transcript

    except Exception as e:
        set_status(f"Transcription error: {e}")
        print("Whisper error:", repr(e))
        return ""


def record_transcribe(status_callback=None):
    """
    Full pipeline: record → check silence → transcribe via Groq Whisper.
    Returns the transcript string (empty string on failure).
    """
    wav_bytes = record_audio(status_callback)

    if not wav_bytes:
        return ""

    transcript = transcribe_audio(wav_bytes, status_callback)

    if status_callback:
        try:
            status_callback("Ready")
        except Exception:
            pass

    return transcript


# =========================================================
# LOCAL PC COMMANDS (fast, no AI call needed)
# =========================================================

def run_local_command(command):
    """
    Handles an allow-listed set of local actions.
    Returns a response string on match, or None if no local command matched.
    """
    cmd = command.lower().strip()

    # ── Websites ──────────────────────────────────────────
    if any(k in cmd for k in ("open google", "google kholo", "google khol")):
        webbrowser.open("https://www.google.com")
        return "Google open kar diya! 🌐"

    if any(k in cmd for k in ("open youtube", "youtube kholo", "youtube khol")):
        webbrowser.open("https://www.youtube.com")
        return "YouTube open kar diya! 📺"

    if any(k in cmd for k in ("open github", "github kholo", "github khol")):
        webbrowser.open("https://github.com")
        return "GitHub open kar diya! 💻"

    if any(k in cmd for k in ("open gmail", "gmail kholo", "gmail khol")):
        webbrowser.open("https://mail.google.com")
        return "Gmail open kar diya! 📧"

    if any(k in cmd for k in ("open chatgpt", "chatgpt kholo")):
        webbrowser.open("https://chatgpt.com")
        return "ChatGPT open kar diya! 🤖"

    # ── Windows Apps ──────────────────────────────────────
    if any(k in cmd for k in ("open notepad", "notepad kholo", "notepad khol")):
        subprocess.Popen(["notepad.exe"])
        return "Notepad open kar diya! 📝"

    if any(k in cmd for k in ("open calculator", "calculator kholo", "calc kholo")):
        subprocess.Popen(["calc.exe"])
        return "Calculator open kar diya! 🔢"

    if any(k in cmd for k in ("open explorer", "file explorer", "folder kholo")):
        subprocess.Popen(["explorer.exe"])
        return "File Explorer open kar diya! 📁"

    if any(k in cmd for k in ("open task manager", "task manager kholo")):
        subprocess.Popen(["taskmgr.exe"])
        return "Task Manager open kar diya! 📊"

    if any(k in cmd for k in ("open cmd", "command prompt kholo", "terminal kholo")):
        subprocess.Popen(["cmd.exe"])
        return "Command Prompt open kar diya! ⌨️"

    if any(k in cmd for k in ("open vscode", "open vs code", "vscode kholo")):
        _paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""),
                         "Programs", "Microsoft VS Code", "Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
        ]
        for path in _paths:
            if os.path.isfile(path):
                subprocess.Popen([path])
                return "VS Code open kar diya! 💡"
        try:
            subprocess.Popen(["code"])
            return "VS Code open karne ki koshish ki!"
        except FileNotFoundError:
            return "VS Code nahi mila. PATH mein Code.exe add karo."

    # ── Utility ───────────────────────────────────────────
    if any(k in cmd for k in ("what time", "time batao", "waqt batao", "time kya hai")):
        return "Abhi " + datetime.now().strftime("%I:%M %p") + " hai. ⏰"

    if any(k in cmd for k in ("what date", "date batao", "aaj ki date")):
        return "Aaj " + datetime.now().strftime("%A, %d %B %Y") + " hai. 📅"

    if any(k in cmd for k in ("show desktop", "desktop dikhao", "desktop pe jao")):
        try:
            import pyautogui
            pyautogui.hotkey("win", "d")
            return "Desktop show kar diya! 🖥️"
        except Exception:
            return "pyautogui install karo desktop shortcut ke liye."

    if any(k in cmd for k in ("clear chat", "chat clear karo", "history delete")):
        clear_memory()
        return "Chat history clear kar di! ✅"

    if any(k in cmd for k in ("volume up", "awaaz barhao")):
        try:
            import pyautogui
            for _ in range(5):
                pyautogui.press("volumeup")
            return "Volume badhа diya! 🔊"
        except Exception:
            return "Volume control ke liye pyautogui chahiye."

    if any(k in cmd for k in ("volume down", "awaaz kam karo")):
        try:
            import pyautogui
            for _ in range(5):
                pyautogui.press("volumedown")
            return "Volume kam kar diya! 🔉"
        except Exception:
            return "Volume control ke liye pyautogui chahiye."

    if any(k in cmd for k in ("mute", "sound band karo")):
        try:
            import pyautogui
            pyautogui.press("volumemute")
            return "Mute kar diya! 🔇"
        except Exception:
            return "Mute ke liye pyautogui chahiye."

    return None   # No local command matched


# =========================================================
# MESSAGE HANDLER
# =========================================================

def handle_message(message, status_callback=None):
    """
    First tries a local PC command; if none matches, asks Groq AI.
    """
    local_response = run_local_command(message)
    if local_response:
        return local_response

    return ask_ai(message, status_callback=status_callback)


# =========================================================
# CLI TEST MODE
# =========================================================

if __name__ == "__main__":
    print("JARVIS engine – CLI test mode")
    print("Type 'exit' to quit.\n")

    while True:
        user_text = input("You: ").strip()

        if user_text.lower() in ("exit", "quit"):
            break

        if not user_text:
            continue

        try:
            resp = handle_message(user_text)
            print("JARVIS:", resp)
            threading.Thread(target=speak, args=(resp,), daemon=True).start()
        except Exception as err:
            print("Error:", err)
