"""
ToastWidget — Saf Qt kayan bildirim penceresi.

QSystemTrayIcon.showMessage() kullanılmaz çünkü Windows'ta
native bildirime tıklandığında python.exe yeniden başlatılır
ve konsol penceresi açılır; bu davranış Qt sinyalleriyle engellenemez.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QApplication, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve


class _ToastWidget(QFrame):
    """Ekranın sağ alt köşesinde beliren, otomatik kaybolan bildirim."""

    def __init__(self, title: str, message: str, parent=None, duration: int = 4000):
        super().__init__(
            parent,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.duration = duration

        # ── Stil ──
        self.setStyleSheet("""
            QFrame#toast {
                background-color: #1E1E2E;
                border: 1px solid #45475A;
                border-left: 4px solid #89B4FA;
                border-radius: 8px;
            }
        """)
        self.setObjectName("toast")
        self.setFixedWidth(320)

        # ── Layout ──
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # Başlık satırı
        title_row = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #CDD6F4; font-weight: bold; font-size: 10pt;")
        title_lbl.setWordWrap(False)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #6C7086; border: none; font-size: 9pt; }"
            "QPushButton:hover { color: #F38BA8; }"
        )
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._dismiss)

        title_row.addWidget(title_lbl, 1)
        title_row.addWidget(close_btn)
        layout.addLayout(title_row)

        # Mesaj metni
        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet("color: #A6ADC8; font-size: 9pt;")
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)

        self.adjustSize()

        # ── Opaklık efekti ──
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

        # ── Otomatik kapatma zamanlayıcısı ──
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_fade_out)

    def show_toast(self):
        """Widget'ı konumlandırıp gösterir."""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.right() - self.width() - 16,
                geo.bottom() - self.height() - 16,
            )
        self.show()
        self._timer.start(self.duration)

    def _start_fade_out(self):
        """Fade-out animasyonu başlatır."""
        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._anim.setDuration(600)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self.close)
        self._anim.start()

    def _dismiss(self):
        """X butonuyla anında kapatır."""
        self._timer.stop()
        self.close()
