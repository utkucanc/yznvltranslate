"""
project_page.py — Project sayfası (QStackedWidget index 1).

Sol: Proje listesi (mevcut QListWidget) + istatistik kartları + araç çubuğu
Sağ: Project Details paneli (seçili projenin config.ini'si)
"""

import os
import configparser

from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QProgressBar,
    QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.dark_theme import (
    BG_PANEL, BG_PANEL2, BORDER, TEXT_MAIN, TEXT_DIM, TEXT_FAINT,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_PURPLE,
    ACCENT_RED, ACCENT_CYAN
)
from core.localization import tr

# ------------------------------------------------------------------
# Yardımcılar
# ------------------------------------------------------------------

def _badge(text: str, color: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"""
        color: {color}; background: {color}22;
        border: 1px solid {color}55; border-radius: 4px;
        padding: 2px 8px; font-size: 11px; font-weight: 600;
    """)
    return lbl


def _dot(color: str, size: int = 8) -> QLabel:
    d = QLabel()
    d.setFixedSize(size, size)
    d.setStyleSheet(f"background:{color}; border-radius:{size // 2}px;")
    return d


def _stat_card(title: str, value: str, color: str = None) -> QFrame:
    f = QFrame()
    f.setObjectName("statCard")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(4)
    t = QLabel(title)
    t.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
    v = QLabel(value)
    v.setStyleSheet(f"color:{color or TEXT_MAIN}; font-size:20px; font-weight:700;")
    lay.addWidget(t)
    lay.addWidget(v)
    return f


# ------------------------------------------------------------------
# Ana oluşturucu
# ------------------------------------------------------------------

