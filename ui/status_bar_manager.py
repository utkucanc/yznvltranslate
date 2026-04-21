"""
StatusBarManager — Uygulama alt bilgi barı oluşturucu ve güncelleyici.
"""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt


class StatusBarManager:
    def __init__(self, main_window):
        self.win = main_window

    def create(self):
        win = self.win
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.Shape.StyledPanel)
        # Inline stil qt-material override'dan korur
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #11111B;
                color: #A6ADC8;
                border-top: 1px solid #252537;
                padding: 0px 6px;
            }
            QLabel {
                color: #A6ADC8;
                font-size: 8pt;
                background: transparent;
                border: none;
                padding: 0;
            }
            QPushButton {
                color: #89DCEB;
                background: transparent;
                border: none;
                font-size: 13pt;
                font-weight: bold;
                padding: 0 4px;
                min-height: 0;
                max-height: 24px;
            }
            QPushButton:hover { color: #74C7EC; }
        """)
        status_frame.setFixedHeight(28)
        bar_layout = QHBoxLayout(status_frame)
        bar_layout.setContentsMargins(8, 0, 8, 0)
        bar_layout.setSpacing(14)

        win.sb_status_label = QLabel("🟢 Hazır")
        win.sb_model_label = QLabel("🤖 Model: -")
        win.sb_api_label = QLabel("🔑 API: -")
        win.sb_speed_label = QLabel("⚡ Hız: -")
        win.sb_requests_label = QLabel("📡 İstek: 0")
        win.sb_tokens_label = QLabel("📊 Token: 0")
        win.sb_refresh_btn = QPushButton("↻  UI Yenile")
        win.sb_refresh_btn.setFixedHeight(22)
        win.sb_refresh_btn.setToolTip("Dosya listesini yeniden yükle (UI Yenile)")
        win.sb_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        win.sb_refresh_btn.clicked.connect(win.refresh_ui_and_theme)

        for w in [win.sb_status_label, win.sb_model_label, win.sb_api_label,
                   win.sb_speed_label, win.sb_requests_label, win.sb_tokens_label]:
            bar_layout.addWidget(w)
        bar_layout.addStretch()
        bar_layout.addWidget(win.sb_refresh_btn)
        win.outer_layout.addWidget(status_frame)

    def update(self):
        win = self.win
        status_icon = "🟢" if win._current_status == "Hazır" else "🟡"
        win.sb_status_label.setText(f"{status_icon} {win._current_status}")
        win.sb_model_label.setText(f"🤖 Model: {win._current_model or '-'}")
        win.sb_api_label.setText(f"🔑 API: {win._current_api_name or '-'}")
        current_req_count = win.request_counter_manager.get_count(win._current_model, win._current_api_name)
        win.sb_requests_label.setText(f"📡 İstek: {current_req_count}")
        win.sb_tokens_label.setText(f"📊 Token: {win._api_token_count}")
        if win._translation_speed > 0:
            win.sb_speed_label.setText(f"⚡ Hız: {win._translation_speed:.1f} dk/bölüm")
        else:
            win.sb_speed_label.setText("⚡ Hız: -")
