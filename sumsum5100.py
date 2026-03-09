"""
Text Summarizer GUI
Install: pip install sumy pdfminer.six python-docx nltk
Run:     python text_summarizer.py
"""

import sys, threading, os, re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.lex_rank import LexRankSummarizer
    from sumy.summarizers.lsa import LsaSummarizer
    from sumy.summarizers.text_rank import TextRankSummarizer
    from sumy.summarizers.luhn import LuhnSummarizer
    from pdfminer.high_level import extract_text as pdf_extract
    from pdfminer.layout import LAParams
    import docx, nltk
    for _r, _n in {"tokenizers/punkt_tab":"punkt_tab","corpora/stopwords":"stopwords"}.items():
        try:    nltk.data.find(_r)
        except LookupError: nltk.download(_n, quiet=True)
except ImportError as e:
    tk.Tk().withdraw()
    messagebox.showerror("Missing library", f"{e}\n\nRun:  pip install sumy pdfminer.six python-docx nltk")
    sys.exit(1)

_TOK = Tokenizer("english")
ALGOS = {
    "LexRank  —  graph-based (recommended)": LexRankSummarizer(),
    "LSA  —  latent semantic analysis":      LsaSummarizer(),
    "TextRank  —  keyword graph":            TextRankSummarizer(),
    "Luhn  —  high-frequency words":         LuhnSummarizer(),
}

DARK  = dict(BG="#0F1117", PANEL="#1A1D27", ENTRY="#12151F", TEXT="#E8E9F3",
             DIM="#6B7280", BORDER="#2D3048", ACCENT="#5E6AD2", ACCENT2="#9B8FE8", SUCCESS="#34D399")
LIGHT = dict(BG="#E8E8E8", PANEL="#D0D0D0", ENTRY="#F5F5F5", TEXT="#1A1D27",
             DIM="#555555", BORDER="#AAAAAA", ACCENT="#5E6AD2", ACCENT2="#4C56B0", SUCCESS="#059669")

def clean(t):
    t = re.sub(r"-\n(\S)",r"\1",t); t = re.sub(r"(?<!\n)\n(?!\n)"," ",t)
    t = re.sub(r"\n{3,}","\n\n",t); t = re.sub(r"[^\x09\x0A\x20-\x7E\u00A0-\uFFFF]","",t)
    return t.strip()

def read_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        for enc in ("utf-8","latin-1","cp1252"):
            try: return clean(open(path,encoding=enc).read())
            except UnicodeDecodeError: pass
        return clean(open(path,encoding="utf-8",errors="replace").read())
    elif ext == ".pdf":
        return clean(pdf_extract(path,laparams=LAParams(line_margin=0.5,boxes_flow=0.5)) or "")
    elif ext in (".docx",".doc"):
        return clean("\n".join(p.text for p in docx.Document(path).paragraphs if p.text.strip()))
    return f"Unsupported: {ext}"

def do_summarize(text, summarizer, n):
    return "\n\n".join(str(s) for s in summarizer(PlaintextParser.from_string(text,_TOK).document,n))

        
def pct_to_n(text, pct):
    return max(1, round(max(1,len(re.split(r'(?<=[.!?])\s+',text.strip())))*pct/100))

