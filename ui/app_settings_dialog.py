"""
AppSettingsDialog — Uygulama geneli ayarlar penceresi.

Özellikler:
  - Tema seçeneği (Karanlık / Aydınlık / Sistem)
  - ML Terminoloji maks token limiti
  - Özel JS Script kaynağı ekleme (site adı + JS dosya yolu)
  - Log seviyesi seçimi
  - Ayarlar AppConfigs/app_settings.json içinde saklanır
"""

import os
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QGroupBox, QFormLayout, QLineEdit,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QTabWidget, QWidget, QFrame, QInputDialog
)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt, pyqtSignal
from logger import app_logger

APP_SETTINGS_FILE = os.path.join(os.getcwd(), "AppConfigs", "app_settings.json")

DEFAULT_SETTINGS = {
    "theme": "dark",
    "ml_max_tokens": 450000,
    "log_level": "INFO",
    "custom_js_sources": [],   # [{"name": "Site Adı", "js_path": "/path/to/script.js"}, ...]
    "notifications_enabled": True,
    "promt_generator_max_tokens": 40000,
}

THEMES = {
    "dark":          "Karanlık Mod (Material Teal)",
    "dark_blue":     "Karanlık Mod (Material Blue)",
    "dark_purple":   "Karanlık Mod (Material Purple)",
    "dark_amber":    "Karanlık Mod (Material Amber)",
    "light":         "Aydınlık Mod",
    "system":        "Sistem Varsayılanı",
}

# qt-material tema XML eşlemeleri
MATERIAL_THEME_MAP = {
    "dark":        "dark_teal.xml",
    "dark_blue":   "dark_blue.xml",
    "dark_purple": "dark_purple.xml",
    "dark_amber":  "dark_amber.xml",
    "light":       "light_blue.xml",
}


