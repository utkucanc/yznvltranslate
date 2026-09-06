"""
terminology_page.py — Terminology sayfası (QStackedWidget'a eklenen gömülü sayfa).

Görsel layout korunarak tam iş mantığı eklenmiştir:
- Gerçek TerminologyManager(win.current_project_path) ile entegrasyon
- Proje değişimlerinde otomatik veri yenileme (refresh_terminology_page)
- Canlı arama ve filtreleme
- Tablo üzerinde ÇİFT TIKLAYARAK doğrudan hücre düzenleme (Source, Target, Note) ve Otomatik Kayıt
- Terim Detayları panelinde "Terimi Düzenle" butonu ile ayrıntılı düzenleme ve kaydetme
- Terim ekleme, silme, onaylama (ambiguous toggle), içe/dışa aktarma, temizleme
"""

import os
import configparser
from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QComboBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSizePolicy, QTextEdit, QMessageBox, QInputDialog, QFileDialog, QDialog
)
from PyQt6.QtCore import Qt, QTimer

from ui.dark_theme import (
    BG_PANEL, BG_PANEL2, BORDER, TEXT_MAIN, TEXT_DIM, TEXT_FAINT,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_PURPLE,
    ACCENT_RED, ACCENT_CYAN
)
from core.localization import tr
from terminology.terminology_manager import TerminologyManager


def _badge(text: str, color: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"""
        color: {color}; background: {color}22;
        border: 1px solid {color}55; border-radius: 4px;
        padding: 2px 8px; font-size: 11px; font-weight: 600;
    """)
    return lbl


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:14px; font-weight:700;")
    return lbl


