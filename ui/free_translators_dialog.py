"""
free_translators_dialog.py — Ücretsiz Çeviriciler (DeepL, Yandex) ve Proxy Yönetim Paneli.

Özellikler:
  - Tek bir derli toplu diyalog (3 sekme):
      1. DeepL (API Key listesi, CRUD, Rotasyon, Gerçek Bağlantı Testi)
      2. Yandex (API Key listesi, CRUD, Rotasyon, Gerçek Bağlantı Testi)
      3. Google Translate Proxy (Proxy listesi, CRUD, Aktif proxy seçimi, Gerçek Bağlantı Testi)
  - AppConfigs/app_settings.json ile tam kalıcı çift yönlü senkronizasyon.
"""

import os
import json
import uuid
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QGroupBox, QFormLayout, QLineEdit,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QTabWidget, QWidget, QFrame,
    QCheckBox, QInputDialog, QApplication
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, pyqtSignal

from core.free_translators import (
    load_free_translators_config, save_free_translators_config,
    format_proxy_url, test_proxy_connection,
    DeepLTranslator, YandexTranslator
)
from ui.dark_theme import (
    BG_APP, BG_PANEL, BG_PANEL2, BORDER, TEXT_MAIN, TEXT_DIM, TEXT_FAINT,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED, ACCENT_PURPLE
)
from logger import app_logger
from core.localization import tr


