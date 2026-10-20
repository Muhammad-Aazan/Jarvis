"""
JARVIS Dashboard - Enhanced UI/UX
Fixed, polished, and production-ready
"""

import threading
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from datetime import datetime
import math

import psutil

import JARVIS as engine


# =========================================================
# THEME
# =========================================================

BG          = "#07111b"
PANEL       = "#0b1c2a"
PANEL_DARK  = "#060f18"
PANEL_LIGHT = "#0f2233"
CYAN        = "#00e5ff"
CYAN_DIM    = "#0d8a9e"
CYAN_DARK   = "#062630"
WHITE       = "#d8f7ff"
WHITE_DIM   = "#90b8c8"
MUTED       = "#4e7a8a"
GREEN       = "#00ffaa"
GREEN_DIM   = "#00994d"
RED         = "#ff4d6a"
ORANGE      = "#ffaa33"
YELLOW      = "#ffe066"
BORDER      = "#0e2a3d"

FONT        = "Segoe UI"
FONT_MONO   = "Consolas"


# =========================================================
# ANIMATED ORB (Canvas-based pulse ring)
# =========================================================

class OrbWidget(tk.Canvas):
    """Animated pulsing orb that shows JARVIS state."""

    IDLE_COLOR    = "#00e5ff"
    ACTIVE_COLOR  = "#00ffaa"
    LISTEN_COLOR  = "#ff4d6a"
    THINK_COLOR   = "#ffaa33"

    def __init__(self, parent, size=80, **kwargs):
        super().__init__(parent, width=size, height=size,
                         bg=BG, highlightthickness=0, **kwargs)
        self.size    = size
        self.cx      = size // 2
        self.cy      = size // 2
        self.radius  = size // 2 - 8
        self._angle  = 0
        self._state  = "idle"
        self._color  = self.IDLE_COLOR
        self._pulse  = 0.0
        self._pulse_dir = 1
        self._running = True
        self._draw()
        self._animate()

    def _draw(self):
        self.delete("all")
        r = self.radius
        cx, cy = self.cx, self.cy

        # Outer glow ring
        glow_r = r + 4 + int(self._pulse * 6)
        alpha_hex = format(int(80 + self._pulse * 60), "02x")
        glow_color = self._color
        self.create_oval(
            cx - glow_r, cy - glow_r,
            cx + glow_r, cy + glow_r,
            outline=glow_color, width=2
        )

        # Middle ring
        self.create_oval(
            cx - r - 2, cy - r - 2,
            cx + r + 2, cy + r + 2,
            outline=self._color, width=1
        )

        # Inner filled circle
        inner_r = int(r * 0.65)
        self.create_oval(
            cx - inner_r, cy - inner_r,
            cx + inner_r, cy + inner_r,
            fill=self._color, outline=""
        )

        # Rotating arc (only when active)
        if self._state != "idle":
            start = self._angle % 360
            self.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=start, extent=110,
                outline=self._color, width=3, style="arc"
            )

        # Center dot
        dot = 5
        self.create_oval(
            cx - dot, cy - dot,
            cx + dot, cy + dot,
            fill=BG, outline=""
        )

    def _animate(self):
        if not self._running:
            return

        self._angle = (self._angle + (3 if self._state != "idle" else 1)) % 360
        self._pulse += 0.06 * self._pulse_dir
        if self._pulse >= 1.0:
            self._pulse_dir = -1
        elif self._pulse <= 0.0:
            self._pulse_dir = 1

        self._draw()
        self.after(40, self._animate)

    def set_state(self, state):
        """state: 'idle' | 'listening' | 'thinking' | 'speaking'"""
        self._state = state
        self._color = {
            "idle":      self.IDLE_COLOR,
            "listening": self.LISTEN_COLOR,
            "thinking":  self.THINK_COLOR,
            "speaking":  self.ACTIVE_COLOR,
        }.get(state, self.IDLE_COLOR)

    def stop(self):
        self._running = False


# =========================================================
# PROGRESS BAR WIDGET
# =========================================================

