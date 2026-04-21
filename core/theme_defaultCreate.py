"""
theme_defaultCreate.py — Varsayılan tema dosyalarını oluşturucu.

Build alındığında AppConfigs/themes/ klasöründeki dosyalar kullanıcı dizininde
bulunmayabilir. Bu modül uygulama başlangıcında eksik tema dosyalarını oluşturur.

Kullanım:
    from core.theme_defaultCreate import ensure_default_themes
    ensure_default_themes()
"""

import os
import json
from logger import app_logger

# ═══════════════════════════════════════════════════════
# DEFAULT DARK.QSS İÇERİĞİ
# ═══════════════════════════════════════════════════════
_DARK_QSS = r"""/* ==============================================================
   dark.qss — Premium Karanlık Mod Override Katmanı
   Novel Çeviri Aracı V2.4.0
   qt-material (dark_teal) base + proje spesifik overrides
   ============================================================== */

/* ── Temel Widget Stilleri ── */
QWidget {
    font-family: "Segoe UI Variable", "Segoe UI", "Inter", Arial, sans-serif;
    font-size: 9pt;
    letter-spacing: 0.01em;
}

/* ── Ana Pencere Arka Planı ── */
QMainWindow {
    background-color: #1E1E2E;
}

QDialog {
    background-color: #1E1E2E;
    color: #CDD6F4;
}

/* ── Genel QPushButton — KOMPAKT ── */
QPushButton {
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 9pt;
    font-weight: 500;
    letter-spacing: 0.02em;
    min-height: 14px;
    max-height: 28px;
}

QPushButton:disabled {
    opacity: 0.45;
}

QPushButton[class="btn-success"] { background-color: #2E7D32; color: #ffffff; border: none; }
QPushButton[class="btn-success"]:hover { background-color: #388E3C; }
QPushButton[class="btn-success"]:pressed { background-color: #1B5E20; }

QPushButton[class="btn-primary"] { background-color: #283593; color: #ffffff; border: none; }
QPushButton[class="btn-primary"]:hover { background-color: #303F9F; }
QPushButton[class="btn-primary"]:pressed { background-color: #1A237E; }

QPushButton[class="btn-info"] { background-color: #0D47A1; color: #ffffff; border: none; }
QPushButton[class="btn-info"]:hover { background-color: #1565C0; }
QPushButton[class="btn-info"]:pressed { background-color: #0A2F6B; }

QPushButton[class="btn-stop"] { background-color: #B71C1C; color: #ffffff; border: none; }
QPushButton[class="btn-stop"]:hover { background-color: #C62828; }
QPushButton[class="btn-stop"]:pressed { background-color: #7F0000; }

QPushButton[class="btn-purple"] { background-color: #6A1B9A; color: #ffffff; border: none; }
QPushButton[class="btn-purple"]:hover { background-color: #7B1FA2; }
QPushButton[class="btn-purple"]:pressed { background-color: #4A148C; }

QPushButton[class="btn-teal"] { background-color: #00695C; color: #ffffff; border: none; }
QPushButton[class="btn-teal"]:hover { background-color: #00796B; }
QPushButton[class="btn-teal"]:pressed { background-color: #004D40; }

QPushButton[class="btn-brown"] { background-color: #4E342E; color: #ffffff; border: none; }
QPushButton[class="btn-brown"]:hover { background-color: #5D4037; }
QPushButton[class="btn-brown"]:pressed { background-color: #3E2723; }

QPushButton[class="btn-deep-purple"] { background-color: #4527A0; color: #ffffff; border: none; }
QPushButton[class="btn-deep-purple"]:hover { background-color: #512DA8; }
QPushButton[class="btn-deep-purple"]:pressed { background-color: #311B92; }

QPushButton[class="btn-pink"] { background-color: #880E4F; color: #ffffff; border: none; }
QPushButton[class="btn-pink"]:hover { background-color: #AD1457; }
QPushButton[class="btn-pink"]:pressed { background-color: #560027; }

QPushButton[class="btn-steel"] { background-color: #37474F; color: #ffffff; border: none; }
QPushButton[class="btn-steel"]:hover { background-color: #455A64; }

QPushButton[class="btn-ocean"] { background-color: #01579B; color: #ffffff; border: none; }
QPushButton[class="btn-ocean"]:hover { background-color: #0277BD; }

QPushButton[class="btn-clear"] {
    background-color: transparent;
    color: #6C7086;
    border: 1px solid #45475A;
    border-radius: 4px;
    padding: 2px 5px;
    font-size: 8pt;
    max-width: 22px; min-width: 22px;
    max-height: 22px; min-height: 22px;
}
QPushButton[class="btn-clear"]:hover {
    background-color: #313244;
    color: #F38BA8;
    border-color: #F38BA8;
}

/* ── Input Alanları ── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #181825;
    color: #CDD6F4;
    border: 1px solid #45475A;
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 9pt;
    selection-background-color: #89B4FA;
    selection-color: #1E1E2E;
}

QLineEdit { min-height: 14px; max-height: 28px; }
QTextEdit, QPlainTextEdit { min-height: 60px; }

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #89B4FA;
    background-color: #1A1A2C;
}

/* ── Tablo ── */
QTableWidget {
    background-color: #181825;
    color: #CDD6F4;
    gridline-color: #2A2A3E;
    border: 1px solid #313244;
    border-radius: 5px;
    selection-background-color: #2D2D3F;
    alternate-background-color: #1E1E30;
    font-size: 10pt;
}
QTableWidget::item { padding: 3px 5px; }
QTableWidget::item:selected, QTableWidget::item:selected:focus {
    background-color: #3A3A55; color: #CDD6F4;
}

QHeaderView::section {
    background-color: #252537; color: #89B4FA;
    border: none; border-bottom: 2px solid #45475A;
    padding: 4px 6px; font-weight: 600; font-size: 8pt; letter-spacing: 0.02em;
}
QHeaderView { font-size: 8pt; }

/* ── Liste ── */
QListWidget {
    background-color: #181825; color: #CDD6F4;
    border: 1px solid #313244; border-radius: 4px;
    outline: none; font-size: 10pt;
}
QListWidget::item { padding: 4px 7px; border-radius: 2px; }
QListWidget::item:selected, QListWidget::item:selected:focus {
    background-color: #3A3A55; color: #89DCEB;
}
QListWidget::item:hover { background-color: #2A2A40; }

/* ── ComboBox ── */
QComboBox {
    background-color: #252537; color: #CDD6F4;
    border: 1px solid #45475A; border-radius: 4px;
    padding: 3px 8px; font-size: 9pt;
    min-height: 14px; max-height: 26px;
}
QComboBox:hover { border-color: #89B4FA; background-color: #2D2D45; }
QComboBox:focus { border-color: #89B4FA; }
QComboBox::drop-down { border: none; width: 18px; }

QComboBox QAbstractItemView {
    background-color: #1E1E2E; color: #CDD6F4;
    border: 1px solid #45475A;
    selection-background-color: #3A3A55;
    selection-color: #89DCEB;
    outline: none; font-size: 9pt;
}
QComboBox::item:selected,
QComboBox QAbstractItemView::item:selected,
QComboBox QListView::item:selected,
QComboBox QListView::item:selected:focus,
QComboBox QAbstractItemView::item:hover {
    background-color: #3A3A55; color: #89DCEB;
}
QComboBox QAbstractItemView::item {
    background-color: #1E1E2E; color: #CDD6F4; padding: 4px 8px;
}

/* ── Progress Bar ── */
QProgressBar {
    background-color: #181830; border: none; border-radius: 5px;
    text-align: center; font-size: 7pt; font-weight: 600;
    color: #CDD6F4; min-height: 10px; max-height: 10px;
}
QProgressBar::chunk {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0.0 #48CAE4, stop: 0.4 #89B4FA,
        stop: 0.8 #CBA6F7, stop: 1.0 #F38BA8
    );
    border-radius: 5px;
}

/* ── ScrollBar ── */
QScrollBar:vertical { background-color: #111120; width: 6px; border-radius: 3px; margin: 0; }
QScrollBar::handle:vertical { background-color: #45475A; border-radius: 3px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background-color: #89B4FA; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; background: none; }
QScrollBar:horizontal { background-color: #111120; height: 6px; border-radius: 3px; margin: 0; }
QScrollBar::handle:horizontal { background-color: #45475A; border-radius: 3px; min-width: 20px; }
QScrollBar::handle:horizontal:hover { background-color: #89B4FA; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; background: none; }

/* ── Tab Widget ── */
QTabWidget::pane { border: 1px solid #313244; border-radius: 5px; background-color: #1E1E2E; top: -1px; }
QTabBar::tab { background-color: #252537; color: #A6ADC8; padding: 5px 14px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; font-size: 8pt; }
QTabBar::tab:selected { background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #89B4FA, stop: 1 #74C7EC); color: #1E1E2E; font-weight: 700; }
QTabBar::tab:hover:!selected { background-color: #313244; color: #CDD6F4; }

/* ── GroupBox ── */
QGroupBox { border: 1px solid #313244; border-radius: 6px; margin-top: 8px; padding: 8px 6px 6px 6px; font-size: 8pt; }
QGroupBox::title { color: #89B4FA; subcontrol-origin: margin; left: 8px; padding: 0 3px; font-weight: 600; }

/* ── MenuBar ── */
QMenuBar { background-color: #11111B; color: #CDD6F4; border-bottom: 1px solid #1E1E2E; padding: 1px; font-size: 9pt; }
QMenuBar::item { padding: 3px 8px; border-radius: 3px; }
QMenuBar::item:selected { background-color: #313244; color: #89B4FA; }

QMenu { background-color: #1E1E2E; color: #CDD6F4; border: 1px solid #45475A; border-radius: 5px; padding: 3px; font-size: 9pt; }
QMenu::item { padding: 4px 22px 4px 10px; border-radius: 3px; }
QMenu::item:selected { background-color: #313244; color: #89B4FA; }
QMenu::separator { height: 1px; background-color: #313244; margin: 3px 6px; }

/* ── Label ── */
QLabel { color: #CDD6F4; font-size: 9pt; }

/* ── Checkbox ── */
QCheckBox { color: #CDD6F4; spacing: 5px; font-size: 9pt; }
QCheckBox::indicator { width: 13px; height: 13px; border: 1px solid #45475A; border-radius: 2px; background-color: #252537; }
QCheckBox::indicator:hover { border-color: #89B4FA; }
QCheckBox::indicator:checked { background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #89B4FA, stop: 1 #74C7EC); border-color: #89B4FA; }

/* ── SpinBox ── */
QSpinBox { background-color: #252537; color: #CDD6F4; border: 1px solid #45475A; border-radius: 4px; padding: 2px 6px; font-size: 9pt; min-height: 14px; max-height: 26px; }
QSpinBox:hover { border-color: #89B4FA; }
QSpinBox:focus { border-color: #89B4FA; background-color: #1A1A2C; }

/* ── QDialogButtonBox ── */
QDialogButtonBox QPushButton { min-width: 70px; padding: 4px 14px; }

/* ── Status Bar ── */
QStatusBar { background-color: #11111B; color: #A6ADC8; border-top: 1px solid #252537; padding: 1px 6px; font-size: 8pt; }
QStatusBar::item { border: none; }

/* ── ScrollArea ── */
QScrollArea { border: none; background-color: transparent; }
QScrollArea > QWidget > QWidget { background-color: transparent; }
"""

