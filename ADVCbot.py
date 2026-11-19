import tkinter as tk
import re
import sys
import os


COPPER_CONDUCTIVITY = 57
CABLE_SECTIONS = [0.5, 0.75, 1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400]
BREAKERS = [1, 2, 4, 6, 10, 16, 20, 25, 32, 40, 50, 63]

FONT = {"h1": ("Consolas", 18, "bold"), "h2": ("Consolas", 14), "body": ("Consolas", 11), "small": ("Consolas", 9), "btn": ("Consolas", 12), "card_title": ("Consolas", 13, "bold"), "unit": ("Consolas", 11)}

LIGHT = {"bg": "#f5f5f5", "fg": "#1a1a1a", "accent": "#000", "entry": "#ffffff", "btn": "#e0e0e0", "btn_a": "#c0c0c0", "card": "#ffffff", "sep": "#cccccc"}
DARK = {"bg": "#1a1a1a", "fg": "#e8e8e8", "accent": "#ffffff", "entry": "#2a2a2a", "btn": "#333333", "btn_a": "#505050", "card": "#252525", "sep": "#444444"}

ICON_FONT = ("Consolas", 18, "bold")
ICON_OK = "v"
ICON_FAIL = "x"
ICON_WARN = "▲"

OK_COLOR = "#4caf50"
FAIL_COLOR = "#f44336"
WARN_COLOR = "#ff9800"


def format_decimal(value):
    return f"{value:g}".replace(".", ",")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("ADVCbot")
        self.root.geometry("820x640")
        self.root.resizable(False, False)
        self.dark = True
        self.t = DARK
        self.root.configure(bg=self.t["bg"])
        self.history = []
        self.pages = {}
        for P in (Menu, Calc, Result, History):
            self.pages[P.__name__] = P(self.root, self)
            self.pages[P.__name__].place(relwidth=1, relheight=1)
        self.show("Menu")

    def show(self, name):
        page = self.pages[name]
        if hasattr(page, 'on_show'):
            page.on_show()
        page.tkraise()

    def toggle_theme(self):
        self.dark = not self.dark
        self.t = DARK if self.dark else LIGHT
        self.root.configure(bg=self.t["bg"])
        for p in self.pages.values():
            p.paint(self.t)


class Menu(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=app.t["bg"], highlightthickness=0, bd=0)
        self.app = app
        self._build()
        self.paint(app.t)

    def _build(self):
        top = tk.Frame(self)
        top.pack(fill="x", padx=24, pady=24)
        self.header = tk.Label(top, text="ADVCbot", font=FONT["h1"])
        self.header.pack(side="left")
        btns = tk.Frame(top)
        btns.pack(side="right")
        self.hist_btn = tk.Button(btns, text="История", font=FONT["body"], bd=1, relief="flat", cursor="hand2",
                                  command=lambda: self.app.show("History"))
        self.hist_btn.pack(side="left", padx=4)
        self.theme_btn = tk.Button(btns, text="☀ / ☾", font=FONT["body"], bd=1, relief="flat", cursor="hand2",
                                   command=self.app.toggle_theme)
        self.theme_btn.pack(side="left", padx=4)
        tk.Frame(self).pack(expand=True)
        self.calc_btn = tk.Button(self, text="Расчёт электрических нагрузок", font=FONT["btn"], bd=1, relief="flat",
                                  cursor="hand2", width=38, height=2, command=lambda: self.app.show("Calc"))
        self.calc_btn.pack(pady=6)
        self.later_btn = tk.Button(self, text="*Позже...", font=FONT["btn"], bd=1, relief="flat",
                                   cursor="hand2", width=38, height=2)
        self.later_btn.pack(pady=6)
        tk.Frame(self).pack(expand=True)
        self.footer = tk.Label(self, text="Почта для связи: EUsik@advc.ru", font=FONT["small"])
        self.footer.pack(side="bottom", pady=12)

    def paint(self, t):
        self.configure(bg=t["bg"])
        self.header.configure(bg=t["bg"], fg=t["accent"])
        self.footer.configure(bg=t["bg"], fg="#888")
        for b in [self.hist_btn, self.theme_btn, self.calc_btn, self.later_btn]:
            b.configure(bg=t["btn"], fg=t["fg"], activebackground=t["btn_a"], activeforeground=t["fg"])
        for child in self.winfo_children():
            if isinstance(child, tk.Frame):
                child.configure(bg=t["bg"])
                for sub in child.winfo_children():
                    if isinstance(sub, tk.Frame):
                        sub.configure(bg=t["bg"])


