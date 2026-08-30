"""
Novel Translator Pro - v2.1.0
Görsellerdeki dashboard / project / new-project tasarımlarının PySide6 ile
birebir yeniden üretimi.

Çalıştırmak için:
    pip install PySide6 matplotlib
    python novel_translator_pro.py
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPushButton, QLineEdit, QComboBox, QFrame, QTableWidget,
    QTableWidgetItem, QProgressBar, QCheckBox, QRadioButton,
    QScrollArea, QTextEdit, QAbstractItemView, QStackedWidget, QDialog,
    QSlider, QTextEdit as QTextArea, QButtonGroup
)

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ----------------------------------------------------------------------
# Renk paleti (görsellerdeki koyu temaya göre)
# ----------------------------------------------------------------------
BG_APP        = "#0b0f19"
BG_PANEL      = "#111827"
BG_PANEL2     = "#0f1522"
BORDER        = "#1f2937"
TEXT_MAIN     = "#e5e7eb"
TEXT_DIM      = "#e4e9f2"
TEXT_FAINT    = "#e4e9f2"
ACCENT_BLUE   = "#3b82f6"
ACCENT_GREEN  = "#22c55e"
ACCENT_ORANGE = "#f59e0b"
ACCENT_PURPLE = "#a855f7"
ACCENT_RED    = "#ef4444"
ACCENT_CYAN   = "#38bdf8"
ACCENT_GRAY   = "#6b7280"

FONT_FAMILY = "Segoe UI"


# ------------------------------------------------------------------
# Ortak yardımcı bileşenler
# ------------------------------------------------------------------
def card(title=None, extra_header=None, obj="card"):
    frame = QFrame()
    frame.setObjectName(obj)
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(16, 14, 16, 14)
    outer.setSpacing(10)

    if title is not None:
        header = QHBoxLayout()
        lbl = QLabel(title)
        lbl.setObjectName("cardTitle")
        header.addWidget(lbl)
        header.addStretch()
        if extra_header:
            header.addWidget(extra_header)
        outer.addLayout(header)

    body = QVBoxLayout()
    body.setSpacing(8)
    outer.addLayout(body)
    return frame, body


def badge(text, color):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"""
        color: {color};
        background: {color}22;
        border: 1px solid {color}55;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 600;
    """)
    return lbl


def dot(color, size=8):
    d = QLabel()
    d.setFixedSize(size, size)
    d.setStyleSheet(f"background:{color}; border-radius:{size//2}px;")
    return d


def vline():
    v = QFrame()
    v.setFrameShape(QFrame.VLine)
    v.setStyleSheet(f"color:{BORDER};")
    return v


def status_color(status):
    return {
        "Active": ACCENT_BLUE,
        "Completed": ACCENT_CYAN,
        "Queued": ACCENT_ORANGE,
        "Archived": ACCENT_PURPLE,
    }.get(status, TEXT_DIM)


class SidebarButton(QPushButton):
    def __init__(self, icon_txt, text):
        super().__init__(f"  {icon_txt}   {text}")
        self.setObjectName("navBtn")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(38)

    def set_active(self, active):
        self.setObjectName("navBtnActive" if active else "navBtn")
        self.style().unpolish(self)
        self.style().polish(self)


class StatCard(QFrame):
    def __init__(self, title, value, value_color=None, delta=None, delta_up=True):
        super().__init__()
        self.setObjectName("statCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)
        t = QLabel(title)
        t.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        v = QLabel(value)
        v.setStyleSheet(f"color:{value_color or TEXT_MAIN}; font-size:22px; font-weight:700;")
        lay.addWidget(t)
        lay.addWidget(v)
        if delta:
            arrow = "↑" if delta_up else "↓"
            color = ACCENT_GREEN if delta_up else ACCENT_RED
            d = QLabel(f"{arrow} {delta}")
            d.setStyleSheet(f"color:{color}; font-size:11px; font-weight:600;")
            lay.addWidget(d)


def make_table(headers, rows):
    table = QTableWidget(len(rows), len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.setSelectionMode(QAbstractItemView.NoSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.horizontalHeader().setStretchLastSection(True)
    table.setStyleSheet(f"""
        QTableWidget {{
            background: transparent; color: {TEXT_MAIN}; border: none;
            font-size: 12px; gridline-color: {BORDER};
        }}
        QHeaderView::section {{
            background: transparent; color: {TEXT_FAINT}; border: none;
            border-bottom: 1px solid {BORDER}; padding: 6px; font-size: 11px;
        }}
        QTableWidget::item {{ border-bottom: 1px solid {BORDER}; padding: 4px; }}
    """)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            table.setItem(r, c, QTableWidgetItem(str(val)))
    table.resizeColumnsToContents()
    return table


# ------------------------------------------------------------------
# Grafikler
# ------------------------------------------------------------------
class RequestsChart(FigureCanvas):
    def __init__(self):
        fig = Figure(figsize=(4, 2.2), dpi=100)
        fig.patch.set_alpha(0)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.setStyleSheet("background: transparent;")
        self.draw_chart()

    def draw_chart(self):
        ax = self.ax
        ax.clear()
        ax.set_facecolor("none")
        days = ["18 May", "19 May", "20 May", "21 May", "22 May", "23 May", "24 May"]
        requests = [95, 140, 110, 135, 132, 100, 150]
        tokens = [220, 400, 300, 430, 340, 260, 470]
        ax.plot(days, requests, color=ACCENT_BLUE, marker="o", markersize=4, linewidth=1.8, label="Requests")
        ax.plot(days, tokens, color=ACCENT_PURPLE, marker="o", markersize=4, linewidth=1.8, label="Tokens (K)")
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(colors=TEXT_FAINT, labelsize=7)
        ax.grid(True, color=BORDER, linewidth=0.6, alpha=0.5)
        ax.legend(facecolor=BG_PANEL, edgecolor=BORDER, labelcolor=TEXT_DIM, fontsize=7, loc="upper left", frameon=False)
        self.figure.tight_layout(pad=0.4)
        self.draw()


class DonutChart(FigureCanvas):
    """Progress Overview donut grafiği (65% Overall Progress)."""
    def __init__(self, completed_pct, queue_pct, remaining_pct, center_text, center_sub):
        fig = Figure(figsize=(2.2, 2.2), dpi=100)
        fig.patch.set_alpha(0)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.setStyleSheet("background: transparent;")
        self.draw_chart(completed_pct, queue_pct, remaining_pct, center_text, center_sub)

    def draw_chart(self, completed_pct, queue_pct, remaining_pct, center_text, center_sub):
        ax = self.ax
        ax.clear()
        sizes = [completed_pct, queue_pct, remaining_pct]
        colors = [ACCENT_BLUE, ACCENT_ORANGE, "#2b3444"]
        wedges, _ = ax.pie(
            sizes, colors=colors, startangle=90, counterclock=False,
            wedgeprops=dict(width=0.32, edgecolor=BG_PANEL, linewidth=2)
        )
        ax.text(0, 0.12, center_text, ha="center", va="center",
                 color=TEXT_MAIN, fontsize=17, fontweight="bold")
        ax.text(0, -0.18, center_sub, ha="center", va="center",
                 color=TEXT_FAINT, fontsize=7)
        ax.set_aspect("equal")
        self.figure.tight_layout(pad=0)
        self.draw()


# ------------------------------------------------------------------
# New Project Modal
# ------------------------------------------------------------------
class StyleOptionCard(QFrame):
    def __init__(self, icon, title, sub, group: QButtonGroup, value, checked=False):
        super().__init__()
        self.setObjectName("styleCard")
        self.setCursor(Qt.PointingHandCursor)
        self.value = value
        self._checked = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size:18px; color:{ACCENT_BLUE};")
        top.addWidget(icon_lbl)
        top.addStretch()
        self.check_dot = QLabel("●")
        self.check_dot.setStyleSheet(f"color:{ACCENT_BLUE};")
        self.check_dot.setVisible(checked)
        top.addWidget(self.check_dot)
        lay.addLayout(top)

        t = QLabel(title)
        t.setStyleSheet(f"color:{TEXT_MAIN}; font-size:13px; font-weight:700;")
        lay.addWidget(t)

        s = QLabel(sub)
        s.setWordWrap(True)
        s.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        lay.addWidget(s)

        self.group = group
        group.add_card(self)
        self.set_checked(checked)

    def set_checked(self, val):
        self._checked = val
        self.check_dot.setVisible(val)
        self.setObjectName("styleCardActive" if val else "styleCard")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        self.group.select(self)


class StyleCardGroup:
    """StyleOptionCard'lar için basit tekli-seçim yöneticisi (QButtonGroup yerine)."""
    def __init__(self):
        self.cards = []
        self.selected_value = None

    def add_card(self, c):
        self.cards.append(c)

    def select(self, card):
        for c in self.cards:
            c.set_checked(c is card)
        self.selected_value = card.value