# ═══════════════════════════════════════════════════════
# DEFAULT LIGHT.QSS İÇERİĞİ
# ═══════════════════════════════════════════════════════
_LIGHT_QSS = r"""/* ==============================================================
   light.qss — Premium Aydınlık Mod Override Katmanı
   Novel Çeviri Aracı V2.4.0
   qt-material (light_blue) base + proje spesifik overrides
   ============================================================== */

QWidget { font-family: "Segoe UI Variable", "Segoe UI", "Inter", Arial, sans-serif; font-size: 9pt; letter-spacing: 0.01em; }
QMainWindow { background-color: #F5F5F9; }
QDialog { background-color: #F5F5F9; color: #2C2C3A; }

QPushButton { border-radius: 5px; padding: 4px 10px; font-size: 9pt; font-weight: 500; letter-spacing: 0.02em; min-height: 14px; max-height: 28px; }
QPushButton:disabled { opacity: 0.45; }

QPushButton[class="btn-success"] { background-color: #388E3C; color: #fff; border: none; }
QPushButton[class="btn-success"]:hover { background-color: #43A047; }
QPushButton[class="btn-success"]:pressed { background-color: #2E7D32; }

QPushButton[class="btn-primary"] { background-color: #3949AB; color: #fff; border: none; }
QPushButton[class="btn-primary"]:hover { background-color: #3F51B5; }

QPushButton[class="btn-info"] { background-color: #1565C0; color: #fff; border: none; }
QPushButton[class="btn-info"]:hover { background-color: #1976D2; }

QPushButton[class="btn-stop"] { background-color: #C62828; color: #fff; border: none; }
QPushButton[class="btn-stop"]:hover { background-color: #D32F2F; }

QPushButton[class="btn-purple"] { background-color: #7B1FA2; color: #fff; border: none; }
QPushButton[class="btn-purple"]:hover { background-color: #8E24AA; }

QPushButton[class="btn-teal"] { background-color: #00796B; color: #fff; border: none; }
QPushButton[class="btn-teal"]:hover { background-color: #00897B; }

QPushButton[class="btn-brown"] { background-color: #5D4037; color: #fff; border: none; }
QPushButton[class="btn-brown"]:hover { background-color: #6D4C41; }

QPushButton[class="btn-deep-purple"] { background-color: #512DA8; color: #fff; border: none; }
QPushButton[class="btn-deep-purple"]:hover { background-color: #5E35B1; }

QPushButton[class="btn-pink"] { background-color: #AD1457; color: #fff; border: none; }
QPushButton[class="btn-pink"]:hover { background-color: #C2185B; }

QPushButton[class="btn-steel"] { background-color: #546E7A; color: #fff; border: none; }
QPushButton[class="btn-steel"]:hover { background-color: #607D8B; }

QPushButton[class="btn-ocean"] { background-color: #0277BD; color: #fff; border: none; }
QPushButton[class="btn-ocean"]:hover { background-color: #0288D1; }

QPushButton[class="btn-clear"] { background-color: transparent; color: #9E9E9E; border: 1px solid #C5C7D2; border-radius: 4px; padding: 2px 5px; font-size: 8pt; max-width: 22px; min-width: 22px; max-height: 22px; min-height: 22px; }
QPushButton[class="btn-clear"]:hover { background-color: #FFEBEE; color: #C62828; border-color: #C62828; }

QLineEdit, QTextEdit, QPlainTextEdit { background-color: #FFFFFF; color: #2C2C3A; border: 1px solid #C5C7D2; border-radius: 4px; padding: 3px 6px; font-size: 9pt; selection-background-color: #1565C0; selection-color: #FFFFFF; }
QLineEdit { min-height: 14px; max-height: 28px; }
QTextEdit, QPlainTextEdit { min-height: 60px; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border: 1px solid #1565C0; background-color: #FAFAFE; }

QTableWidget { background-color: #FFFFFF; color: #2C2C3A; gridline-color: #E8E8F0; border: 1px solid #D0D0DC; border-radius: 5px; font-size: 10pt; }
QTableWidget::item { padding: 3px 5px; }
QTableWidget::item:selected, QTableWidget::item:selected:focus { background-color: #DDEEFF; color: #0D47A1; }
QHeaderView::section { background-color: #EEEEF8; color: #1565C0; border: none; border-bottom: 2px solid #C5C7D2; padding: 4px 6px; font-weight: 600; font-size: 8pt; }
QHeaderView { font-size: 8pt; }

QListWidget { background-color: #FFFFFF; color: #2C2C3A; border: 1px solid #D0D0DC; border-radius: 4px; outline: none; font-size: 10pt; }
QListWidget::item { padding: 4px 7px; border-radius: 2px; }
QListWidget::item:selected, QListWidget::item:selected:focus { background-color: #DDEEFF; color: #0D47A1; }
QListWidget::item:hover { background-color: #EEF2FF; }

QComboBox { background-color: #FFFFFF; color: #2C2C3A; border: 1px solid #C5C7D2; border-radius: 4px; padding: 3px 8px; font-size: 9pt; min-height: 14px; max-height: 26px; }
QComboBox:hover { border-color: #1565C0; }
QComboBox QAbstractItemView { background-color: #FFFFFF; color: #2C2C3A; border: 1px solid #C5C7D2; selection-background-color: #DDEEFF; selection-color: #0D47A1; outline: none; font-size: 9pt; }
QComboBox::item:selected, QComboBox QAbstractItemView::item:selected, QComboBox QListView::item:selected, QComboBox QListView::item:selected:focus, QComboBox QAbstractItemView::item:hover { background-color: #DDEEFF; color: #0D47A1; }
QComboBox QAbstractItemView::item { background-color: #FFFFFF; color: #2C2C3A; padding: 4px 8px; }

QProgressBar { background-color: #E8E8F4; border: none; border-radius: 5px; font-size: 7pt; font-weight: 600; color: #2C2C3A; min-height: 10px; max-height: 10px; }
QProgressBar::chunk { background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0.0 #1976D2, stop: 0.5 #7E57C2, stop: 1.0 #EC407A); border-radius: 5px; }

QScrollBar:vertical { background-color: #F0F0F8; width: 6px; border-radius: 3px; margin: 0; }
QScrollBar::handle:vertical { background-color: #C5C7D2; border-radius: 3px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background-color: #1565C0; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; background: none; }
QScrollBar:horizontal { background-color: #F0F0F8; height: 6px; border-radius: 3px; margin: 0; }
QScrollBar::handle:horizontal { background-color: #C5C7D2; border-radius: 3px; min-width: 20px; }
QScrollBar::handle:horizontal:hover { background-color: #1565C0; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; background: none; }

QTabWidget::pane { border: 1px solid #D0D0DC; border-radius: 5px; background-color: #F5F5F9; top: -1px; }
QTabBar::tab { background-color: #E8E8F0; color: #6C6F85; padding: 5px 14px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; font-size: 8pt; }
QTabBar::tab:selected { background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #1565C0, stop: 1 #1976D2); color: #FFFFFF; font-weight: 700; }
QTabBar::tab:hover:!selected { background-color: #D8D8E8; color: #2C2C3A; }

QGroupBox { border: 1px solid #D0D0DC; border-radius: 6px; margin-top: 8px; padding: 8px 6px 6px 6px; font-size: 8pt; background-color: #F9F9FD; }
QGroupBox::title { color: #1565C0; subcontrol-origin: margin; left: 8px; padding: 0 3px; font-weight: 600; }

QMenuBar { background-color: #EEEEF8; color: #2C2C3A; border-bottom: 1px solid #D0D0DC; padding: 1px; font-size: 9pt; }
QMenuBar::item { padding: 3px 8px; border-radius: 3px; }
QMenuBar::item:selected { background-color: #DDEEFF; color: #1565C0; }

QMenu { background-color: #FFFFFF; color: #2C2C3A; border: 1px solid #D0D0DC; border-radius: 5px; padding: 3px; font-size: 9pt; }
QMenu::item { padding: 4px 22px 4px 10px; border-radius: 3px; }
QMenu::item:selected { background-color: #DDEEFF; color: #1565C0; }
QMenu::separator { height: 1px; background-color: #E0E0EC; margin: 3px 6px; }

QLabel { color: #2C2C3A; font-size: 9pt; }

QCheckBox { color: #2C2C3A; spacing: 5px; font-size: 9pt; }
QCheckBox::indicator { width: 13px; height: 13px; border: 1px solid #C5C7D2; border-radius: 2px; background-color: #FFFFFF; }
QCheckBox::indicator:hover { border-color: #1565C0; }
QCheckBox::indicator:checked { background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #1565C0, stop: 1 #1976D2); border-color: #1565C0; }

QSpinBox { background-color: #FFFFFF; color: #2C2C3A; border: 1px solid #C5C7D2; border-radius: 4px; padding: 2px 6px; font-size: 9pt; min-height: 14px; max-height: 26px; }
QSpinBox:hover { border-color: #1565C0; }
QSpinBox:focus { border-color: #1565C0; }

QDialogButtonBox QPushButton { min-width: 70px; padding: 4px 14px; }

QStatusBar { background-color: #EEEEF8; color: #6C6F85; border-top: 1px solid #D0D0DC; padding: 1px 6px; font-size: 8pt; }
QStatusBar::item { border: none; }

QScrollArea { border: none; background-color: transparent; }
QScrollArea > QWidget > QWidget { background-color: transparent; }
"""

