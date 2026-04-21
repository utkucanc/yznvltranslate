"""
MLTerminologyRangeDialog — YZ ile terminoloji çıkarımı için bölüm aralığı seçim penceresi.

Kullanım:
    dialog = MLTerminologyRangeDialog(project_path, parent=self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        start_ch, end_ch, max_tokens = dialog.get_values()
        # ... işlemi başlat
"""

import os
import configparser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QSpinBox, QDialogButtonBox,
    QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


def _get_chapter_count(project_path: str) -> int:
    """Projenin dwnld klasöründeki txt dosyası sayısını (bölüm sayısı) döndürür."""
    dwnld_dir = os.path.join(project_path, "dwnld")
    if not os.path.exists(dwnld_dir):
        return 1
    files = sorted([f for f in os.listdir(dwnld_dir) if f.endswith(".txt")])
    return len(files) if files else 1


def _get_last_operation(project_path: str) -> tuple[int, int]:
    """
    Projenin config.ini dosyasından son terminoloji işleminin bölüm bilgisini okur.
    Returns: (last_start, last_end) — bulunamazsa (0, 0) döndürür.
    """
    config_path = os.path.join(project_path, "config", "config.ini")
    if not os.path.exists(config_path):
        return 0, 0
    cfg = configparser.ConfigParser()
    try:
        cfg.read(config_path, encoding="utf-8")
        last_start = cfg.getint("TerminologyOp", "last_start_chapter", fallback=0)
        last_end = cfg.getint("TerminologyOp", "last_end_chapter", fallback=0)
        return last_start, last_end
    except Exception:
        return 0, 0


def _get_ml_max_tokens() -> int:
    """app_settings.json'dan ml_max_tokens değerini okur."""
    try:
        settings_path = os.path.join(os.getcwd(), "AppConfigs", "app_settings.json")
        if os.path.exists(settings_path):
            import json
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return int(data.get("ml_max_tokens", 450000))
    except Exception:
        pass
    return 450000


class MLTerminologyRangeDialog(QDialog):
    """Terminoloji çıkarımı için başlangıç/bitiş bölümü ve token limiti seçim penceresi."""

    def __init__(self, project_path: str, parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.setWindowTitle("Terminoloji Çıkar — Bölüm Aralığı")
        self.setMinimumWidth(400)
        self.setModal(True)

        total_chapters = _get_chapter_count(project_path)
        last_start, last_end = _get_last_operation(project_path)
        ml_max_tokens = _get_ml_max_tokens()

        # Varsayılan başlangıç: son işlemin bitiş bölümü + 1 (veya 1)
        default_start = (last_end + 1) if last_end > 0 else 1
        if default_start > total_chapters:
            default_start = 1
        default_end = total_chapters

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Başlık
        title = QLabel("🤖 YZ ile Terminoloji Çıkar")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Son işlem bilgisi
        if last_end > 0:
            last_info = QLabel(f"Son İşlem: Başlangıç Bölümü: {last_start}, Bitiş Bölümü: {last_end}")
            last_info.setStyleSheet("color: #888; font-size: 9pt;")
            last_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(last_info)

        # Bölüm aralığı
        range_group = QGroupBox("Bölüm Aralığı")
        form = QFormLayout(range_group)
        form.setSpacing(8)

        self.start_spin = QSpinBox()
        self.start_spin.setMinimum(1)
        self.start_spin.setMaximum(max(total_chapters, 1))
        self.start_spin.setValue(default_start)
        self.start_spin.setSuffix(f"  (Toplam: {total_chapters})")
        form.addRow("Başlangıç Bölümü:", self.start_spin)

        self.end_spin = QSpinBox()
        self.end_spin.setMinimum(1)
        self.end_spin.setMaximum(max(total_chapters, 1))
        self.end_spin.setValue(default_end)
        form.addRow("Bitiş Bölümü:", self.end_spin)

        layout.addWidget(range_group)

        # Token limiti
        token_group = QGroupBox("Ayarlar")
        token_form = QFormLayout(token_group)
        token_form.setSpacing(8)

        self.token_spin = QSpinBox()
        self.token_spin.setMinimum(50000)
        self.token_spin.setMaximum(2000000)
        self.token_spin.setSingleStep(50000)
        self.token_spin.setValue(ml_max_tokens)
        self.token_spin.setSuffix(" token")
        token_note = QLabel("(Uygulama ayarlarındaki ML Maks Token değeri)")
        token_note.setStyleSheet("color: #888; font-size: 8pt;")
        token_form.addRow("ML Maks Token:", self.token_spin)
        token_form.addRow("", token_note)
        layout.addWidget(token_group)

        # Butonlar
        btn_layout = QHBoxLayout()
        self.extract_btn = QPushButton("🚀 Terminoloji Çıkar")
        self.extract_btn.setStyleSheet(
            "background-color: #E91E63; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px;"
        )
        self.extract_btn.clicked.connect(self._on_extract)

        self.cancel_btn = QPushButton("İptal")
        self.cancel_btn.setStyleSheet("padding: 8px 16px; border-radius: 4px;")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.extract_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def _on_extract(self):
        start = self.start_spin.value()
        end = self.end_spin.value()
        if start > end:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Hata", "Başlangıç bölümü bitiş bölümünden büyük olamaz.")
            return
        self.accept()

    def get_values(self) -> tuple[int, int, int]:
        """(start_chapter, end_chapter, max_tokens) döndürür."""
        return self.start_spin.value(), self.end_spin.value(), self.token_spin.value()