def _card() -> tuple[QFrame, QVBoxLayout]:
    f = QFrame()
    f.setObjectName("card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(10)
    return f, lay


def _kv_label(text: str, color: str, size: int) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{color}; font-size:{size}px; margin-top:4px;")
    return lbl


def build_terminology_page(main_window) -> QScrollArea:
    """
    Terminology sayfasını oluşturur.
    """
    win = main_window

    outer = QWidget()
    root = QHBoxLayout(outer)
    root.setContentsMargins(14, 14, 14, 14)
    root.setSpacing(14)

    # -- SOL: Overview + Toolbar + Ekleme Çubuğu + Tablo --
    left = QVBoxLayout()
    left.setSpacing(14)

    left.addWidget(_build_overview_card(win))
    left.addLayout(_build_add_term_bar(win))
    left.addLayout(_build_toolbar_row(win))
    left.addWidget(_build_terms_table_card(win), 1)

    left_w = QWidget()
    left_w.setLayout(left)
    root.addWidget(left_w, 3)

    # -- SAĞ: Last Extraction Info + Term Details --
    right = QVBoxLayout()
    right.setSpacing(14)
    right.addWidget(_build_last_extraction_card(win))
    win.term_page_details_frame = _build_term_details_card(win)
    right.addWidget(win.term_page_details_frame, 1)

    right_w = QWidget()
    right_w.setLayout(right)
    right_w.setMinimumWidth(300)
    right_w.setMaximumWidth(360)
    root.addWidget(right_w)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
    scroll.setWidget(outer)

    # İlk veri yükleme
    QTimer.singleShot(100, lambda: refresh_terminology_page(win))

    return scroll


# -- Overview & Stat Kartları ------------------------------------------

def _build_overview_card(win) -> QFrame:
    frame, lay = _card()
    
    top_row = QHBoxLayout()
    top_row.addWidget(_section_title(tr("terminology.window_title", "Terminoloji Sözlüğü")))
    top_row.addStretch()

    refresh_btn = QPushButton(tr("terminology.btn_refresh", "🔄 Yenile"))
    refresh_btn.setObjectName("smallBtn")
    refresh_btn.clicked.connect(lambda: refresh_terminology_page(win))
    top_row.addWidget(refresh_btn)

    import_btn = QPushButton(tr("terminology.btn_import", "📥 İçe Aktar"))
    import_btn.setObjectName("smallBtn")
    import_btn.clicked.connect(lambda: _on_import_terms(win))
    top_row.addWidget(import_btn)

    export_btn = QPushButton(tr("terminology.btn_export", "📤 Dışa Aktar"))
    export_btn.setObjectName("smallBtn")
    export_btn.clicked.connect(lambda: _on_export_terms(win))
    top_row.addWidget(export_btn)

    clear_btn = QPushButton(tr("terminology.btn_clear_all", "🧹 Tümünü Temizle"))
    clear_btn.setObjectName("smallBtn")
    clear_btn.setStyleSheet(f"color: {ACCENT_RED};")
    clear_btn.clicked.connect(lambda: _on_clear_terms(win))
    top_row.addWidget(clear_btn)

    lay.addLayout(top_row)

    row = QHBoxLayout()
    row.setSpacing(10)

    win.term_stat_total = _mini_stat_widget("Toplam Terim", "0")
    win.term_stat_approved = _mini_stat_widget("Onaylı", "0", "0%", ACCENT_GREEN)
    win.term_stat_pending = _mini_stat_widget("Gözden Geçirilecek", "0", "0%", ACCENT_ORANGE)

    row.addWidget(win.term_stat_total)
    row.addWidget(win.term_stat_approved)
    row.addWidget(win.term_stat_pending)

    win.term_page_overview_row = QWidget()
    win.term_page_overview_row.setLayout(row)
    lay.addWidget(win.term_page_overview_row)
    return frame


def _mini_stat_widget(title: str, value: str, sub: str = "", color: str = None) -> QFrame:
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
    if sub:
        s = QLabel(sub)
        s.setStyleSheet(f"color:{color or TEXT_FAINT}; font-size:10px;")
        lay.addWidget(s)
    f.lbl_value = v
    if sub:
        f.lbl_sub = s
    return f


# -- Terim Ekleme Çubuğu ---------------------------------------------

def _build_add_term_bar(win) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(8)

    win.term_add_source = QLineEdit()
    win.term_add_source.setPlaceholderText(tr("terminology.placeholder_source", "Kaynak Terim (ör: 黑暗之王)"))

    win.term_add_target = QLineEdit()
    win.term_add_target.setPlaceholderText(tr("terminology.placeholder_target", "Hedef Çeviri (ör: Karanlık Kral)"))

    win.term_add_note = QLineEdit()
    win.term_add_note.setPlaceholderText(tr("terminology.placeholder_note", "Not (opsiyonel)"))

    add_btn = QPushButton(tr("terminology.btn_add", "➕ Ekle"))
    add_btn.setObjectName("primaryBtn")
    add_btn.setStyleSheet(f"background-color: {ACCENT_GREEN}; color: white; font-weight: bold;")
    add_btn.clicked.connect(lambda: _on_add_term(win))

    win.term_add_source.returnPressed.connect(add_btn.click)
    win.term_add_target.returnPressed.connect(add_btn.click)
    win.term_add_note.returnPressed.connect(add_btn.click)

    lay.addWidget(win.term_add_source, 2)
    lay.addWidget(win.term_add_target, 2)
    lay.addWidget(win.term_add_note, 2)
    lay.addWidget(add_btn, 1)

    return lay


# -- Arama / Filtre Araç Çubuğu -------------------------------------

def _build_toolbar_row(win) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(8)

    win.term_page_search_input = QLineEdit()
    win.term_page_search_input.setPlaceholderText("🔍  Terimlerde ara...")
    win.term_page_search_input.textChanged.connect(lambda: _filter_table(win))
    row.addWidget(win.term_page_search_input, 3)

    win.term_page_status_filter = QComboBox()
    win.term_page_status_filter.addItems(["Tüm Durumlar", "Onaylı", "Gözden Geçirilecek"])
    win.term_page_status_filter.currentIndexChanged.connect(lambda: _filter_table(win))
    row.addWidget(win.term_page_status_filter, 2)

    return row


# -- Terim Tablosu ----------------------------------------------------

_TABLE_HEADERS = ["Kaynak Terim (Source)", "Hedef Çeviri (Target)", "Not", "Durum", "İşlem"]


def _build_terms_table_card(win) -> QFrame:
    frame, lay = _card()

    header_row = QHBoxLayout()
    win.term_page_count_label = QLabel("0 terim gösteriliyor (Çift tıklayarak düzenleyebilirsiniz)")
    win.term_page_count_label.setStyleSheet(f"color:{TEXT_FAINT}; font-size:12px;")
    header_row.addWidget(win.term_page_count_label)
    header_row.addStretch()
    lay.addLayout(header_row)

    table = QTableWidget(0, len(_TABLE_HEADERS))
    table.setObjectName("terminologyTable")
    table.setHorizontalHeaderLabels(_TABLE_HEADERS)
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

    # Çift tıkla doğrudan tablo hücresi düzenleme izni
    table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)

    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

    table.setStyleSheet(f"""
        QTableWidget {{
            background: transparent; color: {TEXT_MAIN}; border: none; font-size: 12px;
        }}
        QHeaderView::section {{
            background: transparent; color: {TEXT_FAINT}; border: none;
            border-bottom: 1px solid {BORDER}; padding: 6px; font-size: 11px;
        }}
        QTableWidget::item {{ border-bottom: 1px solid {BORDER}; padding: 6px; }}
        QTableWidget::item:selected {{ background: {ACCENT_BLUE}22; color: {TEXT_MAIN}; }}
    """)

    table.itemSelectionChanged.connect(lambda: _on_table_selection_changed(win))
    table.itemChanged.connect(lambda item: _on_table_item_changed(win, item))

    win.term_page_table = table
    lay.addWidget(table, 1)

    return frame