class FreeTranslatorsDialog(QDialog):
    """DeepL, Yandex ve Google Proxy ayarlarını tek ekranda yöneten panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("free_translators.dialog_title", "Ücretsiz Çeviriciler ve Proxy Yönetimi"))
        self.setMinimumSize(780, 560)
        self.resize(840, 600)

        self.config_data = load_free_translators_config()

        self._init_ui()
        self._load_data_to_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Üst Bilgi Başlığı
        header_row = QHBoxLayout()
        icon_lbl = QLabel("🌐")
        icon_lbl.setStyleSheet(f"font-size: 22px; padding: 4px;")
        header_row.addWidget(icon_lbl)

        header_text_box = QVBoxLayout()
        title_lbl = QLabel(tr("free_translators.header_title", "Ücretsiz Çeviriciler & Proxy Yapılandırması"))
        title_lbl.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 15px; font-weight: 700;")
        sub_lbl = QLabel(tr("free_translators.header_sub", "DeepL, Yandex anahtarlarını, rotasyon havuzlarını ve Google Translate proxy'lerini yönetin."))
        sub_lbl.setStyleSheet(f"color: {TEXT_FAINT}; font-size: 11px;")
        header_text_box.addWidget(title_lbl)
        header_text_box.addWidget(sub_lbl)
        header_row.addLayout(header_text_box)
        header_row.addStretch()

        main_layout.addLayout(header_row)

        # Sekme Kontrolü
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER};
                background: {BG_PANEL};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background: {BG_PANEL2};
                color: {TEXT_DIM};
                padding: 8px 18px;
                font-weight: 600;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background: {BG_PANEL};
                color: {ACCENT_BLUE};
                border-bottom: 2px solid {ACCENT_BLUE};
            }}
        """)

        # Sekmeler oluştur
        self.tab_deepl = self._build_deepl_tab()
        self.tab_yandex = self._build_yandex_tab()
        self.tab_proxy = self._build_proxy_tab()

        self.tabs.addTab(self.tab_deepl, "🔵 DeepL")
        self.tabs.addTab(self.tab_yandex, "🔴 Yandex")
        self.tabs.addTab(self.tab_proxy, "🛡️ Google Translate (Proxy)")

        main_layout.addWidget(self.tabs)

        # Alt Butonlar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self.btn_save_all = QPushButton(tr("free_translators.btn_save_all", "💾 Tüm Ayarları Kaydet"))
        self.btn_save_all.setStyleSheet(f"""
            background-color: {ACCENT_BLUE}; color: white;
            font-weight: bold; padding: 8px 20px; border-radius: 6px;
        """)
        self.btn_save_all.clicked.connect(self._on_save_all)

        self.btn_cancel = QPushButton(tr("free_translators.btn_close", "Kapat"))
        self.btn_cancel.setStyleSheet(f"""
            background-color: {BG_PANEL2}; color: {TEXT_MAIN};
            border: 1px solid {BORDER}; padding: 8px 18px; border-radius: 6px;
        """)
        self.btn_cancel.clicked.connect(self.reject)

        bottom_bar.addStretch()
        bottom_bar.addWidget(self.btn_cancel)
        bottom_bar.addWidget(self.btn_save_all)

        main_layout.addLayout(bottom_bar)

    # -------------------------------------------------------------------------
    # Sekme 1: DeepL
    # -------------------------------------------------------------------------
    def _build_deepl_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        # Bilgi kutusu
        info = QLabel(
            "DeepL Free (:fx) veya DeepL Pro API anahtarlarınızı girin.\n"
            "Birden fazla anahtar girildiğinde rotasyon etkinleştirilirse round-robin olarak dönüşümlü kullanılır."
        )
        info.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        lay.addWidget(info)

        # Anahtar Listesi
        lay.addWidget(QLabel("Kayıtlı DeepL API Anahtarları:"))
        self.deepl_list = QListWidget()
        self.deepl_list.setStyleSheet(f"background: {BG_PANEL2}; border: 1px solid {BORDER}; border-radius: 6px;")
        lay.addWidget(self.deepl_list)

        # Butonlar (Ekle / Düzenle / Sil)
        btn_row = QHBoxLayout()
        self.btn_deepl_add = QPushButton("➕ Anahtar Ekle")
        self.btn_deepl_add.clicked.connect(self._add_deepl_key)
        self.btn_deepl_edit = QPushButton("✏️ Düzenle")
        self.btn_deepl_edit.clicked.connect(self._edit_deepl_key)
        self.btn_deepl_del = QPushButton("🗑️ Sil")
        self.btn_deepl_del.setStyleSheet(f"color: {ACCENT_RED};")
        self.btn_deepl_del.clicked.connect(self._delete_deepl_key)

        btn_row.addWidget(self.btn_deepl_add)
        btn_row.addWidget(self.btn_deepl_edit)
        btn_row.addWidget(self.btn_deepl_del)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # Rotasyon Switch
        self.deepl_rot_check = QCheckBox("DeepL Anahtar Rotasyonu (Round-Robin)")
        self.deepl_rot_check.setStyleSheet(f"color: {TEXT_MAIN}; font-weight: 600; font-size: 12px;")
        lay.addWidget(self.deepl_rot_check)

        # Test Bölümü
        test_group = QGroupBox("Bağlantı Testi")
        test_group.setStyleSheet(f"QGroupBox {{ color: {TEXT_MAIN}; border: 1px solid {BORDER}; border-radius: 6px; margin-top: 6px; padding: 10px; }}")
        t_lay = QVBoxLayout(test_group)
        t_row = QHBoxLayout()

        self.deepl_test_input = QLineEdit()
        self.deepl_test_input.setPlaceholderText("Test edilecek DeepL API Key (veya listeden seçin)")
        self.btn_deepl_test = QPushButton("🔗 Test Et")
        self.btn_deepl_test.setStyleSheet(f"background-color: {ACCENT_ORANGE}; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_deepl_test.clicked.connect(self._test_deepl)

        t_row.addWidget(self.deepl_test_input)
        t_row.addWidget(self.btn_deepl_test)
        t_lay.addLayout(t_row)

        self.deepl_test_result = QLabel("")
        self.deepl_test_result.setWordWrap(True)
        t_lay.addWidget(self.deepl_test_result)
        lay.addWidget(test_group)

        self.deepl_list.currentItemChanged.connect(
            lambda cur: self.deepl_test_input.setText(cur.text().strip()) if cur else None
        )

        return w

    # -------------------------------------------------------------------------
    # Sekme 2: Yandex
    # -------------------------------------------------------------------------
    def _build_yandex_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        # Bilgi kutusu
        info = QLabel(
            "Yandex Sözlük ('dict.1.1...') veya Yandex Çeviri API anahtarlarınızı girin.\n"
            "Anahtar girilmezse veya geçersizse sistem otomatik olarak MyMemory Translator fallback kullanır."
        )
        info.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        lay.addWidget(info)

        # Anahtar Listesi
        lay.addWidget(QLabel("Kayıtlı Yandex API Anahtarları:"))
        self.yandex_list = QListWidget()
        self.yandex_list.setStyleSheet(f"background: {BG_PANEL2}; border: 1px solid {BORDER}; border-radius: 6px;")
        lay.addWidget(self.yandex_list)

        # Butonlar
        btn_row = QHBoxLayout()
        self.btn_yandex_add = QPushButton("➕ Anahtar Ekle")
        self.btn_yandex_add.clicked.connect(self._add_yandex_key)
        self.btn_yandex_edit = QPushButton("✏️ Düzenle")
        self.btn_yandex_edit.clicked.connect(self._edit_yandex_key)
        self.btn_yandex_del = QPushButton("🗑️ Sil")
        self.btn_yandex_del.setStyleSheet(f"color: {ACCENT_RED};")
        self.btn_yandex_del.clicked.connect(self._delete_yandex_key)

        btn_row.addWidget(self.btn_yandex_add)
        btn_row.addWidget(self.btn_yandex_edit)
        btn_row.addWidget(self.btn_yandex_del)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # Rotasyon Switch
        self.yandex_rot_check = QCheckBox("Yandex Anahtar Rotasyonu (Round-Robin)")
        self.yandex_rot_check.setStyleSheet(f"color: {TEXT_MAIN}; font-weight: 600; font-size: 12px;")
        lay.addWidget(self.yandex_rot_check)

        # Test Bölümü
        test_group = QGroupBox("Bağlantı Testi")
        test_group.setStyleSheet(f"QGroupBox {{ color: {TEXT_MAIN}; border: 1px solid {BORDER}; border-radius: 6px; margin-top: 6px; padding: 10px; }}")
        t_lay = QVBoxLayout(test_group)
        t_row = QHBoxLayout()

        self.yandex_test_input = QLineEdit()
        self.yandex_test_input.setPlaceholderText("Test edilecek Yandex API Key (veya listeden seçin)")
        self.btn_yandex_test = QPushButton("🔗 Test Et")
        self.btn_yandex_test.setStyleSheet(f"background-color: {ACCENT_ORANGE}; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_yandex_test.clicked.connect(self._test_yandex)

        t_row.addWidget(self.yandex_test_input)
        t_row.addWidget(self.btn_yandex_test)
        t_lay.addLayout(t_row)

        self.yandex_test_result = QLabel("")
        self.yandex_test_result.setWordWrap(True)
        t_lay.addWidget(self.yandex_test_result)
        lay.addWidget(test_group)

        self.yandex_list.currentItemChanged.connect(
            lambda cur: self.yandex_test_input.setText(cur.text().strip()) if cur else None
        )

        return w

    # -------------------------------------------------------------------------
    # Sekme 3: Google Translate (Proxy)
    # -------------------------------------------------------------------------
    def _build_proxy_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        info = QLabel(
            "Google Translate isteklerinin IP engeline takılmaması için proxy ekleyin.\n"
            "Desteklenen türler: HTTP, HTTPS, SOCKS4, SOCKS5 (kullanıcı adı ve şifre opsiyoneldir)."
        )
        info.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        lay.addWidget(info)

        # Proxy Tablosu
        self.proxy_table = QTableWidget()
        self.proxy_table.setColumnCount(5)
        self.proxy_table.setHorizontalHeaderLabels(["Aktif", "Tür", "Host", "Port", "Kullanıcı Adı"])
        self.proxy_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.proxy_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.proxy_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.proxy_table.setStyleSheet(f"background: {BG_PANEL2}; border: 1px solid {BORDER};")
        lay.addWidget(self.proxy_table)

        # Form Alanları (Düzenleme / Ekleme için)
        form_box = QGroupBox("Proxy Bilgileri (Ekle / Düzenle)")
        form_box.setStyleSheet(f"QGroupBox {{ color: {TEXT_MAIN}; border: 1px solid {BORDER}; border-radius: 6px; padding: 10px; }}")
        f_lay = QFormLayout(form_box)

        self.p_type_combo = QComboBox()
        self.p_type_combo.addItems(["http", "https", "socks4", "socks5"])
        self.p_host_input = QLineEdit()
        self.p_host_input.setPlaceholderText("örn: 185.147.69.48")
        self.p_port_input = QSpinBox()
        self.p_port_input.setRange(1, 65535)
        self.p_port_input.setValue(1080)
        self.p_user_input = QLineEdit()
        self.p_user_input.setPlaceholderText("Opsiyonel")
        self.p_pass_input = QLineEdit()
        self.p_pass_input.setPlaceholderText("Opsiyonel")
        self.p_pass_input.setEchoMode(QLineEdit.EchoMode.Password)

        f_lay.addRow("Proxy Türü:", self.p_type_combo)
        f_lay.addRow("Sunucu (Host):", self.p_host_input)
        f_lay.addRow("Port:", self.p_port_input)
        f_lay.addRow("Kullanıcı Adı:", self.p_user_input)
        f_lay.addRow("Şifre:", self.p_pass_input)

        lay.addWidget(form_box)

        # Tablo Alt Butonları
        btn_bar = QHBoxLayout()
        self.btn_proxy_add = QPushButton("➕ Yeni Proxy Ekle")
        self.btn_proxy_add.clicked.connect(self._add_proxy)
        self.btn_proxy_update = QPushButton("💾 Seçiliyi Güncelle")
        self.btn_proxy_update.clicked.connect(self._update_selected_proxy)
        self.btn_proxy_del = QPushButton("🗑️ Sil")
        self.btn_proxy_del.setStyleSheet(f"color: {ACCENT_RED};")
        self.btn_proxy_del.clicked.connect(self._delete_selected_proxy)
        self.btn_proxy_set_active = QPushButton("⭐ Aktif Yap")
        self.btn_proxy_set_active.setStyleSheet(f"background-color: {ACCENT_GREEN}; color: white; font-weight: bold;")
        self.btn_proxy_set_active.clicked.connect(self._set_active_proxy)

        self.btn_proxy_test = QPushButton("🔗 Bu Proxy'yi Test Et")
        self.btn_proxy_test.setStyleSheet(f"background-color: {ACCENT_ORANGE}; color: white; font-weight: bold;")
        self.btn_proxy_test.clicked.connect(self._test_current_proxy)

        btn_bar.addWidget(self.btn_proxy_add)
        btn_bar.addWidget(self.btn_proxy_update)
        btn_bar.addWidget(self.btn_proxy_del)
        btn_bar.addWidget(self.btn_proxy_set_active)
        btn_bar.addWidget(self.btn_proxy_test)
        lay.addLayout(btn_bar)

        self.proxy_test_result = QLabel("")
        self.proxy_test_result.setWordWrap(True)
        lay.addWidget(self.proxy_test_result)

        self.proxy_table.itemSelectionChanged.connect(self._on_proxy_table_selected)

        return w

    # -------------------------------------------------------------------------
    # Veri Yükleme ve Arayüz Güncelleme
    # -------------------------------------------------------------------------
    def _load_data_to_ui(self):
        # DeepL
        self.deepl_list.clear()
        for k in self.config_data.get("deepl_keys", []):
            self.deepl_list.addItem(k)
        self.deepl_rot_check.setChecked(self.config_data.get("deepl_use_rotation", True))

        # Yandex
        self.yandex_list.clear()
        for k in self.config_data.get("yandex_keys", []):
            self.yandex_list.addItem(k)
        self.yandex_rot_check.setChecked(self.config_data.get("yandex_use_rotation", True))

        # Proxies
        self._refresh_proxy_table()

    def _refresh_proxy_table(self):
        proxies = self.config_data.get("proxies", [])
        self.proxy_table.setRowCount(len(proxies))

        for row, p in enumerate(proxies):
            is_active = p.get("active", False)
            active_item = QTableWidgetItem("✅ Aktif" if is_active else "—")
            if is_active:
                active_item.setForeground(QColor(ACCENT_GREEN))

            self.proxy_table.setItem(row, 0, active_item)
            self.proxy_table.setItem(row, 1, QTableWidgetItem(p.get("type", "http")))
            self.proxy_table.setItem(row, 2, QTableWidgetItem(p.get("host", "")))
            self.proxy_table.setItem(row, 3, QTableWidgetItem(str(p.get("port", ""))))
            self.proxy_table.setItem(row, 4, QTableWidgetItem(p.get("username", "")))

    # -------------------------------------------------------------------------
    # DeepL Eylemleri
    # -------------------------------------------------------------------------
    def _add_deepl_key(self):
        text, ok = QInputDialog.getText(self, "DeepL Anahtarı Ekle", "Yeni DeepL API Anahtarı:")
        if ok and text.strip():
            key = text.strip()
            self.deepl_list.addItem(key)
            self.deepl_test_input.setText(key)

    def _edit_deepl_key(self):
        cur = self.deepl_list.currentItem()
        if not cur:
            QMessageBox.information(self, "Bilgi", "Lütfen düzenlenecek anahtarı seçin.")
            return
        text, ok = QInputDialog.getText(self, "DeepL Anahtarını Düzenle", "API Anahtarı:", text=cur.text())
        if ok and text.strip():
            cur.setText(text.strip())
            self.deepl_test_input.setText(text.strip())

    def _delete_deepl_key(self):
        cur_row = self.deepl_list.currentRow()
        if cur_row < 0:
            QMessageBox.information(self, "Bilgi", "Lütfen silinecek anahtarı seçin.")
            return
        if QMessageBox.question(self, "Onay", "Bu anahtarı silmek istediğinize emin misiniz?") == QMessageBox.StandardButton.Yes:
            self.deepl_list.takeItem(cur_row)
            self.deepl_test_input.clear()

    def _test_deepl(self):
        key = self.deepl_test_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Uyarı", "Lütfen test edilecek bir DeepL API anahtarı girin.")
            return

        self.deepl_test_result.setText("⏳ DeepL bağlantısı test ediliyor...")
        self.deepl_test_result.setStyleSheet(f"color: {ACCENT_ORANGE}; font-weight: 600;")
        QApplication.processEvents()

        ok, msg = DeepLTranslator.test_connection(key)
        if ok:
            self.deepl_test_result.setText(f"✅ {msg}")
            self.deepl_test_result.setStyleSheet(f"color: {ACCENT_GREEN}; font-weight: 600;")
        else:
            self.deepl_test_result.setText(f"❌ {msg}")
            self.deepl_test_result.setStyleSheet(f"color: {ACCENT_RED}; font-weight: 600;")

    # -------------------------------------------------------------------------
    # Yandex Eylemleri
    # -------------------------------------------------------------------------
    def _add_yandex_key(self):
        text, ok = QInputDialog.getText(self, "Yandex Anahtarı Ekle", "Yeni Yandex API Anahtarı:")
        if ok and text.strip():
            key = text.strip()
            self.yandex_list.addItem(key)
            self.yandex_test_input.setText(key)

    def _edit_yandex_key(self):
        cur = self.yandex_list.currentItem()
        if not cur:
            QMessageBox.information(self, "Bilgi", "Lütfen düzenlenecek anahtarı seçin.")
            return
        text, ok = QInputDialog.getText(self, "Yandex Anahtarını Düzenle", "API Anahtarı:", text=cur.text())
        if ok and text.strip():
            cur.setText(text.strip())
            self.yandex_test_input.setText(text.strip())

    def _delete_yandex_key(self):
        cur_row = self.yandex_list.currentRow()
        if cur_row < 0:
            QMessageBox.information(self, "Bilgi", "Lütfen silinecek anahtarı seçin.")
            return
        if QMessageBox.question(self, "Onay", "Bu anahtarı silmek istediğinize emin misiniz?") == QMessageBox.StandardButton.Yes:
            self.yandex_list.takeItem(cur_row)
            self.yandex_test_input.clear()

    def _test_yandex(self):
        key = self.yandex_test_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Uyarı", "Lütfen test edilecek bir Yandex API anahtarı girin.")
            return

        self.yandex_test_result.setText("⏳ Yandex bağlantısı test ediliyor...")
        self.yandex_test_result.setStyleSheet(f"color: {ACCENT_ORANGE}; font-weight: 600;")
        QApplication.processEvents()

        ok, msg = YandexTranslator.test_connection(key)
        if ok:
            self.yandex_test_result.setText(f"✅ {msg}")
            self.yandex_test_result.setStyleSheet(f"color: {ACCENT_GREEN}; font-weight: 600;")
        else:
            self.yandex_test_result.setText(f"❌ {msg}")
            self.yandex_test_result.setStyleSheet(f"color: {ACCENT_RED}; font-weight: 600;")

    # -------------------------------------------------------------------------
    # Proxy Eylemleri
    # -------------------------------------------------------------------------
    def _on_proxy_table_selected(self):
        row = self.proxy_table.currentRow()
        proxies = self.config_data.get("proxies", [])
        if 0 <= row < len(proxies):
            p = proxies[row]
            self.p_type_combo.setCurrentText(p.get("type", "http"))
            self.p_host_input.setText(p.get("host", ""))
            self.p_port_input.setValue(int(p.get("port", 1080)))
            self.p_user_input.setText(p.get("username", ""))
            self.p_pass_input.setText(p.get("password", ""))

    def _get_form_proxy_dict(self) -> dict | None:
        host = self.p_host_input.text().strip()
        if not host:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen proxy sunucu (host) adresini girin.")
            return None
        return {
            "id": str(uuid.uuid4())[:8],
            "type": self.p_type_combo.currentText(),
            "host": host,
            "port": self.p_port_input.value(),
            "username": self.p_user_input.text().strip(),
            "password": self.p_pass_input.text().strip(),
            "active": False
        }

    def _add_proxy(self):
        p = self._get_form_proxy_dict()
        if not p:
            return
        proxies = self.config_data.setdefault("proxies", [])
        # İlk proxy ise otomatik aktif yap
        if len(proxies) == 0:
            p["active"] = True
        proxies.append(p)
        self._refresh_proxy_table()
        self.proxy_table.selectRow(len(proxies) - 1)

    def _update_selected_proxy(self):
        row = self.proxy_table.currentRow()
        proxies = self.config_data.get("proxies", [])
        if 0 <= row < len(proxies):
            new_p = self._get_form_proxy_dict()
            if not new_p:
                return
            new_p["id"] = proxies[row].get("id", str(uuid.uuid4())[:8])
            new_p["active"] = proxies[row].get("active", False)
            proxies[row] = new_p
            self._refresh_proxy_table()
            self.proxy_table.selectRow(row)
        else:
            QMessageBox.information(self, "Bilgi", "Lütfen güncellenecek bir proxy seçin.")

    def _delete_selected_proxy(self):
        row = self.proxy_table.currentRow()
        proxies = self.config_data.get("proxies", [])
        if 0 <= row < len(proxies):
            if QMessageBox.question(self, "Onay", "Seçili proxy'yi silmek istediğinize emin misiniz?") == QMessageBox.StandardButton.Yes:
                removed = proxies.pop(row)
                if removed.get("active") and proxies:
                    proxies[0]["active"] = True
                self._refresh_proxy_table()
                self._clear_proxy_form()
        else:
            QMessageBox.information(self, "Bilgi", "Lütfen silinecek bir proxy seçin.")

    def _set_active_proxy(self):
        row = self.proxy_table.currentRow()
        proxies = self.config_data.get("proxies", [])
        if 0 <= row < len(proxies):
            for i, p in enumerate(proxies):
                p["active"] = (i == row)
            self._refresh_proxy_table()
            self.proxy_table.selectRow(row)
        else:
            QMessageBox.information(self, "Bilgi", "Lütfen aktif yapılacak bir proxy seçin.")

    def _clear_proxy_form(self):
        self.p_host_input.clear()
        self.p_port_input.setValue(1080)
        self.p_user_input.clear()
        self.p_pass_input.clear()

    def _test_current_proxy(self):
        p = self._get_form_proxy_dict()
        if not p:
            return

        self.proxy_test_result.setText("⏳ Proxy üzerinden bağlantı test ediliyor...")
        self.proxy_test_result.setStyleSheet(f"color: {ACCENT_ORANGE}; font-weight: 600;")
        QApplication.processEvents()

        ok, msg = test_proxy_connection(p, timeout=7)
        if ok:
            self.proxy_test_result.setText(f"✅ {msg}")
            self.proxy_test_result.setStyleSheet(f"color: {ACCENT_GREEN}; font-weight: 600;")
        else:
            self.proxy_test_result.setText(f"❌ {msg}")
            self.proxy_test_result.setStyleSheet(f"color: {ACCENT_RED}; font-weight: 600;")

    # -------------------------------------------------------------------------
    # Kaydet & Senkronizasyon
    # -------------------------------------------------------------------------
    def _on_save_all(self):
        # DeepL
        deepl_keys = []
        for i in range(self.deepl_list.count()):
            k = self.deepl_list.item(i).text().strip()
            if k:
                deepl_keys.append(k)

        # Yandex
        yandex_keys = []
        for i in range(self.yandex_list.count()):
            k = self.yandex_list.item(i).text().strip()
            if k:
                yandex_keys.append(k)

        # Proxies
        proxies = self.config_data.get("proxies", [])
        google_proxy = {}
        for p in proxies:
            if p.get("active"):
                url = format_proxy_url(p)
                if url:
                    google_proxy = {"http": url, "https": url}
                break

        to_save = {
            "deepl_keys": deepl_keys,
            "deepl_use_rotation": self.deepl_rot_check.isChecked(),
            "yandex_keys": yandex_keys,
            "yandex_use_rotation": self.yandex_rot_check.isChecked(),
            "proxies": proxies,
            "google_proxy": google_proxy
        }

        success = save_free_translators_config(to_save)
        if success:
            QMessageBox.information(self, "Başarılı", "Çevirici ve proxy ayarları başarıyla kaydedildi.")
            self.accept()
        else:
            QMessageBox.critical(self, "Hata", "Ayarlar kaydedilirken bir hata oluştu.")
