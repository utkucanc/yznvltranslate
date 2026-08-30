"""
sidebar_builder.py — Sol navigasyon çubuğu.

Navigasyon öğeleri:
  Dashboard, Project, File Queue, Translate, Terminology,
  PromptGen, Batch Mode, Text Editor, Merge/Export, Statistics, Logs

Alt kısım:
  Aktif proje adı, + New Project butonu, GitHub/Help/Settings ikon butonları
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.dark_theme import (
    BG_APP, BG_PANEL, BG_PANEL2, BORDER, TEXT_MAIN, TEXT_DIM, TEXT_FAINT,
    ACCENT_BLUE, ACCENT_GREEN
)


# Navigasyon öğeleri: (ikon, ad, hedef_index_veya_None)
NAV_ITEMS = [
    ("🏠", "Dashboard",     0),   # Stack index 0
    ("📁", "Project",       1),   # Stack index 1
    ("🔤", "Terminology",   "dlg_terminology"),
    ("✨", "Prompts",     "dlg_prompt")
]


class SidebarButton(QPushButton):
    """Navigasyon çubuğu butonu."""
    def __init__(self, icon_txt: str, text: str):
        super().__init__(f"  {icon_txt}   {text}")
        self.setObjectName("navBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(38)
        self.setFont(QFont("Segoe UI", 11))

    def set_active(self, active: bool):
        self.setObjectName("navBtnActive" if active else "navBtn")
        self.style().unpolish(self)
        self.style().polish(self)


def build_sidebar(main_window) -> QFrame:
    """
    Sol sidebar panelini oluşturur.

    Eklenen referanslar:
        win.nav_buttons          — {name: SidebarButton} sözlüğü
        win.sidebar_project_label — Aktif proje adı QLabel
    """
    win = main_window
    win.nav_buttons = {}

    panel = QFrame()
    panel.setObjectName("sidebar")
    panel.setFixedWidth(210)

    lay = QVBoxLayout(panel)
    lay.setContentsMargins(10, 14, 10, 14)
    lay.setSpacing(2)

    # ── Logo / Başlık ──────────────────────────────────────────────
    title_row = QHBoxLayout()
    logo = QLabel("🧩")
    logo.setStyleSheet(f"color:{ACCENT_BLUE}; font-size:18px;")
    title_row.addWidget(logo)
    title_lbl = QLabel("Novel Translator")
    title_lbl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:13px; font-weight:700;")
    title_row.addWidget(title_lbl)
    title_row.addStretch()
    lay.addLayout(title_row)

    # Separator
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet(f"color:{BORDER}; margin: 6px 0;")
    lay.addWidget(sep)

    # ── Navigasyon butonları ──────────────────────────────────────
    for icon, name, target in NAV_ITEMS:
        btn = SidebarButton(icon, name)

        if isinstance(target, int):
            # Stack index
            idx = target  # closure için kopyala
            btn.clicked.connect(lambda checked, i=idx, n=name: _nav_click(win, i, n))
        elif target == "dlg_terminology":
            btn.clicked.connect(lambda: _open_terminology(win))
        elif target == "dlg_prompt":
            btn.clicked.connect(lambda: _open_prompt(win))
        elif target == "dlg_text_editor":
            btn.clicked.connect(lambda: _open_text_editor(win))

        win.nav_buttons[name] = btn
        lay.addWidget(btn)

    lay.addStretch()

    # ── Aktif Proje ──────────────────────────────────────────────
    active_box = QFrame()
    active_box.setObjectName("activeProject")
    ab = QVBoxLayout(active_box)
    ab.setContentsMargins(10, 10, 10, 10)
    ab.setSpacing(4)

    al = QLabel("Active Project")
    al.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
    ab.addWidget(al)

    prow = QHBoxLayout()
    prow.setSpacing(6)
    win.sidebar_project_label = QLabel("—")
    win.sidebar_project_label.setStyleSheet(
        f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;"
    )
    prow.addWidget(win.sidebar_project_label, 1)
    dot = QLabel()
    dot.setFixedSize(8, 8)
    dot.setStyleSheet(f"background:{ACCENT_GREEN}; border-radius:4px;")
    prow.addWidget(dot)
    ab.addLayout(prow)
    lay.addWidget(active_box)

    # ── Yeni Proje ────────────────────────────────────────────────
    new_proj = QPushButton("+  New Project")
    new_proj.setObjectName("newProjectBtn")
    new_proj.setCursor(Qt.CursorShape.PointingHandCursor)
    new_proj.clicked.connect(win.new_project_clicked)
    lay.addWidget(new_proj)

    # ── Alt ikon satırı ──────────────────────────────────────────
    icons_row = QHBoxLayout()
    icons_row.setSpacing(4)

    github_btn = QPushButton("🐙")
    github_btn.setObjectName("iconBtn")
    github_btn.setToolTip("GitHub")
    github_btn.clicked.connect(win.show_help_clicked)
    icons_row.addWidget(github_btn)

    help_btn = QPushButton("❓")
    help_btn.setObjectName("iconBtn")
    help_btn.setToolTip("Yardım")
    help_btn.clicked.connect(win.show_help_clicked)
    icons_row.addWidget(help_btn)

    settings_btn = QPushButton("⚙")
    settings_btn.setObjectName("iconBtn")
    settings_btn.setToolTip("Uygulama Ayarları")
    settings_btn.clicked.connect(win.open_app_settings_dialog)
    icons_row.addWidget(settings_btn)

    icons_row.addStretch()
    lay.addLayout(icons_row)

    return panel


def _nav_click(win, stack_index: int, name: str):
    """Stack sayfasını ve aktif nav butonunu günceller."""
    if hasattr(win, 'main_stack'):
        win.main_stack.setCurrentIndex(stack_index)
    win.set_active_nav(name)


def _open_terminology(win):
    """Terminology dialog'unu açar."""
    try:
        from dialogs import TerminologyDialog
        TerminologyDialog(win).exec()
    except Exception as e:
        from logger import app_logger
        app_logger.warning(f"Terminology dialog açılamadı: {e}")


def _open_prompt(win):
    """Prompt editor dialog'unu açar."""
    try:
        win.open_prompt_editor()
    except Exception as e:
        from logger import app_logger
        app_logger.warning(f"Prompt editor açılamadı: {e}")


def _open_text_editor(win):
    """Text editor dialog'unu açar."""
    try:
        from ui.text_editor_dialog import TextEditorDialog
        dlg = TextEditorDialog(win)
        dlg.exec()
    except Exception as e:
        from logger import app_logger
        app_logger.warning(f"Text editor açılamadı: {e}")


def update_sidebar_project_label(win):
    """Aktif proje adını sidebar'da günceller."""
    if not hasattr(win, 'sidebar_project_label'):
        return
    if hasattr(win, 'project_list'):
        item = win.project_list.currentItem()
        name = item.text() if item else "—"
    else:
        name = "—"
    win.sidebar_project_label.setText(name)
