import json
import queue
import subprocess
import webbrowser
import sounddevice as sd
from vosk import Model, KaldiRecognizer

MODEL_PATH = "model"

# Handsfree microphone from your device list.
# If Windows changes the device order, check sd.query_devices() again.
MIC_DEVICE = 1
SAMPLE_RATE = 16000

audio_queue = queue.Queue()

# Limit Vosk to likely commands and common Roman Urdu variants.
# This helps recognition, but doesn't make an English model fluent in Urdu.
COMMAND_GRAMMAR = [
    "open vscode",
    "open vs code",
    "open v s code",
    "open visual studio code",
    "open this code",
    "open his code",
    "open chrome",
    "open google chrome",
    "open edge",
    "open microsoft edge",
    "open youtube",
    "open google",
    "open antigravity",

    "vscode kholo",
    "vs code kholo",
    "chrome kholo",
    "google chrome kholo",
    "edge kholo",
    "youtube kholo",
    "google kholo",
    "antigravity kholo",

    "stop jarvis",
    "exit",
    "jarvis band karo",
    "jarvis ruk jao",

    "[unk]"
]

print("=" * 40)
print("       J.A.R.V.I.S. ASSISTANT")
print("=" * 40)

print("Loading voice model...")
model = Model(MODEL_PATH)

recognizer = KaldiRecognizer(
    model,
    SAMPLE_RATE,
    json.dumps(COMMAND_GRAMMAR)
)

print("JARVIS is online!")
print("Try: open visual studio code, open chrome, open youtube.")
print("Roman Urdu: chrome kholo, youtube kholo, jarvis band karo.")
print("Press Ctrl+C to stop.\n")


def open_app(app_name):
    try:
        subprocess.Popen(
            f'start "" "{app_name}"',
            shell=True
        )
        print(f"JARVIS: Opening {app_name}...")
    except Exception as error:
        print(f"JARVIS: Could not open app: {error}")


def handle_command(command):
    command = command.lower().strip()
    print(f"\nYou said: {command}")

    # VS Code — include common transcript variations
    if any(phrase in command for phrase in [
        "vscode",
        "vs code",
        "v s code",
        "visual studio code",
        "this code",
        "his code"
    ]):
        open_app("code")

    elif "chrome" in command:
        open_app("chrome")

    elif "edge" in command:
        open_app("msedge")

    elif "antigravity" in command:
        open_app("antigravity")

    elif "youtube" in command:
        webbrowser.open("https://www.youtube.com/")

    elif "google" in command:
        webbrowser.open("https://www.google.com/")

    elif any(phrase in command for phrase in [
        "stop jarvis",
        "exit",
        "band karo",
        "ruk jao"
    ]):
        print("JARVIS: Goodbye, sir!")
        raise KeyboardInterrupt

    else:
        print("JARVIS: Command not recognized.")


def audio_callback(indata, frames, time, status):
    if status:
        print("Audio status:", status)

    audio_queue.put(bytes(indata))


try:
    with sd.RawInputStream(
        device=MIC_DEVICE,
        samplerate=SAMPLE_RATE,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=audio_callback,
    ):
        print(f"JARVIS: Listening on microphone device {MIC_DEVICE}...")

        while True:
            data = audio_queue.get()

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "")

                if text:
                    handle_command(text)

except KeyboardInterrupt:
    print("\nJARVIS: Shutting down.")

except Exception as error:
    print(f"\nJARVIS error: {error}")