def build_project_page(main_window) -> QScrollArea:
    """
    Project sayfasını oluşturur.
    Eklenen referanslar:
        win.proj_page_details_frame  — Project Details QFrame (güncellenebilir)
        win.proj_page_total_card     — Toplam proje stat kartı
        win.proj_page_active_card    — Aktif proje stat kartı
        win.proj_page_done_card      — Tamamlanan proje stat kartı
    """
    win = main_window

    outer = QWidget()
    root = QHBoxLayout(outer)
    root.setContentsMargins(14, 14, 14, 14)
    root.setSpacing(14)

    # ── Sol: Liste + araç çubuğu + istatistik + tablo ──
    root.addWidget(_build_project_list_side(win), 3)

    # ── Sağ: Project Details paneli ──
    win.proj_page_details_frame = _build_project_details_panel(win)
    root.addWidget(win.proj_page_details_frame, 1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
    scroll.setWidget(outer)
    return scroll


# ------------------------------------------------------------------
# Sol taraf: Proje listesi
# ------------------------------------------------------------------

def _build_project_list_side(win) -> QWidget:
    container = QWidget()
    lay = QVBoxLayout(container)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(14)

    # Başlık
    t = QLabel("Projects")
    t.setStyleSheet(f"color:{TEXT_MAIN}; font-size:22px; font-weight:700;")
    sub = QLabel("Çeviri projelerinizi yönetin ve organize edin")
    sub.setStyleSheet(f"color:{TEXT_FAINT}; font-size:12px;")
    lay.addWidget(t)
    lay.addWidget(sub)

    # ── Araç çubuğu ──
    toolbar = QHBoxLayout()
    toolbar.setSpacing(8)

    # Mevcut arama input'unu buraya taşı
    if hasattr(win, 'project_search_input'):
        win.project_search_input.setPlaceholderText("🔍  Proje ara...")
        toolbar.addWidget(win.project_search_input, 1)
    if hasattr(win, 'project_search_clear_btn'):
        toolbar.addWidget(win.project_search_clear_btn)

    toolbar.addStretch()

    refresh_btn = QPushButton("⟳  Yenile")
    refresh_btn.setObjectName("smallBtn")
    refresh_btn.clicked.connect(win.load_existing_projects)
    toolbar.addWidget(refresh_btn)

    new_btn = QPushButton("+  Yeni Proje")
    new_btn.setObjectName("primaryBtn")
    new_btn.clicked.connect(win.new_project_clicked)
    toolbar.addWidget(new_btn)

    del_btn = QPushButton("🗑  Sil")
    del_btn.setObjectName("dangerBtn")
    del_btn.clicked.connect(win.delete_project_clicked)
    toolbar.addWidget(del_btn)

    lay.addLayout(toolbar)

    # ── Özet istatistik kartları ──
    stats_row = QHBoxLayout()
    stats_row.setSpacing(10)
    total_count, active_count, done_count = _count_projects()

    win.proj_page_total_card  = _stat_card("Toplam Proje", str(total_count))
    win.proj_page_active_card = _stat_card("Aktif", str(active_count), ACCENT_GREEN)
    win.proj_page_done_card   = _stat_card("Tamamlanan", str(done_count), ACCENT_BLUE)
    stats_row.addWidget(win.proj_page_total_card)
    stats_row.addWidget(win.proj_page_active_card)
    stats_row.addWidget(win.proj_page_done_card)
    stats_row.addStretch()
    lay.addLayout(stats_row)

    # ── Mevcut QListWidget ──
    if hasattr(win, 'project_list'):
        list_card = QFrame()
        list_card.setObjectName("card")
        lc_lay = QVBoxLayout(list_card)
        lc_lay.setContentsMargins(8, 8, 8, 8)
        lc_lay.addWidget(win.project_list)
        # Minimum yükseklik
        win.project_list.setMinimumHeight(300)
        win.project_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        lay.addWidget(list_card, 1)

    return container


# ------------------------------------------------------------------
# Sağ taraf: Project Details paneli
# ------------------------------------------------------------------

def _build_project_details_panel(win) -> QFrame:
    """Seçili projenin detay panelini oluşturur."""
    frame = QFrame()
    frame.setObjectName("card")
    frame.setMinimumWidth(240)
    frame.setMaximumWidth(320)

    _populate_project_details(win, frame)
    return frame


def _populate_project_details(win, frame: QFrame, project_name: str = None):
    """Panel içeriğini temizler ve yeniden doldurur."""
    # Mevcut layout'u temizle
    old_layout = frame.layout()
    if old_layout:
        while old_layout.count():
            item = old_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                sub = item.layout()
                while sub.count():
                    sub_item = sub.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
        try:
            from PyQt6 import sip
            sip.delete(old_layout)
        except Exception:
            pass

    outer = QVBoxLayout(frame)
    outer.setContentsMargins(16, 14, 16, 14)
    outer.setSpacing(10)

    # Başlık
    head_row = QHBoxLayout()
    icon = QLabel("📁")
    icon.setFixedSize(48, 48)
    icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon.setStyleSheet(
        f"background:{ACCENT_BLUE}22; color:{ACCENT_BLUE}; "
        f"font-size:22px; border-radius:8px;"
    )
    head_row.addWidget(icon)
    head_row.addStretch()
    if project_name:
        edit_btn = QPushButton("⚙")
        edit_btn.setStyleSheet(f"font-size:25px")
            
        edit_btn.setObjectName("iconBtn")
        edit_btn.setToolTip("Proje Ayarları")
        edit_btn.clicked.connect(lambda: win.open_project_settings_dialog())
        head_row.addWidget(edit_btn)
    outer.addLayout(head_row)

    if not project_name:
        placeholder = QLabel("Detayları görmek için\nbir proje seçin")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(f"color:{TEXT_FAINT}; font-size:12px;")
        outer.addWidget(placeholder)
        outer.addStretch()
        return

    # Proje adı + badge
    name_row = QHBoxLayout()
    nl = QLabel(project_name)
    nl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:14px; font-weight:700;")
    nl.setWordWrap(True)
    name_row.addWidget(nl, 1)
    name_row.addWidget(_badge("Aktif", ACCENT_GREEN))
    outer.addLayout(name_row)

    # Config verilerini oku
    meta = _read_project_meta(project_name)
    path_lbl = QLabel(meta.get("_path", ""))
    path_lbl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
    path_lbl.setWordWrap(True)
    outer.addWidget(path_lbl)

    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet(f"color:{BORDER};")
    outer.addWidget(sep)

    # Meta satırları
    display_keys = [
        ("link",                 "URL"),
        ("translation_provider", "Sağlayıcı"),
        ("model",                "Model"),
        ("max_retries",          "Max Deneme"),
        ("cache_enabled",        "Cache"),
        ("terminology_enabled",  "Terminoloji"),
        ("async_enabled",        "Async Mod"),
        ("async_threads",        "İş Parçacığı"),
        ("batch_enabled",        "Batch Mod"),
        ("mcp_endpoint_id",      "MCP Endpoint"),
    ]
    for key, label in display_keys:
        val = meta.get(key, "—")
        if not val:
            val = "—"
        row = QHBoxLayout()
        kl = QLabel(label)
        kl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
        vl = QLabel(str(val))
        vl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:11px; font-weight:600;")
        vl.setWordWrap(True)
        row.addWidget(kl)
        row.addStretch()
        row.addWidget(vl)
        outer.addLayout(row)

    # Progress Overview (dosya sayısı)
    prog_title = QLabel("Progress Overview")
    prog_title.setStyleSheet(f"color:{TEXT_MAIN}; font-size:13px; font-weight:700; margin-top:8px;")
    outer.addWidget(prog_title)

    total, done = _count_project_files(project_name)
    pct = int((done / total * 100) if total > 0 else 0)
    pb = QProgressBar()
    pb.setValue(pct)
    pb.setFixedHeight(8)
    pb.setTextVisible(False)
    outer.addWidget(pb)
    prog_lbl = QLabel(f"{pct}%  —  {done} / {total} dosya")
    prog_lbl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
    outer.addWidget(prog_lbl)

    # Recent Activity
    act_title = QLabel("Son Aktivite")
    act_title.setStyleSheet(f"color:{TEXT_MAIN}; font-size:13px; font-weight:700; margin-top:8px;")
    outer.addWidget(act_title)

    recent = _get_recent_files(project_name)
    for fname, mtime in recent[:4]:
        row = QHBoxLayout()
        ic = QLabel("✔")
        ic.setStyleSheet(f"color:{ACCENT_GREEN}; font-size:11px;")
        row.addWidget(ic)
        v = QVBoxLayout()
        v.setSpacing(0)
        t1 = QLabel(fname)
        t1.setStyleSheet(f"color:{TEXT_MAIN}; font-size:11px;")
        t2 = QLabel(mtime)
        t2.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        v.addWidget(t1)
        v.addWidget(t2)
        row.addLayout(v)
        row.addStretch()
        outer.addLayout(row)
    if project_name:
        splitButton = QPushButton(tr("right_panel.btn_split", "✂  Toplu Bölüm Ekle"))
        splitButton.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        splitButton.setObjectName("splitButton")
        splitButton.setCursor(Qt.CursorShape.PointingHandCursor)
        splitButton.clicked.connect(win.start_split_process)
        outer.addWidget(splitButton)
    
    outer.addStretch()


# ------------------------------------------------------------------
# Güncelleme fonksiyonu (main_window'dan çağrılır)
# ------------------------------------------------------------------

def refresh_project_details(win):
    """Proje sayfası detay panelini aktif seçime göre günceller."""
    if not hasattr(win, 'proj_page_details_frame'):
        return
    project_name = None
    if hasattr(win, 'project_list'):
        item = win.project_list.currentItem()
        if item:
            project_name = item.text()
    _populate_project_details(win, win.proj_page_details_frame, project_name)

    # Stat kartlarını güncelle
    total_count, active_count, done_count = _count_projects()
    if hasattr(win, 'proj_page_total_card'):
        _update_stat_value(win.proj_page_total_card, str(total_count))
    if hasattr(win, 'proj_page_active_card'):
        _update_stat_value(win.proj_page_active_card, str(active_count))
    if hasattr(win, 'proj_page_done_card'):
        _update_stat_value(win.proj_page_done_card, str(done_count))


def _update_stat_value(card: QFrame, value: str):
    for child in card.findChildren(QLabel):
        if "20px" in child.styleSheet():
            child.setText(value)
            break


# ------------------------------------------------------------------
# Veri fonksiyonları
# ------------------------------------------------------------------

def _count_projects():
    """Toplam, aktif ve tamamlanan proje sayılarını döndürür."""
    total = active = done = 0
    try:
        base = os.getcwd()
        for name in os.listdir(base):
            cfg = os.path.join(base, name, "config", "config.ini")
            if os.path.isdir(os.path.join(base, name)) and os.path.exists(cfg):
                total += 1
                # Tamamlanma kontrolü
                trslt = os.path.join(base, name, "trslt")
                dwnld = os.path.join(base, name, "dwnld")
                t = len([f for f in os.listdir(trslt) if f.endswith(".txt")]) if os.path.exists(trslt) else 0
                d = len([f for f in os.listdir(dwnld) if f.endswith(".txt")]) if os.path.exists(dwnld) else 0
                if d > 0 and t >= d:
                    done += 1
                elif d > 0:
                    active += 1
    except Exception:
        pass
    return total, active, done


def _read_project_meta(project_name: str) -> dict:
    """Proje config.ini'sini okuyarak meta sözlüğü döndürür."""
    result = {}
    try:
        base = os.getcwd()
        project_path = os.path.join(base, project_name)
        result["_path"] = project_path
        cfg_path = os.path.join(project_path, "config", "config.ini")
        if not os.path.exists(cfg_path):
            return result
        cfg = configparser.ConfigParser()
        cfg.read(cfg_path, encoding="utf-8")
        result["link"]                 = cfg.get("ProjectInfo", "link", fallback="—")
        result["max_retries"]          = cfg.get("ProjectInfo", "max_retries", fallback="3")
        result["model"]                = _read_global_model()
        result["translation_provider"] = cfg.get("API", "translation_provider", fallback="llm")
        result["cache_enabled"]        = cfg.get("Features", "cache_enabled", fallback="False")
        result["terminology_enabled"]  = cfg.get("Features", "terminology_enabled", fallback="True")
        result["async_enabled"]        = cfg.get("Features", "async_enabled", fallback="False")
        result["async_threads"]        = cfg.get("Features", "async_threads", fallback="3")
        result["batch_enabled"]        = cfg.get("Batch", "batch_enabled", fallback="False")
        result["mcp_endpoint_id"]      = cfg.get("MCP", "endpoint_id", fallback="—")
    except Exception:
        pass
    return result


def _read_global_model() -> str:
    cfg_path = os.path.join(os.getcwd(), "AppConfigs", "GVersion.ini")
    cfg = configparser.ConfigParser()
    if os.path.exists(cfg_path):
        cfg.read(cfg_path)
        return cfg.get("Version", "model_name", fallback="gemini-2.5-flash")
    return "gemini-2.5-flash"


def _count_project_files(project_name: str):
    """(total_dwnld, done_trslt) dosya sayılarını döndürür."""
    try:
        base = os.path.join(os.getcwd(), project_name)
        dwnld = os.path.join(base, "dwnld")
        trslt = os.path.join(base, "trslt")
        total = len([f for f in os.listdir(dwnld) if f.endswith(".txt")]) if os.path.exists(dwnld) else 0
        done  = len([f for f in os.listdir(trslt) if f.endswith(".txt")]) if os.path.exists(trslt) else 0
        return total, done
    except Exception:
        return 0, 0


def _get_recent_files(project_name: str, n: int = 4):
    """Son n çevirilen dosyanın (ad, tarih) listesini döndürür."""
    import datetime
    result = []
    try:
        trslt = os.path.join(os.getcwd(), project_name, "trslt")
        if not os.path.exists(trslt):
            return result
        files = [(f, os.path.getmtime(os.path.join(trslt, f)))
                 for f in os.listdir(trslt) if f.endswith(".txt")]
        files.sort(key=lambda x: x[1], reverse=True)
        for fname, mtime in files[:n]:
            dt = datetime.datetime.fromtimestamp(mtime).strftime("%d %b %Y %H:%M")
            result.append((fname, dt))
    except Exception:
        pass
    return result
