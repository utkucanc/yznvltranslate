"""
text_editor_page.py — Text Editor sayfası (QStackedWidget'a eklenen gömülü sayfa).

Görsel layout ve çift panelli tasarım korunarak tam iş mantığı eklenmiştir:
- Projenin dwnld/ ve trslt/ klasörlerinden canlı bölüm (chapter) listesi yükleme
- Orijinal metin (dwnld) ile çevrilmiş metin (trslt, translated_... desteğiyle) doğru eşleştirme
- Çeviri metninde yapılan değişiklikleri diskteki dosyaya kaydetme (Save)
- ESC kısayolu ile kolayca Dashboard sayfasına dönme
- RetranslateWorker (QThread) ile tek bölümü arka planda tekrar çevirme
- Canlı karakter/kelime/satır sayısı hesaplama
- Terminology Hints bölümünde o metinde geçen terimleri TerminologyManager'dan çekip listeleme
"""

import os
import configparser
from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QComboBox, QPlainTextEdit,
    QListWidget, QListWidgetItem, QProgressBar, QSizePolicy, QTabWidget,
    QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QSize
from PyQt6.QtGui import QFont, QShortcut, QKeySequence

from ui.dark_theme import (
    BG_PANEL, BG_PANEL2, BORDER, TEXT_MAIN, TEXT_DIM, TEXT_FAINT,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_PURPLE,
    ACCENT_RED, ACCENT_CYAN
)
from core.localization import tr
from terminology.terminology_manager import TerminologyManager
from ui.text_editor_dialog import RetranslateWorker


def _badge(text: str, color: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"""
        color: {color}; background: {color}22;
        border: 1px solid {color}55; border-radius: 4px;
        padding: 2px 8px; font-size: 11px; font-weight: 600;
    """)
    return lbl


