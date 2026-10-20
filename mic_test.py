
import sounddevice as sd
import numpy as np

MIC_DEVICE = 1
SAMPLE_RATE = 16000

print("Speak into your microphone for 5 seconds...")

try:
    audio = sd.rec(
        int(5 * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=MIC_DEVICE
    )
    sd.wait()

    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(audio ** 2)))

    print(f"Peak level: {peak:.4f}")
    print(f"Average level (RMS): {rms:.4f}")

    if peak < 0.005:
        print("Mic audio is extremely low or silent.")
    else:
        print("Mic is receiving audio.")

except Exception as e:
    print("Microphone error:", e)
