import sys
import os
import configparser
from PyQt6.QtWidgets import (
    QDialog, QLineEdit, QFormLayout, QDialogButtonBox, 
    QMessageBox, QLabel, QApplication, QTextEdit, QListWidget, 
    QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QInputDialog,
    QSpinBox, QCheckBox, QGroupBox, QSplitter, QWidget, QProgressBar
)
from PyQt6.QtGui import QIntValidator, QFont, QIcon, QAction
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QSize
from logger import app_logger

# ─── V2.1.0 Geriye Uyumluluk Re-export'lar ───
# ui/ paketine taşınan sınıflar burada da erişilebilir kalır.
# Eski "from dialogs import X" çağrıları kırılmaz.
try:
    from ui.app_settings_dialog import AppSettingsDialog
    from ui.file_preview_dialog import FilePreviewDialog
except ImportError:
    pass  # ui paketi henüz mevcut değilse sessizce geç



# --- Yardımcı Fonksiyonlar ---
def get_config_path(subfolder):
    """AppConfigs altındaki klasör yollarını döndürür."""
    base_path = os.getcwd()
    path = os.path.join(base_path, "AppConfigs", subfolder)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def load_files_to_combo(combobox, subfolder):
    """Belirtilen klasördeki txt dosyalarını combobox'a yükler."""
    folder = get_config_path(subfolder)
    combobox.clear()
    combobox.addItem("Seçiniz...", None)
    if os.path.exists(folder):
        files = sorted([f for f in os.listdir(folder) if f.endswith('.txt')])
        for f in files:
            file_path = os.path.join(folder, f)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read().strip()
                # Item text: Dosya Adı, Item Data: Dosya İçeriği
                combobox.addItem(f.replace('.txt', ''), content)
            except:
                pass


