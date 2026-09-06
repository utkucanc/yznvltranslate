"""
connection_bar_builder.py — Üst bağlantı çubuğu (MCP / Model / Key Pool / Rotation).

Gerçek veriye bağlantılar:
  - MCP endpoint sayısı: llm_provider.load_endpoints()
  - Aktif model: llm_provider.get_active_endpoint()
  - API key sayısı: AppConfigs/APIKeys/MCP/ ve AppConfigs/APIKeys/
  - Key rotasyonu durumu: aktif endpoint'in use_key_rotation değeri
"""

import os
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.dark_theme import (
    BG_PANEL, BG_PANEL2, BORDER, TEXT_MAIN, TEXT_DIM, TEXT_FAINT,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED, ACCENT_GRAY, FONT_FAMILY
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
        win.conn_model_label      — Aktif model QLabel
        win.conn_keypool_label    — Key pool sayısı QLabel
        win.conn_rotation_label   — Rotation durumu QLabel
        win.conn_rotation_dot     — Rotation durum noktası QLabel
    """
    win = main_window
    bar = QFrame()
    bar.setObjectName("connbar")
    bar.setFixedHeight(72)

    lay = QHBoxLayout(bar)
    lay.setContentsMargins(16, 8, 16, 8)
    lay.setSpacing(20)

    # -- 1. MCP Bağlantısı (Tıklanabilir -> mcp_server_dialog açılır) --
    mcp_row = QHBoxLayout()
    mcp_row.setSpacing(8)
    plug_lbl = QLabel("🔌")
    plug_lbl.setStyleSheet("font-size:16px;")
    mcp_row.addWidget(plug_lbl)

    mcp_info = QVBoxLayout()
    mcp_info.setSpacing(2)
    mcp_title = QLabel("MCP Connection")
    mcp_title.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px; font-weight:600;")
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
    mcp_w.setCursor(Qt.CursorShape.PointingHandCursor)
    mcp_w.setToolTip("Yapay Zeka Kaynağı (MCP) ayarlarını açmak için tıklayın")
    mcp_w.mousePressEvent = lambda event: win.open_mcp_dialog()
    lay.addWidget(mcp_w)
    lay.addWidget(_vline())

    # -- 2. Model Alanı (Salt-okunur, MCP'deki aktif modeli gösterir) --
    rot_active, active_model = _get_active_rotation_and_model(win)
    win.conn_model_label = QLabel(active_model)
    win.conn_model_label.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
    lay.addWidget(_labeled("Active Model", win.conn_model_label))
    lay.addWidget(_vline())

    # -- 3. Key Pool (Butona tıklanınca mcp_server_dialog açılır) --
    key_row = QHBoxLayout()
    key_row.setSpacing(8)
    key_row.addWidget(QLabel("🔑"))

    key_info = QVBoxLayout()
    key_info.setSpacing(2)
    kt = QLabel("Key Pool")
    kt.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px; font-weight:600;")
    key_info.addWidget(kt)

    key_count = _count_api_keys()
    win.conn_keypool_label = QLabel(f"{key_count} Keys Loaded")
    win.conn_keypool_label.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
    key_info.addWidget(win.conn_keypool_label)
    key_row.addLayout(key_info)

    key_pool_btn = QPushButton("⚙️")
    key_pool_btn.setObjectName("iconBtn")
    key_pool_btn.setFixedSize(28, 28)
    key_pool_btn.setToolTip("Key Pool ve MCP Ayarlarını Aç")
    key_pool_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    key_pool_btn.clicked.connect(win.open_mcp_dialog)
    key_row.addWidget(key_pool_btn)

    key_w = QWidget()
    key_w.setLayout(key_row)
    key_w.setCursor(Qt.CursorShape.PointingHandCursor)
    key_w.setToolTip("Key Pool ve MCP Ayarlarını Aç")
    key_w.mousePressEvent = lambda event: win.open_mcp_dialog()
    lay.addWidget(key_w)
    lay.addWidget(_vline())

    # -- 4. Rotation Göstergesi (Aktif / Kapalı dinamik durumu) --
    rot_row = QHBoxLayout()
    rot_row.setSpacing(8)
    rot_row.addWidget(QLabel("⚡"))

    rot_info = QVBoxLayout()
    rot_info.setSpacing(2)
    rt = QLabel("Rotation Status")
    rt.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px; font-weight:600;")
    rot_info.addWidget(rt)

    rot_val_row = QHBoxLayout()
    rot_val_row.setSpacing(6)
    rot_text = "Rotation: Aktif" if rot_active else "Rotation: Kapalı"
    win.conn_rotation_label = QLabel(rot_text)
    win.conn_rotation_label.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
    rot_val_row.addWidget(win.conn_rotation_label)

    win.conn_rotation_dot = QLabel()
    win.conn_rotation_dot.setFixedSize(8, 8)
    dot_color = ACCENT_GREEN if rot_active else ACCENT_RED
    win.conn_rotation_dot.setStyleSheet(f"background:{dot_color}; border-radius:4px;")
    rot_val_row.addWidget(win.conn_rotation_dot)

    rot_info.addLayout(rot_val_row)
    rot_row.addLayout(rot_info)

    rot_w = QWidget()
    rot_w.setLayout(rot_row)
    rot_w.setCursor(Qt.CursorShape.PointingHandCursor)
    rot_w.setToolTip("Rotasyon durumunu değiştirmek için MCP Ayarlarını açın")
    rot_w.mousePressEvent = lambda event: win.open_mcp_dialog()
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
    """API anahtarları sayısını (MCP ve standart APIKeys) döndürür."""
    total = 0
    try:
        keys_dir = os.path.join(os.getcwd(), "AppConfigs", "APIKeys")
        if os.path.exists(keys_dir):
            total += len([f for f in os.listdir(keys_dir) if f.endswith(".txt")])

        mcp_keys_dir = os.path.join(keys_dir, "MCP")
        if os.path.exists(mcp_keys_dir):
            total += len([f for f in os.listdir(mcp_keys_dir) if f.endswith(".txt")])
    except Exception:
        pass
    return total


def _get_active_rotation_and_model(win=None) -> tuple[bool, str]:
    """Aktif MCP endpoint'inin rotasyon durumunu ve model adını döndürür."""
    try:
        from core.llm_provider import get_active_endpoint
        ep = get_active_endpoint()
        if ep:
            rot = ep.get("use_key_rotation", True)
            model = ep.get("model_id") or "gemini-2.5-flash"
            return rot, model
    except Exception:
        pass

    fallback_model = "gemini-2.5-flash"
    if win and hasattr(win, "get_gemini_model_version"):
        fallback_model = win.get_gemini_model_version()
    return True, fallback_model


def _refresh_connection_bar(win) -> None:
    """Bağlantı çubuğu verilerini yeniler."""
    try:
        ep_count = _count_endpoints()
        if hasattr(win, 'conn_mcp_badge'):
            if ep_count > 0:
                win.conn_mcp_badge.setText(f"Connected ({ep_count} endpoint)")
                win.conn_mcp_badge.setStyleSheet(f"""
                    color: {ACCENT_GREEN}; background: {ACCENT_GREEN}22;
                    border: 1px solid {ACCENT_GREEN}55;
                    border-radius: 4px; padding: 2px 8px;
                    font-size: 11px; font-weight: 600;
                """)
            else:
                win.conn_mcp_badge.setText("Not Configured")
                win.conn_mcp_badge.setStyleSheet(f"""
                    color: {ACCENT_ORANGE}; background: {ACCENT_ORANGE}22;
                    border: 1px solid {ACCENT_ORANGE}55;
                    border-radius: 4px; padding: 2px 8px;
                    font-size: 11px; font-weight: 600;
                """)

        key_count = _count_api_keys()
        if hasattr(win, 'conn_keypool_label'):
            win.conn_keypool_label.setText(f"{key_count} Keys Loaded")

        rot_active, active_model = _get_active_rotation_and_model(win)
        if hasattr(win, 'conn_model_label'):
            win.conn_model_label.setText(active_model)

        if hasattr(win, 'conn_rotation_label'):
            win.conn_rotation_label.setText("Rotation: Aktif" if rot_active else "Rotation: Kapalı")

        if hasattr(win, 'conn_rotation_dot'):
            dot_color = ACCENT_GREEN if rot_active else ACCENT_RED
            win.conn_rotation_dot.setStyleSheet(f"background:{dot_color}; border-radius:4px;")

    except Exception as e:
        from logger import app_logger
        app_logger.warning(f"Connection bar yenilenemedi: {e}")
