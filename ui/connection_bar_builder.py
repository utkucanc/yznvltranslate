"""
connection_bar_builder.py — Üst bağlantı çubuğu (MCP / Provider / Model / Key Pool).

Gerçek veriye bağlantılar:
  - MCP endpoint sayısı: llm_provider.load_endpoints()
  - API key sayısı: AppConfigs/APIKeys/ klasöründeki .txt dosyaları
  - Aktif model: GVersion.ini
  - Aktif provider: projenin config.ini'si (project seçiliyse)
"""

import os
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.dark_theme import (
    BG_PANEL, BG_PANEL2, BORDER, TEXT_MAIN, TEXT_DIM, TEXT_FAINT,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, FONT_FAMILY
)


def _labeled(label_text: str, widget: QWidget) -> QWidget:
    """Etiket + widget'ı dikey olarak saran yardımcı."""
    box = QVBoxLayout()
    box.setSpacing(2)
    box.setContentsMargins(0, 0, 0, 0)
    lbl = QLabel(label_text)
    lbl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
    box.addWidget(lbl)
    box.addWidget(widget)
    wrap = QWidget()
    wrap.setLayout(box)
    return wrap


def _vline() -> QFrame:
    v = QFrame()
    v.setFrameShape(QFrame.Shape.VLine)
    v.setStyleSheet(f"color: {BORDER}; max-height: 40px;")
    return v


def _badge(text: str, color: str) -> QLabel:
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


def build_connection_bar(main_window) -> QFrame:
    """
    Üst bağlantı çubuğunu oluşturur ve main_window'a widget referansları ekler.

    Eklenen referanslar:
        win.conn_mcp_badge        — MCP bağlantı durumu etiketi
        win.conn_provider_combo   — Provider QComboBox
        win.conn_model_label      — Aktif model QLabel
        win.conn_keypool_label    — Key pool sayısı QLabel
        win.conn_rotation_label   — Rotation durumu QLabel
    """
    win = main_window
    bar = QFrame()
    bar.setObjectName("connbar")
    bar.setFixedHeight(72)

    lay = QHBoxLayout(bar)
    lay.setContentsMargins(16, 8, 16, 8)
    lay.setSpacing(20)

    # -- MCP Bağlantısı ----------------------------------------------
    mcp_row = QHBoxLayout()
    mcp_row.setSpacing(8)
    plug_lbl = QLabel("🔌")
    plug_lbl.setStyleSheet(f"font-size:16px;")
    mcp_row.addWidget(plug_lbl)

    mcp_info = QVBoxLayout()
    mcp_info.setSpacing(2)
    mcp_title = QLabel("MCP Connection")
    mcp_title.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
    mcp_info.addWidget(mcp_title)

    # Gerçek bağlantı sayısını oku
    ep_count = _count_endpoints()
    if ep_count > 0:
        win.conn_mcp_badge = _badge(f"Connected ({ep_count} endpoint)", ACCENT_GREEN)
    else:
        win.conn_mcp_badge = _badge("Not Configured", ACCENT_ORANGE)
    mcp_info.addWidget(win.conn_mcp_badge)
    mcp_row.addLayout(mcp_info)

    mcp_w = QWidget()
    mcp_w.setLayout(mcp_row)
    lay.addWidget(mcp_w)
    lay.addWidget(_vline())

    # -- Provider --------------------------------------------------
    win.conn_provider_combo = QComboBox()
    win.conn_provider_combo.addItem("✨ Google Gemini", "gemini")
    win.conn_provider_combo.addItem("OpenAI", "openai")
    win.conn_provider_combo.addItem("Anthropic Claude", "claude")
    win.conn_provider_combo.addItem("DeepSeek", "deepseek")
    win.conn_provider_combo.setFixedWidth(160)
    lay.addWidget(_labeled("Provider", win.conn_provider_combo))

    # -- Model ------------------------------------------------------
    current_model = win.get_gemini_model_version() if hasattr(win, 'get_gemini_model_version') else "gemini-2.5-flash"
    win.conn_model_label = QLabel(current_model)
    win.conn_model_label.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
    lay.addWidget(_labeled("Active Model", win.conn_model_label))
    lay.addWidget(_vline())

    # -- Key Pool --------------------------------------------------
    key_row = QHBoxLayout()
    key_row.setSpacing(8)
    key_row.addWidget(QLabel("🔑"))

    key_info = QVBoxLayout()
    key_info.setSpacing(2)
    kt = QLabel("Key Pool")
    kt.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
    key_info.addWidget(kt)

    key_count = _count_api_keys()
    win.conn_keypool_label = QLabel(f"{key_count} Keys Loaded")
    win.conn_keypool_label.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
    key_info.addWidget(win.conn_keypool_label)
    key_row.addLayout(key_info)

    refresh_btn = QPushButton("⟳")
    refresh_btn.setObjectName("iconBtn")
    refresh_btn.setFixedSize(28, 28)
    refresh_btn.setToolTip("Key Pool'u yenile")
    refresh_btn.clicked.connect(lambda: _refresh_connection_bar(win))
    key_row.addWidget(refresh_btn)
    key_w = QWidget()
    key_w.setLayout(key_row)
    lay.addWidget(key_w)

    # -- Rotation --------------------------------------------------
    rot_row = QHBoxLayout()
    rot_row.setSpacing(8)
    rot_row.addWidget(QLabel("⚡"))

    rot_info = QVBoxLayout()
    rot_info.setSpacing(2)
    rt = QLabel("Rotating")
    rt.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
    rot_info.addWidget(rt)

    rot_val_row = QHBoxLayout()
    rot_val_row.setSpacing(6)
    win.conn_rotation_label = QLabel("Auto (Round Robin)")
    win.conn_rotation_label.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
    rot_val_row.addWidget(win.conn_rotation_label)
    dot = QLabel()
    dot.setFixedSize(8, 8)
    dot.setStyleSheet(f"background:{ACCENT_GREEN}; border-radius:4px;")
    rot_val_row.addWidget(dot)
    rot_info.addLayout(rot_val_row)
    rot_row.addLayout(rot_info)
    rot_w = QWidget()
    rot_w.setLayout(rot_row)
    lay.addWidget(rot_w)

    lay.addStretch()
    return bar


