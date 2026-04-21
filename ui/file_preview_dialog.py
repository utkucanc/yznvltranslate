"""
FilePreviewDialog — Hızlı bölüm önizleme popup'ı.

Sağ tıklama menüsünden açılır. Salt okunur, hızlı gösterim.
Tam editörde açma butonu sunar.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


class FilePreviewDialog(QDialog):
    """Dosya içeriğini hızlıca önizleyen salt okunur popup."""

    PREVIEW_CHARS = 6000  # Gösterilecek max karakter

    def __init__(self, file_path: str, parent=None, project_path: str = None):
        super().__init__(parent)
        self.file_path = file_path
        self.project_path = project_path
        file_name = os.path.basename(file_path)

        self.setWindowTitle(f"📄 Önizleme — {file_name}")
        self.resize(820, 650)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(6, 6, 6, 6)

        # Bilgi şeridi
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #1A2730; border-radius: 4px; padding: 2px 6px;")
        info_frame.setFixedHeight(28)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(6, 2, 6, 2)
        info_layout.setSpacing(8)
        self.file_label = QLabel(f"📄 {file_name}")
        self.file_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.file_label.setStyleSheet("color: #80CBC4; background: transparent;")
        self.size_label = QLabel("")
        self.size_label.setStyleSheet("color: #78909C; font-size: 8pt; background: transparent;")
        info_layout.addWidget(self.file_label)
        info_layout.addStretch()
        info_layout.addWidget(self.size_label)
        layout.addWidget(info_frame)

        # Metin görünümü — ANA ALAN
        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setFont(QFont("Consolas", 10))
        self.text_view.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.text_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.text_view.setMinimumHeight(300)
        layout.addWidget(self.text_view, 1)  # stretch=1 -> bütün boşluk buraya

        # Butonlar
        btn_layout = QHBoxLayout()
        self.open_editor_btn = QPushButton("✏️ Tam Editörde Aç")
        self.open_editor_btn.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold; "
            "padding: 7px 14px; border-radius: 4px;"
        )
        self.open_editor_btn.clicked.connect(self._open_in_editor)
        close_btn = QPushButton("Kapat")
        close_btn.setStyleSheet("padding: 7px 14px; border-radius: 4px;")
        close_btn.clicked.connect(self.close)
        self.truncate_label = QLabel("")
        self.truncate_label.setStyleSheet("color: #F57F17; font-size: 9pt;")
        btn_layout.addWidget(self.open_editor_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.truncate_label)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self._load_file()

    def _load_file(self):
        if not os.path.exists(self.file_path):
            self.text_view.setPlainText("Dosya bulunamadı.")
            return
        try:
            file_size = os.path.getsize(self.file_path)
            self.size_label.setText(f"{file_size / 1024:.1f} KB")
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if len(content) > self.PREVIEW_CHARS:
                self.text_view.setPlainText(content[: self.PREVIEW_CHARS])
                self.truncate_label.setText(
                    f"⚠️ İlk {self.PREVIEW_CHARS:,} karakter gösteriliyor "
                    f"(toplam: {len(content):,})"
                )
            else:
                self.text_view.setPlainText(content)
        except Exception as e:
            self.text_view.setPlainText(f"Dosya okunamadı: {e}")

    def _open_in_editor(self):
        """Tam editörde açar."""
        try:
            from text_editor_dialog import TextEditorDialog
            editor = TextEditorDialog(self.file_path, self.parent(), project_path=self.project_path)
            self.close()
            editor.exec()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Hata", f"Editör açılamadı: {e}")