class Calc(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=app.t["bg"], highlightthickness=0, bd=0)
        self.app = app
        self.entries = {}
        self.labels = {}
        self.unit_labels = {}
        self.rows = []
        self.undo_stack = {}
        self._build()
        self.paint(app.t)

    def _build(self):
        top = tk.Frame(self)
        top.pack(fill="x", padx=24, pady=24)
        self.header = tk.Label(top, text="ADVCbot", font=FONT["h1"])
        self.header.pack(side="left")
        self.back_btn = tk.Button(top, text="← Назад", font=FONT["body"], bd=1, relief="flat", cursor="hand2",
                                  command=lambda: self.app.show("Menu"))
        self.back_btn.pack(side="left", padx=16)
        tk.Frame(self).pack(expand=True)
        form = tk.Frame(self)
        form.pack()
        limits = [5, 5, 4]
        fields = [
            ("Мощность:", "Вт", 5, False),
            ("Напряжение:", "В", 5, False),
            ("Длина кабеля:", "м", 4, True),
        ]
        for name, unit, lim, allow_decimal in fields:
            row = tk.Frame(form)
            row.pack(pady=6)
            self.rows.append(row)
            lbl = tk.Label(row, text=name, font=FONT["h2"], width=16, anchor="e")
            lbl.pack(side="left", padx=(0, 8))
            self.labels[name] = lbl
            vcmd = (self.register(lambda v, L=lim, D=allow_decimal: self._valid(v, L, D)), '%P')
            e = tk.Entry(row, font=FONT["h2"], bd=1, relief="solid", width=10, justify="center",
                         validate="key", validatecommand=vcmd)
            e.pack(side="left")
            unit_lbl = tk.Label(row, text=unit, font=FONT["unit"], width=3, anchor="w")
            unit_lbl.pack(side="left", padx=(6, 0))
            self.unit_labels[name] = unit_lbl
            self.undo_stack[e] = []
            e.bind("<KeyRelease>", lambda ev, entry=e: self._save_state(entry))
            e.bind("<Control-c>", lambda e: e.widget.event_generate("<<Copy>>"))
            e.bind("<Control-v>", lambda e, L=lim, D=allow_decimal: self._paste(e, L, D))
            e.bind("<Control-x>", lambda e: e.widget.event_generate("<<Cut>>"))
            e.bind("<Control-z>", lambda e: self._undo(e))
            e.bind("<Control-a>", lambda e: self._select_all(e))
            self.entries[name] = e
        self.error = tk.Label(form, text="", font=FONT["body"], fg=FAIL_COLOR)
        self.error.pack(pady=8)
        self.calc_btn = tk.Button(form, text="Рассчитать", font=FONT["btn"], bd=1, relief="flat",
                                  cursor="hand2", width=38, height=2, command=self._calc)
        self.calc_btn.pack(pady=12)
        tk.Frame(self).pack(expand=True)
        self.footer = tk.Label(self, text="Почта для связи: EUsik@advc.ru", font=FONT["small"])
        self.footer.pack(side="bottom", pady=12)

    def _valid(self, v, limit, allow_decimal=False):
        if v == "": return True
        if allow_decimal:
            if not re.match(r'^(?:[1-9][0-9]*(?:,[0-9]*)?|0,[0-9]*)$', v):
                return False
        elif not re.match(r'^[1-9][0-9]*$', v):
            return False
        return len(v) <= limit

    def _save_state(self, entry):
        text = entry.get()
        if not self.undo_stack[entry] or self.undo_stack[entry][-1] != text:
            self.undo_stack[entry].append(text)
            if len(self.undo_stack[entry]) > 50:
                self.undo_stack[entry].pop(0)

    def _undo(self, event):
        entry = event.widget
        if len(self.undo_stack[entry]) > 1:
            self.undo_stack[entry].pop()
            entry.delete(0, tk.END)
            entry.insert(0, self.undo_stack[entry][-1])
        elif len(self.undo_stack[entry]) == 1:
            entry.delete(0, tk.END)
        return "break"

    def _paste(self, event, limit, allow_decimal=False):
        try:
            text = event.widget.clipboard_get().strip()
        except:
            return "break"
        if allow_decimal:
            text = re.sub(r'[^0-9,]', '', text)
            if text.count(',') > 1:
                return "break"
            if not text or not re.match(r'^(?:[1-9][0-9]*(?:,[0-9]*)?|0,[0-9]*)$', text):
                return "break"
        else:
            text = re.sub(r'[^0-9]', '', text).lstrip("0")
            if not text or not re.match(r'^[1-9][0-9]*$', text):
                return "break"
        if len(text) > limit:
            return "break"
        event.widget.insert(tk.INSERT, text)
        return "break"

    def _select_all(self, event):
        event.widget.select_range(0, tk.END)
        event.widget.icursor(tk.END)
        return "break"

    def _calc(self):
        self.error.config(text="")
        P_raw = self.entries["Мощность:"].get()
        U_raw = self.entries["Напряжение:"].get()
        L_raw = self.entries["Длина кабеля:"].get()
        if not P_raw or not U_raw or not L_raw:
            self.error.config(text="Заполните все поля")
            return
        if L_raw.endswith(","):
            self.error.config(text="Введите корректную длину кабеля")
            return
        P = int(P_raw)
        U = int(U_raw)
        L = float(L_raw.replace(",", "."))
        if P <= 0 or U <= 0 or L <= 0:
            self.error.config(text="Значения должны быть > 0")
            return
        I = round(P / U, 2)
        if I > BREAKERS[-1]:
            data = {"P": P, "U": U, "L": L, "I": I, "S": None, "B": None, "dU": None, "ok": False, "overcurrent": True}
            self.app.history.append(data)
            self.app.pages["Result"].set_data(data)
            self.app.show("Result")
            return
        section = None
        for s in CABLE_SECTIONS:
            dU = (2 * L * I) / (COPPER_CONDUCTIVITY * s)
            if dU <= 1.0:
                section = s
                break
        if section is None:
            section = CABLE_SECTIONS[-1]
        dU = (2 * L * I) / (COPPER_CONDUCTIVITY * section)
        breaker = next((r for r in BREAKERS if r >= I), BREAKERS[-1])
        data = {"P": P, "U": U, "L": L, "I": I, "S": section, "B": breaker, "dU": dU, "ok": dU <= 1.0, "overcurrent": False}
        self.app.history.append(data)
        self.app.pages["Result"].set_data(data)
        self.app.show("Result")

    def on_show(self):
        for e in self.entries.values():
            e.delete(0, tk.END)
            self.undo_stack[e] = []
        self.error.config(text="")

    def paint(self, t):
        self.configure(bg=t["bg"])
        self.header.configure(bg=t["bg"], fg=t["accent"])
        self.footer.configure(bg=t["bg"], fg="#888")
        self.error.configure(bg=t["bg"])
        self.back_btn.configure(bg=t["btn"], fg=t["fg"], activebackground=t["btn_a"], activeforeground=t["fg"])
        self.calc_btn.configure(bg=t["btn"], fg=t["fg"], activebackground=t["btn_a"], activeforeground=t["fg"])
        for row in self.rows:
            row.configure(bg=t["bg"])
        for lbl in self.labels.values():
            lbl.configure(bg=t["bg"], fg=t["fg"])
        for ul in self.unit_labels.values():
            ul.configure(bg=t["bg"], fg=t["fg"])
        for child in self.winfo_children():
            if isinstance(child, tk.Frame):
                child.configure(bg=t["bg"])
                for sub in child.winfo_children():
                    if isinstance(sub, tk.Frame):
                        sub.configure(bg=t["bg"])
                    elif isinstance(sub, tk.Label):
                        if sub != self.error and sub not in self.labels.values() and sub not in self.unit_labels.values():
                            sub.configure(bg=t["bg"], fg=t["fg"])
                    elif isinstance(sub, tk.Entry):
                        sub.configure(bg=t["entry"], fg=t["fg"], insertbackground=t["fg"])


