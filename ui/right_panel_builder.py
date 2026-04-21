"""
RightPanelBuilder — Sağ panel (butonlar, progress bar, durum etiketi) oluşturucu.

Sorumluluklar:
  - Sağ paneldeki tüm butonları, widget'ları ve layout'u oluşturma
  - Butonların sinyal bağlantılarını yapma
"""

from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QSpinBox, QProgressBar, QMessageBox,
    QGraphicsDropShadowEffect
)


def _make_glow(color: str, blur: int = 18, offset_y: int = 3) -> QGraphicsDropShadowEffect:
    """Verilen renkte yumuşak parlama (glow) efekti döndürür."""
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, offset_y)
    shadow.setColor(QColor(color))
    return shadow


def build_right_panel(main_window):
    """Sağ paneli oluşturur ve main_layout'a ekler. Tüm widget'lar main_window üzerine atanır."""
    win = main_window
    right_layout = QVBoxLayout()
    right_layout.setSpacing(4)
    right_layout.setContentsMargins(4, 4, 4, 4)

    # ── İndirme Yöntemi ──
    win.downloadMethodCombo = QComboBox()
    win.downloadMethodCombo.addItems([
        "Booktoki JS İle İndir (Selenium)",
        "69shuba JS İle İndir (Selenium)",
        "Novelfire JS İle İndir (Selenium)",
        "Normal Web Kazıma (Requests) (Tavsiye Edilmez)"
    ])
    dl_label = QLabel("İndirme Yöntemi:")
    dl_label.setFont(QFont("Segoe UI", 8))
    right_layout.addWidget(dl_label)
    right_layout.addWidget(win.downloadMethodCombo)

    # ── İndirme Butonu ──
    win.startButton = QPushButton("⬇  İndirmeyi Başlat")
    win.startButton.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    win.startButton.setProperty("class", "btn-success")
    win.startButton.setCursor(Qt.CursorShape.PointingHandCursor)
    win.startButton.clicked.connect(win.start_download_process)
    win.startButton.setGraphicsEffect(_make_glow("#2E7D32", blur=16, offset_y=2))
    right_layout.addWidget(win.startButton)

    # ── Toplu Bölüm Ekle ──
    win.splitButton = QPushButton("✂  Toplu Bölüm Ekle")
    win.splitButton.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    win.splitButton.setProperty("class", "btn-primary")
    win.splitButton.setCursor(Qt.CursorShape.PointingHandCursor)
    win.splitButton.clicked.connect(win.start_split_process)
    right_layout.addWidget(win.splitButton)

    # ── Çeviri Butonu ──
    win.translateButton = QPushButton("🌐  Seçilenleri Çevir")
    win.translateButton.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    win.translateButton.setProperty("class", "btn-info")
    win.translateButton.setCursor(Qt.CursorShape.PointingHandCursor)
    win.translateButton.clicked.connect(win.start_translation_process)
    win.translateButton.setEnabled(False)
    win.translateButton.setGraphicsEffect(_make_glow("#0D47A1", blur=16, offset_y=2))
    right_layout.addWidget(win.translateButton)

    # ── Sayılı Çevir ──
    limit_layout = QHBoxLayout()
    limit_layout.setSpacing(4)
    win.limit_checkbox = QCheckBox("Sayılı çevir")
    win.limit_checkbox.setFont(QFont("Segoe UI", 8))
    win.limit_checkbox.setToolTip("İşaretlenirse sadece yandaki sayı kadar dosya çevrilip durur.")
    win.limit_spinbox = QSpinBox()
    win.limit_spinbox.setMinimum(1)
    win.limit_spinbox.setMaximum(99999)
    win.limit_spinbox.setValue(20)
    win.limit_spinbox.setEnabled(True)
    win.limit_spinbox.setFixedWidth(100)
    win.limit_checkbox.toggled.connect(win.limit_spinbox.setEnabled)
    limit_layout.addWidget(win.limit_checkbox)
    limit_layout.addStretch()
    limit_layout.addWidget(win.limit_spinbox)
    right_layout.addLayout(limit_layout)

    # ── Kapatma Checkbox ──
    win.shutdown_checkbox = QCheckBox("⚡ Çeviri Bitince Kapat")
    win.shutdown_checkbox.setFont(QFont("Segoe UI", 8))
    win.shutdown_checkbox.setToolTip("Çeviri tamamlanınca bilgisayarı ONAYSIZ kapar")
    win.shutdown_checkbox.toggled.connect(win.on_shutdown_checkbox_toggled)
    right_layout.addWidget(win.shutdown_checkbox)

    # ── Birleştirme Butonu ──
    win.mergeButton = QPushButton("🔗  Seçili Çevirileri Birleştir")
    win.mergeButton.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    win.mergeButton.setProperty("class", "btn-purple")
    win.mergeButton.setCursor(Qt.CursorShape.PointingHandCursor)
    win.mergeButton.clicked.connect(win.start_merging_process)
    win.mergeButton.setEnabled(False)
    right_layout.addWidget(win.mergeButton)

    # ── Durdur Butonu ──
    win.stopTranslationButton = QPushButton("■  Çeviriyi Durdur")
    win.stopTranslationButton.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
    win.stopTranslationButton.setProperty("class", "btn-stop")
    win.stopTranslationButton.setCursor(Qt.CursorShape.PointingHandCursor)
    win.stopTranslationButton.clicked.connect(win.stop_translation_process)
    win.stopTranslationButton.setVisible(False)
    right_layout.addWidget(win.stopTranslationButton)

    # ── Hata Kontrol Butonu ──
    win.errorCheckButton = QPushButton("🔍  Çeviri Hata Kontrol")
    win.errorCheckButton.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    win.errorCheckButton.setProperty("class", "btn-teal")
    win.errorCheckButton.setCursor(Qt.CursorShape.PointingHandCursor)
    win.errorCheckButton.clicked.connect(win.start_error_check_process)
    win.errorCheckButton.setEnabled(False)
    right_layout.addWidget(win.errorCheckButton)

    # ── EPUB Butonu ──
    win.epubButton = QPushButton("📚  Seçilenleri EPUB Yap")
    win.epubButton.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    win.epubButton.setProperty("class", "btn-brown")
    win.epubButton.setCursor(Qt.CursorShape.PointingHandCursor)
    win.epubButton.clicked.connect(win.start_epub_process)
    win.epubButton.setEnabled(False)
    right_layout.addWidget(win.epubButton)

    # ── Token Say Butonu ──
    win.token_count_button = QPushButton("🔢  Token Say")
    win.token_count_button.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    win.token_count_button.setProperty("class", "btn-deep-purple")
    win.token_count_button.setCursor(Qt.CursorShape.PointingHandCursor)
    win.token_count_button.clicked.connect(win.start_token_counting_manually)
    win.token_count_button.setEnabled(False)
    right_layout.addWidget(win.token_count_button)

    # ── Progress Bar ──
    win.progressBar = QProgressBar(win)
    win.progressBar.setTextVisible(True)
    win.progressBar.setAlignment(Qt.AlignmentFlag.AlignCenter)
    win.progressBar.setVisible(False)
    win.progressBar.setFixedHeight(14)
    right_layout.addWidget(win.progressBar)

    # ── Durum Etiketi ──
    win.statusLabel = QLabel("Durum: Hazır")
    win.statusLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
    win.statusLabel.setFont(QFont("Segoe UI", 10))
    win.statusLabel.setWordWrap(True)
    right_layout.addWidget(win.statusLabel)

    # ── Token Bilgileri — kompakt ──
    win.total_tokens_label = QLabel("Toplam Token: 0")
    win.total_tokens_label.setFont(QFont("Segoe UI", 8))
    win.total_original_tokens_label = QLabel("Orijinal Token: 0")
    win.total_original_tokens_label.setFont(QFont("Segoe UI", 8))
    win.total_translated_tokens_label = QLabel("Çevrilen Token: 0")
    win.total_translated_tokens_label.setFont(QFont("Segoe UI", 8))
    win.token_progress_bar = QProgressBar(win)
    win.token_progress_bar.setTextVisible(True)
    win.token_progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
    win.token_progress_bar.setVisible(False)
    win.token_progress_bar.setFixedHeight(10)
    token_info_layout = QVBoxLayout()
    token_info_layout.setSpacing(2)
    token_info_layout.addWidget(win.total_tokens_label)
    token_info_layout.addWidget(win.total_original_tokens_label)
    token_info_layout.addWidget(win.total_translated_tokens_label)
    token_info_layout.addWidget(win.token_progress_bar)
    right_layout.addLayout(token_info_layout)

    # ── Seç (Vurgulananları İşaretle) ──
    win.selectHighlightedButton = QPushButton("☑  Seç (Vurgulananları İşaretle)")
    win.selectHighlightedButton.setFont(QFont("Segoe UI", 9))
    win.selectHighlightedButton.setProperty("class", "btn-steel")
    win.selectHighlightedButton.setCursor(Qt.CursorShape.PointingHandCursor)
    win.selectHighlightedButton.clicked.connect(win.mark_highlighted_rows_checked)
    right_layout.addWidget(win.selectHighlightedButton)

    # ── Terminoloji Butonu ──
    win.generateTerminologyButton = QPushButton("🤖  YZ İle Terminoloji Üret")
    win.generateTerminologyButton.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    win.generateTerminologyButton.setProperty("class", "btn-pink")
    win.generateTerminologyButton.setCursor(Qt.CursorShape.PointingHandCursor)
    win.generateTerminologyButton.clicked.connect(win.start_ml_terminology_process)
    win.generateTerminologyButton.setEnabled(False)
    win.generateTerminologyButton.setGraphicsEffect(_make_glow("#880E4F", blur=14, offset_y=2))
    right_layout.addWidget(win.generateTerminologyButton)

    # ── Proje Ayarları ──
    win.projectSettingsButton = QPushButton("⚙  Proje Ayarları")
    win.projectSettingsButton.setFont(QFont("Segoe UI", 9))
    win.projectSettingsButton.setProperty("class", "btn-ocean")
    win.projectSettingsButton.setCursor(Qt.CursorShape.PointingHandCursor)
    win.projectSettingsButton.clicked.connect(win.open_project_settings_dialog)
    right_layout.addWidget(win.projectSettingsButton)

    # ── Yardım ──
    win.helpButton = QPushButton("❓  Yardım")
    win.helpButton.setFont(QFont("Segoe UI", 9))
    win.helpButton.setProperty("class", "btn-ocean")
    win.helpButton.setCursor(Qt.CursorShape.PointingHandCursor)
    win.helpButton.clicked.connect(win.show_help_clicked)
    right_layout.addWidget(win.helpButton)

    right_layout.addStretch()
    win.main_layout.addLayout(right_layout, 1)