class ToggleSwitch(QCheckBox):
    def __init__(self, checked=True):
        super().__init__()
        self.setChecked(checked)
        self.setObjectName("toggleSwitch")
        self.setFixedSize(38, 20)
        self.setCursor(Qt.PointingHandCursor)


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Project")
        self.setModal(True)
        self.setMinimumSize(1000, 640)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        self.style_group = StyleCardGroup()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        panel = QFrame()
        panel.setObjectName("card")
        outer.addWidget(panel)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        # Header
        header = QHBoxLayout()
        icon = QLabel("📁")
        icon.setStyleSheet(f"""
            background:{ACCENT_BLUE}22; color:{ACCENT_BLUE};
            border-radius:8px; font-size:16px; padding:6px 10px;
        """)
        header.addWidget(icon)
        title = QLabel("Create New Project")
        title.setStyleSheet(f"color:{TEXT_MAIN}; font-size:17px; font-weight:700;")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setObjectName("iconBtn")
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        lay.addLayout(header)

        # 3 sütun
        cols = QHBoxLayout()
        cols.setSpacing(20)
        cols.addLayout(self.build_column1(), 1)
        cols.addWidget(vline())
        cols.addLayout(self.build_column2(), 1)
        cols.addWidget(vline())
        cols.addLayout(self.build_column3(), 1)
        lay.addLayout(cols, 1)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("smallBtn")
        cancel.clicked.connect(self.reject)
        create = QPushButton("+  Create Project")
        create.setObjectName("primaryBtn")
        create.clicked.connect(self.accept)
        footer.addWidget(cancel)
        footer.addWidget(create)
        lay.addLayout(footer)

    def section_title(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color:{TEXT_MAIN}; font-size:13px; font-weight:700;")
        return l

    def field_label(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
        return l

    def hint_label(self, text):
        l = QLabel(text)
        l.setWordWrap(True)
        l.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        return l

    # ---- Kolon 1: Basic Information ----
    def build_column1(self):
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(self.section_title("1. Basic Information"))

        col.addWidget(self.field_label("Project Name"))
        name = QLineEdit()
        name.setPlaceholderText("Enter project name...")
        col.addWidget(name)
        col.addWidget(self.hint_label("A unique name for your novel project."))

        col.addWidget(self.field_label("Source Language"))
        src = QComboBox()
        src.addItem("🌐  Select source language...")
        src.addItems(["Japanese (JP)", "Korean (KR)", "Chinese (ZH)", "English (EN)"])
        col.addWidget(src)

        col.addWidget(self.field_label("Target Language"))
        tgt = QComboBox()
        tgt.addItem("🌐  Select target language...")
        tgt.addItems(["Türkçe (TR)", "English (EN)"])
        col.addWidget(tgt)

        col.addWidget(self.field_label("Description (Optional)"))
        desc = QTextArea()
        desc.setPlaceholderText("Enter project description...")
        desc.setFixedHeight(90)
        col.addWidget(desc)
        char_count = QLabel("0 / 500")
        char_count.setAlignment(Qt.AlignRight)
        char_count.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        col.addWidget(char_count)

        col.addStretch()
        return col

    # ---- Kolon 2: Project Settings ----
    def build_column2(self):
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(self.section_title("2. Project Settings"))

        col.addWidget(self.field_label("Translation Style"))
        style_row = QHBoxLayout()
        style_row.setSpacing(8)
        style_row.addWidget(StyleOptionCard("⇄", "Literal", "Word-for-word accurate translation.", self.style_group, "literal"))
        style_row.addWidget(StyleOptionCard("⚖", "Balanced", "Balance between accuracy and readability.", self.style_group, "balanced", checked=True))
        style_row.addWidget(StyleOptionCard("🍃", "Natural", "Natural and fluent translation.", self.style_group, "natural"))
        col.addLayout(style_row)

        col.addWidget(self.field_label("Default Model"))
        model = QComboBox()
        model.addItems(["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-pro"])
        col.addWidget(model)
        col.addWidget(self.hint_label("You can change the model later in project settings."))

        workers_row = QHBoxLayout()
        workers_row.addWidget(self.field_label("Parallel Workers"))
        workers_row.addStretch()
        workers_val = QLabel("3")
        workers_val.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:700;")
        workers_row.addWidget(workers_val)
        col.addLayout(workers_row)

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(1)
        slider.setMaximum(10)
        slider.setValue(3)
        slider.valueChanged.connect(lambda v: workers_val.setText(str(v)))
        col.addWidget(slider)
        minmax = QHBoxLayout()
        l1 = QLabel("1"); l1.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        l2 = QLabel("10"); l2.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        minmax.addWidget(l1); minmax.addStretch(); minmax.addWidget(l2)
        col.addLayout(minmax)
        col.addWidget(self.hint_label("Recommended: 3 for Gemini (RPM: 11-12)"))

        col.addLayout(self.toggle_row("Batch Mode (Test)", "Pack multiple chapters into a single request to save quota.", True))
        col.addLayout(self.toggle_row("Translation Cache", "Enable automatic cache to reduce cost and improve speed.", True))
        col.addLayout(self.toggle_row("Quality Check", "Enable similarity check, language detection and CJK scan.", True))

        col.addStretch()
        return col

    def toggle_row(self, title, sub, checked):
        row = QVBoxLayout()
        row.setSpacing(2)
        top = QHBoxLayout()
        t = QLabel(title)
        t.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
        top.addWidget(t)
        top.addStretch()
        top.addWidget(ToggleSwitch(checked))
        row.addLayout(top)
        row.addWidget(self.hint_label(sub))
        return row

    # ---- Kolon 3: Project Storage + Advanced ----
    def build_column3(self):
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(self.section_title("3. Project Storage"))

        col.addWidget(self.field_label("Project Location"))
        loc_row = QHBoxLayout()
        loc = QLineEdit("D:\\NovelTranslator\\Projects")
        loc_row.addWidget(loc)
        browse = QPushButton("📂")
        browse.setObjectName("iconBtn")
        loc_row.addWidget(browse)
        col.addLayout(loc_row)

        col.addWidget(self.field_label("Project Structure Preview"))
        tree = QFrame()
        tree.setObjectName("innerCard")
        tl = QVBoxLayout(tree)
        tl.setSpacing(3)
        tree_lines = [
            "📁 My New Project/",
            "   📁 source/",
            "   📁 translated/",
            "   📁 cache/",
            "   📁 terminology/",
            "   📁 logs/",
            "   {} config.json",
        ]
        for line in tree_lines:
            l = QLabel(line)
            l.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px; font-family: Consolas, monospace;")
            tl.addWidget(l)
        col.addWidget(tree)

        col.addWidget(self.section_title("4. Advanced (Optional)"))

        col.addWidget(self.field_label("Prompt Template"))
        prompt_tpl = QComboBox()
        prompt_tpl.addItems(["Auto (PromptGen will generate)", "Manual"])
        col.addWidget(prompt_tpl)
        col.addWidget(self.hint_label("AI will generate optimal prompt for your project."))

        col.addWidget(self.field_label("Terminology Extraction Range"))
        term_range = QComboBox()
        term_range.addItems(["All Chapters (After Translation)", "First 10 Chapters", "Manual"])
        col.addWidget(term_range)
        col.addWidget(self.hint_label("Extract terminology after translation is completed."))

        col.addStretch()
        return col


# ------------------------------------------------------------------
# Ana Pencere
# ------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Novel Translator Pro")
        self.resize(1536, 1024)
        self.setStyleSheet(self.build_stylesheet())
        self.nav_buttons = {}

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self.build_titlebar())
        root.addWidget(self.build_connection_bar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self.build_sidebar())

        self.stack = QStackedWidget()
        self.dashboard_page = self.build_dashboard_page()
        self.project_page = self.build_project_page()
        self.stack.addWidget(self.dashboard_page)   # index 0
        self.stack.addWidget(self.project_page)     # index 1
        body.addWidget(self.stack, 1)

        root.addLayout(body, 1)
        root.addWidget(self.build_statusbar())

        self.set_active_nav("Dashboard")

    # ------------------------------------------------------------------
    def open_new_project_dialog(self):
        dlg = NewProjectDialog(self)
        dlg.exec()

    def set_active_nav(self, name):
        for n, btn in self.nav_buttons.items():
            btn.set_active(n == name)

    def goto_dashboard(self):
        self.stack.setCurrentIndex(0)
        self.set_active_nav("Dashboard")

    def goto_project(self):
        self.stack.setCurrentIndex(1)
        self.set_active_nav("Project")

    # ------------------------------------------------------------------
    def build_titlebar(self):
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(52)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)

        logo = QLabel("🧩")
        logo.setStyleSheet(f"color:{ACCENT_BLUE}; font-size:18px;")
        lay.addWidget(logo)

        title = QLabel("Novel Translator Pro")
        title.setStyleSheet(f"color:{TEXT_MAIN}; font-size:15px; font-weight:700;")
        lay.addWidget(title)

        ver = QLabel("v2.1.0")
        ver.setStyleSheet(f"color:{TEXT_FAINT}; font-size:12px;")
        lay.addWidget(ver)

        lay.addStretch()

        for txt in ["⚙ Settings", "◐ Theme", "❓ Help"]:
            b = QPushButton(txt)
            b.setObjectName("ghostBtn")
            lay.addWidget(b)

        for sym in ["—", "▢", "✕"]:
            b = QPushButton(sym)
            b.setObjectName("winBtn")
            b.setFixedSize(30, 30)
            lay.addWidget(b)

        return bar

    def build_connection_bar(self):
        bar = QFrame()
        bar.setObjectName("connbar")
        bar.setFixedHeight(85)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(24)

        def labeled(label, widget):
            box = QVBoxLayout()
            box.setSpacing(2)
            l = QLabel(label)
            l.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
            box.addWidget(l)
            box.addWidget(widget)
            wrap = QWidget()
            wrap.setLayout(box)
            return wrap

        mcp = QHBoxLayout()
        mcp.addWidget(QLabel("🔌"))
        mcp_lbl = QVBoxLayout()
        t = QLabel("MCP Connection")
        t.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        mcp_lbl.addWidget(t)
        mcp_lbl.addWidget(badge("Connected", ACCENT_GREEN))
        mcp.addLayout(mcp_lbl)
        mcp_w = QWidget(); mcp_w.setLayout(mcp)
        lay.addWidget(mcp_w)
        lay.addWidget(vline())

        provider = QComboBox()
        provider.addItems(["✨ Google Gemini", "OpenAI", "Anthropic Claude", "DeepSeek"])
        lay.addWidget(labeled("Provider", provider))

        base_url = QLineEdit("https://generativelanguage.googleapis.com")
        base_url.setMinimumWidth(260)
        lay.addWidget(labeled("Base URL", base_url))

        model = QComboBox()
        model.addItems(["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-pro"])
        lay.addWidget(labeled("Model", model))
        lay.addWidget(vline())

        keypool = QHBoxLayout()
        keypool.addWidget(QLabel("🔑"))
        kp_lbl = QVBoxLayout()
        t2 = QLabel("Key Pool")
        t2.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        kp_lbl.addWidget(t2)
        kp_val = QLabel("12 Keys Loaded")
        kp_val.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
        kp_lbl.addWidget(kp_val)
        keypool.addLayout(kp_lbl)
        refresh = QPushButton("⟳")
        refresh.setObjectName("iconBtn")
        keypool.addWidget(refresh)
        kp_w = QWidget(); kp_w.setLayout(keypool)
        lay.addWidget(kp_w)

        rot = QHBoxLayout()
        rot.addWidget(QLabel("⚡"))
        rot_lbl = QVBoxLayout()
        t3 = QLabel("Rotating")
        t3.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        rot_lbl.addWidget(t3)
        rot_val = QHBoxLayout()
        rv = QLabel("Auto (Round Robin)")
        rv.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
        rot_val.addWidget(rv)
        rot_val.addWidget(dot(ACCENT_GREEN))
        rot_lbl.addLayout(rot_val)
        rot.addLayout(rot_lbl)
        rot_w = QWidget(); rot_w.setLayout(rot)
        lay.addWidget(rot_w)

        lay.addStretch()
        return bar

    def build_sidebar(self):
        panel = QFrame()
        panel.setObjectName("sidebar")
        panel.setFixedWidth(200)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 12, 10, 12)
        lay.setSpacing(4)

        items = [
            ("🏠", "Dashboard"), ("📁", "Project"), ("🗂", "File Queue"),
            ("🌐", "Translate"), ("🔤", "Terminology"), ("✨", "PromptGen"),
            ("📦", "Batch Mode"), ("📝", "Text Editor"), ("🔀", "Merge / Export"),
            ("📊", "Statistics"), ("🧾", "Logs"),
        ]
        for icon, text in items:
            btn = SidebarButton(icon, text)
            if text == "Dashboard":
                btn.clicked.connect(self.goto_dashboard)
            elif text == "Project":
                btn.clicked.connect(self.goto_project)
            lay.addWidget(btn)
            self.nav_buttons[text] = btn

        lay.addStretch()

        active_box = QFrame()
        active_box.setObjectName("activeProject")
        ab = QVBoxLayout(active_box)
        al = QLabel("Active Project")
        al.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        ab.addWidget(al)
        row = QHBoxLayout()
        pn = QLabel("Re:Zero Web Novel")
        pn.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
        row.addWidget(pn)
        row.addWidget(QLabel("Open"))
        row.addWidget(dot(ACCENT_GREEN))
        ab.addLayout(row)
        lay.addWidget(active_box)

        new_proj = QPushButton("+  New Project")
        new_proj.setObjectName("newProjectBtn")
        new_proj.clicked.connect(self.open_new_project_dialog)
        lay.addWidget(new_proj)

        icons_row = QHBoxLayout()
        for i in ["🐙", "❓", "⚙"]:
            b = QPushButton(i)
            b.setObjectName("iconBtn")
            icons_row.addWidget(b)
        icons_row.addStretch()
        lay.addLayout(icons_row)

        return panel

    # ------------------------------------------------------------------
    # DASHBOARD SAYFASI
    # ------------------------------------------------------------------
    def build_dashboard_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        inner = QWidget()
        scroll.setWidget(inner)

        grid = QVBoxLayout(inner)
        grid.setContentsMargins(14, 14, 14, 14)
        grid.setSpacing(14)

        row1 = QHBoxLayout()
        row1.setSpacing(14)
        row1.addWidget(self.build_project_files(), 3)
        row1.addWidget(self.build_translation_queue(), 3)
        row1.addWidget(self.build_statistics(), 3)
        grid.addLayout(row1, 1)

        row2 = QHBoxLayout()
        row2.setSpacing(14)
        row2.addWidget(self.build_logs(), 4)
        row2.addWidget(self.build_merge_export(), 2)
        row2.addWidget(self.build_terminology(), 2)
        grid.addLayout(row2)

        return scroll

    def build_project_files(self):
        add_files = QPushButton("Add Single File")
        add_folder = QPushButton("Add Bulk")
        
        for b in (add_files, add_folder):
            b.setObjectName("smallBtn")
        header_extra = QWidget()
        hl = QHBoxLayout(header_extra)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(add_files); hl.addWidget(add_folder)

        frame, body = card("Project Files (86)", header_extra)

        search = QLineEdit()
        search.setPlaceholderText("🔍  Search files...")
        search_row = QHBoxLayout()
        search_row.addWidget(search)
        filt = QPushButton("▽")
        filt.setObjectName("iconBtn")
        search_row.addWidget(filt)
        body.addLayout(search_row)

        files = [
            ("001", "Prologue", "✔ Translated", ACCENT_GREEN),
            ("002", "Chapter 1", "✔ Translated", ACCENT_GREEN),
            ("003", "Chapter 2", "◐ Translating", ACCENT_BLUE),
            ("004", "Chapter 3", "⏳ Queued", TEXT_DIM),
            ("005", "Chapter 4", "⏳ Queued", TEXT_DIM),
            ("006", "Chapter 5", "⏳ Queued", TEXT_DIM),
        ]
        for num, name, status, color in files:
            row = QHBoxLayout()
            row.addWidget(QCheckBox())
            nlab = QLabel(f"{num}   {name}")
            nlab.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px;")
            row.addWidget(nlab)
            row.addStretch()
            slab = QLabel(status)
            slab.setStyleSheet(f"color:{color}; font-size:11px; font-weight:600;")
            row.addWidget(slab)
            body.addLayout(row)

        dots = QLabel("...")
        dots.setStyleSheet(f"color:{TEXT_FAINT};")
        dots.setAlignment(Qt.AlignCenter)
        body.addWidget(dots)

        last_row = QHBoxLayout()
        last_row.addWidget(QCheckBox())
        nlab = QLabel("086   Chapter 86")
        nlab.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px;")
        last_row.addWidget(nlab)
        last_row.addStretch()
        slab = QLabel("⏳ Queued")
        slab.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px; font-weight:600;")
        last_row.addWidget(slab)
        body.addLayout(last_row)

        body.addStretch()
        footer = QLabel("Total: 86      Completed: 2      Translating: 1      Queued: 83")
        footer.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px; border-top:1px solid {BORDER}; padding-top:8px;")
        body.addWidget(footer)
        return frame

    def build_translation_queue(self):
        start = QPushButton("▶  Start")
        start.setObjectName("primaryBtn")
        pause = QPushButton("⏸  Pause")
        pause.setObjectName("smallBtn")
        header_extra = QWidget()
        hl = QHBoxLayout(header_extra)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(start); hl.addWidget(pause)

        frame, body = card("Translation Queue", header_extra)

        cur = QLabel("Current Task")
        cur.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
        body.addWidget(cur)

        task_row = QHBoxLayout()
        task_row.addWidget(QLabel("📄"))
        tn = QLabel("Chapter 2.txt")
        tn.setStyleSheet(f"color:{TEXT_MAIN}; font-size:13px; font-weight:600;")
        task_row.addWidget(tn)
        task_row.addStretch()
        pct = QLabel("65%")
        pct.setStyleSheet(f"color:{TEXT_MAIN}; font-size:13px; font-weight:700;")
        task_row.addWidget(pct)
        body.addLayout(task_row)

        pb = QProgressBar()
        pb.setValue(65)
        pb.setFixedHeight(8)
        pb.setTextVisible(False)
        body.addWidget(pb)

        meta = QLabel("Progress: 128 / 198 paragraphs        ETA: 00:01:42        Worker: 2 / 3")
        meta.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
        body.addWidget(meta)

        wtitle = QLabel("Worker Status (3)")
        wtitle.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px; font-weight:600; margin-top:6px;")
        body.addWidget(wtitle)

        for name, pctv, rpm, key in [("Worker 1", 78, "11.2", "Key #3"), ("Worker 2", 65, "11.6", "Key #7"), ("Worker 3", 45, "10.8", "Key #12")]:
            wrow = QFrame()
            wl = QVBoxLayout(wrow)
            wl.setContentsMargins(0, 4, 0, 4)
            wl.setSpacing(4)
            top = QHBoxLayout()
            top.addWidget(QLabel("📄"))
            n = QLabel(name)
            n.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
            top.addWidget(n)
            top.addWidget(dot(ACCENT_GREEN))
            proc = QLabel("Processing...")
            proc.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
            top.addWidget(proc)
            top.addStretch()
            rpm_l = QLabel(f"RPM: {rpm}")
            rpm_l.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
            top.addWidget(rpm_l)
            wl.addLayout(top)
            bar_row = QHBoxLayout()
            bar = QProgressBar()
            bar.setValue(pctv)
            bar.setFixedHeight(6)
            bar.setTextVisible(False)
            bar_row.addWidget(bar, 1)
            pl = QLabel(f"{pctv}%")
            pl.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
            bar_row.addWidget(pl)
            kl = QLabel(key)
            kl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
            bar_row.addWidget(kl)
            wl.addLayout(bar_row)
            body.addWidget(wrow)

        feat_grid = QGridLayout()
        feat_grid.setSpacing(8)
        features = [
            ("⧉", "Paragraph Split", "Auto", "Split by paragraphs for better token efficiency.", ACCENT_GREEN),
            ("⛁", "Translation Cache", "ON", "Auto cache enabled. Hit rate 78.4%.", ACCENT_ORANGE),
            ("🔤", "Terminology Memory", "ON", "Consistent terms across all chapters.", ACCENT_GREEN),
            ("✔", "Quality Check", "ON", "Similarity, langdetect and CJK scan activated.", ACCENT_CYAN),
            ("📦", "Batch Mode", "ON", "Pack multiple chapters in one request.", ACCENT_PURPLE),
        ]
        for i, (icon, title, status, sub, color) in enumerate(features):
            fcard = QFrame()
            fcard.setObjectName("featureCard")
            fl = QVBoxLayout(fcard)
            fl.setContentsMargins(12, 10, 12, 10)
            fl.setSpacing(4)
            icon_lbl = QLabel(icon)
            icon_lbl.setFixedSize(30, 30)
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setStyleSheet(f"background:{color}22; color:{color}; border-radius:7px; font-size:15px; font-weight:700;")
            fl.addWidget(icon_lbl)
            t = QLabel(title)
            t.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
            fl.addWidget(t)
            s = QLabel(status)
            s.setStyleSheet(f"color:{color}; font-size:12px; font-weight:700;")
            fl.addWidget(s)
            sub_l = QLabel(sub)
            sub_l.setWordWrap(True)
            sub_l.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
            fl.addWidget(sub_l)
            feat_grid.addWidget(fcard, i // 3, i % 3)
        body.addLayout(feat_grid)

        prompt_frame = QFrame()
        prompt_frame.setObjectName("innerCard")
        pl = QVBoxLayout(prompt_frame)
        ph = QHBoxLayout()
        pt = QLabel("Prompt (Current)")
        pt.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:700;")
        ph.addWidget(pt)
        ph.addStretch()
        edit_btn = QPushButton("✎  Edit with PromptGen")
        edit_btn.setObjectName("purpleBtn")
        ph.addWidget(edit_btn)
        pl.addLayout(ph)

        meta_row = QLabel("Mode: <b>Balanced</b>      Target Language: <b>Türkçe</b>")
        meta_row.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
        pl.addWidget(meta_row)

        prompt_text = QLabel(
            "Anlamı koruyarak doğal ve akıcı bir çeviri yap.\n"
            "Kültürel öğeleri hedef dile uygun şekilde çevir.\n"
            "Karakter isimlerini, teknik terimleri ve önemli özel isimleri çevirme.\n"
            "Üslubu ve dil bilgisi kurallarına ve yazıma dikkat yansıt."
        )
        prompt_text.setWordWrap(True)
        prompt_text.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px; line-height:150%;")
        pl.addWidget(prompt_text)

        gen_row = QHBoxLayout()
        genl = QLabel("Generated by AI\nModel: gemini-1.5-pro\nGenerated: 2024-05-24 14:32")
        genl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        gen_row.addWidget(genl)
        gen_row.addStretch()
        regen = QPushButton("⟳  Regenerate")
        regen.setObjectName("smallBtn")
        gen_row.addWidget(regen)
        pl.addLayout(gen_row)

        body.addWidget(prompt_frame)
        body.addStretch()
        return frame

    def build_statistics(self):
        header_extra = QComboBox()
        header_extra.addItems(["Today", "Last 7 Days", "Last 30 Days"])
        frame, body = card("Statistics Overview", header_extra)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(8)
        stats = [
            ("Total Tokens", "1,248,531", "15.6%", True),
            ("Total Requests", "342", "12.3%", True),
            ("Total Cost (USD)", "$2.48", "8.7%", False),
            ("Avg. Response Time", "4.21s", None, True),
            ("Success Rate", "99.1%", None, True),
            ("Cache Hit Rate", "78.4%", None, True),
        ]
        for i, (t, v, d, up) in enumerate(stats):
            stats_grid.addWidget(StatCard(t, v, None, d, up), i // 3, i % 3)
        body.addLayout(stats_grid)

        chart_title = QLabel("API Requests (Last 7 Days)")
        chart_title.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px; font-weight:600; margin-top:6px;")
        body.addWidget(chart_title)
        body.addWidget(RequestsChart())

        req_header = QHBoxLayout()
        rh = QLabel("Request List (Last 20)")
        rh.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:700;")
        req_header.addWidget(rh)
        req_header.addStretch()
        view_all = QPushButton("View All")
        view_all.setObjectName("linkBtn")
        req_header.addWidget(view_all)
        body.addLayout(req_header)

        rows = [
            ("14:32:21", "gemini-1.5-pro", "8,523", "✔", "$0.016"),
            ("14:31:48", "gemini-1.5-pro", "7,112", "✔", "$0.013"),
            ("14:31:12", "gemini-1.5-pro", "9,001", "✔", "$0.017"),
            ("14:30:41", "gemini-1.5-pro", "6,500", "✔", "$0.012"),
            ("14:30:05", "gemini-1.5-pro", "8,912", "✔", "$0.016"),
        ]
        table = make_table(["Time", "Model", "Tokens", "Status", "Cost"], rows)
        table.setFixedHeight(180)
        body.addWidget(table)
        return frame

    def build_logs(self):
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("smallBtn")
        frame, body = card("Logs", clear_btn)

        log_lines = [
            ("[14:32:21]", "[INFO]", "Worker 2 completed paragraph 128/198 - from cache(similarity: 92%)", TEXT_DIM),
            ("[14:32:20]", "[INFO]", "Worker 1 -> API Request sent (Tokens: 2,153)", TEXT_DIM),
            ("[14:32:19]", "[INFO]", "Worker 3 -> API Response received (Tokens: 2,048) - 2.31s", TEXT_DIM),
            ("[14:32:18]", "[INFO]", "Cache hit: 78.4% (10,231 / 13,047 paragraphs)", TEXT_DIM),
            ("[14:32:17]", "[WARN]", "Similarity check: 82% - Text may be untranslated. (Chapter 1.txt)", ACCENT_ORANGE),
            ("[14:32:16]", "[INFO]", "Batch mode: 5 chapters packed into 1 request", TEXT_DIM),
            ("[14:32:15]", "[INFO]", "Language detected: tr (0.99)", TEXT_DIM),
        ]
        log_box = QTextEdit()
        log_box.setReadOnly(True)
        log_box.setStyleSheet(f"""
            QTextEdit {{
                background: {BG_PANEL2}; border: 1px solid {BORDER}; border-radius: 6px;
                color: {TEXT_DIM}; font-family: Consolas, monospace; font-size: 11px; padding: 8px;
            }}
        """)
        html_lines = []
        for time_, level, msg, color in log_lines:
            lvl_color = ACCENT_ORANGE if level == "[WARN]" else ACCENT_CYAN
            html_lines.append(
                f'<span style="color:{TEXT_FAINT}">{time_}</span> '
                f'<span style="color:{lvl_color}; font-weight:600">{level}</span> '
                f'<span style="color:{color}">{msg}</span>'
            )
        log_box.setHtml("<br>".join(html_lines))
        log_box.setMinimumHeight(220)
        body.addWidget(log_box)
        return frame

    def build_merge_export(self):
        frame, body = card("Merge / Export")
        fmt_label = QLabel("Output Format")
        fmt_label.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
        body.addWidget(fmt_label)

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QRadioButton("TXT"))
        epub_radio = QRadioButton("EPUB")
        epub_radio.setChecked(True)
        fmt_row.addWidget(epub_radio)
        fmt_row.addStretch()
        body.addLayout(fmt_row)

        settings_btn = QPushButton("⚙  Merge Settings")
        settings_btn.setObjectName("smallBtnFull")
        body.addWidget(settings_btn)

        export_btn = QPushButton("⇩  Merge & Export")
        export_btn.setObjectName("greenBtn")
        body.addWidget(export_btn)
        body.addStretch()
        return frame

    def build_terminology(self):
        frame, body = card("Terminology (Last Update)")
        stats_row = QHBoxLayout()
        for title, val, color in [("Total Terms", "2,341", TEXT_MAIN), ("New Terms", "+152", ACCENT_GREEN), ("Last Update", "24 May 14:00", TEXT_MAIN)]:
            box = QVBoxLayout()
            t = QLabel(title)
            t.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
            v = QLabel(val)
            v.setStyleSheet(f"color:{color}; font-size:14px; font-weight:700;")
            box.addWidget(t); box.addWidget(v)
            w = QWidget(); w.setLayout(box)
            stats_row.addWidget(w)
        body.addLayout(stats_row)
        open_btn = QPushButton("⚙  Open Terminology Manager")
        open_btn.setObjectName("smallBtnFull")
        body.addWidget(open_btn)
        body.addStretch()
        return frame

    # ------------------------------------------------------------------
    # PROJECT SAYFASI
    # ------------------------------------------------------------------
    def build_project_page(self):
        outer = QWidget()
        root = QHBoxLayout(outer)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(14)

        # Sol taraf: Başlık + arama + istatistik + tablo
        left = QVBoxLayout()
        left.setSpacing(14)

        title_row = QVBoxLayout()
        t = QLabel("Projects")
        t.setStyleSheet(f"color:{TEXT_MAIN}; font-size:22px; font-weight:700;")
        sub = QLabel("Manage and organize your translation projects")
        sub.setStyleSheet(f"color:{TEXT_FAINT}; font-size:12px;")
        title_row.addWidget(t)
        title_row.addWidget(sub)
        left.addLayout(title_row)

        toolbar = QHBoxLayout()
        search = QLineEdit()
        search.setPlaceholderText("🔍  Search projects...")
        toolbar.addWidget(search, 1)
        filt = QPushButton("▽")
        filt.setObjectName("iconBtn")
        toolbar.addWidget(filt)
        toolbar.addStretch()
        imp = QPushButton("⇧  Import Project")
        imp.setObjectName("smallBtn")
        toolbar.addWidget(imp)
        ref = QPushButton("⟳  Refresh")
        ref.setObjectName("smallBtn")
        toolbar.addWidget(ref)
        newp = QPushButton("+  New Project")
        newp.setObjectName("primaryBtn")
        newp.clicked.connect(self.open_new_project_dialog)
        toolbar.addWidget(newp)
        left.addLayout(toolbar)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        stats_row.addWidget(StatCard("Total Projects", "24"))
        stats_row.addWidget(StatCard("Active Projects", "8", ACCENT_GREEN))
        stats_row.addWidget(StatCard("Completed", "10", ACCENT_BLUE))
        stats_row.addWidget(StatCard("Archived", "6", ACCENT_PURPLE))
        stats_row.addWidget(StatCard("Total Size", "128.7 GB", ACCENT_ORANGE))
        left.addLayout(stats_row)

        table_frame = QFrame()
        table_frame.setObjectName("card")
        tf_lay = QVBoxLayout(table_frame)
        tf_lay.setContentsMargins(4, 8, 4, 8)

        projects = [
            ("Re:Zero Web Novel", "D:\\NovelTranslator\\Projects\\rezero", "JP", "EN", 65, "86 / 132 chapters", "Active", "24 May 2024 14:32", "12.4 GB"),
            ("Solo Leveling", "D:\\NovelTranslator\\Projects\\sololeveling", "KR", "EN", 42, "67 / 160 chapters", "Active", "24 May 2024 13:15", "8.7 GB"),
            ("Martial God Asura", "D:\\NovelTranslator\\Projects\\mga", "ZH", "EN", 100, "233 / 233 chapters", "Completed", "23 May 2024 22:10", "15.2 GB"),
            ("Overgeared", "D:\\NovelTranslator\\Projects\\overgeared", "KR", "EN", 18, "28 / 157 chapters", "Active", "23 May 2024 18:45", "6.1 GB"),
            ("The Beginning After The End", "D:\\NovelTranslator\\Projects\\tbate", "EN", "TR", 88, "408 / 463 chapters", "Active", "23 May 2024 16:20", "10.3 GB"),
            ("Lord of Mysteries", "D:\\NovelTranslator\\Projects\\lom", "ZH", "EN", 5, "8 / 1438 chapters", "Active", "23 May 2024 11:05", "22.8 GB"),
            ("Tales of Demons and Gods", "D:\\NovelTranslator\\Projects\\todag", "ZH", "EN", 100, "499 / 499 chapters", "Completed", "22 May 2024 20:30", "18.6 GB"),
            ("Versatile Mage", "D:\\NovelTranslator\\Projects\\versatilemage", "ZH", "EN", 0, "0 / 1129 chapters", "Queued", "22 May 2024 15:40", "9.9 GB"),
            ("Archived Project Example", "D:\\NovelTranslator\\Projects\\archive-example", "JP", "EN", 100, "120 / 120 chapters", "Archived", "20 May 2024 09:15", "4.7 GB"),
        ]

        header_row = QHBoxLayout()
        for text, stretch in [("Project Name", 4), ("Source", 1), ("Target", 1), ("Progress", 3), ("Status", 2), ("Last Updated", 2), ("Size", 1), ("Actions", 2)]:
            l = QLabel(text)
            l.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px; font-weight:600;")
            header_row.addWidget(l, stretch)
        header_row_w = QWidget()
        header_row_w.setLayout(header_row)
        header_row_w.setStyleSheet(f"border-bottom:1px solid {BORDER};")
        tf_lay.addWidget(header_row_w)

        for name, path, src, tgt, pct, chapters, status, updated, size in projects:
            row = QHBoxLayout()
            row.setContentsMargins(4, 8, 4, 8)

            name_box = QHBoxLayout()
            name_box.addWidget(QLabel("📁"))
            name_v = QVBoxLayout()
            name_v.setSpacing(0)
            nl = QLabel(name)
            nl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
            pl_ = QLabel(path)
            pl_.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
            name_v.addWidget(nl)
            name_v.addWidget(pl_)
            name_box.addLayout(name_v)
            name_w = QWidget(); name_w.setLayout(name_box)
            row.addWidget(name_w, 4)

            row.addWidget(badge(src, TEXT_DIM), 1)
            row.addWidget(badge(tgt, TEXT_DIM), 1)

            prog_box = QVBoxLayout()
            prog_box.setSpacing(2)
            pb = QProgressBar()
            pb.setValue(pct)
            pb.setFixedHeight(6)
            pb.setTextVisible(False)
            prog_box.addWidget(pb)
            prog_lbl = QLabel(f"{pct}%   {chapters}")
            prog_lbl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
            prog_box.addWidget(prog_lbl)
            prog_w = QWidget(); prog_w.setLayout(prog_box)
            row.addWidget(prog_w, 3)

            row.addWidget(badge(status, status_color(status)), 2)

            upd = QLabel(updated)
            upd.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
            row.addWidget(upd, 2)

            sz = QLabel(size)
            sz.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
            row.addWidget(sz, 1)

            actions = QHBoxLayout()
            for sym in ["▶", "📂", "⋮"]:
                b = QPushButton(sym)
                b.setObjectName("iconBtn")
                actions.addWidget(b)
            actions_w = QWidget(); actions_w.setLayout(actions)
            row.addWidget(actions_w, 2)

            row_w = QWidget()
            row_w.setLayout(row)
            row_w.setStyleSheet(f"border-bottom:1px solid {BORDER};")
            tf_lay.addWidget(row_w)

        tf_lay.addStretch()

        pagination = QHBoxLayout()
        showing = QLabel("Showing 1 to 9 of 24 projects")
        showing.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
        pagination.addWidget(showing)
        pagination.addStretch()
        for sym in ["«", "‹"]:
            b = QPushButton(sym); b.setObjectName("iconBtn"); pagination.addWidget(b)
        for num in ["1", "2", "3"]:
            b = QPushButton(num)
            b.setObjectName("pageBtnActive" if num == "1" else "pageBtn")
            pagination.addWidget(b)
        for sym in ["›", "»"]:
            b = QPushButton(sym); b.setObjectName("iconBtn"); pagination.addWidget(b)
        pagination.addStretch()
        per_page = QComboBox()
        per_page.addItems(["10 / page", "25 / page", "50 / page"])
        pagination.addWidget(per_page)
        tf_lay.addLayout(pagination)

        left.addWidget(table_frame, 1)

        left_scroll_w = QWidget()
        left_scroll_w.setLayout(left)
        root.addWidget(left_scroll_w, 3)

        # Sağ taraf: Project Details paneli
        root.addWidget(self.build_project_details_panel(), 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;")
        scroll.setWidget(outer)
        return scroll

    def build_project_details_panel(self):
        frame, body = card("Project Details")

        head = QHBoxLayout()
        icon = QLabel("📁")
        icon.setFixedSize(56, 56)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"background:{ACCENT_BLUE}22; color:{ACCENT_BLUE}; font-size:26px; border-radius:10px;")
        head.addWidget(icon)
        head.addStretch()
        edit_b = QPushButton("✎")
        edit_b.setObjectName("iconBtn")
        head.addWidget(edit_b)
        body.addLayout(head)

        name_row = QHBoxLayout()
        nl = QLabel("Re:Zero Web Novel")
        nl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:15px; font-weight:700;")
        name_row.addWidget(nl)
        name_row.addWidget(badge("Active", ACCENT_GREEN))
        name_row.addStretch()
        body.addLayout(name_row)

        path = QLabel("D:\\NovelTranslator\\Projects\\rezero")
        path.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        body.addWidget(path)

        meta = [
            ("Source Language", "Japanese (JP)"),
            ("Target Language", "English (EN)"),
            ("Translation Style", "Balanced"),
            ("Model", "gemini-1.5-pro"),
            ("Created", "15 May 2024 10:30"),
            ("Last Updated", "24 May 2024 14:32"),
            ("Total Chapters", "132"),
            ("Completed", "86"),
            ("In Queue", "10"),
            ("Failed", "0"),
            ("Total Size", "12.4 GB"),
        ]
        for k, v in meta:
            row = QHBoxLayout()
            kl = QLabel(k)
            kl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
            vl = QLabel(v)
            vl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:11px; font-weight:600;")
            row.addWidget(kl)
            row.addStretch()
            row.addWidget(vl)
            body.addLayout(row)

        prog_title = QLabel("Progress Overview")
        prog_title.setStyleSheet(f"color:{TEXT_MAIN}; font-size:13px; font-weight:700; margin-top:8px;")
        body.addWidget(prog_title)

        prog_row = QHBoxLayout()
        prog_row.addWidget(DonutChart(65, 8, 27, "65%", "Overall Progress"))
        legend = QVBoxLayout()
        legend.setSpacing(6)
        for label, val, color in [("Completed", "86 (65%)", ACCENT_BLUE), ("In Queue", "10 (8%)", ACCENT_ORANGE), ("Remaining", "36 (27%)", "#4b5563")]:
            lrow = QHBoxLayout()
            lrow.addWidget(dot(color, 9))
            ll = QLabel(label)
            ll.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
            lrow.addWidget(ll)
            lrow.addStretch()
            lv = QLabel(val)
            lv.setStyleSheet(f"color:{TEXT_MAIN}; font-size:11px; font-weight:600;")
            lrow.addWidget(lv)
            legend.addLayout(lrow)
        legend.addStretch()
        prog_row.addLayout(legend)
        body.addLayout(prog_row)

        act_header = QHBoxLayout()
        at = QLabel("Recent Activity")
        at.setStyleSheet(f"color:{TEXT_MAIN}; font-size:13px; font-weight:700; margin-top:6px;")
        act_header.addWidget(at)
        act_header.addStretch()
        va = QPushButton("View All")
        va.setObjectName("linkBtn")
        act_header.addWidget(va)
        body.addLayout(act_header)

        for txt, time_ in [
            ("Chapter 86.txt translated", "24 May 2024 14:31"),
            ("Chapter 85.txt translated", "24 May 2024 14:28"),
            ("Chapter 84.txt translated", "24 May 2024 14:25"),
        ]:
            row = QHBoxLayout()
            ic = QLabel("✔")
            ic.setStyleSheet(f"color:{ACCENT_GREEN}; font-size:12px;")
            row.addWidget(ic)
            v = QVBoxLayout()
            v.setSpacing(0)
            t1 = QLabel(txt)
            t1.setStyleSheet(f"color:{TEXT_MAIN}; font-size:11px;")
            t2 = QLabel(time_)
            t2.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
            v.addWidget(t1); v.addWidget(t2)
            row.addLayout(v)
            row.addStretch()
            body.addLayout(row)

        body.addStretch()
        return frame

    # ------------------------------------------------------------------
    def build_statusbar(self):
        bar = QFrame()
        bar.setObjectName("statusbar")
        bar.setFixedHeight(30)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)

        ready_row = QHBoxLayout()
        ready_row.addWidget(dot(ACCENT_GREEN, 7))
        ready = QLabel("Ready")
        ready.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
        ready_row.addWidget(ready)
        rw = QWidget(); rw.setLayout(ready_row)
        lay.addWidget(rw)

        lay.addStretch()
        info = QLabel(
            "Workers: 3     Batch Mode: ON     Cache: ON     Terminology: ON     "
            "Quality Check: ON     Total Tokens: 1,248,531     Total Cost: $2.48     RPM: 11.4"
        )
        info.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
        lay.addWidget(info)
        return bar

    # ------------------------------------------------------------------
    def build_stylesheet(self):
        return f"""
        QMainWindow, QWidget {{
            background: {BG_APP}; color: {TEXT_MAIN}; font-family: '{FONT_FAMILY}';
        }}
        #topbar {{ background: {BG_APP}; border-bottom: 1px solid {BORDER}; }}
        #connbar {{ background: {BG_PANEL}; border-bottom: 1px solid {BORDER}; }}
        #sidebar {{ background: {BG_APP}; border-right: 1px solid {BORDER}; }}
        #statusbar {{ background: {BG_PANEL}; border-top: 1px solid {BORDER}; }}
        #card, #innerCard, #statCard, #featureCard, #activeProject {{
            background: {BG_PANEL}; border: 1px solid {BORDER}; border-radius: 10px;
        }}
        #innerCard {{ background: {BG_PANEL2}; }}
        #cardTitle {{ color: {TEXT_MAIN}; font-size: 14px; font-weight: 700; }}
        #styleCard {{
            background: {BG_PANEL2}; border: 1px solid {BORDER}; border-radius: 8px;
        }}
        #styleCardActive {{
            background: {ACCENT_BLUE}18; border: 1px solid {ACCENT_BLUE}; border-radius: 8px;
        }}
        QPushButton {{
            color: {TEXT_MAIN}; background: {BG_PANEL2}; border: 1px solid {BORDER};
            border-radius: 6px; padding: 6px 10px; font-size: 12px;
        }}
        QPushButton:hover {{ background: #182234; }}
        #navBtn {{
            text-align: left; background: transparent; border: none; color: {TEXT_DIM};
            border-radius: 8px; font-size: 13px;
        }}
        #navBtn:hover {{ background: {BG_PANEL2}; color: {TEXT_MAIN}; }}
        #navBtnActive {{
            text-align: left; background: {ACCENT_BLUE}22; border: 1px solid {ACCENT_BLUE}55;
            color: {ACCENT_BLUE}; border-radius: 8px; font-size: 13px; font-weight: 600;
        }}
        #ghostBtn {{ background: transparent; border: none; color: {TEXT_DIM}; font-size: 12px; }}
        #ghostBtn:hover {{ color: {TEXT_MAIN}; }}
        #winBtn {{ background: transparent; border: none; color: {TEXT_DIM}; }}
        #winBtn:hover {{ background: {BG_PANEL2}; }}
        #iconBtn {{
            background: {BG_PANEL2}; border: 1px solid {BORDER}; border-radius: 6px;
            max-width: 30px; padding: 4px;
        }}
        #smallBtn {{
            background: {BG_PANEL2}; border: 1px solid {BORDER}; border-radius: 6px;
            font-size: 11px; padding: 5px 10px;
        }}
        #smallBtnFull {{
            background: {BG_PANEL2}; border: 1px solid {BORDER}; border-radius: 6px;
            font-size: 12px; padding: 8px;
        }}
        #primaryBtn {{
            background: {ACCENT_BLUE}; border: none; color: white; border-radius: 6px;
            font-weight: 600; padding: 6px 14px;
        }}
        #primaryBtn:hover {{ background: #2563eb; }}
        #purpleBtn {{
            background: {ACCENT_PURPLE}22; border: 1px solid {ACCENT_PURPLE}66; color: {ACCENT_PURPLE};
            border-radius: 6px; font-size: 11px; padding: 5px 10px;
        }}
        #greenBtn {{
            background: {ACCENT_GREEN}; border: none; color: white; border-radius: 6px;
            font-weight: 700; padding: 9px;
        }}
        #greenBtn:hover {{ background: #16a34a; }}
        #linkBtn {{ background: transparent; border: none; color: {ACCENT_BLUE}; font-size: 11px; }}
        #pageBtn {{
            background: {BG_PANEL2}; border: 1px solid {BORDER}; border-radius: 6px;
            font-size: 11px; padding: 4px 10px;
        }}
        #pageBtnActive {{
            background: {ACCENT_BLUE}; border: none; color: white; border-radius: 6px;
            font-size: 11px; padding: 4px 10px; font-weight: 700;
        }}
        QLineEdit, QComboBox, QTextEdit {{
            background: {BG_PANEL2}; border: 1px solid {BORDER}; border-radius: 6px;
            padding: 5px 8px; color: {TEXT_MAIN}; font-size: 12px;
        }}
        QComboBox::drop-down {{ border: none; }}
        QProgressBar {{ background: {BG_PANEL2}; border: none; border-radius: 4px; }}
        QProgressBar::chunk {{ background: {ACCENT_BLUE}; border-radius: 4px; }}
        QCheckBox, QRadioButton {{ color: {TEXT_DIM}; font-size: 12px; }}
        QSlider::groove:horizontal {{ height: 4px; background: {BG_PANEL2}; border-radius: 2px; }}
        QSlider::handle:horizontal {{
            background: {ACCENT_BLUE}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
        }}
        QSlider::sub-page:horizontal {{ background: {ACCENT_BLUE}; border-radius: 2px; }}
        QCheckBox#toggleSwitch {{ spacing: 0px; }}
        QCheckBox#toggleSwitch::indicator {{
            width: 36px; height: 20px; border-radius: 10px;
            background: {BORDER}; border: 1px solid {BORDER};
        }}
        QCheckBox#toggleSwitch::indicator:checked {{
            background: {ACCENT_BLUE}; border: 1px solid {ACCENT_BLUE};
        }}
        QScrollBar:vertical {{ background: {BG_APP}; width: 10px; }}
        QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 24px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