class StatBar(tk.Frame):
    """Thin colored progress bar for CPU/RAM display."""

    def __init__(self, parent, label, color=CYAN, **kwargs):
        super().__init__(parent, bg=PANEL, **kwargs)
        self._color = color

        header = tk.Frame(self, bg=PANEL)
        header.pack(fill="x")

        self._name_label = tk.Label(
            header, text=label, bg=PANEL, fg=MUTED,
            font=(FONT, 8, "bold")
        )
        self._name_label.pack(side="left")

        self._val_label = tk.Label(
            header, text="—", bg=PANEL, fg=WHITE,
            font=(FONT_MONO, 8, "bold")
        )
        self._val_label.pack(side="right")

        self._bar_bg = tk.Frame(self, bg=PANEL_DARK, height=4)
        self._bar_bg.pack(fill="x", pady=(2, 0))
        self._bar_bg.pack_propagate(False)

        self._bar = tk.Frame(self._bar_bg, bg=color, height=4)
        self._bar.place(x=0, y=0, relheight=1.0, relwidth=0.0)

    def update_value(self, percent):
        self._val_label.configure(text=f"{percent:.0f}%")
        color = (RED if percent > 85 else ORANGE if percent > 65 else self._color)
        self._bar.configure(bg=color)
        self._bar.place(relwidth=min(percent / 100.0, 1.0))


# =========================================================
# MAIN DASHBOARD
# =========================================================

