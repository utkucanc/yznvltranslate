"""
dark_theme.py — Novel Translator Pro koyu tema stylesheet sistemi.

Referans: novel_translator_pro2.py / build_stylesheet()
Renk paleti birebir korunuyor; PyQt6 enum'ları kullanılıyor.
"""

from PyQt6.QtWidgets import QApplication

# ------------------------------------------------------------------
# Renk paleti
# ------------------------------------------------------------------
BG_APP        = "#0b0f19"
BG_PANEL      = "#111827"
BG_PANEL2     = "#0f1522"
BORDER        = "#1f2937"
TEXT_MAIN     = "#e5e7eb"
TEXT_DIM      = "#9ca3af"
TEXT_FAINT    = "#6b7280"
ACCENT_BLUE   = "#3b82f6"
ACCENT_GREEN  = "#22c55e"
ACCENT_ORANGE = "#f59e0b"
ACCENT_PURPLE = "#a855f7"
ACCENT_RED    = "#ef4444"
ACCENT_CYAN   = "#38bdf8"
ACCENT_GRAY   = "#6b7280"
FONT_FAMILY   = "Segoe UI"


def build_dark_stylesheet() -> str:
    """Novel Translator Pro koyu tema stylesheet'ini döndürür."""
    return f"""
    /* ── Temel ── */
    QMainWindow, QWidget {{
        background: {BG_APP};
        color: {TEXT_MAIN};
        font-family: '{FONT_FAMILY}';
        font-size: 12px;
    }}

    /* ── Üst / Bağlantı / Alt çubuklar ── */
    #topbar   {{ background: {BG_APP};   border-bottom: 1px solid {BORDER}; }}
    #connbar  {{ background: {BG_PANEL}; border-bottom: 1px solid {BORDER}; }}
    #sidebar  {{ background: {BG_APP};   border-right:  1px solid {BORDER}; }}
    #statusbar {{ background: {BG_PANEL}; border-top: 1px solid {BORDER}; }}

    /* ── Kartlar ── */
    #card, #innerCard, #statCard, #featureCard, #activeProject {{
        background: {BG_PANEL};
        border: 1px solid {BORDER};
        border-radius: 10px;
    }}
    #innerCard {{ background: {BG_PANEL2}; }}
    #cardTitle {{
        color: {TEXT_MAIN};
        font-size: 14px;
        font-weight: 700;
    }}

    /* ── Translation Style kartları ── */
    #styleCard {{
        background: {BG_PANEL2};
        border: 1px solid {BORDER};
        border-radius: 8px;
    }}
    #styleCardActive {{
        background: {ACCENT_BLUE}18;
        border: 1px solid {ACCENT_BLUE};
        border-radius: 8px;
    }}

    /* ── Butonlar ── */
    QPushButton {{
        color: {TEXT_MAIN};
        background: {BG_PANEL2};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}
    QPushButton:hover {{ background: #182234; border-color: {ACCENT_BLUE}66; }}
    QPushButton:pressed {{ background: {BG_APP}; }}
    QPushButton:disabled {{ color: {TEXT_FAINT}; background: {BG_APP}; border-color: {BORDER}; }}

    /* Navigasyon butonları */
    #navBtn {{
        text-align: left;
        background: transparent;
        border: none;
        color: {TEXT_DIM};
        border-radius: 8px;
        font-size: 13px;
        padding: 8px 10px;
    }}
    #navBtn:hover {{ background: {BG_PANEL2}; color: {TEXT_MAIN}; }}
    #navBtnActive {{
        text-align: left;
        background: {ACCENT_BLUE}22;
        border: 1px solid {ACCENT_BLUE}55;
        color: {ACCENT_BLUE};
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        padding: 8px 10px;
    }}

    /* Hayalet / ikon butonlar */
    #ghostBtn {{ background: transparent; border: none; color: {TEXT_DIM}; font-size: 12px; }}
    #ghostBtn:hover {{ color: {TEXT_MAIN}; }}
    #winBtn {{ background: transparent; border: none; color: {TEXT_DIM}; }}
    #winBtn:hover {{ background: {BG_PANEL2}; }}
    #iconBtn {{
        background: {BG_PANEL2};
        border: 1px solid {BORDER};
        border-radius: 6px;
        max-width: 30px;
        padding: 4px;
    }}
    #iconBtn:hover {{ border-color: {ACCENT_BLUE}66; }}

    /* Boyutlu butonlar */
    #smallBtn {{
        background: {BG_PANEL2};
        border: 1px solid {BORDER};
        border-radius: 6px;
        font-size: 11px;
        padding: 5px 10px;
    }}
    #smallBtnFull {{
        background: {BG_PANEL2};
        border: 1px solid {BORDER};
        border-radius: 6px;
        font-size: 12px;
        padding: 8px;
    }}
    #primaryBtn {{
        background: {ACCENT_BLUE};
        border: none;
        color: white;
        border-radius: 6px;
        font-weight: 600;
        padding: 6px 14px;
    }}
    #primaryBtn:hover {{ background: #2563eb; }}
    #primaryBtn:disabled {{ background: {ACCENT_BLUE}55; color: {TEXT_FAINT}; }}

    #purpleBtn {{
        background: {ACCENT_PURPLE}22;
        border: 1px solid {ACCENT_PURPLE}66;
        color: {ACCENT_PURPLE};
        border-radius: 6px;
        font-size: 11px;
        padding: 5px 10px;
    }}
    #greenBtn {{
        background: {ACCENT_GREEN};
        border: none;
        color: white;
        border-radius: 6px;
        font-weight: 700;
        padding: 9px;
    }}
    #greenBtn:hover {{ background: #16a34a; }}
    #greenBtn:disabled {{ background: {ACCENT_GREEN}55; }}

    #dangerBtn {{
        background: {ACCENT_RED}22;
        border: 1px solid {ACCENT_RED}66;
        color: {ACCENT_RED};
        border-radius: 6px;
        font-size: 11px;
        padding: 5px 10px;
    }}
    #orangeBtn {{
        background: {ACCENT_ORANGE}22;
        border: 1px solid {ACCENT_ORANGE}66;
        color: {ACCENT_ORANGE};
        border-radius: 6px;
        font-size: 11px;
        padding: 5px 10px;
    }}
    #linkBtn {{ background: transparent; border: none; color: {ACCENT_BLUE}; font-size: 11px; }}
    #linkBtn:hover {{ color: white; }}

    /* Sayfalama */
    #pageBtn {{
        background: {BG_PANEL2};
        border: 1px solid {BORDER};
        border-radius: 6px;
        font-size: 11px;
        padding: 4px 10px;
    }}
    #pageBtnActive {{
        background: {ACCENT_BLUE};
        border: none;
        color: white;
        border-radius: 6px;
        font-size: 11px;
        padding: 4px 10px;
        font-weight: 700;
    }}

    /* Yeni proje butonu (sidebar) */
    #newProjectBtn {{
        background: {ACCENT_BLUE};
        border: none;
        color: white;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        padding: 9px 14px;
    }}
    #newProjectBtn:hover {{ background: #2563eb; }}

    /* ── Form elemanları ── */
    QLineEdit, QComboBox, QTextEdit, QSpinBox {{
        background: {BG_PANEL2};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 5px 8px;
        color: {TEXT_MAIN};
        font-size: 12px;
    }}
    QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QSpinBox:focus {{
        border-color: {ACCENT_BLUE}88;
    }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox::down-arrow {{ width: 10px; height: 10px; }}
    QComboBox QAbstractItemView {{
        background: {BG_PANEL};
        border: 1px solid {BORDER};
        selection-background-color: {ACCENT_BLUE}44;
        color: {TEXT_MAIN};
    }}

    /* ── Progress Bar ── */
    QProgressBar {{
        background: {BG_PANEL2};
        border: none;
        border-radius: 4px;
        color: {TEXT_MAIN};
        text-align: center;
        font-size: 10px;
    }}
    QProgressBar::chunk {{
        background: {ACCENT_BLUE};
        border-radius: 4px;
    }}

    /* ── Checkbox / Radio ── */
    QCheckBox, QRadioButton {{ color: {TEXT_DIM}; font-size: 12px; }}
    QCheckBox::indicator, QRadioButton::indicator {{
        border: 1px solid {BORDER};
        border-radius: 3px;
        width: 14px; height: 14px;
        background: {BG_PANEL2};
    }}
    QCheckBox::indicator:checked {{
        background: {ACCENT_BLUE};
        border-color: {ACCENT_BLUE};
    }}
    QRadioButton::indicator {{ border-radius: 7px; }}
    QRadioButton::indicator:checked {{
        background: {ACCENT_BLUE};
        border-color: {ACCENT_BLUE};
    }}

    /* ── Toggle Switch (özel QCheckBox) ── */
    QCheckBox#toggleSwitch {{ spacing: 0px; }}
    QCheckBox#toggleSwitch::indicator {{
        width: 36px; height: 20px;
        border-radius: 10px;
        background: {BORDER};
        border: 1px solid {BORDER};
    }}
    QCheckBox#toggleSwitch::indicator:checked {{
        background: {ACCENT_BLUE};
        border: 1px solid {ACCENT_BLUE};
    }}

    /* ── Slider ── */
    QSlider::groove:horizontal {{
        height: 4px;
        background: {BG_PANEL2};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {ACCENT_BLUE};
        width: 14px; height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::sub-page:horizontal {{
        background: {ACCENT_BLUE};
        border-radius: 2px;
    }}

    /* ── Tablo ── */
    QTableWidget, QTableView {{
        background: transparent;
        color: {TEXT_MAIN};
        border: none;
        font-size: 12px;
        gridline-color: {BORDER};
        alternate-background-color: {BG_PANEL2};
        selection-background-color: {ACCENT_BLUE}33;
    }}
    QHeaderView::section {{
        background: transparent;
        color: {TEXT_FAINT};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 6px;
        font-size: 11px;
        font-weight: 600;
    }}
    QTableWidget::item {{
        border-bottom: 1px solid {BORDER};
        padding: 4px;
    }}
    QTableWidget::item:selected {{
        background: {ACCENT_BLUE}33;
        color: {TEXT_MAIN};
    }}

    /* ── Liste Widget ── */
    QListWidget {{
        background: transparent;
        border: none;
        color: {TEXT_MAIN};
    }}
    QListWidget::item {{
        padding: 6px 10px;
        border-radius: 6px;
    }}
    QListWidget::item:hover {{
        background: {BG_PANEL2};
    }}
    QListWidget::item:selected {{
        background: {ACCENT_BLUE}33;
        color: {ACCENT_BLUE};
    }}

    /* ── Scroll Bar ── */
    QScrollBar:vertical {{
        background: {BG_APP};
        width: 8px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{ background: #374151; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar:horizontal {{
        background: {BG_APP};
        height: 8px;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background: {BORDER};
        border-radius: 4px;
        min-width: 24px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}

    /* ── Menü ── */
    QMenuBar {{
        background: {BG_APP};
        color: {TEXT_DIM};
        border-bottom: 1px solid {BORDER};
    }}
    QMenuBar::item:selected {{ background: {BG_PANEL2}; color: {TEXT_MAIN}; }}
    QMenu {{
        background: {BG_PANEL};
        border: 1px solid {BORDER};
        color: {TEXT_MAIN};
        border-radius: 6px;
    }}
    QMenu::item:selected {{ background: {ACCENT_BLUE}33; }}

    /* ── Splitter ── */
    QSplitter::handle {{ background: {BORDER}; }}

    /* ── GroupBox ── */
    QGroupBox {{
        border: 1px solid {BORDER};
        border-radius: 8px;
        margin-top: 8px;
        padding-top: 8px;
        color: {TEXT_DIM};
        font-size: 11px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
        color: {TEXT_DIM};
    }}

    /* ── ToolTip ── */
    QToolTip {{
        background: {BG_PANEL};
        color: {TEXT_MAIN};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 11px;
    }}

    /* ── Dialog ── */
    QDialog {{
        background: {BG_APP};
        color: {TEXT_MAIN};
    }}

    /* ── Tab Widget ── */
    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-radius: 6px;
        background: {BG_PANEL};
    }}
    QTabBar::tab {{
        background: {BG_PANEL2};
        color: {TEXT_DIM};
        padding: 6px 14px;
        border: 1px solid {BORDER};
        border-bottom: none;
        border-radius: 4px 4px 0 0;
    }}
    QTabBar::tab:selected {{
        background: {BG_PANEL};
        color: {TEXT_MAIN};
        border-bottom: 1px solid {BG_PANEL};
    }}
    """


def apply_dark_pro_theme(app: QApplication) -> None:
    """Novel Translator Pro koyu temasını uygulamaya uygular."""
    app.setStyle("Fusion")
    app.setStyleSheet(build_dark_stylesheet())