# -- Last Extraction Info Kartı --------------------------------------

def _build_last_extraction_card(win) -> QFrame:
    frame, lay = _card()
    lay.addWidget(_section_title("Son İşlem Bilgisi"))

    win.term_last_start_lbl = QLabel("—")
    win.term_last_end_lbl = QLabel("—")

    for k, lbl in [("Başlangıç Bölümü", win.term_last_start_lbl), ("Bitiş Bölümü", win.term_last_end_lbl)]:
        r = QHBoxLayout()
        kl = QLabel(k)
        kl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:11px;")
        lbl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:11px; font-weight:600;")
        r.addWidget(kl)
        r.addStretch()
        r.addWidget(lbl)
        lay.addLayout(r)

    return frame


# -- Term Details Kartı ----------------------------------------------

def _build_term_details_card(win) -> QFrame:
    frame, lay = _card()

    header = QHBoxLayout()
    header.addWidget(_section_title("Terim Detayları"))
    header.addStretch()

    edit_btn = QPushButton("✎ Düzenle")
    edit_btn.setObjectName("smallBtn")
    edit_btn.clicked.connect(lambda: _on_edit_selected_term(win))
    win.term_detail_edit_btn = edit_btn
    header.addWidget(edit_btn)

    lay.addLayout(header)

    lay.addWidget(_kv_label("Kaynak Terim", TEXT_FAINT, 10))
    win.term_detail_source = QLabel("—")
    win.term_detail_source.setStyleSheet(f"color:{TEXT_MAIN}; font-size:18px; font-weight:700;")
    lay.addWidget(win.term_detail_source)

    lay.addWidget(_kv_label("Hedef Çeviri", TEXT_FAINT, 10))
    win.term_detail_target = QLabel("—")
    win.term_detail_target.setStyleSheet(f"color:{TEXT_MAIN}; font-size:14px; font-weight:600;")
    lay.addWidget(win.term_detail_target)

    lay.addWidget(_kv_label("Notlar", TEXT_FAINT, 10))
    win.term_detail_note = QLabel("—")
    win.term_detail_note.setWordWrap(True)
    win.term_detail_note.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
    lay.addWidget(win.term_detail_note)

    lay.addWidget(_kv_label("Durum", TEXT_FAINT, 10))
    win.term_detail_status_badge = _badge("Approved", ACCENT_GREEN)
    lay.addWidget(win.term_detail_status_badge)

    lay.addSpacing(10)

    # Detay içi hızlı işlem butonları
    btn_row = QHBoxLayout()
    win.term_detail_approve_btn = QPushButton("✓ Onayla")
    win.term_detail_approve_btn.setObjectName("smallBtn")
    win.term_detail_approve_btn.setStyleSheet(f"background-color: {ACCENT_GREEN}; color: white;")
    win.term_detail_approve_btn.clicked.connect(lambda: _on_approve_selected_term(win))

    win.term_detail_delete_btn = QPushButton("🗑️ Sil")
    win.term_detail_delete_btn.setObjectName("smallBtn")
    win.term_detail_delete_btn.setStyleSheet(f"background-color: {ACCENT_RED}; color: white;")
    win.term_detail_delete_btn.clicked.connect(lambda: _on_delete_selected_term(win))

    btn_row.addWidget(win.term_detail_approve_btn)
    btn_row.addWidget(win.term_detail_delete_btn)
    lay.addLayout(btn_row)

    lay.addStretch()
    return frame