def _card() -> tuple[QFrame, QVBoxLayout]:
    f = QFrame()
    f.setObjectName("card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(8)
    return f, lay


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:13px; font-weight:700;")
    return lbl


def _status_color(status: str) -> str:
    return {
        "Çevrildi": ACCENT_GREEN,
        "Translated": ACCENT_GREEN,
        "Sırada": ACCENT_ORANGE,
        "In Queue": ACCENT_ORANGE,
        "Çevrilmedi": TEXT_FAINT,
        "Untranslated": TEXT_FAINT,
        "Düzenlendi": ACCENT_BLUE,
        "Edited": ACCENT_BLUE,
    }.get(status, TEXT_DIM)


def build_text_editor_page(main_window) -> QScrollArea:
    """
    Text Editor sayfasını oluşturur.
    """
    win = main_window

    outer = QWidget()
    root = QVBoxLayout(outer)
    root.setContentsMargins(14, 14, 14, 14)
    root.setSpacing(14)

    # ESC Kısayolu: Basıldığında Dashboard'a döner
    esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), outer)
    esc_shortcut.activated.connect(lambda: _close_editor_view(win))

    # Ctrl+S Kısayolu: Basıldığında kaydeder
    save_shortcut = QShortcut(QKeySequence("Ctrl+S"), outer)
    save_shortcut.activated.connect(lambda: save_current_editor_file(win))

    # 1. Üst Bar (Proje & Dosya İşlemleri)
    root.addWidget(_build_project_header_bar(win))

    # 2. Ana Gövde (Sol Liste + Orta Editör + Sağ Araçlar)
    body = QHBoxLayout()
    body.setSpacing(14)
    body.addWidget(_build_chapter_list_panel(win), 2)
    body.addWidget(_build_editor_center_panel(win), 6)
    body.addWidget(_build_right_tools_panel(win), 2)

    body_w = QWidget()
    body_w.setLayout(body)
    root.addWidget(body_w, 1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
    scroll.setWidget(outer)

    # State değişkenleri
    win._editor_current_file_path = None
    win._editor_original_content = ""
    win._editor_has_unsaved = False

    # İlk yükleme
    QTimer.singleShot(100, lambda: refresh_text_editor_page(win))

    return scroll


# ── Üst Bilgi Barı ───────────────────────────────────────────────────

def _build_project_header_bar(win) -> QFrame:
    frame = QFrame()
    frame.setObjectName("card")
    lay = QHBoxLayout(frame)
    lay.setContentsMargins(14, 10, 14, 10)
    lay.setSpacing(16)

    win.editor_proj_name_lbl = QLabel("—")
    win.editor_proj_name_lbl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")

    proj_row = QHBoxLayout()
    kl = QLabel("Proje:")
    kl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:12px;")
    proj_row.addWidget(kl)
    proj_row.addWidget(win.editor_proj_name_lbl)
    lay.addLayout(proj_row)

    lay.addWidget(_vline())

    # İşlem Butonları
    save_btn = QPushButton("💾  Kaydet (Ctrl+S)")
    save_btn.setObjectName("primaryBtn")
    save_btn.setStyleSheet(f"background-color: {ACCENT_GREEN}; color: white; font-weight: bold;")
    save_btn.clicked.connect(lambda: save_current_editor_file(win))

    retranslate_btn = QPushButton("🔄  Tekrar Çevir")
    retranslate_btn.setObjectName("smallBtn")
    retranslate_btn.setStyleSheet(f"background-color: {ACCENT_BLUE}; color: white;")
    retranslate_btn.clicked.connect(lambda: _retranslate_current_chapter(win))
    win.editor_retranslate_btn = retranslate_btn

    close_btn = QPushButton("✕  Kapat (ESC)")
    close_btn.setObjectName("smallBtn")
    close_btn.setToolTip("Dashboard sayfasına dön (ESC)")
    close_btn.clicked.connect(lambda: _close_editor_view(win))

    for b in (save_btn, retranslate_btn, close_btn):
        lay.addWidget(b)

    return frame


def _vline() -> QFrame:
    v = QFrame()
    v.setFrameShape(QFrame.Shape.VLine)
    v.setStyleSheet(f"color:{BORDER};")
    return v


# ── Sol Panel: Bölüm Listesi ─────────────────────────────────────────

def _build_chapter_list_panel(win) -> QFrame:
    frame, lay = _card()

    win.editor_chapter_search = QLineEdit()
    win.editor_chapter_search.setPlaceholderText("🔍  Bölümlerde ara...")
    win.editor_chapter_search.textChanged.connect(lambda: _filter_chapter_list(win))
    lay.addWidget(win.editor_chapter_search)

    win.editor_chapter_stats_lbl = QLabel("Bölüm Yükleniyor...")
    win.editor_chapter_stats_lbl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
    lay.addWidget(win.editor_chapter_stats_lbl)

    chapter_list = QListWidget()
    chapter_list.setObjectName("editorChapterList")
    chapter_list.setStyleSheet(f"""
        QListWidget {{ background: transparent; border: none; color: {TEXT_MAIN}; }}
        QListWidget::item {{ padding: 4px 6px; border-radius: 6px; }}
        QListWidget::item:hover {{ background: {BG_PANEL2}; }}
        QListWidget::item:selected {{ background: {ACCENT_BLUE}33; color: {TEXT_MAIN}; }}
    """)
    chapter_list.itemSelectionChanged.connect(lambda: _on_chapter_selected(win))

    win.editor_chapter_list = chapter_list
    lay.addWidget(chapter_list, 1)

    return frame


# ── Orta Panel: Çift Panel Editör ────────────────────────────────────

def _build_editor_center_panel(win) -> QFrame:
    frame, lay = _card()

    title_row = QHBoxLayout()
    win.editor_chapter_title = QLabel("Bölüm Seçilmedi")
    win.editor_chapter_title.setStyleSheet(f"color:{TEXT_MAIN}; font-size:14px; font-weight:700;")
    title_row.addWidget(win.editor_chapter_title)
    title_row.addStretch()

    win.editor_save_status_lbl = QLabel("")
    win.editor_save_status_lbl.setStyleSheet(f"color:{ACCENT_GREEN}; font-size:11px;")
    title_row.addWidget(win.editor_save_status_lbl)
    lay.addLayout(title_row)

    panels = QHBoxLayout()
    panels.setSpacing(10)

    # Orijinal Panel
    panels.addWidget(_build_text_panel(win, "Orijinal Metin (dwnld)", "Kaynak", is_source=True), 1)

    swap = QLabel("↔")
    swap.setStyleSheet(f"color:{TEXT_FAINT}; font-size:16px;")
    swap.setAlignment(Qt.AlignmentFlag.AlignCenter)
    panels.addWidget(swap)

    # Çeviri Paneli
    panels.addWidget(_build_text_panel(win, "Çevrilen Metin (trslt)", "Hedef", is_source=False), 1)
    lay.addLayout(panels, 1)

    return frame


def _build_text_panel(win, title: str, lang_code: str, is_source: bool) -> QFrame:
    panel = QFrame()
    panel.setObjectName("innerCard")
    p_lay = QVBoxLayout(panel)
    p_lay.setContentsMargins(10, 10, 10, 10)
    p_lay.setSpacing(6)

    header = QHBoxLayout()
    t = QLabel(title)
    t.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:700;")
    header.addWidget(t)
    header.addWidget(_badge(lang_code, ACCENT_BLUE if is_source else ACCENT_PURPLE))
    header.addStretch()

    counts = QLabel("Karakter: 0  |  Kelime: 0")
    counts.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
    header.addWidget(counts)
    p_lay.addLayout(header)

    text_edit = QPlainTextEdit()
    text_edit.setPlaceholderText("Orijinal metin bulunamadı..." if is_source else "Çeviri henüz yapılmadı / düzenlenebilir...")
    text_edit.setStyleSheet(f"""
        QPlainTextEdit {{
            background: {BG_PANEL2}; border: 1px solid {BORDER}; border-radius: 6px;
            color: {TEXT_MAIN}; font-size: 13px; padding: 8px;
        }}
    """)

    if is_source:
        text_edit.setReadOnly(True)
        win.editor_source_text = text_edit
        win.editor_source_counts = counts
    else:
        text_edit.textChanged.connect(lambda: _on_target_text_changed(win))
        win.editor_target_text = text_edit
        win.editor_target_counts = counts

    p_lay.addWidget(text_edit, 1)
    return panel


# ── Sağ Panel: AI Tools / Notes / Terminology Hints ─────────────────

def _build_right_tools_panel(win) -> QFrame:
    frame, lay = _card()

    tabs = QTabWidget()
    tabs.setObjectName("editorRightTabs")
    tabs.addTab(_build_ai_tools_tab(win), "AI & Terminology")
    win.editor_right_tabs = tabs
    lay.addWidget(tabs, 1)

    return frame


def _build_ai_tools_tab(win) -> QWidget:
    tab = QWidget()
    lay = QVBoxLayout(tab)
    lay.setContentsMargins(4, 8, 4, 4)
    lay.setSpacing(10)

    lay.addWidget(_section_title("Hızlı İşlemler"))
    retrans_btn = QPushButton("🔄  Bölümü Tekrar Çevir")
    retrans_btn.setObjectName("smallBtnFull")
    retrans_btn.clicked.connect(lambda: _retranslate_current_chapter(win))
    lay.addWidget(retrans_btn)

    lay.addWidget(_terminology_hints_card(win))

    lay.addStretch()
    return tab


def _terminology_hints_card(win) -> QFrame:
    frame = QFrame()
    frame.setObjectName("innerCard")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(10, 10, 10, 10)
    lay.setSpacing(6)

    header = QHBoxLayout()
    header.addWidget(_section_title("Bu Bölümdeki Terimler"))
    header.addStretch()
    lay.addLayout(header)

    win.editor_term_hints_container = QVBoxLayout()
    lay.addLayout(win.editor_term_hints_container)

    return frame


# ──────────────────────────────────────────────────────────────────────
# İŞ MANTIKLARI VE CANLI VERİ YÜKLEME
# ──────────────────────────────────────────────────────────────────────

def refresh_text_editor_page(win, target_file_path: str = None):
    """
    Proje dwnld/ ve trslt/ klasörlerini tarayarak bölüm listesini doldurur.
    target_file_path verilmişse o dosyayı doğrudan açar.
    """
    project_path = getattr(win, 'current_project_path', None)
    if hasattr(win, 'editor_proj_name_lbl'):
        p_name = os.path.basename(project_path) if project_path else "Seçilmedi"
        win.editor_proj_name_lbl.setText(p_name)

    if not project_path or not os.path.exists(project_path):
        if hasattr(win, 'editor_chapter_list'):
            win.editor_chapter_list.clear()
        if hasattr(win, 'editor_chapter_stats_lbl'):
            win.editor_chapter_stats_lbl.setText("Proje seçilmedi")
        return

    dwnld_dir = os.path.join(project_path, "dwnld")
    trslt_dir = os.path.join(project_path, "trslt")

    files = []
    if os.path.exists(dwnld_dir):
        files = sorted([f for f in os.listdir(dwnld_dir) if f.endswith('.txt')])
    elif os.path.exists(trslt_dir):
        files = sorted([f for f in os.listdir(trslt_dir) if f.endswith('.txt')])

    total = len(files)
    translated_count = 0

    if hasattr(win, 'editor_chapter_list'):
        list_widget = win.editor_chapter_list
        list_widget.blockSignals(True)
        list_widget.clear()

        selected_row = 0

        for idx, filename in enumerate(files):
            dwnld_file = os.path.join(dwnld_dir, filename)

            # Çevrilmiş dosya eşleştirme (translated_... veya birebir dosya adı)
            cand1 = os.path.join(trslt_dir, f"translated_{filename}")
            cand2 = os.path.join(trslt_dir, filename)

            if os.path.exists(cand1):
                trslt_file = cand1
                is_translated = True
            elif os.path.exists(cand2):
                trslt_file = cand2
                is_translated = True
            else:
                trslt_file = cand1
                is_translated = False

            if is_translated:
                translated_count += 1
                status = "Çevrildi"
            else:
                status = "Çevrilmedi"

            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 36))

            row_w = QWidget()
            row_w.setMinimumHeight(34)
            r_lay = QHBoxLayout(row_w)
            r_lay.setContentsMargins(6, 4, 6, 4)

            num_lbl = QLabel(f"{idx+1:03d}")
            num_lbl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px; background:transparent;")

            title_lbl = QLabel(filename)
            title_lbl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600; background:transparent;")
            title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

            status_lbl = QLabel(status)
            status_lbl.setStyleSheet(f"color:{_status_color(status)}; font-size:11px; font-weight:600; background:transparent;")

            r_lay.addWidget(num_lbl)
            r_lay.addWidget(title_lbl)
            r_lay.addWidget(status_lbl)

            item.setData(Qt.ItemDataRole.UserRole, (dwnld_file, trslt_file, filename, is_translated))
            list_widget.addItem(item)
            list_widget.setItemWidget(item, row_w)

            if target_file_path and (target_file_path == trslt_file or target_file_path == dwnld_file or os.path.basename(target_file_path) == filename or os.path.basename(target_file_path) == f"translated_{filename}"):
                selected_row = idx

        list_widget.blockSignals(False)

        if total > 0:
            list_widget.setCurrentRow(selected_row)
            _load_chapter_data_by_item(win, list_widget.item(selected_row))

    if hasattr(win, 'editor_chapter_stats_lbl'):
        win.editor_chapter_stats_lbl.setText(f"Toplam: {total}  •  Çevrilen: {translated_count}  •  Kalan: {total - translated_count}")


