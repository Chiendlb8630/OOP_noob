"""Ứng dụng ghi lại các buổi học và tính tổng thời gian học."""

from datetime import date, datetime
import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from uuid import uuid4


DATA_FILE = Path(__file__).with_name("study_sessions.json")

BG = "#f3f6f3"
SURFACE = "#ffffff"
BORDER = "#d8e2db"
TEXT = "#172b20"
MUTED = "#627468"
GREEN = "#1f8052"


def session_minutes(session: dict[str, str]) -> int:
    day = datetime.strptime(session["date"], "%Y-%m-%d").date()
    start = datetime.strptime(session["start"], "%H:%M").time()
    end = datetime.strptime(session["end"], "%H:%M").time()
    start_at = datetime.combine(day, start)
    end_at = datetime.combine(day, end)
    return int((end_at - start_at).total_seconds() // 60)


def format_duration(minutes: int) -> str:
    hours, remaining_minutes = divmod(minutes, 60)
    return f"{hours} giờ {remaining_minutes:02d} phút"


class StudyTracker:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Study Tracker | Theo dõi giờ học")
        self.root.geometry("900x650")
        self.root.minsize(760, 540)
        self.root.configure(bg=BG)

        self.storage_available = True
        self.load_error = ""
        self.sessions = self.load_sessions()

        self.configure_style()
        self.build_interface()
        self.refresh_history()

        if self.load_error:
            self.root.after_idle(
                lambda: messagebox.showerror("Không đọc được lịch sử", self.load_error)
            )

    def configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Study.Treeview", background=SURFACE, fieldbackground=SURFACE,
            foreground=TEXT, rowheight=36, borderwidth=0,
            font=("TkDefaultFont", 10),
        )
        style.configure(
            "Study.Treeview.Heading", background="#edf2ee", foreground=MUTED,
            relief="flat", font=("TkDefaultFont", 9, "bold"), padding=(10, 9),
        )
        style.map("Study.Treeview", background=[("selected", "#d6f2e1")])
        style.configure(
            "Study.Vertical.TScrollbar", background=SURFACE,
            troughcolor=BG, bordercolor=BG, arrowcolor=MUTED,
        )

    def build_interface(self) -> None:
        page = tk.Frame(self.root, bg=BG)
        page.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

        header = tk.Frame(page, bg=BG)
        header.pack(fill=tk.X)
        badge = tk.Label(
            header, text="◷", bg=GREEN, fg=SURFACE,
            font=("TkDefaultFont", 22, "bold"), width=3, pady=8,
        )
        badge.pack(side=tk.LEFT, padx=(0, 14))
        heading = tk.Frame(header, bg=BG)
        heading.pack(side=tk.LEFT)
        tk.Label(
            heading, text="Study Tracker", bg=BG, fg=TEXT,
            font=("TkDefaultFont", 21, "bold"),
        ).pack(anchor="w")
        tk.Label(
            heading, text="Ghi lại từng buổi học và theo dõi tiến độ của bạn",
            bg=BG, fg=MUTED, font=("TkDefaultFont", 10),
        ).pack(anchor="w", pady=(3, 0))

        self.total_label = tk.Label(
            header, text="0 giờ 00 phút", bg=SURFACE, fg=GREEN,
            font=("TkDefaultFont", 14, "bold"), padx=16, pady=12,
        )
        self.total_label.pack(side=tk.RIGHT, anchor="center")

        self.total_caption = tk.Label(
            page, text="TỔNG THỜI GIAN HỌC", bg=BG, fg=MUTED,
            font=("TkDefaultFont", 8, "bold"),
        )
        self.total_caption.pack(anchor="e", pady=(7, 0))

        form = tk.Frame(page, bg=SURFACE, highlightbackground=BORDER,
                        highlightthickness=1, padx=18, pady=16)
        form.pack(fill=tk.X, pady=(22, 20))
        tk.Label(form, text="Thêm buổi học", bg=SURFACE, fg=TEXT,
                 font=("TkDefaultFont", 13, "bold")).grid(
                     row=0, column=0, columnspan=6, sticky="w", pady=(0, 13)
                 )

        self.date_entry = self.make_field(form, "Ngày học", 1, 0, width=18)
        self.date_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        self.start_entry = self.make_field(form, "Bắt đầu", 1, 2, width=12)
        self.end_entry = self.make_field(form, "Kết thúc", 1, 4, width=12)

        self.add_button = tk.Button(
            form, text="＋  Lưu buổi học", command=self.add_session,
            bg=GREEN, fg=SURFACE, activebackground="#2d9865", activeforeground=SURFACE,
            relief=tk.FLAT, bd=0, font=("TkDefaultFont", 10, "bold"),
            cursor="hand2", padx=14, pady=10,
        )
        self.add_button.grid(row=1, column=6, rowspan=2, padx=(14, 0), sticky="sew")
        tk.Label(
            form, text="Định dạng ngày: YYYY-MM-DD     •     Giờ: HH:MM (24 giờ)",
            bg=SURFACE, fg=MUTED, font=("TkDefaultFont", 9),
        ).grid(row=3, column=0, columnspan=6, sticky="w", pady=(11, 0))

        history_header = tk.Frame(page, bg=BG)
        history_header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(history_header, text="Lịch sử học tập", bg=BG, fg=TEXT,
                 font=("TkDefaultFont", 15, "bold")).pack(side=tk.LEFT)
        self.count_label = tk.Label(history_header, text="0 buổi", bg=BG,
                                    fg=MUTED, font=("TkDefaultFont", 10))
        self.count_label.pack(side=tk.LEFT, padx=(11, 0), pady=(3, 0))

        table_frame = tk.Frame(page, bg=BORDER, padx=1, pady=1)
        table_frame.pack(fill=tk.BOTH, expand=True)
        columns = ("date", "start", "end", "duration")
        self.history = ttk.Treeview(
            table_frame, columns=columns, show="headings", style="Study.Treeview",
            selectmode="browse",
        )
        self.history.heading("date", text="NGÀY HỌC", anchor="w")
        self.history.heading("start", text="BẮT ĐẦU", anchor="center")
        self.history.heading("end", text="KẾT THÚC", anchor="center")
        self.history.heading("duration", text="THỜI LƯỢNG", anchor="e")
        self.history.column("date", width=210, anchor="w", stretch=True)
        self.history.column("start", width=130, anchor="center", stretch=False)
        self.history.column("end", width=130, anchor="center", stretch=False)
        self.history.column("duration", width=190, anchor="e", stretch=True)
        scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.history.yview,
            style="Study.Vertical.TScrollbar",
        )
        self.history.configure(yscrollcommand=scrollbar.set)
        self.history.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        footer = tk.Frame(page, bg=BG)
        footer.pack(fill=tk.X, pady=(12, 0))
        tk.Label(
            footer, text=f"Lịch sử được lưu tại {DATA_FILE.name}",
            bg=BG, fg=MUTED, font=("TkDefaultFont", 9),
        ).pack(side=tk.LEFT)
        self.delete_button = tk.Button(
            footer, text="Xóa buổi đã chọn", command=self.delete_selected,
            bg=SURFACE, fg=TEXT, activebackground=BORDER, activeforeground=TEXT,
            relief=tk.FLAT, bd=0, font=("TkDefaultFont", 9),
            cursor="hand2", padx=12, pady=8, state=tk.DISABLED,
        )
        self.delete_button.pack(side=tk.RIGHT)
        self.history.bind("<<TreeviewSelect>>", self.update_delete_button)

        for column in (0, 2, 4):
            form.grid_columnconfigure(column, weight=1)
        form.grid_columnconfigure(1, weight=2)
        form.grid_columnconfigure(3, weight=1)
        form.grid_columnconfigure(5, weight=1)

    @staticmethod
    def make_field(parent: tk.Frame, label: str, row: int, column: int,
                   width: int) -> tk.Entry:
        wrapper = tk.Frame(parent, bg=SURFACE)
        wrapper.grid(row=row, column=column, columnspan=2,
                     sticky="ew", padx=(0, 10))
        tk.Label(wrapper, text=label, bg=SURFACE, fg=MUTED,
                 font=("TkDefaultFont", 9)).pack(anchor="w", pady=(0, 5))
        entry = tk.Entry(
            wrapper, width=width, bg=BG, fg=TEXT, insertbackground=TEXT,
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=GREEN,
            font=("TkDefaultFont", 11),
        )
        entry.pack(fill=tk.X, ipady=8)
        return entry

    def load_sessions(self) -> list[dict[str, str]]:
        if not DATA_FILE.exists():
            return []
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("Tệp dữ liệu không có định dạng danh sách.")
            sessions = []
            for item in data:
                if not isinstance(item, dict):
                    raise ValueError("Một mục trong lịch sử không hợp lệ.")
                session = {
                    "id": str(item.get("id") or uuid4().hex),
                    "date": str(item["date"]),
                    "start": str(item["start"]),
                    "end": str(item["end"]),
                }
                if session_minutes(session) <= 0:
                    raise ValueError("Giờ kết thúc phải sau giờ bắt đầu.")
                sessions.append(session)
            return sessions
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.storage_available = False
            self.load_error = (
                f"Không thể đọc {DATA_FILE.name}: {exc}\n"
                "Lịch sử hiện tại không được ghi đè để tránh mất dữ liệu."
            )
            return []

    def save_sessions(self, sessions: list[dict[str, str]]) -> bool:
        if not self.storage_available:
            messagebox.showerror("Không thể lưu", self.load_error)
            return False
        temporary_file = DATA_FILE.with_suffix(".tmp")
        try:
            temporary_file.write_text(
                json.dumps(sessions, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary_file.replace(DATA_FILE)
            return True
        except OSError as exc:
            try:
                temporary_file.unlink(missing_ok=True)
            except OSError:
                pass
            messagebox.showerror("Không thể lưu lịch sử", str(exc))
            return False

    def add_session(self) -> None:
        date_text = self.date_entry.get().strip()
        start_text = self.start_entry.get().strip()
        end_text = self.end_entry.get().strip()
        try:
            datetime.strptime(date_text, "%Y-%m-%d")
            datetime.strptime(start_text, "%H:%M")
            datetime.strptime(end_text, "%H:%M")
        except ValueError:
            messagebox.showwarning(
                "Thông tin chưa hợp lệ",
                "Hãy nhập ngày theo dạng YYYY-MM-DD và giờ theo dạng HH:MM.",
            )
            return

        session = {
            "id": uuid4().hex,
            "date": date_text,
            "start": start_text,
            "end": end_text,
        }
        duration = session_minutes(session)
        if duration <= 0:
            messagebox.showwarning(
                "Giờ học chưa hợp lệ", "Giờ kết thúc phải sau giờ bắt đầu trong cùng ngày."
            )
            return

        updated_sessions = self.sessions + [session]
        if self.save_sessions(updated_sessions):
            self.sessions = updated_sessions
            self.start_entry.delete(0, tk.END)
            self.end_entry.delete(0, tk.END)
            self.start_entry.focus_set()
            self.refresh_history()

    def delete_selected(self) -> None:
        selected = self.history.selection()
        if not selected:
            return
        session_id = selected[0]
        if not messagebox.askyesno("Xóa buổi học", "Bạn có chắc muốn xóa buổi học này?"):
            return
        updated_sessions = [s for s in self.sessions if s["id"] != session_id]
        if self.save_sessions(updated_sessions):
            self.sessions = updated_sessions
            self.refresh_history()

    def update_delete_button(self, _event: tk.Event | None = None) -> None:
        state = tk.NORMAL if self.history.selection() else tk.DISABLED
        self.delete_button.configure(state=state)

    def refresh_history(self) -> None:
        for item in self.history.get_children():
            self.history.delete(item)

        ordered = sorted(
            self.sessions,
            key=lambda item: (item["date"], item["start"]),
            reverse=True,
        )
        for session in ordered:
            self.history.insert(
                "", tk.END, iid=session["id"],
                values=(session["date"], session["start"], session["end"],
                        format_duration(session_minutes(session))),
            )

        total_minutes = sum(session_minutes(session) for session in self.sessions)
        self.total_label.configure(text=format_duration(total_minutes))
        decimal_hours = f"{total_minutes / 60:.2f}".replace(".", ",")
        self.total_caption.configure(
            text=f"TỔNG THỜI GIAN HỌC  •  {decimal_hours} GIỜ"
        )
        count = len(self.sessions)
        self.count_label.configure(text=f"{count} buổi")
        self.update_delete_button()


def main() -> None:
    root = tk.Tk()
    StudyTracker(root)
    root.mainloop()


if __name__ == "__main__":
    main()
