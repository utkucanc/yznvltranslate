"""
FileTableManager — Ana penceredeki QTableWidget (Dosya Listesi) yönetimini sağlar.
"""
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from core.localization import tr

class FileTableManager:
    """QTableWidget üzerinde dosya verilerini göstermek için UI yöneticisi."""
    def __init__(self, table_widget: QTableWidget):
        self.table = table_widget
        self._setup_table()

    def _setup_table(self):
        """Tablonun sütun ve görünüm ayarlarını yapar."""
        headers = [
            tr("file_table.header_select", "Seç"),
            tr("file_table.header_original_file", "Orijinal Dosya"),
            tr("file_table.header_translated_file", "Çevrilen Dosya"),
            tr("file_table.header_creation_date", "Oluşturma Tarihi"),
            tr("file_table.header_size", "Boyut"),
            tr("file_table.header_status", "Durum"),
            tr("file_table.header_original_token", "Orijinal Token"),
            tr("file_table.header_translated_token", "Çevrilen Token")
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Seç
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Orijinal Dosya
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Çevrilen Dosya
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)      # Oluşturma Tarihi
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)      # Boyut
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)      # Durum
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)      # Orijinal Token
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)      # Çevrilen Token
        
        # Sütunları daraltarak ekrana sığdır
        self.table.setColumnWidth(0, 30)   # Seç
        self.table.setColumnWidth(1, 110)  # Orijinal Dosya
        self.table.setColumnWidth(2, 160)  # Çevrilen Dosya
        self.table.setColumnWidth(3, 125) # Tarih
        self.table.setColumnWidth(4, 70)  # Boyut
        self.table.setColumnWidth(5, 90)  # Durum
        self.table.setColumnWidth(6, 100)  # Orijinal Token
        self.table.setColumnWidth(7, 100)  # Çevrilen Token
        self.table.setAlternatingRowColors(True)

    def populate(self, sorted_entries: list[dict]):
        """FileListManager'dan gelen verilerle tabloyu doldurur."""
        self.table.setRowCount(len(sorted_entries))
        for row, entry_data in enumerate(sorted_entries):
            self._populate_row(row, entry_data)

    def _populate_row(self, row: int, entry_data: dict):
        # Column 0: Checkbox
        checkbox_item = QTableWidgetItem()
        checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        checkbox_item.setCheckState(Qt.CheckState.Unchecked)
        self.table.setItem(row, 0, checkbox_item)

        # Column 1: Original File Name
        self.table.setItem(row, 1, QTableWidgetItem(entry_data["original_file_name"]))

        # Column 2: Translated File Name
        translated_display = entry_data["translated_file_name"] if entry_data["translated_file_name"] else tr("file_table.none", "Yok")
        self.table.setItem(row, 2, QTableWidgetItem(translated_display))
        
        # Column 3: Creation Date (Original)
        self.table.setItem(row, 3, QTableWidgetItem(entry_data["original_creation_time"]))
        
        # Column 4: Size (Original)
        self.table.setItem(row, 4, QTableWidgetItem(entry_data["original_file_size"]))
        
        # Column 5: Status 
        status_text = entry_data["display_status"]
        
        # Translate status text for user interface
        if status_text == "Birleştirildi":
            display_status = tr("file_table.status_merged", "Birleştirildi")
        elif status_text == "Çevrildi":
            display_status = tr("file_table.status_translated", "Çevrildi")
        elif status_text == "İndirildi":
            display_status = tr("file_table.status_downloaded", "İndirildi")
        elif status_text == "Orijinali Yok":
            display_status = tr("file_table.status_no_original", "Orijinali Yok")
        elif status_text == "Orijinali Yok, Çevrildi":
            display_status = tr("file_table.status_no_original_translated", "Orijinali Yok, Çevrildi")
        elif status_text == "Orijinali Yok, Çevrilmedi":
            display_status = tr("file_table.status_no_original_untranslated", "Orijinali Yok, Çevrilmedi")
        elif status_text.startswith("Hata:"):
            display_status = status_text.replace("Hata:", tr("file_table.status_error_prefix", "Hata:"), 1)
        else:
            display_status = tr(f"file_table.status_{status_text}", status_text)
            
        status_item = QTableWidgetItem(display_status)
        
        if status_text.startswith("Hata:"):
            status_item.setForeground(QColor(Qt.GlobalColor.red)) 
            status_item.setToolTip(display_status)
        elif status_text in ("Çevrildi", "Birleştirildi", "Orijinali Yok, Çevrildi"): 
            status_item.setForeground(QColor(Qt.GlobalColor.darkGreen)) 
        elif status_text == "Orijinali Yok":
            status_item.setForeground(QColor(Qt.GlobalColor.darkMagenta)) 
        else: 
            status_item.setForeground(QColor(Qt.GlobalColor.darkGray)) 
        
        self.table.setItem(row, 5, status_item)

        # Column 6: Original Token Count
        orig_token_val = entry_data["original_token_count"]
        if orig_token_val == "Hesaplanmadı":
            orig_token_display = tr("file_table.token_not_calculated", "Hesaplanmadı")
        elif orig_token_val == "Yok":
            orig_token_display = tr("file_table.none", "Yok")
        else:
            orig_token_display = str(orig_token_val)
            
        original_token_item = QTableWidgetItem(orig_token_display)
        if orig_token_val == "Hesaplanmadı":
            original_token_item.setForeground(QColor(Qt.GlobalColor.blue))
        self.table.setItem(row, 6, original_token_item)
        
        # Column 7: Translated Token Count
        trsl_token_val = entry_data["translated_token_count"]
        if trsl_token_val == "Hesaplanmadı":
            trsl_token_display = tr("file_table.token_not_calculated", "Hesaplanmadı")
        elif trsl_token_val == "Yok":
            trsl_token_display = tr("file_table.none", "Yok")
        else:
            trsl_token_display = str(trsl_token_val)
            
        translated_token_item = QTableWidgetItem(trsl_token_display)
        if trsl_token_val in ("Hesaplanmadı", "Yok"):
            translated_token_item.setForeground(QColor(Qt.GlobalColor.blue))
        self.table.setItem(row, 7, translated_token_item)