def _filter_chapter_list(win):
    if not hasattr(win, 'editor_chapter_list'):
        return
    query = win.editor_chapter_search.text().strip().lower()
    list_widget = win.editor_chapter_list
    for i in range(list_widget.count()):
        item = list_widget.item(i)
        data = item.data(Qt.ItemDataRole.UserRole)
        filename = data[2] if data else ""
        item.setHidden(bool(query and query not in filename.lower()))


def _on_chapter_selected(win):
    list_widget = win.editor_chapter_list
    item = list_widget.currentItem()
    if item:
        _load_chapter_data_by_item(win, item)


def _load_chapter_data_by_item(win, item):
    if not item:
        return
    data = item.data(Qt.ItemDataRole.UserRole)
    if not data:
        return

    dwnld_file, trslt_file, filename, is_translated = data

    win.editor_chapter_title.setText(f"Bölüm: {filename}")

    # Orijinal metin oku
    src_text = ""
    if os.path.exists(dwnld_file):
        try:
            with open(dwnld_file, 'r', encoding='utf-8') as f:
                src_text = f.read()
        except Exception:
            pass
    elif is_translated and os.path.exists(trslt_file):
        try:
            with open(trslt_file, 'r', encoding='utf-8') as f:
                src_text = f.read()
        except Exception:
            pass

    # Çeviri metni oku (eğer dosya diskte varsa)
    tgt_text = ""
    if is_translated and os.path.exists(trslt_file):
        try:
            with open(trslt_file, 'r', encoding='utf-8') as f:
                tgt_text = f.read()
        except Exception:
            pass

    win._editor_current_file_path = trslt_file
    win._editor_original_content = tgt_text
    win._editor_has_unsaved = False

    win.editor_source_text.setPlainText(src_text)
    win.editor_target_text.setPlainText(tgt_text)

    _update_counts(win.editor_source_text, win.editor_source_counts)
    _update_counts(win.editor_target_text, win.editor_target_counts)

    _refresh_terminology_hints(win, src_text)