# ----------------------------------------------------------------------
# İŞ MANTIKLARI VE CANLI YENİLEME (VERİ ENTEGRASYONU)
# ----------------------------------------------------------------------

def _get_manager(win) -> TerminologyManager | None:
    project_path = getattr(win, 'current_project_path', None)
    if not project_path and hasattr(win, 'project_list') and win.project_list.currentItem():
        p_name = win.project_list.currentItem().text()
        if p_name:
            project_path = os.path.join(os.getcwd(), p_name)
    if project_path and os.path.exists(project_path):
        return TerminologyManager(project_path)
    return None


def refresh_terminology_page(win):
    """Projenin terminology.json verisini okur ve tüm arayüzü günceller."""
    manager = _get_manager(win)
    if not manager:
        if hasattr(win, 'term_page_table'):
            win.term_page_table.setRowCount(0)
        if hasattr(win, 'term_page_count_label'):
            win.term_page_count_label.setText("Proje seçilmedi")
        return

    terms = manager.get_all_terms()
    total_count = len(terms)
    pending_count = len(manager.get_pending_review_terms())
    approved_count = total_count - pending_count

    # Stats kartlarını güncelle
    if hasattr(win, 'term_stat_total'):
        win.term_stat_total.lbl_value.setText(f"{total_count:,}")
    if hasattr(win, 'term_stat_approved'):
        win.term_stat_approved.lbl_value.setText(f"{approved_count:,}")
        pct = (approved_count / total_count * 100) if total_count else 0
        win.term_stat_approved.lbl_sub.setText(f"{pct:.1f}%")
    if hasattr(win, 'term_stat_pending'):
        win.term_stat_pending.lbl_value.setText(f"{pending_count:,}")
        pct = (pending_count / total_count * 100) if total_count else 0
        win.term_stat_pending.lbl_sub.setText(f"{pct:.1f}%")

    # Son işlem bilgisini config.ini'den oku
    project_path = getattr(win, 'current_project_path', '')
    if project_path:
        config_path = os.path.join(project_path, "config", "config.ini")
        if os.path.exists(config_path):
            try:
                cfg = configparser.ConfigParser()
                cfg.read(config_path, encoding="utf-8")
                start = cfg.get("TerminologyOp", "last_start_chapter", fallback="—")
                end = cfg.get("TerminologyOp", "last_end_chapter", fallback="—")
                win.term_last_start_lbl.setText(str(start))
                win.term_last_end_lbl.setText(str(end))
            except Exception:
                pass

    _populate_table(win, terms)


def _populate_table(win, terms: list[dict]):
    table = win.term_page_table
    table.blockSignals(True)
    table.setRowCount(0)

    search_text = win.term_page_search_input.text().strip().lower()
    status_filter = win.term_page_status_filter.currentText()

    filtered_terms = []
    for t in terms:
        src = t.get("source", "")
        tgt = t.get("target", "")
        note = t.get("note", "")
        ambiguous = t.get("ambiguous", False)

        if search_text and (search_text not in src.lower() and search_text not in tgt.lower() and search_text not in note.lower()):
            continue

        if status_filter == "Onaylı" and ambiguous:
            continue
        if status_filter == "Gözden Geçirilecek" and not ambiguous:
            continue

        filtered_terms.append(t)

    table.setRowCount(len(filtered_terms))
    win.term_page_count_label.setText(f"{len(filtered_terms)} / {len(terms)} terim (Çift tıklayarak düzenleyin)")

    for row_idx, t in enumerate(filtered_terms):
        src = t.get("source", "")
        tgt = t.get("target", "")
        note = t.get("note", "")
        ambiguous = t.get("ambiguous", False)

        item_src = QTableWidgetItem(src)
        item_tgt = QTableWidgetItem(tgt)
        item_note = QTableWidgetItem(note)

        item_src.setData(Qt.ItemDataRole.UserRole, t)

        table.setItem(row_idx, 0, item_src)
        table.setItem(row_idx, 1, item_tgt)
        table.setItem(row_idx, 2, item_note)

        badge_text = "Gözden Geçir" if ambiguous else "Onaylı"
        badge_color = ACCENT_ORANGE if ambiguous else ACCENT_GREEN
        table.setCellWidget(row_idx, 3, _badge(badge_text, badge_color))

        # Satır içi hızlı sil butonu
        del_btn = QPushButton("🗑️")
        del_btn.setObjectName("iconBtn")
        del_btn.setToolTip(tr("terminology_page_extra.tooltip_delete_term", "Terimi Sil"))
        del_btn.clicked.connect(lambda checked, s=src: _delete_term_by_source(win, s))
        table.setCellWidget(row_idx, 4, del_btn)

    table.blockSignals(False)

    if len(filtered_terms) > 0:
        table.selectRow(0)
    else:
        _clear_term_details(win)


