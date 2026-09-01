"""
dashboard_page.py — Dashboard sayfası (QStackedWidget index 0).

Kartlar:
  1. Project Files  — mevcut file_table (QTableWidget) + arama
  2. Translation Queue — progressBar, statusLabel, translateButton, stopButton
  3. Statistics Overview — request_counter_manager + matplotlib grafiği
  4. Logs — app_logger → QTextEdit
  5. Merge / Export — mergeButton, epubButton
  6. Terminology — generateTerminologyButton + terim sayısı

Önemli: Bu modül mevcut widget referanslarını (self.xxx) yeniden
OLUŞTURMAZ; mevcut main_window attribute'larını düzenler ve kartlara yerleştirir.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QProgressBar,
    QTextEdit, QCheckBox, QSpinBox, QRadioButton, QButtonGroup,
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
# Yardımcı bileşenler
# ------------------------------------------------------------------

def _card(title: str = None, extra_widget: QWidget = None, obj: str = "card"):
    """Başlıklı kart QFrame + body QVBoxLayout döndürür."""
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
        if extra_widget:
            header.addWidget(extra_widget)
        outer.addLayout(header)

    body = QVBoxLayout()
    body.setSpacing(8)
    outer.addLayout(body)
    return frame, body


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


def _dot(color: str, size: int = 8) -> QLabel:
    d = QLabel()
    d.setFixedSize(size, size)
    d.setStyleSheet(f"background:{color}; border-radius:{size // 2}px;")
    return d


# ------------------------------------------------------------------
# Ana oluşturucu
# ------------------------------------------------------------------

def build_dashboard_page(main_window) -> QScrollArea:
    """
    Dashboard sayfasını oluşturur.
    main_window'daki mevcut widget'ları kartlara yerleştirir.
    """
    win = main_window

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

    inner = QWidget()
    scroll.setWidget(inner)

    root = QVBoxLayout(inner)
    root.setContentsMargins(14, 14, 14, 14)
    root.setSpacing(14)

    # -- Satır 1: Project Files | Translation Queue & Terminology | Merge/Export --
    row1 = QHBoxLayout()
    row1.setSpacing(14)
    row1.addWidget(_build_project_files_card(win), 5)
    row1.addWidget(_build_translation_queue_card(win), 4)
    row1.addWidget(_build_merge_export_card(win), 3)
    root.addLayout(row1, 2)

    # -- Satır 2: Logs | Statistics Overview --
    row2 = QHBoxLayout()
    row2.setSpacing(14)
    row2.addWidget(_build_logs_card(win), 3)
    row2.addWidget(_build_statistics_card(win), 3)
    root.addLayout(row2, 1)

    return scroll


# ------------------------------------------------------------------
# Kart yapıcıları
# ------------------------------------------------------------------

def _build_project_files_card(win) -> QFrame:
    """Proje dosyaları kartı — mevcut file_table ve arama gömülür."""

    # Kart başlığındaki ekstra butonlar
    add_files_btn = QPushButton(tr("dashboard.btn_add_files", "+ Dosya Ekle"))
    add_files_btn.setObjectName("smallBtn")
    add_files_btn.clicked.connect(lambda: _open_split(win))

    header_w = QWidget()
    hl = QHBoxLayout(header_w)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(6)
    hl.addWidget(add_files_btn)

    # Kart başlığı güncellenecek (dosya sayısı için)
    win._project_files_card_title_lbl = QLabel(tr("dashboard.card_project_files", "Proje Dosyaları"))
    win._project_files_card_title_lbl.setObjectName("cardTitle")

    frame = QFrame()
    frame.setObjectName("card")
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(16, 14, 16, 14)
    outer.setSpacing(10)

    # Başlık satırı
    header_row = QHBoxLayout()
    header_row.addWidget(win._project_files_card_title_lbl)
    header_row.addStretch()
    header_row.addWidget(header_w)
    outer.addLayout(header_row)

    # Arama satırı — mevcut file_search_input buraya taşınıyor
    if hasattr(win, 'file_search_input'):
        search_row = QHBoxLayout()
        search_row.addWidget(win.file_search_input)
        search_row.addWidget(win.file_search_clear_btn)
        outer.addLayout(search_row)

    # Mevcut file_table buraya gömülüyor
    if hasattr(win, 'file_table'):
        outer.addWidget(win.file_table)

    # Alt bilgi satırı
    win._project_files_footer = QLabel(tr("dashboard.footer_no_project", "Proje seçilmedi."))
    win._project_files_footer.setStyleSheet(
        f"color:{TEXT_FAINT}; font-size:11px; "
        f"border-top:1px solid {BORDER}; padding-top:6px;"
    )
    outer.addWidget(win._project_files_footer)

    return frame


def _build_translation_queue_card(win) -> QFrame:
    """Çeviri kuyruğu ve terminoloji kartı — translate/stop butonları, progress bar ve terimler."""

    # Kart başlığı butonları
    header_w = QWidget()
    hl = QHBoxLayout(header_w)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(6)

    if hasattr(win, 'translateButton'):
        hl.addWidget(win.translateButton)
    if hasattr(win, 'stopTranslationButton'):
        hl.addWidget(win.stopTranslationButton)

    frame, body = _card(tr("dashboard.card_translation_queue", "Çeviri Kuyruğu & Terminoloji"), header_w)

    # -- Mevcut görev bilgisi --
    cur_lbl = QLabel(tr("dashboard.current_task", "Mevcut Görev"))
    cur_lbl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
    body.addWidget(cur_lbl)

    task_row = QHBoxLayout()
    task_row.addWidget(QLabel("📄"))
    win._queue_task_label = QLabel("—")
    win._queue_task_label.setStyleSheet(
        f"color:{TEXT_MAIN}; font-size:13px; font-weight:600;"
    )
    task_row.addWidget(win._queue_task_label)
    task_row.addStretch()
    body.addLayout(task_row)

    # Mevcut progress bar gömülüyor
    if hasattr(win, 'progressBar'):
        win.progressBar.setFixedHeight(8)
        win.progressBar.setTextVisible(True)
        body.addWidget(win.progressBar)

    # Status label gömülüyor
    if hasattr(win, 'statusLabel'):
        win.statusLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        win.statusLabel.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
        body.addWidget(win.statusLabel)

    # -- Sayılı çevir --
    limit_row = QHBoxLayout()
    if hasattr(win, 'limit_checkbox'):
        limit_row.addWidget(win.limit_checkbox)
    limit_row.addStretch()
    if hasattr(win, 'limit_spinbox'):
        limit_row.addWidget(win.limit_spinbox)
    body.addLayout(limit_row)

    # -- Kapatma checkbox --
    if hasattr(win, 'shutdown_checkbox'):
        body.addWidget(win.shutdown_checkbox)

    # -- Token bilgileri --
    if hasattr(win, 'total_tokens_label'):
        body.addWidget(win.total_tokens_label)
    if hasattr(win, 'total_original_tokens_label'):
        body.addWidget(win.total_original_tokens_label)
    if hasattr(win, 'total_translated_tokens_label'):
        body.addWidget(win.total_translated_tokens_label)
    if hasattr(win, 'token_progress_bar'):
        body.addWidget(win.token_progress_bar)

    # -- Token say --
    if hasattr(win, 'token_count_button'):
        body.addWidget(win.token_count_button)

    # -- Seç / Vurgulananları İşaretle --
    if hasattr(win, 'selectHighlightedButton'):
        body.addWidget(win.selectHighlightedButton)

    # -- Terminoloji Bölümü --
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet(f"color:{BORDER};")
    body.addWidget(sep)

    term_head = QLabel(tr("dashboard.section_terminology", "📚 Terminoloji"))
    term_head.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
    body.addWidget(term_head)

    stats_row = QHBoxLayout()
    stats_row.setSpacing(8)
    total_terms = _count_terms(win)
    for title, val, color in [
        (tr("dashboard.total_terms", "Toplam Terim"), str(total_terms), TEXT_MAIN),
        (tr("dashboard.status", "Durum"), tr("dashboard.ready", "Hazır"), ACCENT_GREEN),
    ]:
        box = QVBoxLayout()
        t = QLabel(title)
        t.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        v = QLabel(val)
        v.setStyleSheet(f"color:{color}; font-size:14px; font-weight:700;")
        box.addWidget(t)
        box.addWidget(v)
        w = QWidget()
        w.setLayout(box)
        stats_row.addWidget(w)
    body.addLayout(stats_row)

    if hasattr(win, 'generateTerminologyButton'):
        body.addWidget(win.generateTerminologyButton)

    open_btn = QPushButton(tr("dashboard.btn_terminology_manager", "📚  Terminoloji Yöneticisi"))
    open_btn.setObjectName("smallBtnFull")
    open_btn.clicked.connect(lambda: _open_terminology_dialog(win))
    body.addWidget(open_btn)

    body.addStretch()
    return frame


def _build_statistics_card(win) -> QFrame:
    """İstatistik kartı — request count, token bilgisi, matplotlib grafiği."""
    frame, body = _card(tr("dashboard.card_statistics", "İstatistikler"))

    # -- Özet satırı --
    stats_row = QHBoxLayout()
    stats_row.setSpacing(8)

    win._stat_requests_lbl = _make_stat_box(tr("dashboard.stat_total_requests", "Toplam İstek"), "0", ACCENT_BLUE)
    win._stat_tokens_lbl   = _make_stat_box(tr("dashboard.stat_total_tokens",   "Toplam Token"), "0", ACCENT_PURPLE)
    win._stat_speed_lbl    = _make_stat_box(tr("dashboard.stat_avg_speed",      "Ort. Hız"), "—", ACCENT_GREEN)

    stats_row.addWidget(win._stat_requests_lbl)
    stats_row.addWidget(win._stat_tokens_lbl)
    stats_row.addWidget(win._stat_speed_lbl)
    body.addLayout(stats_row)

    # -- Grafik --
    try:
        from ui.stats_chart_widget import StatsChartWidget
        win._stats_chart = StatsChartWidget(win)
        body.addWidget(win._stats_chart)
    except Exception:
        chart_placeholder = QLabel(tr("dashboard.chart_unavailable", "📊 Grafik: matplotlib yüklü değil."))
        chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_placeholder.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
        body.addWidget(chart_placeholder)

    # -- API İstatistikleri butonu --
    api_stats_btn = QPushButton(tr("dashboard.btn_view_api_stats", "📊  API İstatistiklerini Görüntüle"))
    api_stats_btn.setObjectName("smallBtnFull")
    api_stats_btn.clicked.connect(lambda: win.show_api_stats_dialog())
    body.addWidget(api_stats_btn)

    body.addStretch()
    return frame


def _build_logs_card(win) -> QFrame:
    """Log kartı — LogHandler → QTextEdit."""
    clear_btn = QPushButton(tr("dashboard.btn_clear_logs", "Temizle"))
    clear_btn.setObjectName("smallBtn")

    frame, body = _card(tr("dashboard.card_logs", "Loglar"), clear_btn)

    # Log QTextEdit oluştur ve main_window'a kaydet
    win.dashboard_log_box = QTextEdit()
    win.dashboard_log_box.setReadOnly(True)
    win.dashboard_log_box.setMinimumHeight(100)
    win.dashboard_log_box.setStyleSheet(f"""
        QTextEdit {{
            background: {BG_PANEL2};
            border: 1px solid {BORDER};
            border-radius: 6px;
            color: {TEXT_DIM};
            font-family: Consolas, monospace;
            font-size: 11px;
            padding: 8px;
        }}
    """)
    clear_btn.clicked.connect(win.dashboard_log_box.clear)
    body.addWidget(win.dashboard_log_box)

    # Logger handler'ını bağla
    _attach_log_handler(win)

    return frame


def _build_merge_export_card(win) -> QFrame:
    """Birleştir/Dışa aktar kartı."""
    frame, body = _card(tr("dashboard.card_merge_export", "Birleştir / Dışa Aktar"))

    fmt_lbl = QLabel(tr("dashboard.output_format", "Çıktı Formatı"))
    fmt_lbl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
    body.addWidget(fmt_lbl)

    fmt_row = QHBoxLayout()
    txt_radio = QRadioButton("TXT")
    epub_radio = QRadioButton("EPUB")
    epub_radio.setChecked(True)
    fmt_row.addWidget(txt_radio)
    fmt_row.addWidget(epub_radio)
    fmt_row.addStretch()
    body.addLayout(fmt_row)

    # Birleştirme butonu
    if hasattr(win, 'mergeButton'):
        body.addWidget(win.mergeButton)

    # EPUB butonu
    if hasattr(win, 'epubButton'):
        body.addWidget(win.epubButton)




    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet(f"color:{BORDER};")
    body.addWidget(sep)
    if hasattr(win, 'splitButton'):
        body.addWidget(win.splitButton)


    # Hata kontrol
    if hasattr(win, 'errorCheckButton'):
        body.addWidget(win.errorCheckButton)

    # Proje ayarları & yardım
    if hasattr(win, 'projectSettingsButton'):
        body.addWidget(win.projectSettingsButton)
    if hasattr(win, 'helpButton'):
        body.addWidget(win.helpButton)

    body.addStretch()
    return frame


def _build_terminology_card(win) -> QFrame:
    """Terminoloji kartı."""
    frame, body = _card(tr("dashboard.section_terminology", "Terminoloji"))

    # İstatistikler
    stats_row = QHBoxLayout()
    stats_row.setSpacing(8)

    total_terms = _count_terms(win)
    for title, val, color in [
        (tr("dashboard.total_terms", "Toplam Terim"), str(total_terms), TEXT_MAIN),
        (tr("dashboard.status", "Durum"), tr("dashboard.ready", "Hazır"), ACCENT_GREEN),
    ]:
        box = QVBoxLayout()
        t = QLabel(title)
        t.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        v = QLabel(val)
        v.setStyleSheet(f"color:{color}; font-size:14px; font-weight:700;")
        box.addWidget(t)
        box.addWidget(v)
        w = QWidget()
        w.setLayout(box)
        stats_row.addWidget(w)
    body.addLayout(stats_row)

    # YZ Terminoloji butonu
    if hasattr(win, 'generateTerminologyButton'):
        body.addWidget(win.generateTerminologyButton)

    open_btn = QPushButton(tr("dashboard.btn_terminology_manager", "📚  Terminoloji Yöneticisi"))
    open_btn.setObjectName("smallBtnFull")
    open_btn.clicked.connect(lambda: _open_terminology_dialog(win))
    body.addWidget(open_btn)

    body.addStretch()
    return frame


# ------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ------------------------------------------------------------------

def _make_stat_box(title: str, value: str, color: str) -> QFrame:
    """Mini istatistik kutusu."""
    f = QFrame()
    f.setObjectName("statCard")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(10, 8, 10, 8)
    lay.setSpacing(4)
    t = QLabel(title)
    t.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
    v = QLabel(value)
    v.setObjectName(f"_stat_{title.replace(' ', '_')}")
    v.setStyleSheet(f"color:{color}; font-size:18px; font-weight:700;")
    lay.addWidget(t)
    lay.addWidget(v)
    return f


def _count_terms(win) -> int:
    """Aktif proje için terminoloji terim sayısını döndürür."""
    try:
        if not hasattr(win, 'current_project_path') or not win.current_project_path:
            return 0
        term_file = os.path.join(win.current_project_path, "config", "terminology.json")
        if not os.path.exists(term_file):
            return 0
        import json
        with open(term_file, encoding="utf-8") as f:
            data = json.load(f)
        return len(data) if isinstance(data, (list, dict)) else 0
    except Exception:
        return 0


def _open_split(win):
    try:
        win.start_split_process()
    except Exception:
        pass


def _open_terminology_dialog(win):
    try:
        project_path = getattr(win, 'current_project_path', None)
        if not project_path and hasattr(win, 'project_list') and win.project_list.currentItem():
            p_name = win.project_list.currentItem().text()
            if p_name:
                project_path = os.path.join(os.getcwd(), p_name)
        if not project_path or not os.path.exists(project_path):
            from PyQt6.QtWidgets import QMessageBox
            from core.localization import tr
            QMessageBox.warning(
                win,
                tr("sidebar.no_project_title", "Proje Seçilmedi"),
                tr("sidebar.no_project_body", "Lütfen önce bir proje seçin.")
            )
            return
        from dialogs import TerminologyDialog
        TerminologyDialog(project_path, win).exec()
    except Exception as e:
        from logger import app_logger
        app_logger.warning(f"Terminology dialog açılamadı: {e}")


def _attach_log_handler(win):
    """app_logger'a dashboard QTextEdit'e yazan bir handler ekler."""
    try:
        import logging
        from logger import app_logger

        class _DashboardLogHandler(logging.Handler):
            def __init__(self, text_widget: QTextEdit):
                super().__init__()
                self._w = text_widget

            def emit(self, record: logging.LogRecord):
                try:
                    msg = self.format(record)
                    level = record.levelname
                    if level == "WARNING":
                        color = ACCENT_ORANGE
                        lvl_color = ACCENT_ORANGE
                    elif level == "ERROR" or level == "CRITICAL":
                        color = ACCENT_RED
                        lvl_color = ACCENT_RED
                    elif level == "DEBUG":
                        color = TEXT_FAINT
                        lvl_color = TEXT_FAINT
                    else:
                        color = TEXT_DIM
                        lvl_color = ACCENT_CYAN

                    import html
                    safe_msg = html.escape(msg)
                    html_line = (
                        f'<span style="color:{TEXT_FAINT}; font-size:10px;">'
                        f'[{record.asctime if hasattr(record, "asctime") else ""}]</span> '
                        f'<span style="color:{lvl_color}; font-weight:600;">[{level}]</span> '
                        f'<span style="color:{color};">{safe_msg}</span>'
                    )
                    # GUI thread'e taşı
                    from PyQt6.QtCore import QMetaObject, Qt
                    QMetaObject.invokeMethod(
                        self._w, "append",
                        Qt.ConnectionType.QueuedConnection,
                        __import__("PyQt6.QtCore", fromlist=["Q_ARG"]).Q_ARG(str, html_line)
                    )
                except Exception:
                    pass

        handler = _DashboardLogHandler(win.dashboard_log_box)
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.setLevel(logging.DEBUG)
        app_logger.addHandler(handler)
        # Referansı sakla (handler çöp toplanmasın)
        win._dashboard_log_handler = handler
    except Exception as e:
        pass  # Logger bağlanamadıysa sessizce geç


def update_dashboard_stats(win):
    """
    Dashboard istatistik etiketlerini günceller.
    TranslationController'daki sinyaller bu fonksiyonu çağırabilir.
    """
    try:
        if hasattr(win, '_stat_requests_lbl'):
            count = win.request_counter_manager.get_count(
                win._current_model, win._current_api_name
            )
            # value label'ı bul
            for child in win._stat_requests_lbl.findChildren(QLabel):
                if "18px" in child.styleSheet():
                    child.setText(str(count))
                    break
        if hasattr(win, '_stat_tokens_lbl'):
            for child in win._stat_tokens_lbl.findChildren(QLabel):
                if "18px" in child.styleSheet():
                    child.setText(f"{win._api_token_count:,}")
                    break
        if hasattr(win, '_stat_speed_lbl'):
            for child in win._stat_speed_lbl.findChildren(QLabel):
                if "18px" in child.styleSheet():
                    spd = f"{win._translation_speed:.1f} dk/bölüm" if win._translation_speed > 0 else "—"
                    child.setText(spd)
                    break
    except Exception:
        pass


def update_project_files_footer(win):
    """Project Files kart footer'ını günceller."""
    if not hasattr(win, '_project_files_footer'):
        return
    try:
        if win.current_project_path:
            dwnld = os.path.join(win.current_project_path, "dwnld")
            trslt = os.path.join(win.current_project_path, "trslt")
            total = len([f for f in os.listdir(dwnld) if f.endswith(".txt")]) if os.path.exists(dwnld) else 0
            done  = len([f for f in os.listdir(trslt) if f.endswith(".txt")]) if os.path.exists(trslt) else 0
            project_name = win.project_list.currentItem().text() if win.project_list.currentItem() else "?"
            title_tpl = tr("dashboard.card_project_files_with_count", "Proje Dosyaları ({count}) — {project}")
            win._project_files_card_title_lbl.setText(
                title_tpl.format(count=total, project=project_name)
            )
            footer_tpl = tr("dashboard.footer_stats", "Toplam: {total}    Çevrildi: {done}    Kalan: {remaining}")
            win._project_files_footer.setText(
                footer_tpl.format(total=total, done=done, remaining=total - done)
            )
        else:
            win._project_files_card_title_lbl.setText(tr("dashboard.card_project_files", "Proje Dosyaları"))
            win._project_files_footer.setText(tr("dashboard.footer_no_project", "Proje seçilmedi."))
    except Exception:
        pass
