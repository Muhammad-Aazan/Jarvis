
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

MIC_DEVICE = 1
SAMPLE_RATE = 16000
RECORD_SECONDS = 8

print("JARVIS: Whisper model load ho raha hai...", flush=True)

model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)

print("JARVIS: Ready! Urdu ya English mein bolo.", flush=True)
input("Enter dabao aur bolna shuru karo: ")

print("Recording... ab bolo!", flush=True)

audio = sd.rec(
    int(RECORD_SECONDS * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="float32",
    device=MIC_DEVICE
)
sd.wait()

print("Awaaz mil gayi! Text bana raha hoon...", flush=True)

segments, info = model.transcribe(
    audio.flatten(),
    beam_size=5,
    language=None
)

text = " ".join(segment.text.strip() for segment in segments)

print("\nDetected language:", info.language)
print("Tumne kaha:", text if text else "Koi speech detect nahi hui")