def trunc(s, n=35):
    return s if len(s) <= n else s[:n-1]+"…"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Text Summarizer")
        self.state("zoomed")
        try: self.attributes("-zoomed", True)
        except: pass
        self.minsize(900, 600)
        self._dark    = True
        self.T        = DARK
        self.algo_var = tk.StringVar(value=list(ALGOS)[0])
        self.pct      = tk.IntVar(value=30)
        self.status_var = tk.StringVar()
        self.in_wc    = tk.StringVar()
        self._sty     = ttk.Style(self); self._sty.theme_use("clam")
        # collect all themed widgets for simple re-color
        self._tw = []   # list of (widget, attr_dict_fn)
        self.configure(bg=self.T["BG"])
        self._build()

    # ── simple theme toggle: just walk _tw and re-apply colors ────────────────
    def _toggle_theme(self):
        self._dark = not self._dark
        self.T = DARK if self._dark else LIGHT
        T = self.T
        self.configure(bg=T["BG"])
        for w, fn in self._tw:
            try: w.config(**fn(T))
            except: pass
        # update ttk combo + slider colors
        self._sty.configure("D.TCombobox",
            fieldbackground=T["ENTRY"], background=T["ENTRY"],
            foreground=T["TEXT"], selectbackground=T["ACCENT"], selectforeground=T["TEXT"],
            bordercolor=T["BORDER"], arrowcolor=T["ACCENT2"], padding=(6,4))
        self._sty.map("D.TCombobox",
            fieldbackground=[("readonly",T["ENTRY"]),("",T["ENTRY"])],
            foreground=[("readonly",T["TEXT"]),("",T["TEXT"])],
            background=[("readonly",T["ENTRY"]),("active",T["ENTRY"]),("",T["ENTRY"])])
        # override the internal listbox popup colors
        self.option_add("*TCombobox*Listbox.background", T["ENTRY"])
        self.option_add("*TCombobox*Listbox.foreground", T["TEXT"])
        self.option_add("*TCombobox*Listbox.selectBackground", T["ACCENT"])
        self.option_add("*TCombobox*Listbox.selectForeground", T["TEXT"])
        self._sty.configure("D.Horizontal.TScale", troughcolor=T["BORDER"], background=T["BG"])
        self.option_add("*TCombobox*Listbox.background", T["ENTRY"])
        self.option_add("*TCombobox*Listbox.foreground", T["TEXT"])
        self.option_add("*TCombobox*Listbox.selectBackground", T["ACCENT"])
        self.option_add("*TCombobox*Listbox.selectForeground", T["TEXT"])
        self.theme_btn.config(text="☀  Light" if self._dark else "🌙  Dark")

    def _tw_add(self, w, fn):
        self._tw.append((w, fn)); return w

    def _build(self):
        T = self.T

        # ── top bar ───────────────────────────────────────────────────────────
        top = self._tw_add(tk.Frame(self, bg=T["PANEL"], height=56),
                           lambda t: dict(bg=t["PANEL"]))
        top.pack(fill="x"); top.pack_propagate(False)

        self._tw_add(tk.Label(top, text="✦ Text Summarizer", font=("Georgia",18,"bold"),
                 bg=T["PANEL"], fg=T["ACCENT2"], padx=20),
                 lambda t: dict(bg=t["PANEL"], fg=t["ACCENT2"])).pack(side="left", pady=12)

        self.theme_btn = tk.Button(top, text="☀  Light", command=self._toggle_theme,
            bg=T["ENTRY"], fg=T["TEXT"], relief="flat", bd=0,
            font=("Courier New",10,"bold"), padx=14, pady=6, cursor="hand2")
        self._tw.append((self.theme_btn, lambda t: dict(bg=t["ENTRY"], fg=t["TEXT"])))
        self.theme_btn.pack(side="right", padx=20, pady=10)

        # ── control bar ───────────────────────────────────────────────────────
        # Layout: [Algorithm combo] [Length: XX% ---slider---] .............. [status] [Clear] [Summarize]
        ctrl = self._tw_add(tk.Frame(self, bg=T["BG"], pady=8),
                            lambda t: dict(bg=t["BG"]))
        ctrl.pack(fill="x", padx=20)

        self._tw_add(tk.Label(ctrl, text="Algorithm:", font=("Courier New",11), bg=T["BG"], fg=T["DIM"]),
                     lambda t: dict(bg=t["BG"], fg=t["DIM"])).pack(side="left")

        self._sty.configure("D.TCombobox",
            fieldbackground=T["ENTRY"], background=T["ENTRY"],
            foreground=T["TEXT"], selectbackground=T["ACCENT"], selectforeground=T["TEXT"],
            bordercolor=T["BORDER"], arrowcolor=T["ACCENT2"], padding=(6,4))
        self._sty.map("D.TCombobox",
            fieldbackground=[("readonly",T["ENTRY"]),("",T["ENTRY"])],
            foreground=[("readonly",T["TEXT"]),("",T["TEXT"])],
            background=[("readonly",T["ENTRY"]),("active",T["ENTRY"]),("",T["ENTRY"])])
        # override the internal listbox popup colors
        self.option_add("*TCombobox*Listbox.background", T["ENTRY"])
        self.option_add("*TCombobox*Listbox.foreground", T["TEXT"])
        self.option_add("*TCombobox*Listbox.selectBackground", T["ACCENT"])
        self.option_add("*TCombobox*Listbox.selectForeground", T["TEXT"])
        ttk.Combobox(ctrl, textvariable=self.algo_var, values=list(ALGOS), state="readonly",
            width=36, style="D.TCombobox", font=("Courier New",11)).pack(side="left", padx=(8,16))

        self._tw_add(tk.Label(ctrl, text="Length:", font=("Courier New",11), bg=T["BG"], fg=T["DIM"]),
                     lambda t: dict(bg=t["BG"], fg=t["DIM"])).pack(side="left")

        self.pct_lbl = self._tw_add(
            tk.Label(ctrl, text=f"{self.pct.get()}%", font=("Courier New",11,"bold"),
                     bg=T["BG"], fg=T["ACCENT2"], width=4),
            lambda t: dict(bg=t["BG"], fg=t["ACCENT2"]))
        self.pct_lbl.pack(side="left", padx=(6,4))

        self._sty.configure("D.Horizontal.TScale", troughcolor=T["BORDER"], background=T["BG"])
        ttk.Scale(ctrl, from_=5, to=80, variable=self.pct, orient="horizontal",
            style="D.Horizontal.TScale", length=100,
            command=lambda _: self.pct_lbl.config(text=f"{self.pct.get()}%")
            ).pack(side="left", padx=(0,8))

        # right side of ctrl: status | Clear | Summarize
        sum_btn = tk.Button(ctrl, text="⚡  Summarize", command=self._summarize,
            bg=T["ACCENT"], fg="white", relief="flat", bd=0,
            font=("Courier New",11,"bold"), padx=16, pady=6, cursor="hand2")
        self._tw.append((sum_btn, lambda t: dict(bg=t["ACCENT"])))
        sum_btn.pack(side="right", padx=(6,0))

        clr_btn = self._tw_add(
            tk.Button(ctrl, text="✕  Clear", command=self._clear,
                bg=T["PANEL"], fg=T["DIM"], relief="flat", bd=0,
                font=("Courier New",11,"bold"), padx=16, pady=6, cursor="hand2"),
            lambda t: dict(bg=t["PANEL"], fg=t["DIM"]))
        clr_btn.pack(side="right", padx=(0,6))



        # ── paned panels ──────────────────────────────────────────────────────
        self._pane = tk.PanedWindow(self, orient="horizontal", bg=T["BG"],
                                    sashwidth=8, sashrelief="flat", sashpad=2)
        self._tw.append((self._pane, lambda t: dict(bg=t["BG"])))
        self._pane.pack(fill="both", expand=True, padx=20, pady=(4,20))

        self._pane.add(self._panel("INPUT TEXT",     left=True),  minsize=250, stretch="always")
        self._pane.add(self._panel("SUMMARY OUTPUT", left=False), minsize=250, stretch="always")
        self.after(100, lambda: self._pane.sash_place(0, self.winfo_width()//2, 0))

    def _btn(self, parent, text, cmd, bg, fg, fn):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, relief="flat", bd=0,
                      font=("Courier New",11,"bold"), padx=14, pady=6, cursor="hand2")
        self._tw.append((b, fn)); return b

    def _panel(self, label, left):
        T = self.T
        frame = self._tw_add(tk.Frame(self._pane, bg=T["PANEL"]), lambda t: dict(bg=t["PANEL"]))

        hdr = self._tw_add(tk.Frame(frame, bg=T["PANEL"]), lambda t: dict(bg=t["PANEL"]))
        hdr.pack(fill="x", padx=12, pady=(10,4))

        self._tw_add(tk.Label(hdr, text=label, font=("Courier New",10,"bold"),
                 bg=T["PANEL"], fg=T["ACCENT"]),
                 lambda t: dict(bg=t["PANEL"], fg=t["ACCENT"])).pack(side="left")

        if left:
            self._btn(hdr, "📂  Import file", self._import, T["ENTRY"], T["ACCENT2"],
                      lambda t: dict(bg=t["ENTRY"], fg=t["ACCENT2"])).pack(side="right")
            self._tw_add(tk.Label(hdr, textvariable=self.in_wc, font=("Courier New",9),
                     bg=T["PANEL"], fg=T["DIM"]),
                     lambda t: dict(bg=t["PANEL"], fg=t["DIM"])).pack(side="right", padx=10)
        else:
            self._btn(hdr, "📋  Copy", self._copy, T["ENTRY"], T["ACCENT2"],
                      lambda t: dict(bg=t["ENTRY"], fg=t["ACCENT2"])).pack(side="right")
            self.status_lbl = self._tw_add(
                tk.Label(hdr, textvariable=self.status_var, font=("Courier New",10),
                         bg=T["PANEL"], fg=T["DIM"]),
                lambda t: dict(bg=t["PANEL"], fg=t["DIM"]))
            self.status_lbl.pack(side="right", padx=(0,10))

        box = self._tw_add(
            tk.Frame(frame, bg=T["ENTRY"], highlightthickness=1,
                     highlightbackground=T["BORDER"], highlightcolor=T["ACCENT"]),
            lambda t: dict(bg=t["ENTRY"], highlightbackground=t["BORDER"], highlightcolor=t["ACCENT"]))
        box.pack(fill="both", expand=True, padx=8, pady=(0,10))

        txt = self._tw_add(
            tk.Text(box, wrap="word", bg=T["ENTRY"], fg=T["TEXT"], insertbackground=T["TEXT"],
                    relief="flat", bd=0, font=("Georgia",12), padx=14, pady=12,
                    selectbackground=T["ACCENT"], selectforeground="white",
                    spacing3=4, highlightthickness=0),
            lambda t: dict(bg=t["ENTRY"], fg=t["TEXT"], insertbackground=t["TEXT"]))

        self._scrollbar(box, txt).pack(side="right", fill="y", pady=4, padx=(0,2))
        txt.pack(side="left", fill="both", expand=True)
        txt.bind("<MouseWheel>", lambda e: (txt.yview_scroll(int(-e.delta/120),"units"),"break"))
        txt.bind("<Button-4>",   lambda e: txt.yview_scroll(-1,"units"))
        txt.bind("<Button-5>",   lambda e: txt.yview_scroll( 1,"units"))

        if left:
            self.inp = txt; txt.bind("<KeyRelease>", self._wc_update)
            self._placeholder(txt, "Paste your text here, or click  📂 Import file  above…")
        else:
            self.out = txt; txt.config(state="disabled")
        return frame

    def _scrollbar(self, parent, widget):
        T = self.T
        c = self._tw_add(tk.Canvas(parent, width=8, bg=T["PANEL"], highlightthickness=0, bd=0),
                         lambda t: dict(bg=t["PANEL"]))
        drag = {"y": 0}
        def redraw(*_):
            c.delete("all"); h = c.winfo_height()
            if h < 2: return
            t, b = widget.yview()
            c.create_rectangle(3,0,6,h, fill=self.T["BORDER"], outline="")
            if b-t < 0.999:
                c.create_rectangle(2,t*h,7,max(t*h+20,b*h), fill=self.T["ACCENT"], outline="")
        c.bind("<ButtonPress-1>", lambda e: drag.update(y=e.y))
        c.bind("<B1-Motion>", lambda e: (
            widget.yview_moveto(widget.yview()[0]+(e.y-drag["y"])/max(c.winfo_height(),1)),
            drag.update(y=e.y), redraw()))
        c.bind("<Configure>", redraw)
        widget.configure(yscrollcommand=lambda *_: c.after_idle(redraw))
        return c

    def _placeholder(self, w, text):
        w._ph = True; w.insert("1.0", text); w.config(fg=self.T["DIM"])
        def _in(e):
            if w._ph: w.delete("1.0","end"); w.config(fg=self.T["TEXT"]); w._ph = False
        def _out(e):
            if not w.get("1.0","end").strip():
                w.insert("1.0",text); w.config(fg=self.T["DIM"]); w._ph = True
        w.bind("<FocusIn>",_in); w.bind("<FocusOut>",_out)

    def _input_text(self):
        return "" if self.inp._ph else self.inp.get("1.0","end").strip()

    def _wc_update(self, *_):
        t = self._input_text(); self.in_wc.set(f"{len(t.split()):,} words" if t else "")

    def _status(self, msg, color=None):
        self.status_var.set(trunc(msg)); self.status_lbl.config(fg=color or self.T["DIM"])

    def _import(self):
        path = filedialog.askopenfilename(filetypes=[
            ("All supported","*.txt *.pdf *.docx *.doc"),
            ("Text","*.txt"),("PDF","*.pdf"),("Word","*.docx *.doc")])
        if not path: return
        self._status(f"Loading {trunc(os.path.basename(path),25)}…", self.T["ACCENT2"])
        def _load():
            try:    c = read_file(path)
            except Exception as e: c = f"Error: {e}"
            self.after(0, lambda: self._fill(c, path))
        threading.Thread(target=_load, daemon=True).start()

    def _fill(self, content, path):
        self.inp._ph = False; self.inp.config(fg=self.T["TEXT"])
        self.inp.delete("1.0","end"); self.inp.insert("1.0", content)
        self._wc_update()
        self._status(f"Loaded: {trunc(os.path.basename(path),25)}", self.T["SUCCESS"])

    def _summarize(self):
        text = self._input_text()
        if not text:
            messagebox.showwarning("No text", "Please enter or import some text first.")
            return
        s = ALGOS[self.algo_var.get()]
        n = pct_to_n(text, self.pct.get())
        self._status("Summarizing…", self.T["ACCENT2"])
        self.out.config(state="normal")
        self.out.delete("1.0", "end")
        self.out.insert("1.0", "⏳  Generating summary…")
        self.out.config(state="disabled")
        self._animate_status()   # <-- add this
        def _work():
            try:    r = do_summarize(text, s, n)
            except Exception as e: r = f"Error: {e}"
            self.after(0, lambda: (self._stop_animate(), self._show(r)))
        threading.Thread(target=_work, daemon=True).start()

    def _animate_status(self):
        self._animating = True
        dots = ["⏳ Summarizing", "⏳ Summarizing.", "⏳ Summarizing..", "⏳ Summarizing..."]
        self._anim_i = 0
        def _tick():
            if not self._animating: return
            self.status_var.set(dots[self._anim_i % 4])
            self._anim_i += 1
            self._anim_job = self.after(400, _tick)
        _tick()

    def _stop_animate(self):
        self._animating = False
        if hasattr(self, "_anim_job"):
            self.after_cancel(self._anim_job)

    def _show(self, result):
        self.out.config(state="normal"); self.out.delete("1.0","end")
        if result.strip():
            self.out.insert("1.0", result)
            self._status(f"Done — {len(result.split())} words", self.T["SUCCESS"])
        else:
            self.out.insert("1.0", "⚠  No summary could be generated. Try a longer text or different algorithm.")
            self._status("No summary generated", self.T["DIM"])
        self.out.config(state="disabled")

    def _copy(self):
        self.out.config(state="normal"); t = self.out.get("1.0","end").strip()
        self.out.config(state="disabled")
        if t:
            self.clipboard_clear(); self.clipboard_append(t); self._status("Copied!", self.T["SUCCESS"])
        else:
            self._status("Nothing to copy", self.T["DIM"])

    def _clear(self):
        self.inp._ph = False; self.inp.config(fg=self.T["TEXT"]); self.inp.delete("1.0","end")
        self._placeholder(self.inp, "Paste your text here, or click  📂 Import file  above…")
        self.out.config(state="normal"); self.out.delete("1.0","end"); self.out.config(state="disabled")
        self.in_wc.set(""); self._status("Cleared")

if __name__ == "__main__":
    App().mainloop()
