
import re
import unicodedata
from difflib import SequenceMatcher

COMMANDS = {
    "chrome": [
        "chrome", "krom", "cro", "crome",
        "chrome kholo", "krom kholo", "cro kolo",
        "cro cholo", "chrome open", "open chrome",
        "jarvis chrome kholo"
    ],
    "youtube": [
        "youtube", "you tube", "you too", "yoo too",
        "yootoo", "yutu", "youtub",
        "youtube kholo", "you tube kholo",
        "you too kholo", "you too kolo",
        "yoo too cholo", "yootoo khlo",
        "open youtube", "youtube open karo"
    ],
    "google": [
        "google", "gugal", "google kholo",
        "open google", "gugul kolo"
    ],
    "vscode": [
        "vscode", "vs code", "visual studio code",
        "vs code kholo", "open vscode"
    ],
}

def normalize(text):
    text = unicodedata.normalize("NFKC", text.lower())
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())

def words_match(text, phrase):
    text = normalize(text)
    phrase = normalize(phrase)

    if not phrase:
        return False

    if phrase in text:
        return True

    text_words = text.split()
    phrase_words = phrase.split()

    # Single-word variations, e.g. "krom" for "chrome"
    if len(phrase_words) == 1:
        return any(
            SequenceMatcher(None, word, phrase).ratio() >= 0.72
            for word in text_words
        )

    # Match individual words in multi-word commands
    return all(
        any(
            SequenceMatcher(None, word, target).ratio() >= 0.72
            for word in text_words
        )
        for target in phrase_words
    )

def identify_command(transcript):
    text = normalize(transcript)

    # Exact phrase matches first
    for command, phrases in COMMANDS.items():
        for phrase in phrases:
            if normalize(phrase) in text:
                return command

    # Approximate matches next
    for command, phrases in COMMANDS.items():
        for phrase in phrases:
            if words_match(text, phrase):
                return command

    return None

while True:
    spoken_text = input("\nWhisper transcript likho (exit se band): ")

    if spoken_text.lower().strip() == "exit":
        break

    command = identify_command(spoken_text)

    if command:
        print("JARVIS command:", command)
    else:
        print("Command samajh nahi aayi.")