# ═══════════════════════════════════════════════════════
# DEFAULT THEMES_META.JSON İÇERİĞİ
# ═══════════════════════════════════════════════════════
_THEMES_META = {
    "themes": {}
}

# ═══════════════════════════════════════════════════════
# DEFAULT SYSTEM.JSON İÇERİĞİ (boş tema token dosyası)
# ═══════════════════════════════════════════════════════
_SYSTEM_JSON = {
    "base": "dark",
    "label": "System",
    "tokens": {}
}


def ensure_default_themes(base_path: str = None) -> None:
    """
    AppConfigs/themes/ klasöründe eksik olan varsayılan tema dosyalarını oluşturur.

    Oluşturulan dosyalar:
    - dark.qss
    - light.qss
    - themes_meta.json
    - system.json

    Args:
        base_path: Uygulamanın çalıştığı kök dizin. None ise os.getcwd() kullanılır.
    """
    if base_path is None:
        base_path = os.getcwd()

    themes_dir = os.path.join(base_path, "AppConfigs", "themes")

    try:
        os.makedirs(themes_dir, exist_ok=True)
    except Exception as e:
        app_logger.error(f"Tema klasörü oluşturulamadı: {e}")
        return

    # dark.qss
    _write_if_missing(themes_dir, "dark.qss", _DARK_QSS, encoding="utf-8")

    # light.qss
    _write_if_missing(themes_dir, "light.qss", _LIGHT_QSS, encoding="utf-8")

    # themes_meta.json
    meta_path = os.path.join(themes_dir, "themes_meta.json")
    if not os.path.exists(meta_path):
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(_THEMES_META, f, indent=2, ensure_ascii=False)
            app_logger.info("Tema metadata dosyası oluşturuldu: themes_meta.json")
        except Exception as e:
            app_logger.error(f"themes_meta.json oluşturulamadı: {e}")

    # system.json
    system_path = os.path.join(themes_dir, "system.json")
    if not os.path.exists(system_path):
        try:
            with open(system_path, "w", encoding="utf-8") as f:
                json.dump(_SYSTEM_JSON, f, indent=2, ensure_ascii=False)
            app_logger.info("Sistem tema JSON dosyası oluşturuldu: system.json")
        except Exception as e:
            app_logger.error(f"system.json oluşturulamadı: {e}")


def _write_if_missing(directory: str, filename: str, content: str, encoding: str = "utf-8") -> None:
    """Dosya mevcut değilse yazar, mevcutsa dokunmaz."""
    path = os.path.join(directory, filename)
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
            app_logger.info(f"Varsayılan tema dosyası oluşturuldu: {filename}")
        except Exception as e:
            app_logger.error(f"{filename} oluşturulamadı: {e}")
