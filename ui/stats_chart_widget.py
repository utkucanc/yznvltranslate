"""
stats_chart_widget.py — API İstek grafiği (matplotlib FigureCanvas).

request_counter_manager'dan gerçek veriyi alır.
requirements.txt'de zaten mevcut olan matplotlib kullanılır.
"""

import datetime
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use("QtAgg")
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt

from ui.dark_theme import (
    BG_PANEL, BG_PANEL2, BORDER, TEXT_MAIN, TEXT_DIM, TEXT_FAINT,
    ACCENT_BLUE, ACCENT_PURPLE
)


class StatsChartWidget(QWidget):
    """
    Son 7 günün API istek sayısını çizgi grafik olarak gösterir.
    Gerçek veri: win.request_counter_manager
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.win = main_window
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if not MATPLOTLIB_OK:
            lbl = QLabel("Grafik için matplotlib gerekli (pip install matplotlib)")
            lbl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)
            return

        fig = Figure(figsize=(4, 2.0), dpi=96)
        fig.patch.set_alpha(0)
        self.ax = fig.add_subplot(111)
        self.canvas = FigureCanvas(fig)
        self.canvas.setStyleSheet("background: transparent;")
        layout.addWidget(self.canvas)

        self.refresh()

    def refresh(self):
        """Grafiği güncel veriyle yeniler."""
        if not MATPLOTLIB_OK:
            return
        try:
            days, requests = self._get_data()
            ax = self.ax
            ax.clear()
            ax.set_facecolor("none")

            ax.plot(
                days, requests,
                color=ACCENT_BLUE, marker="o",
                markersize=4, linewidth=1.8, label="Requests"
            )

            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.tick_params(colors=TEXT_FAINT, labelsize=7)
            ax.grid(True, color=BORDER, linewidth=0.6, alpha=0.5)
            ax.legend(
                facecolor=BG_PANEL, edgecolor=BORDER,
                labelcolor=TEXT_DIM, fontsize=7,
                loc="upper left", frameon=False
            )
            self.canvas.figure.tight_layout(pad=0.4)
            self.canvas.draw()
        except Exception:
            pass

    def _get_data(self):
        """Son 7 günün verilerini döndürür."""
        today = datetime.date.today()
        day_labels = []
        day_counts = []

        try:
            mgr = self.win.request_counter_manager
            # RequestCounterManager'dan veri al
            # Günlük breakdown yoksa toplam sayıyı bugüne yaz
            total = sum(
                mgr._counts.get(k, 0)
                for k in mgr._counts
            ) if hasattr(mgr, '_counts') else 0
        except Exception:
            total = 0

        for i in range(6, -1, -1):
            d = today - datetime.timedelta(days=i)
            day_labels.append(d.strftime("%d %b"))
            # Gerçek günlük veri yoksa bugüne toplam at
            day_counts.append(total if i == 0 else 0)

        return day_labels, day_counts
