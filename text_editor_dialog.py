"""
Bölüm Düzenleyici — Metin dosyalarını düzenleme, istatistik gösterme
ve tekli bölüm çevirisi yapma imkanı sunar.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QMessageBox, QGroupBox, QComboBox, QStatusBar, QWidget
)
from PyQt6.QtGui import QFont, QShortcut, QKeySequence
from PyQt6.QtCore import Qt
from logger import app_logger


class TextEditorDialog(QDialog):
    """Metin dosyası düzenleyici diyalogu."""

    def __init__(self, file_path: str, parent=None, project_path: str = None):
        super().__init__(parent)
        self.file_path = file_path
        self.project_path = project_path
        self.original_content = ""
        self.has_unsaved_changes = False

        file_name = os.path.basename(file_path)
        self.setWindowTitle(f"Düzenleyici — {file_name}")
        self.resize(800, 650)

        layout = QVBoxLayout(self)

        # Dosya bilgisi
        info_layout = QHBoxLayout()
        self.file_label = QLabel(f"📄 {file_name}")
        self.file_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        info_layout.addWidget(self.file_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Metin düzenleyici
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Consolas", 11))
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.text_edit.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.text_edit)

        # İstatistik barı
        stats_layout = QHBoxLayout()
        self.char_count_label = QLabel("Karakter: 0")
        self.word_count_label = QLabel("Kelime: 0")
        self.line_count_label = QLabel("Satır: 0")
        self.change_indicator = QLabel("")
        self.change_indicator.setStyleSheet("color: #F44336; font-weight: bold;")

        stats_layout.addWidget(self.char_count_label)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.word_count_label)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.line_count_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.change_indicator)
        layout.addLayout(stats_layout)

        # Butonlar
        btn_layout = QHBoxLayout()

        self.save_btn = QPushButton("💾 Kaydet (Ctrl+S)")
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.save_btn.clicked.connect(self.save_file)

        self.retranslate_btn = QPushButton("🔄 Tekrar Çevir")
        self.retranslate_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.retranslate_btn.clicked.connect(self.retranslate_chapter)

        self.close_btn = QPushButton("Kapat")
        self.close_btn.setStyleSheet("padding: 8px; border-radius: 4px;")
        self.close_btn.clicked.connect(self.close)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.retranslate_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        # Kısayollar
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_file)

        # Dosyayı yükle
        self._load_file()

    def _load_file(self):
        """Dosyayı yükler."""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.original_content = content
                self.text_edit.setPlainText(content)
                self.has_unsaved_changes = False
                self.update_stats()
            else:
                self.text_edit.setPlaceholderText("Dosya bulunamadı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya okunamadı: {e}")

    def on_text_changed(self):
        """Metin değiştiğinde çağrılır."""
        self.has_unsaved_changes = (self.text_edit.toPlainText() != self.original_content)
        self.change_indicator.setText("● Değişiklik var" if self.has_unsaved_changes else "")
        self.update_stats()

    def update_stats(self):
        """İstatistikleri günceller."""
        text = self.text_edit.toPlainText()
        chars = len(text)
        words = len(text.split()) if text.strip() else 0
        lines = text.count('\n') + 1 if text else 0

        self.char_count_label.setText(f"Karakter: {chars:,}")
        self.word_count_label.setText(f"Kelime: {words:,}")
        self.line_count_label.setText(f"Satır: {lines:,}")

    def save_file(self):
        """Dosyayı kaydeder."""
        try:
            content = self.text_edit.toPlainText()
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.original_content = content
            self.has_unsaved_changes = False
            self.change_indicator.setText("✓ Kaydedildi")
            self.change_indicator.setStyleSheet("color: #4CAF50; font-weight: bold;")
            # 2 saniye sonra geri al
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: (
                self.change_indicator.setText(""),
                self.change_indicator.setStyleSheet("color: #F44336; font-weight: bold;")
            ))
        except Exception as e:
            QMessageBox.critical(self, "Kayıt Hatası", f"Dosya kaydedilemedi: {e}")

    def retranslate_chapter(self):
        """Tek bölümü tekrar çevirir."""
        if not self.project_path:
            QMessageBox.warning(self, "Uyarı", "Proje yolu belirlenmemiş.")
            return

        # Kayıtlı mı kontrol et
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self, "Kaydet",
                "Kaydedilmemiş değişiklikler var. Önce kaydetmek ister misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_file()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        # Orijinal dosyayı bul
        file_name = os.path.basename(self.file_path)
        if file_name.startswith("translated_"):
            original_name = file_name.replace("translated_", "", 1)
            original_path = os.path.join(self.project_path, "dwnld", original_name)
        else:
            original_path = self.file_path

        if not os.path.exists(original_path):
            QMessageBox.warning(self, "Orijinal Dosya Yok", f"Orijinal dosya bulunamadı:\n{original_path}")
            return

        # Basit tek dosya çevirisi
        try:
            import configparser
            config = configparser.ConfigParser()
            config_path = os.path.join(self.project_path, "config", "config.ini")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config.read_file(f)

            api_key = config.get("API", "gemini_api_key", fallback="")
            startpromt = config.get("Startpromt", "startpromt", fallback="")

            if not api_key:
                QMessageBox.warning(self, "API Anahtarı Yok", "Proje ayarlarında API anahtarı tanımlı değil.")
                return

            with open(original_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            from llm_provider import LLMProvider, create_provider_from_config
            provider = create_provider_from_config(self.project_path, api_key)

            self.retranslate_btn.setEnabled(False)
            self.retranslate_btn.setText("Çevriliyor...")
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()

            full_prompt = startpromt + "\n\n" + original_content
            translated = provider.generate(full_prompt)

            if translated:
                self.text_edit.setPlainText(translated)
                self.has_unsaved_changes = True
                self.change_indicator.setText("● Yeni çeviri — kaydedin")
                QMessageBox.information(self, "Çeviri Tamamlandı", "Bölüm başarıyla tekrar çevrildi.")

        except Exception as e:
            QMessageBox.critical(self, "Çeviri Hatası", f"Tekrar çeviri sırasında hata:\n{e}")
        finally:
            self.retranslate_btn.setEnabled(True)
            self.retranslate_btn.setText("🔄 Tekrar Çevir")

    def closeEvent(self, event):
        """Kapatma sırasında değişiklik kontrolü."""
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self, "Kaydedilmemiş Değişiklikler",
                "Kaydedilmemiş değişiklikler var. Ne yapmak istersiniz?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self.save_file()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def reject(self):
        """ESC tuşu ile kapatma sırasında değişiklik kontrolü."""
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self, "Kaydedilmemiş Değişiklikler",
                "Kaydedilmemiş değişiklikler var. Ne yapmak istersiniz?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self.save_file()
                super().reject()
            elif reply == QMessageBox.StandardButton.Discard:
                super().reject()
            else:
                pass # İptal et, kapatma
        else:
            super().reject()
