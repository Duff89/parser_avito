import tkinter as tk

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None

    def show_tip(self):
        "Display text in tooltip window"
        if self.tip_window or not self.text:
            return
        x, y, _cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("tahoma", "8", "normal"),
            padx=4,
            pady=2,
        )
        label.pack(ipadx=1)

    def hide_tip(self):
        "Hide tooltip window"
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

    def bind(self):
        self.widget.bind("<Enter>", lambda event: self.show_tip())
        self.widget.bind("<Leave>", lambda event: self.hide_tip())