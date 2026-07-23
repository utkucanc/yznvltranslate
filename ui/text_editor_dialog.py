"""
Bölüm Düzenleyici — Metin dosyalarını düzenleme, istatistik gösterme
ve tekli bölüm çevirisi yapma imkanı sunar.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QMessageBox, QGroupBox, QComboBox, QStatusBar, QWidget, QFrame, QSizePolicy
)
from PyQt6.QtGui import QFont, QShortcut, QKeySequence
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from logger import app_logger
from core.localization import tr


class RetranslateWorker(QObject):
    """Tek bölüm tekrar çeviri işlemi için arka plan worker'."""
    finished = pyqtSignal(str)   # translated text
    error = pyqtSignal(str)

    def __init__(self, project_path: str, original_path: str, startpromt: str, api_key: str):
        super().__init__()
        self.project_path = project_path
        self.original_path = original_path
        self.startpromt = startpromt
        self.api_key = api_key

    def run(self):
        try:
            with open(self.original_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Terminoloji entegrasyonu
            terminology_section = ""
            try:
                from terminology.terminology_manager import TerminologyManager
                tm = TerminologyManager(self.project_path)
                terminology_section = tm.build_prompt_section()
                if terminology_section:
                    app_logger.info("Tekrar çeviri için terminoloji bölümü eklendi.")
            except Exception as te:
                app_logger.warning(f"Terminoloji yüklenemedi: {te}")

            from core.llm_provider import create_provider_from_config
            provider = create_provider_from_config(self.project_path, self.api_key)

            full_prompt = self.startpromt
            if terminology_section:
                full_prompt += "\n\n" + terminology_section
            full_prompt += "\n\n" + original_content

            translated = provider.generate(full_prompt)
            if translated:
                self.finished.emit(translated)
            else:
                self.error.emit(tr("text_editor.api_no_response", "API yanit döndürmedi."))
        except Exception as e:
            self.error.emit(str(e))


class TextEditorDialog(QDialog):
    """Metin dosyası düzenleyici diyalogu."""

    def __init__(self, file_path: str, parent=None, project_path: str = None):
        super().__init__(parent)
        self.file_path = file_path
        self.project_path = project_path
        self.original_content = ""
        self.has_unsaved_changes = False

        file_name = os.path.basename(file_path)
        self.setWindowTitle(tr("text_editor.window_title", "Düzenleyici — {}").format(file_name))
        self.resize(800, 650)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(6, 6, 6, 6)

        # Dosya bilgisi — KOMPAKT BANT (tek satır)
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.Shape.NoFrame)
        info_frame.setStyleSheet(
            "QFrame { background-color: #1A2730; border-radius: 4px; padding: 2px 6px; }"
            "QLabel { color: #80CBC4; font-size: 9pt; background: transparent; }"
        )
        info_frame.setMaximumHeight(28)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(6, 2, 6, 2)
        info_layout.setSpacing(6)
        self.file_label = QLabel(f"📄 {file_name}")
        self.file_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        info_layout.addWidget(self.file_label)
        info_layout.addStretch()
        layout.addWidget(info_frame)

        # Metin düzenleyici — ANA ALAN
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Consolas", 10))
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.text_edit.setMinimumHeight(300)
        self.text_edit.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.text_edit, 1)  # stretch=1 → tam ekran kapla

        # İstatistik barı
        stats_layout = QHBoxLayout()
        self.char_count_label = QLabel(tr("text_editor.char_count", "Karakter: 0"))
        self.word_count_label = QLabel(tr("text_editor.word_count", "Kelime: 0"))
        self.line_count_label = QLabel(tr("text_editor.line_count", "Satır: 0"))
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

        self.save_btn = QPushButton(tr("text_editor.btn_save", "💾 Kaydet (Ctrl+S)"))
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.save_btn.clicked.connect(self.save_file)

        self.retranslate_btn = QPushButton(tr("text_editor.btn_retranslate", "🔄 Tekrar Çevir"))
        self.retranslate_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.retranslate_btn.clicked.connect(self.retranslate_chapter)

        self.close_btn = QPushButton(tr("app_settings.btn_close", "Kapat"))
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
                self.text_edit.setPlaceholderText(tr("text_editor.placeholder_not_found", "Dosya bulunamadı."))
        except Exception as e:
            QMessageBox.critical(self, tr("main_window.msg_structure_error_title", "Hata"), tr("prompt_editor.msg_read_error", "Dosya okunamadı: {}").format(e))

    def on_text_changed(self):
        """Metin değiştiğinde çağrılır."""
        self.has_unsaved_changes = (self.text_edit.toPlainText() != self.original_content)
        self.change_indicator.setText(tr("text_editor.unsaved_changes", "● Değişiklik var") if self.has_unsaved_changes else "")
        self.update_stats()

    def update_stats(self):
        """İstatistikleri günceller."""
        text = self.text_edit.toPlainText()
        chars = len(text)
        words = len(text.split()) if text.strip() else 0
        lines = text.count('\n') + 1 if text else 0

        self.char_count_label.setText(tr("text_editor.char_count_val", "Karakter: {count}").format(count=chars))
        self.word_count_label.setText(tr("text_editor.word_count_val", "Kelime: {count}").format(count=words))
        self.line_count_label.setText(tr("text_editor.line_count_val", "Satır: {count}").format(count=lines))

    def save_file(self):
        """Dosyayı kaydeder."""
        try:
            content = self.text_edit.toPlainText()
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.original_content = content
            self.has_unsaved_changes = False
            self.change_indicator.setText(tr("text_editor.saved", "✓ Kaydedildi"))
            self.change_indicator.setStyleSheet("color: #4CAF50; font-weight: bold;")
            # 2 saniye sonra geri al
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: (
                self.change_indicator.setText(""),
                self.change_indicator.setStyleSheet("color: #F44336; font-weight: bold;")
            ))
        except Exception as e:
            QMessageBox.critical(self, tr("menu_bar.msg_save_error_title", "Kayıt Hatası"), tr("text_editor.msg_save_fail", "Dosya kaydedilemedi: {}").format(e))

    def retranslate_chapter(self):
        """Tek bölümü arka planda (QThread) tekrar çevirir — terminoloji entegre."""
        if not self.project_path:
            QMessageBox.warning(self, tr("new_project.msg_warning_title", "Uyarı"), tr("text_editor.msg_no_project_path", "Proje yolu belirlenmemiş."))
            return

        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self, tr("text_editor.save_confirm_title", "Kaydet"),
                tr("text_editor.save_confirm_body", "Kaydedilmemiş değişiklikler var. Önce kaydetmek ister misiniz?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_file()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        file_name = os.path.basename(self.file_path)
        if file_name.startswith("translated_"):
            original_name = file_name.replace("translated_", "", 1)
            original_path = os.path.join(self.project_path, "dwnld", original_name)
        else:
            original_path = self.file_path

        if not os.path.exists(original_path):
            QMessageBox.warning(self, tr("text_editor.msg_no_original_title", "Orijinal Dosya Yok"), tr("text_editor.msg_no_original_body", "Orijinal dosya bulunamadı:\n{}").format(original_path))
            return

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
                QMessageBox.warning(self, tr("text_editor.msg_no_api_key_title", "API Anahtarı Yok"), tr("text_editor.msg_no_api_key_body", "Proje ayarlarında API anahtarı tanımlı değil."))
                return

            self.retranslate_btn.setEnabled(False)
            self.retranslate_btn.setText(tr("text_editor.translating", "⏳ Çevriliyor..."))

            self._retranslate_thread = QThread()
            self._retranslate_worker = RetranslateWorker(self.project_path, original_path, startpromt, api_key)
            self._retranslate_worker.moveToThread(self._retranslate_thread)

            self._retranslate_thread.started.connect(self._retranslate_worker.run)
            self._retranslate_worker.finished.connect(self._on_retranslate_done)
            self._retranslate_worker.error.connect(self._on_retranslate_error)
            self._retranslate_worker.finished.connect(self._retranslate_thread.quit)
            self._retranslate_worker.error.connect(self._retranslate_thread.quit)
            self._retranslate_thread.finished.connect(self._retranslate_thread.deleteLater)

            self._retranslate_thread.start()

        except Exception as e:
            QMessageBox.critical(self, tr("text_editor.msg_translate_error_title", "Çeviri Hatası"), tr("text_editor.msg_translate_start_fail", "Tekrar çeviri başlatılamadı:\n{}").format(e))
            self.retranslate_btn.setEnabled(True)
            self.retranslate_btn.setText(tr("text_editor.btn_retranslate", "🔄 Tekrar Çevir"))

    def _on_retranslate_done(self, translated: str):
        """Arka plan çevirisi tamamlandığında çağrılır."""
        self.text_edit.setPlainText(translated)
        self.has_unsaved_changes = True
        self.change_indicator.setText(tr("text_editor.new_translation_indicator", "● Yeni çeviri — kaydedin"))
        QMessageBox.information(self, tr("text_editor.msg_translate_success_title", "Çeviri Tamamlandı"), tr("text_editor.msg_translate_success_body", "Bölüm başarıyla tekrar çevrildi.\nTerminoloji kuralları uygulandı."))
        self.retranslate_btn.setEnabled(True)
        self.retranslate_btn.setText(tr("text_editor.btn_retranslate", "🔄 Tekrar Çevir"))
        self._retranslate_worker = None
        self._retranslate_thread = None

    def _on_retranslate_error(self, msg: str):
        """Arka plan çevirisi hata verdiğinde çağrılır."""
        QMessageBox.critical(self, tr("text_editor.msg_translate_error_title", "Çeviri Hatası"), tr("text_editor.msg_translate_fail_body", "Tekrar çeviri sırasında hata:\n{}").format(msg))
        self.retranslate_btn.setEnabled(True)
        self.retranslate_btn.setText(tr("text_editor.btn_retranslate", "🔄 Tekrar Çevir"))
        self._retranslate_worker = None
        self._retranslate_thread = None


    def closeEvent(self, event):
        """Kapatma sırasında değişiklik kontrolü."""
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self, tr("text_editor.msg_unsaved_confirm_title", "Kaydedilmemiş Değişiklikler"),
                tr("text_editor.msg_unsaved_confirm_body", "Kaydedilmemiş değişiklikler var. Ne yapmak istersiniz?"),
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
                self, tr("text_editor.msg_unsaved_confirm_title", "Kaydedilmemiş Değişiklikler"),
                tr("text_editor.msg_unsaved_confirm_body", "Kaydedilmemiş değişiklikler var. Ne yapmak istersiniz?"),
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