def _update_counts(text_widget, label_widget):
    if not text_widget or not label_widget:
        return
    text = text_widget.toPlainText()
    chars = len(text)
    words = len(text.split()) if text.strip() else 0
    lines = text.count('\n') + 1 if text else 0
    label_widget.setText(f"Karakter: {chars:,}  |  Kelime: {words:,}  |  Satır: {lines:,}")


def _on_target_text_changed(win):
    _update_counts(win.editor_target_text, win.editor_target_counts)
    current = win.editor_target_text.toPlainText()
    win._editor_has_unsaved = (current != getattr(win, '_editor_original_content', ''))
    if win.editor_save_status_lbl:
        if win._editor_has_unsaved:
            win.editor_save_status_lbl.setText("● Değişiklik var")
            win.editor_save_status_lbl.setStyleSheet(f"color:{ACCENT_ORANGE}; font-weight:bold;")
        else:
            win.editor_save_status_lbl.setText("")


def save_current_editor_file(win):
    file_path = getattr(win, '_editor_current_file_path', None)
    if not file_path:
        QMessageBox.warning(win, "Hata", "Kaydedilecek aktif dosya bulunamadı.")
        return

    try:
        content = win.editor_target_text.toPlainText()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        win._editor_original_content = content
        win._editor_has_unsaved = False
        win.editor_save_status_lbl.setText("✓ Diske Kaydedildi")
        win.editor_save_status_lbl.setStyleSheet(f"color:{ACCENT_GREEN}; font-weight:bold;")

        QTimer.singleShot(2500, lambda: win.editor_save_status_lbl.setText(""))
    except Exception as e:
        QMessageBox.critical(win, "Kayıt Hatası", f"Dosya kaydedilemedi:\n{e}")