def _filter_table(win):
    manager = _get_manager(win)
    if manager:
        _populate_table(win, manager.get_all_terms())


def _on_table_item_changed(win, item: QTableWidgetItem):
    """Kullanıcı tabloda doğrudan bir hücreyi düzenlediğinde çalışır ve diske kaydeder."""
    table = win.term_page_table
    row = item.row()
    src_item = table.item(row, 0)
    tgt_item = table.item(row, 1)
    note_item = table.item(row, 2)

    if not src_item or not tgt_item:
        return

    old_data = src_item.data(Qt.ItemDataRole.UserRole)
    old_source = old_data.get("source", "") if old_data else src_item.text().strip()

    new_source = src_item.text().strip()
    new_target = tgt_item.text().strip()
    new_note = note_item.text().strip() if note_item else ""

    if not new_source or not new_target:
        return

    manager = _get_manager(win)
    if manager:
        # Eğer kaynak terim değiştiyse eskisini sil
        if old_source and old_source.lower() != new_source.lower():
            manager.remove_term(old_source)

        manager.add_term(new_source, new_target, new_note)
        # Detaylar panelini güncelle
        _on_table_selection_changed(win)


def _on_table_selection_changed(win):
    table = win.term_page_table
    selected_items = table.selectedItems()
    if not selected_items:
        _clear_term_details(win)
        return

    row = table.currentRow()
    src_item = table.item(row, 0)
    tgt_item = table.item(row, 1)
    note_item = table.item(row, 2)

    if not src_item:
        return

    term_data = src_item.data(Qt.ItemDataRole.UserRole) or {}

    src = src_item.text().strip() or term_data.get("source", "—")
    tgt = (tgt_item.text().strip() if tgt_item else "") or term_data.get("target", "—")
    note = (note_item.text().strip() if note_item else "") or term_data.get("note", "—") or "—"
    ambiguous = term_data.get("ambiguous", False)

    win.term_detail_source.setText(src)
    win.term_detail_target.setText(tgt)
    win.term_detail_note.setText(note)

    if hasattr(win, 'term_detail_edit_btn'):
        win.term_detail_edit_btn.setEnabled(True)

    if ambiguous:
        win.term_detail_status_badge.setText("Gözden Geçirilecek")
        win.term_detail_status_badge.setStyleSheet(f"color:{ACCENT_ORANGE}; background:{ACCENT_ORANGE}22; border:1px solid {ACCENT_ORANGE}55; border-radius:4px; padding:2px 8px;")
        win.term_detail_approve_btn.setEnabled(True)
    else:
        win.term_detail_status_badge.setText("Onaylı")
        win.term_detail_status_badge.setStyleSheet(f"color:{ACCENT_GREEN}; background:{ACCENT_GREEN}22; border:1px solid {ACCENT_GREEN}55; border-radius:4px; padding:2px 8px;")
        win.term_detail_approve_btn.setEnabled(False)


def _clear_term_details(win):
    win.term_detail_source.setText("—")
    win.term_detail_target.setText("—")
    win.term_detail_note.setText("—")
    win.term_detail_status_badge.setText("Seçim Yok")
    win.term_detail_approve_btn.setEnabled(False)
    if hasattr(win, 'term_detail_edit_btn'):
        win.term_detail_edit_btn.setEnabled(False)


