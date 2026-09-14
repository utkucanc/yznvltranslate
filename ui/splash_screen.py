"""
ui/splash_screen.py — Uygulama Açılış (Splash) Ekranı.

Görsel olarak splash.jpeg dosyasını kullanır.
Frameless, ekranda ortalanmış ve dark_theme renk paletiyle uyumlu özel açılış ekranı.
"""

import os
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QProgressBar,
    QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor

from ui.dark_theme import (
    BG_PANEL, BG_PANEL2, BORDER, TEXT_MAIN, TEXT_DIM, TEXT_FAINT,
    ACCENT_BLUE
)


class CustomSplashScreen(QWidget):
    """
    Özel Tasarımlı Uygulama Açılış Ekranı (Splash Screen).
    """

    def __init__(self, image_path: str = "splash.jpeg", parent=None):
        super().__init__(parent)
        self.image_path = image_path if os.path.exists(image_path) else "logo256.ico"

        # Pencere özellikleri
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(540, 360)

        self._init_ui()
        self._center_on_screen()

    def _center_on_screen(self):
        """Açılış ekranını bilgisayar ekranının ortasına yerleştirir."""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(geo.x() + x, geo.y() + y)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Kart Çerçevesi
        self.card = QFrame()
        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PANEL2};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        # Splash Görseli / Logo Alanı
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: none; background: transparent;")

        if os.path.exists(self.image_path):
            pixmap = QPixmap(self.image_path)
            scaled_pixmap = pixmap.scaled(
                508, 200,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            # Yuvarlatılmış görsel kırpma
            cropped_pixmap = QPixmap(508, 190)
            cropped_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(cropped_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(QRectF(0, 0, 508, 190), 10, 10)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, scaled_pixmap)
            painter.end()
            self.image_label.setPixmap(cropped_pixmap)
        else:
            self.image_label.setText("📖 Novel Çeviri Aracı")
            self.image_label.setStyleSheet(f"color:{ACCENT_BLUE}; font-size:24px; font-weight:bold; border:none;")

        card_layout.addWidget(self.image_label)

        # Başlık ve Versiyon
        title_row = QHBoxLayout()
        title_lbl = QLabel("Novel Çeviri Aracı")
        title_lbl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:15px; font-weight:bold; border:none;")

        ver_lbl = QLabel("v3.1.0")
        ver_lbl.setStyleSheet(f"color:{ACCENT_BLUE}; font-size:11px; font-weight:600; background:{ACCENT_BLUE}22; padding:2px 8px; border-radius:4px; border:none;")

        title_row.addWidget(title_lbl)
        title_row.addStretch()
        title_row.addWidget(ver_lbl)
        card_layout.addLayout(title_row)

        # Durum mesajı
        self.status_lbl = QLabel("Uygulama başlatılıyor...")
        self.status_lbl.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px; border:none;")
        card_layout.addWidget(self.status_lbl)

        # Progress bar (Indeterminate)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {BG_PANEL};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT_BLUE};
                border-radius: 3px;
            }}
        """)
        card_layout.addWidget(self.progress_bar)

        # Gölge efekti
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        layout.addWidget(self.card)

    def set_status(self, message: str):
        """Durum mesajını günceller."""
        self.status_lbl.setText(message)
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

    def finish(self, main_window):
        """MainWindow hazır olduğunda titreme yapmadan splash ekranını kapatır."""
        self.close()