def _retranslate_current_chapter(win):
    project_path = getattr(win, 'current_project_path', None)
    file_path = getattr(win, '_editor_current_file_path', None)

    if not project_path or not file_path:
        QMessageBox.warning(win, "Uyarı", "Geçerli bir proje veya dosya açık değil.")
        return

    file_name = os.path.basename(file_path)
    if file_name.startswith("translated_"):
        file_name = file_name.replace("translated_", "", 1)

    dwnld_path = os.path.join(project_path, "dwnld", file_name)
    if not os.path.exists(dwnld_path):
        QMessageBox.warning(win, "Hata", f"Orijinal kaynak dosya bulunamadı:\n{dwnld_path}")
        return

    config_path = os.path.join(project_path, "config", "config.ini")
    if not os.path.exists(config_path):
        QMessageBox.warning(win, "Hata", "Proje config.ini dosyası bulunamadı.")
        return

    try:
        cfg = configparser.ConfigParser()
        cfg.read(config_path, encoding="utf-8")
        api_key = cfg.get("API", "gemini_api_key", fallback="")
        startpromt = cfg.get("Startpromt", "startpromt", fallback="")

        if not api_key:
            QMessageBox.warning(win, "Hata", "Proje ayarlarında API anahtarı tanımlı değil.")
            return

        if hasattr(win, 'editor_retranslate_btn'):
            win.editor_retranslate_btn.setEnabled(False)
            win.editor_retranslate_btn.setText("⏳ Çevriliyor...")

        win._retranslate_thread = QThread()
        win._retranslate_worker = RetranslateWorker(project_path, dwnld_path, startpromt, api_key)
        win._retranslate_worker.moveToThread(win._retranslate_thread)

        def _done(translated_text):
            win.editor_target_text.setPlainText(translated_text)
            save_current_editor_file(win)
            QMessageBox.information(win, "Çeviri Tamamlandı", "Bölüm tekrar çevrildi ve kaydedildi.")
            if hasattr(win, 'editor_retranslate_btn'):
                win.editor_retranslate_btn.setEnabled(True)
                win.editor_retranslate_btn.setText("🔄  Tekrar Çevir")

        def _error(err_msg):
            QMessageBox.critical(win, "Çeviri Hatası", f"Tekrar çeviri başarısız:\n{err_msg}")
            if hasattr(win, 'editor_retranslate_btn'):
                win.editor_retranslate_btn.setEnabled(True)
                win.editor_retranslate_btn.setText("🔄  Tekrar Çevir")

        win._retranslate_thread.started.connect(win._retranslate_worker.run)
        win._retranslate_worker.finished.connect(_done)
        win._retranslate_worker.error.connect(_error)
        win._retranslate_worker.finished.connect(win._retranslate_thread.quit)
        win._retranslate_worker.error.connect(win._retranslate_thread.quit)

        win._retranslate_thread.start()

    except Exception as e:
        QMessageBox.critical(win, "Hata", f"İşlem başlatılamadı:\n{e}")