class Result(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=app.t["bg"], highlightthickness=0, bd=0)
        self.app = app
        self._build()
        self.paint(app.t)

    def _build(self):
        top = tk.Frame(self)
        top.pack(fill="x", padx=24, pady=24)
        self.header = tk.Label(top, text="ADVCbot", font=FONT["h1"])
        self.header.pack(side="left")
        self.back_btn = tk.Button(top, text="← К расчёту", font=FONT["body"], bd=1, relief="flat", cursor="hand2",
                                  command=lambda: self.app.show("Calc"))
        self.back_btn.pack(side="left", padx=16)
        tk.Frame(self).pack(expand=True)
        self.card = tk.Frame(self, highlightthickness=0, padx=40, pady=30)
        self.card.pack()
        self.lines = [tk.Label(self.card, text="", font=FONT["h2"]) for _ in range(7)]
        for l in self.lines:
            l.pack(anchor="w", pady=3)
        self.status_frame = tk.Frame(self.card)
        self.status_frame.pack(pady=(16, 0))
        self.icon = tk.Label(self.status_frame, text="", font=ICON_FONT)
        self.icon.pack(side="left", padx=(0, 10))
        self.status = tk.Label(self.status_frame, text="", font=FONT["h2"])
        self.status.pack(side="left")
        tk.Frame(self).pack(expand=True)
        self.menu_btn = tk.Button(self, text="В главное меню", font=FONT["btn"], bd=1, relief="flat",
                                  cursor="hand2", width=38, height=2, command=lambda: self.app.show("Menu"))
        self.menu_btn.pack(pady=10)
        self.footer = tk.Label(self, text="Почта для связи: EUsik@advc.ru", font=FONT["small"])
        self.footer.pack(side="bottom", pady=12)

    def set_data(self, d):
        labels = [
            f"Мощность:         {d['P']:.0f} Вт",
            f"Напряжение:       {d['U']:.0f} В",
            f"Длина кабеля:     {format_decimal(d['L'])} м",
            f"Сила тока:        {d['I']:.2f} А",
            f"Сечение кабеля:   {'—' if d.get('overcurrent') else f'{d['S']} мм²'}",
            f"Автомат:          {'—' if d.get('overcurrent') else f'{d['B']} А'}",
            f"Падение напр-я:   {'—' if d.get('overcurrent') else f'{d['dU']:.2f} В'}"
        ]
        for l, text in zip(self.lines, labels):
            l.config(text=text)
        if d.get("overcurrent"):
            self.icon.config(text=ICON_WARN, fg=WARN_COLOR)
            self.status.config(text="Ток превышает 63 А")
        elif d["ok"]:
            self.icon.config(text=ICON_OK, fg=OK_COLOR)
            self.status.config(text="Падение напряжения в норме (≤ 1 В)")
        else:
            self.icon.config(text=ICON_WARN, fg=WARN_COLOR)
            self.status.config(text="Падение напряжения > 1 В — нужен кабель толще")

    def paint(self, t):
        self.configure(bg=t["bg"])
        self.header.configure(bg=t["bg"], fg=t["accent"])
        self.footer.configure(bg=t["bg"], fg="#888")
        self.back_btn.configure(bg=t["btn"], fg=t["fg"], activebackground=t["btn_a"], activeforeground=t["fg"])
        self.menu_btn.configure(bg=t["btn"], fg=t["fg"], activebackground=t["btn_a"], activeforeground=t["fg"])
        self.card.configure(bg=t["card"])
        self.status_frame.configure(bg=t["card"])
        self.icon.configure(bg=t["card"])
        self.status.configure(bg=t["card"], fg=t["fg"])
        for l in self.lines:
            l.configure(bg=t["card"], fg=t["fg"])
        for child in self.winfo_children():
            if isinstance(child, tk.Frame) and child not in [self.card, self.status_frame]:
                child.configure(bg=t["bg"])


