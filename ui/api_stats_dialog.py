"""
ApiStatsDialog — API kullanım istatistikleri diyaloğu.
"""

from datetime import date, timedelta
from PyQt6.QtWidgets import (
    QDialog, QHeaderView, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel
)
from PyQt6.QtCore import Qt


def show_api_stats_dialog(main_window):
    stats = main_window.request_counter_manager.get_daily_stats()
    dialog = QDialog(main_window)
    dialog.setWindowTitle("📊 API Kullanım İstatistikleri")
    dialog.resize(700, 500)
    main_layout = QVBoxLayout(dialog)
    tabs = QTabWidget()

    # ── Matplotlib Grafik ──
    try:
        import matplotlib
        # Backend'i yalnızca henüz başlatılmamışsa ayarla.
        # Çeviri sırasında zaten 'QtAgg' yüklüyse 'Agg' yazmak
        # Qt event loop'unu bozuyor ve worker thread'i askıya alıyor.
        if not matplotlib.is_interactive() and matplotlib.get_backend().lower() == "agg":
            pass  # Zaten Agg, sorun yok
        else:
            # Aktif Qt oturumunda backend değiştirilmez; sadece figure
            # oluşturulurken Agg renderer kullanılır (FigureCanvasAgg).
            pass

        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

        fig = Figure(figsize=(8, 4), facecolor='#1E1E1E')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#2D2D30')
        days = [(str(date.today() - timedelta(days=i))) for i in range(6, -1, -1)]
        totals = [sum(stats.get(d, {}).values()) for d in days]
        short_days = [d[5:] for d in days]
        bars = ax.bar(short_days, totals, color='#4CAF50', alpha=0.85, edgecolor='#2E7D32')
        ax.set_title('Son 7 Günük API İstekleri', color='white', fontsize=12)
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('#555')
        ax.spines['left'].set_color('#555')
        ax.spines['top'].set_color('#1E1E1E')
        ax.spines['right'].set_color('#1E1E1E')
        for bar, val in zip(bars, totals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.1,
                        str(val), ha='center', va='bottom', color='white', fontsize=9)
        fig.tight_layout()
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)
        canvas = FigureCanvas(fig)
        chart_layout.addWidget(canvas)
        tabs.addTab(chart_tab, "📊 Grafik")
    except ImportError:
        chart_tab = QWidget()
        lbl = QLabel("matplotlib yüklenmediğinden grafik gösterilemiyor.\npip install matplotlib")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        QVBoxLayout(chart_tab).addWidget(lbl)
        tabs.addTab(chart_tab, "📊 Grafik")


    # ── Tablo ──
    table_tab = QWidget()
    table_layout = QVBoxLayout(table_tab)
    all_rows = []
    for day, apis in sorted(stats.items(), reverse=True):
        for api_key, count in apis.items():
            all_rows.append((day, api_key, count))
    table = QTableWidget(len(all_rows), 3)
    table.setHorizontalHeaderLabels(["Tarih", "API / Model", "Toplam İstek"])
    table.horizontalHeader().setStretchLastSection(True)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    for i, (day, api, count) in enumerate(all_rows):
        table.setItem(i, 0, QTableWidgetItem(day))
        table.setItem(i, 1, QTableWidgetItem(api))
        table.setItem(i, 2, QTableWidgetItem(str(count)))
    table_layout.addWidget(table)
    tabs.addTab(table_tab, "📝 Tablo")
    main_layout.addWidget(tabs)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Tarih ve API sütunları genişlesin
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # İstek
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # İstek sayısı sütunu esnek olsun
    today_count = main_window.request_counter_manager.get_total_today()
    info_label = QLabel(f"Bugünkü toplam istek: {today_count}")
    info_label.setStyleSheet("font-size: 11pt; padding: 4px;")
    main_layout.addWidget(info_label)

    close_btn = QPushButton("Kapat")
    close_btn.clicked.connect(dialog.close)
    btn_row = QHBoxLayout()
    btn_row.addStretch()
    btn_row.addWidget(close_btn)
    main_layout.addLayout(btn_row)
    dialog.exec()
