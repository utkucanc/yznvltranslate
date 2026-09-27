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
        self.setMinimumHeight(160)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if not MATPLOTLIB_OK:
            lbl = QLabel("Grafik için matplotlib gerekli (pip install matplotlib)")
            lbl.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)
            return

        fig = Figure(figsize=(4, 1.8), dpi=96)
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

            x = list(range(len(days)))
            max_val = max(requests) if requests else 0

            # Çizgi grafik ve dolgu
            ax.plot(
                x, requests,
                color=ACCENT_BLUE, marker="o",
                markersize=4, linewidth=1.8, label="İstekler"
            )
            ax.fill_between(x, requests, 0, color=ACCENT_BLUE, alpha=0.18)

            # Değer etiketleri (non-zero noktalar için)
            for idx, val in enumerate(requests):
                if val > 0:
                    ax.annotate(
                        str(val), (x[idx], val),
                        textcoords="offset points", xytext=(0, 5),
                        ha='center', fontsize=7, color=TEXT_MAIN, fontweight='bold'
                    )

            # Eksen ve sınır ayarları
            ax.set_xticks(x)
            ax.set_xticklabels(days)
            ax.set_xlim(-0.3, len(days) - 0.7)
            if max_val == 0:
                ax.set_ylim(0, 5)
            else:
                ax.set_ylim(0, max_val * 1.35 + 1)

            for spine in ax.spines.values():
                spine.set_visible(False)

            ax.tick_params(colors=TEXT_FAINT, labelsize=7)
            ax.grid(True, color=BORDER, linewidth=0.6, alpha=0.3)
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
        """Son 7 günün verilerini RequestCounterManager'dan döndürür."""
        today = datetime.date.today()
        day_labels = []
        day_counts = []

        mgr = getattr(self.win, "request_counter_manager", None)
        stats = {}
        if mgr:
            if hasattr(mgr, "get_daily_stats"):
                stats = mgr.get_daily_stats()
            elif hasattr(mgr, "_stats"):
                stats = mgr._stats

        for i in range(6, -1, -1):
            d = today - datetime.timedelta(days=i)
            day_str = str(d)
            day_labels.append(d.strftime("%d %b"))

            if day_str in stats:
                day_entry = stats[day_str]
                if isinstance(day_entry, dict):
                    count = sum(day_entry.values())
                elif isinstance(day_entry, (int, float)):
                    count = int(day_entry)
                else:
                    count = 0
            elif i == 0 and mgr and hasattr(mgr, "count") and mgr.count > 0:
                count = mgr.count
            else:
                count = 0

            day_counts.append(count)

        return day_labels, day_counts
