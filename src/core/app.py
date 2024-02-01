import tkinter as tk


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("iRacing Safety Car Generator")
        self.geometry("300x200")

        self.label = tk.Label(self, text="Test")
        self.label.pack(pady=50)