import sounddevice as sd

print("=== AVAILABLE MICROPHONES ===")

for i, device in enumerate(sd.query_devices()):
    if device["max_input_channels"] > 0:
        print(
            f"Device {i}: {device['name']} | "
            f"Input channels: {device['max_input_channels']} | "
            f"Sample rate: {device['default_samplerate']}"
        )

print("\nDefault devices:", sd.default.device)