def _close_editor_view(win):
    if getattr(win, '_editor_has_unsaved', False):
        reply = QMessageBox.question(
            win, "Kaydedilmemiş Değişiklikler",
            "Değişiklikleri kaydetmeden çıkmak istiyor musunuz?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Save:
            save_current_editor_file(win)
        elif reply == QMessageBox.StandardButton.Cancel:
            return

    if hasattr(win, 'main_stack'):
        win.main_stack.setCurrentIndex(0)
    win.set_active_nav("Dashboard")


def _refresh_terminology_hints(win, source_text: str):
    if not hasattr(win, 'editor_term_hints_container'):
        return

    container = win.editor_term_hints_container
    while container.count():
        item = container.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()

    project_path = getattr(win, 'current_project_path', None)
    if not project_path or not source_text:
        return

    try:
        tm = TerminologyManager(project_path)
        all_terms = tm.get_all_terms()
        matched = []

        source_lower = source_text.lower()
        for t in all_terms:
            src = t.get("source", "")
            if src and src.lower() in source_lower:
                matched.append(t)

        if not matched:
            lbl = QLabel("Bu bölümde eşleşen terim yok.")
            lbl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
            container.addWidget(lbl)
            return

        for t in matched[:10]:
            r = QHBoxLayout()
            s = QLabel(t.get("source", ""))
            s.setStyleSheet(f"color:{TEXT_MAIN}; font-size:11px; font-weight:600;")
            arr = QLabel("→")
            arr.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
            tgt = QLabel(t.get("target", ""))
            tgt.setStyleSheet(f"color:{ACCENT_CYAN}; font-size:11px;")

            r.addWidget(s)
            r.addWidget(arr)
            r.addWidget(tgt)
            r.addStretch()

            w = QWidget()
            w.setLayout(r)
            container.addWidget(w)

    except Exception:
        pass