class History(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=app.t["bg"], highlightthickness=0, bd=0)
        self.app = app
        self._built = False
        self._build()
        self.paint(app.t)

    def _build(self):
        top = tk.Frame(self)
        top.pack(fill="x", padx=24, pady=24)
        self.header = tk.Label(top, text="ADVCbot", font=FONT["h1"])
        self.header.pack(side="left")
        self.back_btn = tk.Button(top, text="← Назад", font=FONT["body"], bd=1, relief="flat", cursor="hand2",
                                  command=lambda: self.app.show("Menu"))
        self.back_btn.pack(side="left", padx=16)
        self.title = tk.Label(self, text="История расчётов", font=FONT["h1"])
        self.title.pack(pady=12)
        container = tk.Frame(self)
        container.pack(fill="both", expand=True, padx=20)
        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.scroll = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.content = tk.Frame(self.canvas)
        self.content.bind("<Configure>", self._on_content_resize)
        self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.footer = tk.Label(self, text="Почта для связи: EUsik@advc.ru", font=FONT["small"])
        self.footer.pack(side="bottom", pady=12)
        self._built = True

    def _on_content_resize(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scroll()

    def _on_mousewheel(self, event):
        if self.content.winfo_reqheight() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _update_scroll(self):
        if not self._built: return
        if self.content.winfo_reqheight() <= self.canvas.winfo_height():
            self.scroll.pack_forget()
        else:
            self.scroll.pack(side="right", fill="y")

    def paint(self, t):
        self.configure(bg=t["bg"])
        self.header.configure(bg=t["bg"], fg=t["accent"])
        self.title.configure(bg=t["bg"], fg=t["fg"])
        self.footer.configure(bg=t["bg"], fg="#888")
        self.back_btn.configure(bg=t["btn"], fg=t["fg"], activebackground=t["btn_a"], activeforeground=t["fg"])
        self.canvas.configure(bg=t["bg"])
        self.content.configure(bg=t["bg"])
        for child in self.winfo_children():
            if isinstance(child, tk.Frame) and child != self.content:
                child.configure(bg=t["bg"])

    def on_show(self):
        self._refresh()

    def _refresh(self):
        for w in self.content.winfo_children():
            w.destroy()
        t = self.app.t
        if not self.app.history:
            tk.Label(self.content, text="Пока пусто.", font=FONT["h2"], bg=t["bg"], fg=t["fg"]).pack(pady=30)
            self._update_scroll()
            return
        for i, d in enumerate(reversed(self.app.history)):
            card = tk.Frame(self.content, bg=t["card"], highlightthickness=0, padx=18, pady=14)
            card.pack(fill="x", pady=5)
            num = len(self.app.history) - i
            tk.Label(card, text=f"Расчёт №{num}", font=FONT["card_title"], bg=t["card"], fg=t["fg"]).pack(anchor="w")
            sep = tk.Frame(card, bg=t["sep"], height=1)
            sep.pack(fill="x", pady=(6, 8))
            params = f"P = {d['P']:.0f} Вт    U = {d['U']:.0f} В    L = {format_decimal(d['L'])} м    I = {d['I']:.2f} А"
            tk.Label(card, text=params, font=FONT["body"], bg=t["card"], fg=t["fg"]).pack(anchor="w", pady=(0, 4))
            detail_frame = tk.Frame(card, bg=t["card"])
            detail_frame.pack(fill="x")
            if d.get("overcurrent"):
                tk.Label(detail_frame, text=f"I={d['I']:.2f} А    ", font=FONT["body"], bg=t["card"], fg=t["fg"]).pack(side="left")
                tk.Label(detail_frame, text="▲ Ток > 63 А", font=FONT["body"], bg=t["card"], fg=WARN_COLOR).pack(side="left")
                icon = ICON_FAIL
                icon_color = FAIL_COLOR
            elif d["ok"]:
                result = f"S = {d['S']} мм²    AB = {d['B']} А    dU = {d['dU']:.2f} В"
                tk.Label(detail_frame, text=result, font=FONT["body"], bg=t["card"], fg=t["fg"]).pack(side="left")
                icon = ICON_OK
                icon_color = OK_COLOR
            else:
                tk.Label(detail_frame, text=f"S = {d['S']} мм²    AB = {d['B']} А    dU = {d['dU']:.2f} В    ", font=FONT["body"], bg=t["card"], fg=t["fg"]).pack(side="left")
                tk.Label(detail_frame, text="▲ dU > 1 В", font=FONT["body"], bg=t["card"], fg=WARN_COLOR).pack(side="left")
                icon = ICON_FAIL
                icon_color = FAIL_COLOR
            tk.Label(detail_frame, text=icon, font=ICON_FONT, bg=t["card"], fg=icon_color).pack(side="right", padx=(12, 0))
        self.content.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scroll()
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)


if __name__ == "__main__":
    root = tk.Tk()
    if getattr(sys, 'frozen', False):
        icon_path = os.path.join(os.path.dirname(sys.executable), "advcboticon.ico")
    else:
        icon_path = "advcboticon.ico"
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)
    App(root)
    root.mainloop()