class MCPServerDialog(QDialog):
    """MCP Sunucu Yönetim Paneli — Endpoint ekleme, düzenleme, silme ve anahtar yönetimi."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yapay Zeka Kaynağı Yönetimi (MCP)")
        self.resize(900, 600)
        
        main_layout = QHBoxLayout(self)
        
        # ── Sol Panel: Endpoint Listesi ──
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Kayıtlı Sunucular:"))
        
        self.endpoint_list = QListWidget()
        self.endpoint_list.currentItemChanged.connect(self.on_endpoint_selected)
        left_layout.addWidget(self.endpoint_list)
        
        btn_layout = QHBoxLayout()
        self.new_btn = QPushButton("Yeni")
        self.new_btn.clicked.connect(self.new_endpoint)
        self.del_btn = QPushButton("Sil")
        self.del_btn.setStyleSheet("color: red;")
        self.del_btn.clicked.connect(self.delete_endpoint)
        btn_layout.addWidget(self.new_btn)
        btn_layout.addWidget(self.del_btn)
        left_layout.addLayout(btn_layout)
        
        # Aktif endpoint seçimi
        active_layout = QHBoxLayout()
        self.set_active_btn = QPushButton("Aktif Yap")
        self.set_active_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.set_active_btn.clicked.connect(self.set_active_endpoint)
        active_layout.addWidget(self.set_active_btn)
        left_layout.addLayout(active_layout)
        
        # ── Sağ Panel: Endpoint Formu ──
        right_layout = QVBoxLayout()
        
        form = QFormLayout()
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("benzersiz_kimlik [Listeleme için gerekli. Önemsiz.]")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Sunucu Adı [Listeleme için gerekli. Önemsiz.]")
        
        # ── Tür Seçimi ──
        self.type_combo = QComboBox()
        self.type_combo.addItems(["gemini", "openai_compatible"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        
        # ── Model Seçimi (gemini → combo, openai → text) ──
        # Gemini model combo
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self._populate_gemini_models()

        # OpenAI uyumlu için manuel giriş
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("model-id (ör: gpt-4o, llama-3.3-70b)")

        # ── URL Girişi ──
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.example.com/v1 (Zorunlu!)")
        
        self.rotation_check = QCheckBox("Anahtar Rotasyonu (Key Rotation)")
        self.rotation_check.setChecked(True)
        
        self.headers_input = QLineEdit()
        self.headers_input.setPlaceholderText('{"HTTP-Referer": "...", "X-Title": "..."} [Kaynak zorunlu kılmadıysa boş bırakın.]')
        
        form.addRow("ID:", self.id_input)
        form.addRow("Ad:", self.name_input)
        form.addRow("Tür:", self.type_combo)
        form.addRow("Model:", self.model_combo)
        form.addRow("Model ID:", self.model_input)
        form.addRow("Base URL:", self.url_input)
        form.addRow(self.rotation_check)
        form.addRow("Headers (JSON):", self.headers_input)
        right_layout.addLayout(form)
        
        # API Anahtarları
        right_layout.addWidget(QLabel("API Anahtarları (her satıra bir tane):"))
        self.keys_edit = QTextEdit()
        self.keys_edit.setPlaceholderText("apikey_1\napikey_2\napikey_3")
        self.keys_edit.setMaximumHeight(120)
        right_layout.addWidget(self.keys_edit)
        
        # ── API Aktar Butonu (üstte) ──
        self.import_api_btn = QPushButton("📥 API Editöründen API Aktar")
        self.import_api_btn.setStyleSheet("background-color: #607D8B; color: white; font-weight: bold; padding: 6px;")
        self.import_api_btn.clicked.connect(self.import_from_api_editor)
        right_layout.addWidget(self.import_api_btn)

        # Butonlar (Kaydet ve Bağlantı Testi — import butonunun altında)
        action_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Kaydet")
        self.save_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 6px;")
        self.save_btn.clicked.connect(self.save_endpoint)
        
        self.test_btn = QPushButton("🔗 Bağlantı Testi")
        self.test_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 6px;")
        self.test_btn.clicked.connect(self.test_connection)
        
        action_layout.addWidget(self.save_btn)
        action_layout.addWidget(self.test_btn)
        right_layout.addLayout(action_layout)
        
        self.test_result_label = QLabel("")
        self.test_result_label.setWordWrap(True)
        right_layout.addWidget(self.test_result_label)
        
        right_layout.addStretch()
        
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)
        
        # Başlangıç durumu: gemini seçili
        self._on_type_changed("gemini")
        self._load_list()

    # ── Tür Değişince Model ve URL Göster/Gizle ──
    def _on_type_changed(self, type_text: str):
        """Tür seçimine göre model alanı ve URL alanını göster/gizle."""
        is_gemini = (type_text == "gemini")
        self.model_combo.setVisible(is_gemini)
        self.model_input.setVisible(not is_gemini)
        self.url_input.setVisible(not is_gemini)

    def _populate_gemini_models(self):
        """Gemini model listesini API'den veya varsayılan listeden doldurur."""
        models = []
        try:
            from google import genai
            keys_folder = get_config_path("APIKeys")
            if os.path.exists(keys_folder):
                api_keys = [f for f in os.listdir(keys_folder) if f.endswith('.txt')]
                if api_keys:
                    key_path = os.path.join(keys_folder, api_keys[0])
                    with open(key_path, 'r', encoding='utf-8') as f:
                        api_key = f.read().strip()
                    if api_key:
                        client = genai.Client(api_key=api_key)
                        for m in client.models.list():
                            if 'generateContent' in m.supported_actions:
                                name = m.name.replace("models/", "")
                                models.append(name)
        except Exception as e:
            app_logger.debug(f"Gemini model listesi alınamadı (MCP): {e}")

        if not models:
            models = [
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
            ]
        self.model_combo.clear()
        self.model_combo.addItems(models)

    def import_from_api_editor(self):
        """API Editöründeki kayıtlı anahtarlardan seçim yaparak keys_edit'e ekler."""
        keys_folder = get_config_path("APIKeys")
        if not os.path.exists(keys_folder):
            QMessageBox.warning(self, "Uyarı", "API Editöründe kayıtlı anahtar bulunamadı.")
            return

        key_files = [f for f in os.listdir(keys_folder) if f.endswith('.txt')]
        if not key_files:
            QMessageBox.warning(self, "Uyarı", "API Editöründe kayıtlı anahtar bulunamadı.")
            return

        # Anahtar adlarını listele
        key_names = [f.replace('.txt', '') for f in key_files]

        # Çoklu seçim diyalogu
        from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("API Anahtarı Seç")
        dlg.resize(350, 300)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.addWidget(QLabel("İçe aktarmak istediğiniz anahtarları seçin:"))

        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for name in key_names:
            list_widget.addItem(name)
        dlg_layout.addWidget(list_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dlg
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        dlg_layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        selected_items = list_widget.selectedItems()
        if not selected_items:
            return

        added_keys = []
        for item in selected_items:
            name = item.text()
            key_path = os.path.join(keys_folder, name + ".txt")
            try:
                with open(key_path, 'r', encoding='utf-8') as f:
                    key_value = f.read().strip()
                if key_value:
                    added_keys.append(key_value)
            except Exception as e:
                app_logger.warning(f"Anahtar okunamadı ({name}): {e}")

        if added_keys:
            existing = self.keys_edit.toPlainText().strip()
            existing_list = [k.strip() for k in existing.split('\n') if k.strip()]
            for k in added_keys:
                if k not in existing_list:
                    existing_list.append(k)
            self.keys_edit.setText('\n'.join(existing_list))
            QMessageBox.information(self, "Başarılı", f"{len(added_keys)} anahtar içe aktarıldı.")

    # ── Mevcut endpoint seçilince formu doldur ──
    def _load_list(self):
        """Endpoint listesini yükler."""
        self.endpoint_list.clear()
        try:
            from core.llm_provider import load_endpoints
            data = load_endpoints()
            self._active_id = data.get("active_endpoint_id", "")
            for ep in data.get("endpoints", []):
                prefix = "✅ " if ep["id"] == self._active_id else "   "
                self.endpoint_list.addItem(f"{prefix}{ep['name']} [{ep['type']}]")
        except Exception as e:
            QMessageBox.warning(self, "Uyarı", f"Endpoint listesi yüklenemedi: {e}")
    
    def _get_endpoints_data(self) -> dict:
        try:
            from core.llm_provider import load_endpoints
            return load_endpoints()
        except Exception:
            return {"active_endpoint_id": "", "endpoints": []}
    
    def on_endpoint_selected(self, current, previous):
        if not current:
            return
        idx = self.endpoint_list.row(current)
        data = self._get_endpoints_data()
        endpoints = data.get("endpoints", [])
        if 0 <= idx < len(endpoints):
            ep = endpoints[idx]
            self.id_input.setText(ep.get("id", ""))
            self.name_input.setText(ep.get("name", ""))
            ep_type = ep.get("type", "gemini")
            self.type_combo.setCurrentText(ep_type)
            self._on_type_changed(ep_type)

            model_id = ep.get("model_id", "")
            if ep_type == "gemini":
                self.model_combo.setCurrentText(model_id)
            else:
                self.model_input.setText(model_id)

            self.url_input.setText(ep.get("base_url", "") or "")
            self.rotation_check.setChecked(ep.get("use_key_rotation", True))
            import json
            self.headers_input.setText(json.dumps(ep.get("headers", {})) if ep.get("headers") else "")
            
            # Anahtarları yükle
            try:
                from core.llm_provider import load_api_keys
                keys = load_api_keys(ep["id"])
                self.keys_edit.setText("\n".join(keys))
            except Exception:
                self.keys_edit.clear()
    
    def new_endpoint(self):
        self.endpoint_list.clearSelection()
        self.id_input.clear()
        self.name_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.model_combo.setCurrentIndex(0)
        self.model_input.clear()
        self.url_input.clear()
        self.rotation_check.setChecked(True)
        self.headers_input.clear()
        self.keys_edit.clear()
        self.test_result_label.clear()
        self._on_type_changed("gemini")
    
    def save_endpoint(self):
        ep_id = self.id_input.text().strip()
        ep_name = self.name_input.text().strip()
        
        if not ep_id or not ep_name:
            QMessageBox.warning(self, "Eksik", "ID ve Ad alanları zorunludur.")
            return
        
        import json as _json
        headers = {}
        headers_text = self.headers_input.text().strip()
        if headers_text:
            try:
                headers = _json.loads(headers_text)
            except _json.JSONDecodeError:
                QMessageBox.warning(self, "Hata", "Headers alanı geçerli JSON formatında olmalıdır.")
                return

        ep_type = self.type_combo.currentText()
        if ep_type == "gemini":
            model_id = self.model_combo.currentText().strip()
            base_url = None
        else:
            model_id = self.model_input.text().strip()
            base_url = self.url_input.text().strip() or None

        new_ep = {
            "id": ep_id,
            "name": ep_name,
            "type": ep_type,
            "model_id": model_id,
            "base_url": base_url,
            "use_key_rotation": self.rotation_check.isChecked(),
            "headers": headers
        }
        
        try:
            from core.llm_provider import load_endpoints, save_endpoints, save_api_keys
            data = load_endpoints()
            endpoints = data.get("endpoints", [])
            
            found = False
            for i, ep in enumerate(endpoints):
                if ep["id"] == ep_id:
                    endpoints[i] = new_ep
                    found = True
                    break
            if not found:
                endpoints.append(new_ep)
            
            data["endpoints"] = endpoints
            save_endpoints(data)
            
            keys_text = self.keys_edit.toPlainText().strip()
            keys = [k.strip() for k in keys_text.split("\n") if k.strip()]
            save_api_keys(ep_id, keys)
            
            QMessageBox.information(self, "Başarılı", f"'{ep_name}' kaydedildi.")
            self._load_list()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydetme hatası: {e}")
    
    def delete_endpoint(self):
        current = self.endpoint_list.currentItem()
        if not current:
            return
        idx = self.endpoint_list.row(current)
        
        if QMessageBox.question(self, "Sil", "Bu endpoint'i silmek istediğinize emin misiniz?") != QMessageBox.StandardButton.Yes:
            return
        
        try:
            from core.llm_provider import load_endpoints, save_endpoints
            data = load_endpoints()
            endpoints = data.get("endpoints", [])
            if 0 <= idx < len(endpoints):
                removed = endpoints.pop(idx)
                data["endpoints"] = endpoints
                if data.get("active_endpoint_id") == removed.get("id"):
                    data["active_endpoint_id"] = endpoints[0]["id"] if endpoints else ""
                save_endpoints(data)
                self._load_list()
                self.new_endpoint()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme hatası: {e}")
    
    def set_active_endpoint(self):
        current = self.endpoint_list.currentItem()
        if not current:
            return
        idx = self.endpoint_list.row(current)
        
        try:
            from core.llm_provider import load_endpoints, save_endpoints
            data = load_endpoints()
            endpoints = data.get("endpoints", [])
            if 0 <= idx < len(endpoints):
                data["active_endpoint_id"] = endpoints[idx]["id"]
                save_endpoints(data)
                QMessageBox.information(self, "Başarılı", f"'{endpoints[idx]['name']}' aktif endpoint olarak ayarlandı.")
                self._load_list()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Aktif ayarlama hatası: {e}")
    
    def test_connection(self):
        self.test_result_label.setText("Bağlantı test ediliyor...")
        self.test_result_label.setStyleSheet("color: orange;")
        QApplication.processEvents()
        
        ep_id = self.id_input.text().strip()
        keys_text = self.keys_edit.toPlainText().strip()
        keys = [k.strip() for k in keys_text.split("\n") if k.strip()]
        
        if not keys:
            self.test_result_label.setText("❌ API anahtarı girilmemiş.")
            self.test_result_label.setStyleSheet("color: red;")
            return
        
        import random
        test_key = random.choice(keys)
        
        ep_type = self.type_combo.currentText()
        if ep_type == "gemini":
            model_id = self.model_combo.currentText().strip()
            base_url = None
        else:
            model_id = self.model_input.text().strip()
            base_url = self.url_input.text().strip() or None

        try:
            from core.llm_provider import LLMProvider
            import json as _json
            headers = {}
            if self.headers_input.text().strip():
                try:
                    headers = _json.loads(self.headers_input.text().strip())
                except:
                    pass
            
            ep_config = {
                "id": ep_id,
                "name": self.name_input.text().strip(),
                "type": ep_type,
                "model_id": model_id,
                "base_url": base_url,
                "use_key_rotation": False,
                "headers": headers
            }
            
            provider = LLMProvider(endpoint=ep_config, api_key=test_key)
            success, message = provider.test_connection()
            
            if success:
                self.test_result_label.setText(f"✅ {message}")
                self.test_result_label.setStyleSheet("color: green;")
            else:
                self.test_result_label.setText(f"❌ {message}")
                self.test_result_label.setStyleSheet("color: red;")
        except Exception as e:
            self.test_result_label.setText(f"❌ Hata: {e}")
            self.test_result_label.setStyleSheet("color: red;")
