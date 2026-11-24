"""Desktop interface for the AudioSource C++ example."""

from pathlib import Path
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox
from typing import Optional


SOURCE = Path(__file__).with_name("main.cpp")
VLC_SOURCE = SOURCE.with_name("VlcPlayer.cpp")
HEADERS = [SOURCE.with_name(name) for name in
           ("AudioSource.h", "Radio.h", "Bluetooth.h", "VlcPlayer.h")]
BG = "#0b1220"
SURFACE = "#131e30"
BORDER = "#26354a"
TEXT = "#ecf3fb"
MUTED = "#91a3ba"
CYAN = "#37c9df"
AMBER = "#f4b85a"


class AudioApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Audio Console")
        self.root.geometry("800x500")
        self.root.minsize(680, 450)
        self.root.configure(bg=BG)
        self.build_dir = tempfile.TemporaryDirectory(prefix="audio_source_")
        self.program = Path(self.build_dir.name) / "audio_source"
        self.backend = None
        self.volume_jobs = {}
        self.source_state = {"A": "stopped", "B": "stopped"}
        self.pause_buttons = {}

        page = tk.Frame(root, bg=BG)
        page.pack(fill=tk.BOTH, expand=True, padx=30, pady=24)

        header = tk.Frame(page, bg=BG)
        header.pack(fill=tk.X)
        tk.Label(header, text="♫", bg=CYAN, fg=BG,
                 font=("DejaVu Sans", 22, "bold"), width=3).pack(side=tk.LEFT, padx=(0, 14))
        heading = tk.Frame(header, bg=BG)
        heading.pack(side=tk.LEFT)
        tk.Label(heading, text="Audio Console", bg=BG, fg=TEXT,
                 font=("DejaVu Sans", 20, "bold")).pack(anchor="w")
        tk.Label(heading, text="Điều khiển nguồn âm thanh từ C++", bg=BG,
                 fg=MUTED, font=("DejaVu Sans", 10)).pack(anchor="w", pady=(3, 0))
        self.status_label = tk.Label(header, text="●  Sẵn sàng", bg=SURFACE,
                                     fg=CYAN, font=("DejaVu Sans", 10, "bold"),
                                     padx=14, pady=9)
        self.status_label.pack(side=tk.RIGHT)

        tk.Label(page, text="Chọn nguồn phát", bg=BG, fg=TEXT,
                 font=("DejaVu Sans", 15, "bold")).pack(anchor="w", pady=(32, 5))
        tk.Label(page, text="Điều khiển riêng Radio và Bluetooth.",
                 bg=BG, fg=MUTED, font=("DejaVu Sans", 10)).pack(anchor="w")

        cards = tk.Frame(page, bg=BG)
        cards.pack(fill=tk.X, pady=(18, 26))
        cards.grid_columnconfigure(0, weight=1, uniform="sources")
        cards.grid_columnconfigure(1, weight=1, uniform="sources")
        self.source_card(cards, 0, "A", "Radio", "Nguồn phát radio", AMBER)
        self.source_card(cards, 1, "B", "Bluetooth", "Nguồn phát Bluetooth", CYAN)

        tk.Label(page, text="Đầu ra C++ hiển thị trong terminal mở ứng dụng.",
                 bg=BG, fg=MUTED, font=("DejaVu Sans", 10)).pack(anchor="w")

        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def source_card(self, parent: tk.Frame, column: int, key: str,
                    name: str, description: str, accent: str) -> None:
        outer = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
        outer.grid(row=0, column=column, sticky="nsew",
                   padx=(0, 9) if column == 0 else (9, 0))
        card = tk.Frame(outer, bg=SURFACE, padx=18, pady=16)
        card.pack(fill=tk.BOTH, expand=True)
        top = tk.Frame(card, bg=SURFACE)
        top.pack(fill=tk.X)
        tk.Label(top, text=key, bg=accent, fg=BG,
                 font=("DejaVu Sans", 11, "bold"), width=3,
                 pady=5).pack(side=tk.LEFT)
        tk.Label(top, text=name, bg=SURFACE, fg=TEXT,
                 font=("DejaVu Sans", 16, "bold")).pack(side=tk.LEFT, padx=12)
        tk.Label(card, text=description, bg=SURFACE, fg=MUTED,
                 font=("DejaVu Sans", 10)).pack(anchor="w", pady=(14, 16))
        controls = tk.Frame(card, bg=SURFACE)
        controls.pack(fill=tk.X)
        for action, label in (("PLAY", "Phát"), ("PAUSE", "Tạm dừng"),
                              ("STOP", "Dừng")):
            callback = {"PLAY": self.play_source, "PAUSE": self.toggle_pause,
                        "STOP": self.stop_source}[action]
            button = tk.Button(controls, text=label,
                               command=lambda fn=callback: fn(key),
                               bg=accent if action == "PLAY" else BORDER,
                               fg=BG if action == "PLAY" else TEXT,
                               activebackground=accent, activeforeground=BG,
                               relief=tk.FLAT, bd=0, cursor="hand2",
                               font=("DejaVu Sans", 9, "bold"), pady=9)
            button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            if action == "PAUSE":
                button.configure(state=tk.DISABLED)
                self.pause_buttons[key] = button

        volume_row = tk.Frame(card, bg=SURFACE)
        volume_row.pack(fill=tk.X, pady=(15, 0))
        tk.Label(volume_row, text="Âm lượng", bg=SURFACE, fg=MUTED,
                 font=("DejaVu Sans", 10)).pack(side=tk.LEFT)
        volume_value = tk.Label(volume_row, text="50%", bg=SURFACE, fg=accent,
                                font=("DejaVu Sans", 10, "bold"))
        volume_value.pack(side=tk.RIGHT)

        slider = tk.Scale(card, from_=0, to=100, orient=tk.HORIZONTAL,
                          showvalue=False, bg=SURFACE, fg=TEXT,
                          troughcolor=BORDER, activebackground=accent,
                          highlightthickness=0, bd=0, sliderrelief=tk.FLAT)
        slider.set(50)
        slider.configure(command=lambda value, source=key, label=volume_value:
                         self.queue_volume(source, int(float(value)), label))
        slider.pack(fill=tk.X)

    def queue_volume(self, choice: str, value: int, label: tk.Label) -> None:
        label.configure(text=f"{value}%")
        previous = self.volume_jobs.get(choice)
        if previous is not None:
            self.root.after_cancel(previous)
        self.volume_jobs[choice] = self.root.after(
            150, lambda: self.send_volume(choice, value))

    def send_volume(self, choice: str, value: int) -> None:
        self.volume_jobs.pop(choice, None)
        if self.send_command("VOLUME", choice, value):
            name = "Radio" if choice == "A" else "Bluetooth"
            self.set_status(f"{name}: {value}%")

    def play_source(self, choice: str) -> None:
        if not self.ensure_backend():
            return
        state = self.source_state[choice]
        if state == "paused":
            self.toggle_pause(choice)
        elif self.send_command("PLAY", choice):
            self.source_state[choice] = "playing"
            self.pause_buttons[choice].configure(state=tk.NORMAL, text="Tạm dừng")
            name = "Radio" if choice == "A" else "Bluetooth"
            self.set_status(f"Đang phát {name}", AMBER)

    def toggle_pause(self, choice: str) -> None:
        if not self.ensure_backend():
            return
        state = self.source_state[choice]
        if state not in ("playing", "paused"):
            return
        if self.send_command("PAUSE", choice):
            paused = state == "playing"
            self.source_state[choice] = "paused" if paused else "playing"
            self.pause_buttons[choice].configure(
                text="Tiếp tục" if paused else "Tạm dừng")
            name = "Radio" if choice == "A" else "Bluetooth"
            self.set_status(f"Đã tạm dừng {name}" if paused else f"Đang phát {name}",
                            CYAN if paused else AMBER)

    def stop_source(self, choice: str) -> None:
        if not self.ensure_backend():
            return
        if self.source_state[choice] == "stopped":
            return
        if self.send_command("STOP", choice):
            self.source_state[choice] = "stopped"
            self.pause_buttons[choice].configure(state=tk.DISABLED, text="Tạm dừng")
            name = "Radio" if choice == "A" else "Bluetooth"
            self.set_status(f"Đã dừng {name}")

    def set_status(self, message: str, color: str = CYAN) -> None:
        self.status_label.configure(text=f"●  {message}", fg=color)
        self.root.update_idletasks()

    def compile_if_needed(self) -> bool:
        dependencies = [SOURCE, VLC_SOURCE, *HEADERS]
        missing = next((path for path in dependencies if not path.exists()), None)
        if missing is not None:
            messagebox.showerror("Thiếu file C++", f"Không tìm thấy {missing.name}.")
            self.set_status("Lỗi", "#ff8e8e")
            return False
        latest_source = max(path.stat().st_mtime for path in dependencies)
        if self.program.exists() and self.program.stat().st_mtime >= latest_source:
            return True

        self.set_status("Đang biên dịch", AMBER)
        try:
            result = subprocess.run(
                ["g++", "-std=c++11", str(SOURCE), str(VLC_SOURCE),
                 "-o", str(self.program)],
                capture_output=True, text=True, check=False,
            )
        except OSError as exc:
            messagebox.showerror("Lỗi biên dịch", f"Không chạy được g++: {exc}")
            self.set_status("Lỗi", "#ff8e8e")
            return False

        if result.returncode != 0:
            messagebox.showerror("Lỗi biên dịch", result.stderr or "Biên dịch thất bại.")
            self.set_status("Lỗi biên dịch", "#ff8e8e")
            return False
        return True

    def ensure_backend(self) -> bool:
        if self.backend is not None and self.backend.poll() is None:
            return True
        if self.backend is not None:
            for choice in self.source_state:
                self.source_state[choice] = "stopped"
                self.pause_buttons[choice].configure(state=tk.DISABLED, text="Tạm dừng")
        if not self.compile_if_needed():
            return False

        try:
            self.backend = subprocess.Popen(
                [str(self.program)], stdin=subprocess.PIPE,
                text=True, bufsize=1, cwd=SOURCE.parent,
            )
        except OSError as exc:
            messagebox.showerror("Lỗi chương trình", str(exc))
            self.set_status("Lỗi", "#ff8e8e")
            return False
        return True

    def send_command(self, action: str, choice: str,
                     value: Optional[int] = None) -> bool:
        if not self.ensure_backend():
            return False

        try:
            command = f"{action} {choice}"
            if value is not None:
                command += f" {value}"
            self.backend.stdin.write(command + "\n")
            self.backend.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            messagebox.showerror("Lỗi chương trình", str(exc))
            self.set_status("Lỗi", "#ff8e8e")
            return False
        return True

    def close(self) -> None:
        for job in self.volume_jobs.values():
            self.root.after_cancel(job)
        self.volume_jobs.clear()
        if self.backend is not None and self.backend.poll() is None:
            try:
                self.backend.stdin.write("QUIT\n")
                self.backend.stdin.flush()
            except (BrokenPipeError, OSError):
                pass
            try:
                self.backend.stdin.close()
            except OSError:
                pass
            try:
                self.backend.wait(timeout=2)
            except subprocess.TimeoutExpired:
                if self.backend.poll() is None:
                    self.backend.terminate()
                try:
                    self.backend.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.backend.kill()
                    self.backend.wait()
        self.build_dir.cleanup()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    AudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except tk.TclError as exc:
        print(f"Không mở được GUI: {exc}", file=sys.stderr)
        sys.exit(1)