def load_app_settings() -> dict:
    """AppConfigs/app_settings.json dosyasını okur. Yoksa varsayılanı döndürür."""
    if os.path.exists(APP_SETTINGS_FILE):
        try:
            with open(APP_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Eksik anahtarları varsayılanla tamamla
            for k, v in DEFAULT_SETTINGS.items():
                data.setdefault(k, v)
            return data
        except Exception as e:
            app_logger.warning(f"app_settings.json okunamadı: {e}")
    return DEFAULT_SETTINGS.copy()


def save_app_settings(settings: dict):
    """Ayarları AppConfigs/app_settings.json dosyasına kaydeder."""
    os.makedirs(os.path.dirname(APP_SETTINGS_FILE), exist_ok=True)
    try:
        with open(APP_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        app_logger.error(f"app_settings.json kaydedilemedi: {e}")


def apply_theme(app, theme_name: str):
    """
    Üç aşamalı tema motoru:
      0. Özel JSON tema: ThemeEngine ile token → QSS dönüşümü (öncelikli)
      1. qt-material: Kapsamlı Material Design base stili uygular (yerleşik temalar)
      2. Özel QSS override: AppConfigs/themes/{theme_name}.qss ile
         proje spesifik stilleri (buton renkleri, gradient progress bar vb.) üstüne bindirir.

    qt-material yüklü değilse graceful fallback: sadece özel QSS kullanılır.
    """
    if theme_name == "system":
        app.setStyleSheet("")
        app_logger.info("Tema: Sistem varsayılanı uygulandı.")
        return

    # ── Aşama 0: Özel JSON tema kontrolü ──
    custom_json_file = os.path.join(os.getcwd(), "AppConfigs", "themes", f"{theme_name}.json")
    if os.path.exists(custom_json_file) and theme_name not in ("dark", "light"):
        try:
            from core.theme_engine import load_theme_tokens, tokens_to_qss
            tokens = load_theme_tokens(theme_name)
            custom_qss = tokens_to_qss(tokens)
            app.setStyleSheet(custom_qss)
            app_logger.info(f"Özel JSON teması uygulandı: {theme_name}")
            return
        except Exception as e:
            app_logger.error(f"Özel JSON teması uygulanamadı ({theme_name}): {e}")
            # Fallback: yerleşik tema mantığına devam et

    # Aşama 1: qt-material base tema
    material_applied = False
    material_theme = MATERIAL_THEME_MAP.get(theme_name)
    if material_theme:
        try:
            from qt_material import apply_stylesheet
            # extra: font ve yoğunluk ayarları
            extra = {
                'font_family':    'Segoe UI Variable, Segoe UI',
                'font_size':      '10px',
                'density_scale':  '-1',   # Kompakt görünüm
                'button_shape':   'default',
            }
            apply_stylesheet(app, theme=material_theme, extra=extra)
            material_applied = True
            app_logger.info(f"qt-material teması uygulandı: {material_theme}")
        except ImportError:
            app_logger.warning(
                "qt-material yüklü değil. Özel QSS'e geçiliyor. "
                "Yüklemek için: pip install qt-material"
            )
        except Exception as e:
            app_logger.error(f"qt-material uygulanamadı: {e}")

    # Aşama 2: Özel QSS override katmanı 
    # Hem material üstüne hem de fallback olarak uygulanır
    # dark_blue, dark_purple, dark_amber varyantları için dark.qss override kullanılır
    override_name = theme_name if theme_name in ("dark", "light") else (
        "dark" if theme_name.startswith("dark") else "light"
    )
    theme_file = os.path.join(os.getcwd(), "AppConfigs", "themes", f"{override_name}.qss")
    if os.path.exists(theme_file):
        try:
            with open(theme_file, "r", encoding="utf-8") as f:
                extra_qss = f.read()
            # Mevcut stile ekle (material üstüne bindir)
            current_ss = app.styleSheet() if material_applied else ""
            app.setStyleSheet(current_ss + "\n" + extra_qss)
            app_logger.info(f"QSS override katmanı uygulandı: {override_name}.qss")
        except Exception as e:
            app_logger.error(f"Tema override dosyası okunamadı ({override_name}): {e}")
    else:
        if not material_applied:
            app_logger.warning(f"Tema dosyası bulunamadı ve qt-material yüklü değil: {theme_file}")



class AppSettingsDialog(QDialog):
    """Uygulama Ayarları Penceresi."""

    settings_changed = pyqtSignal(dict)  # Ayarlar değiştiğinde sinyal

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Uygulama Ayarları")
        self.resize(580, 500)
        self.settings = load_app_settings()

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Başlık
        title = QLabel("Uygulama Ayarları")
        title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Sekmeler
        tabs = QTabWidget()

        # Aşama 1: Görünüm
        appearance_tab = QWidget()
        app_layout = QFormLayout(appearance_tab)
        app_layout.setSpacing(12)

        self.theme_combo = QComboBox()
        self._refresh_theme_combo()

        # Tema combo + yönetici butonları yan yana
        theme_row = QHBoxLayout()
        theme_row.setSpacing(4)
        theme_row.addWidget(self.theme_combo, 1)
        theme_edit_btn = QPushButton("🖊️ Düzenle")
        theme_edit_btn.setFixedWidth(90)
        theme_edit_btn.setToolTip("Tema Yöneticisini aç")
        theme_edit_btn.clicked.connect(self._open_theme_manager)
        theme_row.addWidget(theme_edit_btn)
        self._save_as_theme_btn = QPushButton("💾 Farklı Kaydet")
        self._save_as_theme_btn.setFixedWidth(110)
        self._save_as_theme_btn.setToolTip("Aktif temayı farklı isimle kaydet")
        self._save_as_theme_btn.clicked.connect(self._save_theme_as)
        theme_row.addWidget(self._save_as_theme_btn)

        app_layout.addRow("🎨 Tema:", theme_row)

        self.notif_combo = QComboBox()
        self.notif_combo.addItems(["Etkin", "Devre Dışı"])
        self.notif_combo.setCurrentIndex(0 if self.settings.get("notifications_enabled", True) else 1)
        app_layout.addRow("🔔 Bildirimler:", self.notif_combo)

        self.log_combo = QComboBox()
        self.log_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        log_level = self.settings.get("log_level", "INFO")
        log_idx = ["DEBUG", "INFO", "WARNING", "ERROR"].index(log_level) if log_level in ["DEBUG", "INFO", "WARNING", "ERROR"] else 1
        self.log_combo.setCurrentIndex(log_idx)
        app_layout.addRow("📋 Log Seviyesi:", self.log_combo)

        tabs.addTab(appearance_tab, "🎨 Görünüm")

        # Sekme 2: ML / Terminoloji 
        ml_tab = QWidget()
        ml_layout = QFormLayout(ml_tab)
        ml_layout.setSpacing(12)

        self.ml_token_spin = QSpinBox()
        self.ml_token_spin.setMinimum(50000)
        self.ml_token_spin.setMaximum(2000000)
        self.ml_token_spin.setSingleStep(50000)
        self.ml_token_spin.setValue(self.settings.get("ml_max_tokens", 450000))
        self.ml_token_spin.setSuffix(" token")
        ml_layout.addRow("🤖 ML Maks Token:", self.ml_token_spin)

        token_note = QLabel("Bu değer, Yapay Zeka ile Terminoloji Üret işleminde\ngönderilecek maksimum kaynak metin boyutunu belirler.")
        token_note.setStyleSheet("color: #888; font-size: 9pt;")
        ml_layout.addRow("", token_note)

        self.prompt_gen_token_spin = QSpinBox()
        self.prompt_gen_token_spin.setMinimum(5000)
        self.prompt_gen_token_spin.setMaximum(200000)
        self.prompt_gen_token_spin.setSingleStep(5000)
        self.prompt_gen_token_spin.setValue(self.settings.get("promt_generator_max_tokens", 40000))
        self.prompt_gen_token_spin.setSuffix(" token")
        ml_layout.addRow("📝 Prompt Gen Maks Token:", self.prompt_gen_token_spin)

        prompt_note = QLabel("Bu değer, Prompt Generator'ın bölüm örneklemesi sırasında\nkullanacağı maksimum token limitini belirler.")
        prompt_note.setStyleSheet("color: #888; font-size: 9pt;")
        ml_layout.addRow("", prompt_note)

        tabs.addTab(ml_tab, "🤖 ML / Terminoloji")

        # Sekme 3: Özel JS Kaynaklar
        js_tab = QWidget()
        js_layout = QVBoxLayout(js_tab)

        js_note = QLabel("İndirme yöntemi listesine özel JavaScript tabanlı site kaynaklarınızı ekleyebilirsiniz.")
        js_note.setWordWrap(True)
        js_note.setStyleSheet("color: #AAA; font-size: 9pt; margin-bottom: 6px;")
        js_layout.addWidget(js_note)

        self.js_list_widget = QListWidget()
        self.js_list_widget.setMaximumHeight(160)
        self._refresh_js_list()
        js_layout.addWidget(self.js_list_widget)

        # Ekleme alanı
        add_frame = QFrame()
        add_layout = QHBoxLayout(add_frame)
        add_layout.setContentsMargins(0, 0, 0, 0)
        self.js_name_input = QLineEdit()
        self.js_name_input.setPlaceholderText("Site adı (örn: Wuxia World)")
        self.js_path_input = QLineEdit()
        self.js_path_input.setPlaceholderText("JS dosya yolu...")
        self.js_path_input.setReadOnly(True)
        browse_btn = QPushButton("📂")
        browse_btn.setFixedWidth(36)
        browse_btn.clicked.connect(self._browse_js_file)
        add_btn = QPushButton("➕ Ekle")
        add_btn.setFixedWidth(80)
        add_btn.clicked.connect(self._add_js_source)
        remove_btn = QPushButton("🗑 Sil")
        remove_btn.setFixedWidth(80)
        remove_btn.clicked.connect(self._remove_js_source)
        add_layout.addWidget(self.js_name_input, 2)
        add_layout.addWidget(self.js_path_input, 3)
        add_layout.addWidget(browse_btn)
        add_layout.addWidget(add_btn)
        add_layout.addWidget(remove_btn)
        js_layout.addWidget(add_frame)

        tabs.addTab(js_tab, "🌐 JS Kaynaklar")

        layout.addWidget(tabs)

        # Alt butonlar
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Kaydet ve Uygula")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        save_btn.clicked.connect(self._apply_settings)
        cancel_btn = QPushButton("Kapat")
        cancel_btn.setStyleSheet("padding: 8px; border-radius: 4px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    # Tema Yönetimi

    def _refresh_theme_combo(self):
        """Tema combo kutusunu tüm mevcut temalarla (yerleşik + özel) yeniler."""
        try:
            from core.theme_engine import list_themes as _list_themes
            all_themes = _list_themes()
        except Exception:
            all_themes = [{"name": k, "label": v, "builtin": True} for k, v in THEMES.items()]

        # System seçeneği her zaman ekle
        current_theme = self.settings.get("theme", "dark")
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        for t in all_themes:
            self.theme_combo.addItem(t["label"], t["name"])
        self.theme_combo.addItem("Sistem Varsayılanı", "system")

        # Mevcut temayı seç
        all_names = [self.theme_combo.itemData(i) for i in range(self.theme_combo.count())]
        idx = all_names.index(current_theme) if current_theme in all_names else 0
        self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.blockSignals(False)

    def _open_theme_manager(self):
        """Tema Yöneticisi diyalogunu açar."""
        from ui.theme_manager_dialog import ThemeManagerDialog
        current = self.settings.get("theme", "dark")
        dlg = ThemeManagerDialog(current_theme=current, parent=self)
        dlg.theme_applied.connect(self._on_theme_manager_applied)
        dlg.exec()
        # Kapandıktan sonra combo'yu yenile (yeni tema eklenmiş olabilir)
        self._refresh_theme_combo()

    def _on_theme_manager_applied(self, theme_name: str):
        """Tema yöneticisinden varsayılan tema değiştiğinde combo'yu günceller."""
        self.settings["theme"] = theme_name
        self._refresh_theme_combo()

    def _save_theme_as(self):
        """Aktif temayı farklı isimle özel tema olarak kaydeder."""
        from core.theme_engine import (
            load_theme_tokens, save_custom_theme, BUILTIN_THEMES
        )
        current = self.settings.get("theme", "dark")
        name, ok = QInputDialog.getText(
            self, "Temayı Farklı Kaydet",
            "Yeni tema adı (boşluksuz, İngilizce):",
            text=f"{current}_kopya"
        )
        if not ok or not name.strip():
            return
        name = name.strip().lower().replace(" ", "_")
        if name in BUILTIN_THEMES:
            QMessageBox.warning(self, "Hata", "Bu isim yerleşik bir tema için ayrılmıştır.")
            return
        label, ok2 = QInputDialog.getText(
            self, "Temayı Farklı Kaydet",
            "Görünür etiket:",
            text=name.replace("_", " ").title()
        )
        if not ok2:
            return
        tokens = load_theme_tokens(current)
        if save_custom_theme(name, label.strip() or name, current if current not in ("system",) else "dark", tokens):
            self._refresh_theme_combo()
            QMessageBox.information(self, "Kaydedildi",
                                    f"'{label}' adıyla özel tema olarak kaydedildi.")
        else:
            QMessageBox.critical(self, "Hata", "Farklı kaydetme başarısız.")

    # JS Kaynak Yönetimi

    def _refresh_js_list(self):
        self.js_list_widget.clear()
        for src in self.settings.get("custom_js_sources", []):
            name = src.get("name", "?")
            path = src.get("js_path", "")
            item = QListWidgetItem(f"📄 {name}  ←  {os.path.basename(path)}")
            item.setToolTip(path)
            self.js_list_widget.addItem(item)

    def _browse_js_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "JS Dosyası Seç", "", "JavaScript Dosyaları (*.js);;Tüm Dosyalar (*)"
        )
        if path:
            self.js_path_input.setText(path)

    def _add_js_source(self):
        name = self.js_name_input.text().strip()
        path = self.js_path_input.text().strip()
        if not name or not path:
            QMessageBox.warning(self, "Eksik Bilgi", "Site adı ve JS dosya yolunu doldurun.")
            return
        sources = self.settings.setdefault("custom_js_sources", [])
        # Aynı adda kaynak varsa güncelle
        for src in sources:
            if src["name"] == name:
                src["js_path"] = path
                self._refresh_js_list()
                self.js_name_input.clear()
                self.js_path_input.clear()
                return
        sources.append({"name": name, "js_path": path})
        self._refresh_js_list()
        self.js_name_input.clear()
        self.js_path_input.clear()

    def _remove_js_source(self):
        row = self.js_list_widget.currentRow()
        sources = self.settings.get("custom_js_sources", [])
        if 0 <= row < len(sources):
            sources.pop(row)
            self._refresh_js_list()

    # Kaydet 

    def _apply_settings(self):
        self.settings["theme"] = self.theme_combo.currentData()
        self.settings["notifications_enabled"] = self.notif_combo.currentIndex() == 0
        self.settings["log_level"] = self.log_combo.currentText()
        self.settings["ml_max_tokens"] = self.ml_token_spin.value()
        self.settings["promt_generator_max_tokens"] = self.prompt_gen_token_spin.value()
        save_app_settings(self.settings)
        self.settings_changed.emit(self.settings)
        app_logger.info(
            f"Uygulama ayarları kaydedildi: tema={self.settings['theme']}, "
            f"ml_max_tokens={self.settings['ml_max_tokens']}, "
            f"promt_generator_max_tokens={self.settings['promt_generator_max_tokens']}"
        )
        QMessageBox.information(self, "Kaydedildi", "Ayarlar başarıyla kaydedildi ve uygulandı.")

    def get_settings(self) -> dict:
        return self.settings