def _on_edit_selected_term(win):
    """Sağ paneldeki 'Terimi Düzenle' butonuna basılınca açılan düzenleme penceresi."""
    table = win.term_page_table
    row = table.currentRow()
    if row < 0:
        return

    src_item = table.item(row, 0)
    tgt_item = table.item(row, 1)
    note_item = table.item(row, 2)

    if not src_item or not tgt_item:
        return

    old_src = src_item.text().strip()
    old_tgt = tgt_item.text().strip()
    old_note = note_item.text().strip() if note_item else ""

    dlg = QDialog(win)
    dlg.setWindowTitle(tr("terminology_page_extra.edit_term_title", "Terimi Düzenle"))
    dlg.setFixedWidth(380)

    lay = QVBoxLayout(dlg)
    lay.setSpacing(10)

    lay.addWidget(QLabel(tr("terminology_page_extra.label_source_term", "Kaynak Terim:")))
    src_input = QLineEdit(old_src)
    lay.addWidget(src_input)

    lay.addWidget(QLabel(tr("terminology_page_extra.label_target_term", "Hedef Çeviri:")))
    tgt_input = QLineEdit(old_tgt)
    lay.addWidget(tgt_input)

    lay.addWidget(QLabel(tr("terminology_page_extra.label_note", "Not:")))
    note_input = QLineEdit(old_note)
    lay.addWidget(note_input)

    save_btn = QPushButton("💾  Kaydet")
    save_btn.setObjectName("primaryBtn")
    save_btn.setStyleSheet(f"background-color: {ACCENT_GREEN}; color: white; font-weight: bold;")

    def _save():
        new_src = src_input.text().strip()
        new_tgt = tgt_input.text().strip()
        new_note = note_input.text().strip()

        if not new_src or not new_tgt:
            QMessageBox.warning(dlg, "Eksik", "Kaynak ve Hedef alanları boş olamaz.")
            return

        manager = _get_manager(win)
        if manager:
            if old_src.lower() != new_src.lower():
                manager.remove_term(old_src)
            manager.add_term(new_src, new_tgt, new_note)
            dlg.accept()
            refresh_terminology_page(win)

    save_btn.clicked.connect(_save)
    lay.addWidget(save_btn)

    dlg.exec()


def _on_add_term(win):
    manager = _get_manager(win)
    if not manager:
        QMessageBox.warning(win, "Hata", "Lütfen önce bir proje seçin.")
        return

    src = win.term_add_source.text().strip()
    tgt = win.term_add_target.text().strip()
    note = win.term_add_note.text().strip()

    if not src or not tgt:
        QMessageBox.warning(win, "Eksik Bilgi", "Kaynak ve Hedef terim alanları zorunludur.")
        return

    manager.add_term(src, tgt, note)
    win.term_add_source.clear()
    win.term_add_target.clear()
    win.term_add_note.clear()
    refresh_terminology_page(win)


def _delete_term_by_source(win, source: str):
    manager = _get_manager(win)
    if manager:
        manager.remove_term(source)
        refresh_terminology_page(win)


def _on_delete_selected_term(win):
    table = win.term_page_table
    row = table.currentRow()
    if row < 0:
        return
    src_item = table.item(row, 0)
    if src_item:
        source = src_item.text()
        _delete_term_by_source(win, source)


def _on_approve_selected_term(win):
    table = win.term_page_table
    row = table.currentRow()
    if row < 0:
        return
    src_item = table.item(row, 0)
    if src_item:
        source = src_item.text()
        manager = _get_manager(win)
        if manager:
            manager.approve_term(source)
            refresh_terminology_page(win)


def _on_import_terms(win):
    manager = _get_manager(win)
    if not manager:
        QMessageBox.warning(win, "Hata", "Lütfen önce bir proje seçin.")
        return

    text, ok = QInputDialog.getMultiLineText(
        win, tr("terminology.btn_import", "📥 İçe Aktar"),
        tr("terminology.msg_import_body", "Her satıra bir terim girin (kaynak=hedef formatında):"),
        ""
    )
    if ok and text:
        count = manager.import_from_text(text)
        QMessageBox.information(win, "Başarılı", f"{count} terim içe aktarıldı.")
        refresh_terminology_page(win)


def _on_export_terms(win):
    manager = _get_manager(win)
    if not manager:
        QMessageBox.warning(win, "Hata", "Lütfen önce bir proje seçin.")
        return

    text = manager.export_to_text()
    if not text:
        QMessageBox.information(win, "Boş", "Dışa aktarılacak terim yok.")
        return

    path, _ = QFileDialog.getSaveFileName(win, "Terimleri Kaydet", "terminology.txt", "Text Files (*.txt)")
    if path:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        QMessageBox.information(win, "Başarılı", f"Terimler başarıyla kaydedildi:\n{path}")


def _on_clear_terms(win):
    manager = _get_manager(win)
    if not manager:
        return

    reply = QMessageBox.question(
        win, "Tümünü Temizle",
        "Tüm terimleri silmek istediğinize emin misiniz?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    if reply == QMessageBox.StandardButton.Yes:
        manager.clear()
        refresh_terminology_page(win)