# ------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ------------------------------------------------------------------

def _count_endpoints() -> int:
    """Yapılandırılmış MCP endpoint sayısını döndürür."""
    try:
        from core.llm_provider import load_endpoints
        data = load_endpoints()
        return len(data.get("endpoints", []))
    except Exception:
        return 0


def _count_api_keys() -> int:
    """AppConfigs/APIKeys/ klasöründeki .txt dosya sayısını döndürür."""
    try:
        keys_dir = os.path.join(os.getcwd(), "AppConfigs", "APIKeys")
        if os.path.exists(keys_dir):
            return len([f for f in os.listdir(keys_dir) if f.endswith(".txt")])
    except Exception:
        pass
    return 0


def _refresh_connection_bar(win) -> None:
    """Bağlantı çubuğu verilerini yeniler."""
    try:
        ep_count = _count_endpoints()
        if ep_count > 0:
            win.conn_mcp_badge.setText(f"Connected ({ep_count} endpoint)")
            win.conn_mcp_badge.setStyleSheet(f"""
                color: #22c55e; background: #22c55e22;
                border: 1px solid #22c55e55;
                border-radius: 4px; padding: 2px 8px;
                font-size: 11px; font-weight: 600;
            """)
        else:
            win.conn_mcp_badge.setText("Not Configured")
        key_count = _count_api_keys()
        win.conn_keypool_label.setText(f"{key_count} Keys Loaded")
        if hasattr(win, 'get_gemini_model_version'):
            win.conn_model_label.setText(win.get_gemini_model_version())
    except Exception as e:
        from logger import app_logger
        app_logger.warning(f"Connection bar yenilenemedi: {e}")