class JarvisDashboard:
    def __init__(self, root):
        self.root  = root
        self.busy  = False

        self.root.title("J.A.R.V.I.S.  •  Desktop AI")
        self.root.geometry("1240x800")
        self.root.minsize(960, 640)
        self.root.configure(bg=BG)

        # Track voice-countdown timer job
        self._countdown_job = None

        self._build_ui()
        self._update_system_stats()
        self._update_clock()

        self._append_chat(
            "JARVIS",
            "System online. 👋 Type a message or press SPEAK to talk with me.\n"
            "Model: " + engine.GROQ_MODEL
        )

    # =========================================================
    # UI LAYOUT
    # =========================================================

    def _build_ui(self):
        # ── Title bar row ──────────────────────────────────
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=20, pady=(14, 0))

        # Left: logo + subtitle
        logo_block = tk.Frame(top, bg=BG)
        logo_block.pack(side="left")

        tk.Label(
            logo_block, text="J.A.R.V.I.S.",
            bg=BG, fg=CYAN, font=(FONT, 26, "bold")
        ).pack(side="left")

        tk.Label(
            logo_block, text="  PERSONAL DESKTOP AI",
            bg=BG, fg=MUTED, font=(FONT, 10)
        ).pack(side="left", pady=(10, 0))

        # Right: clock + status pill
        right_block = tk.Frame(top, bg=BG)
        right_block.pack(side="right")

        self.clock_label = tk.Label(
            right_block, text="",
            bg=BG, fg=WHITE_DIM, font=(FONT_MONO, 10)
        )
        self.clock_label.pack(side="right", padx=(12, 0), pady=(10, 0))

        self.status_pill = tk.Label(
            right_block, text="● ONLINE",
            bg=BG, fg=GREEN, font=(FONT, 9, "bold")
        )
        self.status_pill.pack(side="right", pady=(10, 0))

        # Divider line
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(10, 0))

        # ── Body (side panel + chat) ────────────────────────
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=10)

        self._build_side_panel(body)
        self._build_chat_panel(body)

        # ── Footer ─────────────────────────────────────────
        tk.Label(
            self.root,
            text="JARVIS v2.0  •  Groq AI + Whisper STT  •  Realtek Mic",
            bg=BG, fg=MUTED, font=(FONT, 8)
        ).pack(pady=(0, 8))

    # ── SIDE PANEL ─────────────────────────────────────────

    def _build_side_panel(self, parent):
        side = tk.Frame(
            parent, bg=PANEL, width=250,
            highlightbackground=BORDER, highlightthickness=1
        )
        side.pack(side="left", fill="y", padx=(0, 12))
        side.pack_propagate(False)

        # Orb + state label
        orb_frame = tk.Frame(side, bg=PANEL)
        orb_frame.pack(pady=(20, 8))

        self.orb = OrbWidget(orb_frame, size=90)
        self.orb.pack()

        self.orb_label = tk.Label(
            side, text="IDLE",
            bg=PANEL, fg=CYAN, font=(FONT, 8, "bold")
        )
        self.orb_label.pack()

        tk.Frame(side, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(12, 0))

        # System stats
        self._section_label(side, "SYSTEM")

        stats_frame = tk.Frame(side, bg=PANEL)
        stats_frame.pack(fill="x", padx=16, pady=4)

        self.cpu_bar  = StatBar(stats_frame, "CPU ", color=CYAN)
        self.cpu_bar.pack(fill="x", pady=3)

        self.ram_bar  = StatBar(stats_frame, "RAM ", color=GREEN)
        self.ram_bar.pack(fill="x", pady=3)

        self.disk_bar = StatBar(stats_frame, "DISK", color=ORANGE)
        self.disk_bar.pack(fill="x", pady=3)

        tk.Frame(side, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(10, 0))

        # Quick Actions
        self._section_label(side, "QUICK ACTIONS")

        actions = [
            ("🌐  Google",       "open google"),
            ("📺  YouTube",      "open youtube"),
            ("📧  Gmail",        "open gmail"),
            ("💻  GitHub",       "open github"),
            ("📝  Notepad",      "open notepad"),
            ("🔢  Calculator",   "open calculator"),
            ("📁  Explorer",     "open explorer"),
            ("💡  VS Code",      "open vscode"),
        ]
        for label, cmd in actions:
            self._quick_btn(side, label, cmd)

        tk.Frame(side, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(10, 0))

        # Mic info
        self._section_label(side, "MICROPHONE")
        tk.Label(
            side,
            text=f"Device {engine.MIC_DEVICE}: Realtek (MME)",
            bg=PANEL, fg=MUTED, font=(FONT, 8)
        ).pack(anchor="w", padx=16)
        tk.Label(
            side,
            text=f"{engine.MIC_SAMPLE_RATE} Hz  |  {engine.RECORD_SECONDS}s record",
            bg=PANEL, fg=MUTED, font=(FONT, 8)
        ).pack(anchor="w", padx=16, pady=(2, 0))

        # Clear memory button
        tk.Frame(side, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(14, 0))
        tk.Button(
            side, text="🗑  Clear History",
            command=self._clear_history,
            bg=PANEL_DARK, fg=RED,
            activebackground=RED, activeforeground=BG,
            relief="flat", font=(FONT, 8, "bold"),
            padx=10, pady=6, cursor="hand2"
        ).pack(fill="x", padx=16, pady=10)

    def _section_label(self, parent, text):
        tk.Label(
            parent, text=text,
            bg=PANEL, fg=CYAN, font=(FONT, 9, "bold")
        ).pack(anchor="w", padx=16, pady=(12, 4))

    def _quick_btn(self, parent, label, cmd):
        btn = tk.Button(
            parent, text=label,
            command=lambda: self._process_message(cmd),
            bg=PANEL_DARK, fg=WHITE_DIM,
            activebackground=CYAN_DARK, activeforeground=CYAN,
            relief="flat", anchor="w",
            font=(FONT, 9), padx=10, pady=7, cursor="hand2"
        )
        btn.pack(fill="x", padx=12, pady=1)

        # Hover effect
        btn.bind("<Enter>", lambda e, b=btn: b.configure(fg=CYAN, bg="#0e2233"))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(fg=WHITE_DIM, bg=PANEL_DARK))

    # ── CHAT PANEL ─────────────────────────────────────────

    def _build_chat_panel(self, parent):
        chat_outer = tk.Frame(
            parent, bg=PANEL_DARK,
            highlightbackground=BORDER, highlightthickness=1
        )
        chat_outer.pack(side="left", fill="both", expand=True)

        # Chat header
        chat_hdr = tk.Frame(chat_outer, bg=PANEL)
        chat_hdr.pack(fill="x")

        tk.Label(
            chat_hdr, text="CONVERSATION",
            bg=PANEL, fg=CYAN, font=(FONT, 11, "bold")
        ).pack(side="left", padx=14, pady=10)

        tk.Button(
            chat_hdr, text="Clear",
            command=self._clear_chat_display,
            bg=PANEL, fg=MUTED,
            activebackground=PANEL_LIGHT, activeforeground=RED,
            relief="flat", font=(FONT, 8), padx=6, cursor="hand2"
        ).pack(side="right", padx=14, pady=10)

        # Chat text area
        self.chat_text = scrolledtext.ScrolledText(
            chat_outer,
            bg=PANEL_DARK, fg=WHITE,
            insertbackground=CYAN,
            font=(FONT, 11),
            wrap="word",
            relief="flat",
            borderwidth=0,
            padx=16, pady=12,
            state="disabled",
            spacing1=2, spacing3=4,
        )
        self.chat_text.pack(fill="both", expand=True)

        # Text tags
        self.chat_text.tag_config("user_name",   foreground=GREEN,    font=(FONT, 10, "bold"))
        self.chat_text.tag_config("jarvis_name", foreground=CYAN,     font=(FONT, 10, "bold"))
        self.chat_text.tag_config("body",        foreground=WHITE_DIM, font=(FONT, 11))
        self.chat_text.tag_config("time",        foreground=MUTED,     font=(FONT_MONO, 8))
        self.chat_text.tag_config("error",       foreground=RED,       font=(FONT, 10))
        self.chat_text.tag_config("system",      foreground=MUTED,     font=(FONT, 9, "italic"))

        # Status strip
        status_strip = tk.Frame(chat_outer, bg=PANEL)
        status_strip.pack(fill="x")

        self.voice_status_var = tk.StringVar(value="Ready")
        self._status_dot = tk.Label(
            status_strip, text="●",
            bg=PANEL, fg=GREEN, font=(FONT, 10)
        )
        self._status_dot.pack(side="left", padx=(14, 4), pady=7)

        tk.Label(
            status_strip,
            textvariable=self.voice_status_var,
            bg=PANEL, fg=WHITE_DIM, font=(FONT, 9)
        ).pack(side="left", pady=7)

        # Countdown label (shows recording seconds left)
        self._countdown_var = tk.StringVar(value="")
        tk.Label(
            status_strip,
            textvariable=self._countdown_var,
            bg=PANEL, fg=ORANGE, font=(FONT_MONO, 9, "bold")
        ).pack(side="right", padx=14, pady=7)

        # Input row
        input_row = tk.Frame(chat_outer, bg=BG)
        input_row.pack(fill="x", padx=10, pady=10)

        self.entry = tk.Entry(
            input_row,
            bg="#0d2030", fg=WHITE,
            insertbackground=CYAN,
            relief="flat",
            font=(FONT, 11),
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=11, padx=(0, 8))
        self.entry.bind("<Return>", lambda e: self._send_text())
        self.entry.bind("<FocusIn>",  lambda e: self.entry.configure(highlightbackground=CYAN_DIM))
        self.entry.bind("<FocusOut>", lambda e: self.entry.configure(highlightbackground=BORDER))

        self.send_btn = tk.Button(
            input_row, text="SEND",
            command=self._send_text,
            bg=CYAN_DIM, fg="white",
            activebackground=CYAN, activeforeground=BG,
            relief="flat", font=(FONT, 10, "bold"),
            padx=20, pady=11, cursor="hand2"
        )
        self.send_btn.pack(side="left", padx=(0, 8))

        self.speak_btn = tk.Button(
            input_row, text="🎙  SPEAK",
            command=self._start_voice,
            bg="#0e2234", fg=CYAN,
            activebackground="#1a3d55", activeforeground=WHITE,
            relief="flat", font=(FONT, 10, "bold"),
            padx=18, pady=11, cursor="hand2"
        )
        self.speak_btn.pack(side="left")

    # =========================================================
    # CHAT HELPERS
    # =========================================================

    def _append_chat(self, speaker, text):
        """Thread-safe chat append."""
        def _do():
            self.chat_text.configure(state="normal")
            ts = datetime.now().strftime("%H:%M")

            if speaker == "You":
                self.chat_text.insert("end", f"\n[{ts}] ", "time")
                self.chat_text.insert("end", f"You\n", "user_name")
                self.chat_text.insert("end", f"{text}\n", "body")
            elif speaker == "JARVIS":
                self.chat_text.insert("end", f"\n[{ts}] ", "time")
                self.chat_text.insert("end", f"J.A.R.V.I.S.\n", "jarvis_name")
                self.chat_text.insert("end", f"{text}\n", "body")
            elif speaker == "error":
                self.chat_text.insert("end", f"\n⚠ {text}\n", "error")
            else:
                self.chat_text.insert("end", f"\n{text}\n", "system")

            self.chat_text.configure(state="disabled")
            self.chat_text.see("end")

        self.root.after(0, _do)

    def _clear_chat_display(self):
        """Clear visible chat (keeps memory)."""
        self.chat_text.configure(state="normal")
        self.chat_text.delete("1.0", "end")
        self.chat_text.configure(state="disabled")
        self._append_chat("system", "Chat display cleared.")

    def _clear_history(self):
        """Clear chat display + conversation memory."""
        if messagebox.askyesno(
            "Clear History",
            "Conversation memory clear kar dein?\nYe action undo nahi hogi.",
            icon="warning"
        ):
            engine.clear_memory()
            self._clear_chat_display()
            self._append_chat("system", "✅ Memory & chat cleared.")

    # =========================================================
    # MESSAGE PROCESSING
    # =========================================================

    def _send_text(self):
        message = self.entry.get().strip()
        if not message:
            return
        self.entry.delete(0, "end")
        self._process_message(message)

    def _process_message(self, message):
        if self.busy:
            self._set_status("JARVIS is busy. Please wait…", "warning")
            return

        self._append_chat("You", message)
        self._set_busy(True)
        self._set_state("thinking")

        threading.Thread(
            target=self._worker_message,
            args=(message,),
            daemon=True
        ).start()

    def _worker_message(self, message):
        try:
            response = engine.handle_message(
                message,
                status_callback=lambda m: self.root.after(
                    0, lambda msg=m: self._set_status(msg)
                )
            )
        except Exception as e:
            response = f"Error: {e}"

        self.root.after(0, lambda: self._finish_response(response))

    def _finish_response(self, response):
        self._append_chat("JARVIS", response)
        self._set_status("Ready", "ok")
        self._set_state("idle")
        self._set_busy(False)

        # Speak in background thread
        threading.Thread(
            target=self._speak_thread,
            args=(response,),
            daemon=True
        ).start()

    def _speak_thread(self, text):
        self.root.after(0, lambda: self._set_state("speaking"))
        engine.speak(text)
        self.root.after(0, lambda: self._set_state("idle"))

    # =========================================================
    # VOICE INPUT
    # =========================================================

    def _start_voice(self):
        if self.busy:
            self._set_status("JARVIS is busy. Please wait…", "warning")
            return

        self._set_busy(True)
        self._set_state("listening")
        self._set_status("🎙 Preparing mic…")
        self._start_countdown(engine.RECORD_SECONDS)

        threading.Thread(target=self._worker_voice, daemon=True).start()

    def _start_countdown(self, seconds):
        """Show countdown during recording."""
        remaining = [seconds]

        def tick():
            if remaining[0] > 0:
                self._countdown_var.set(f"⏱ {remaining[0]}s")
                remaining[0] -= 1
                self._countdown_job = self.root.after(1000, tick)
            else:
                self._countdown_var.set("")

        self._countdown_var.set(f"⏱ {seconds}s")
        self._countdown_job = self.root.after(1000, tick)

    def _worker_voice(self):
        transcript = engine.record_transcribe(
            status_callback=lambda m: self.root.after(
                0, lambda msg=m: self._set_status(msg)
            )
        )

        # Cancel countdown
        if self._countdown_job:
            self.root.after(0, lambda: self.root.after_cancel(self._countdown_job))
        self.root.after(0, lambda: self._countdown_var.set(""))

        if not transcript:
            self.root.after(0, self._voice_failed)
            return

        self.root.after(0, lambda: self._append_chat("You", f"[Voice] {transcript}"))
        self.root.after(0, lambda: self._set_status("Processing…"))
        self.root.after(0, lambda: self._set_state("thinking"))

        try:
            response = engine.handle_message(
                transcript,
                status_callback=lambda m: self.root.after(
                    0, lambda msg=m: self._set_status(msg)
                )
            )
        except Exception as e:
            response = f"Error: {e}"

        self.root.after(0, lambda: self._finish_response(response))

    def _voice_failed(self):
        self._set_status("No speech detected. Try again.", "warning")
        self._set_state("idle")
        self._set_busy(False)

    # =========================================================
    # STATUS + ORB
    # =========================================================

    def _set_status(self, message, level="info"):
        self.voice_status_var.set(message)

        dot_color = {
            "ok":      GREEN,
            "warning": ORANGE,
            "error":   RED,
            "info":    CYAN,
        }.get(level, CYAN)

        if "error" in message.lower() or "failed" in message.lower():
            dot_color = RED
            pill_text = "● ERROR"
            pill_color = RED
        elif "ready" in message.lower():
            dot_color = GREEN
            pill_text = "● ONLINE"
            pill_color = GREEN
        elif "listen" in message.lower():
            dot_color = RED
            pill_text = "● LISTENING"
            pill_color = RED
        elif "think" in message.lower() or "processing" in message.lower():
            dot_color = ORANGE
            pill_text = "● THINKING"
            pill_color = ORANGE
        elif "speak" in message.lower() or "transcrib" in message.lower():
            dot_color = CYAN
            pill_text = "● ACTIVE"
            pill_color = CYAN
        else:
            pill_text = "● ACTIVE"
            pill_color = CYAN

        self._status_dot.configure(fg=dot_color)
        self.status_pill.configure(text=pill_text, fg=pill_color)

    def _set_state(self, state):
        """Update orb + orb label."""
        self.orb.set_state(state)
        labels = {
            "idle":      "IDLE",
            "listening": "LISTENING",
            "thinking":  "THINKING",
            "speaking":  "SPEAKING",
        }
        colors = {
            "idle":      CYAN,
            "listening": RED,
            "thinking":  ORANGE,
            "speaking":  GREEN,
        }
        label = labels.get(state, "ACTIVE")
        color = colors.get(state, CYAN)
        self.orb_label.configure(text=label, fg=color)

    def _set_busy(self, busy):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.send_btn.configure(state=state)
        self.speak_btn.configure(state=state)
        self.entry.configure(state=state)

    # =========================================================
    # SYSTEM STATS + CLOCK
    # =========================================================

    def _update_system_stats(self):
        try:
            cpu  = psutil.cpu_percent(interval=None)
            ram  = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent

            self.cpu_bar.update_value(cpu)
            self.ram_bar.update_value(ram)
            self.disk_bar.update_value(disk)
        except Exception:
            pass

        self.root.after(1500, self._update_system_stats)

    def _update_clock(self):
        now = datetime.now().strftime("%a  %d %b  %H:%M:%S")
        self.clock_label.configure(text=now)
        self.root.after(1000, self._update_clock)


# =========================================================
# ENTRY POINT
# =========================================================

def main():
    root = tk.Tk()

    # Window icon (ignore if no .ico present)
    try:
        root.iconbitmap("jarvis.ico")
    except Exception:
        pass

    app = JarvisDashboard(root)

    def on_close():
        app.orb.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
