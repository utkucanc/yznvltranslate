"""
ThemeManagerDialog — Kapsamlı tema yöneticisi diyalog penceresi.

Özellikler:
  - Kayıtlı temaları listele (sol panel)
  - Yeni tema oluştur / var olan temayı düzenle / sil / farklı kaydet
  - Temaları dışa / içe aktar
  - Varsayılan tema olarak ayarla (app_settings.json günceller)
  - TreeView ile tema kategorileri ve token'ları göster ve düzenle
  - Canlı önizleme kartı (renk değişikliklerini anında yansıtır)
"""

import os
import copy
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QWidget,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QTreeWidget, QTreeWidgetItem, QLineEdit, QColorDialog,
    QFileDialog, QMessageBox, QFrame, QScrollArea,
    QGroupBox, QFormLayout, QDialogButtonBox, QInputDialog,
    QSizePolicy, QApplication
)
from PyQt6.QtGui import QFont, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QSize

from logger import app_logger
from core.theme_engine import (
    list_themes, load_theme_tokens, save_custom_theme, delete_theme,
    export_theme, import_theme, tokens_to_qss, BUILTIN_THEMES, DEFAULT_DARK_TOKENS
)

# Kategori meta verisi (TreeView için insan okunabilir etiketler)
CATEGORY_META = {
    "general":    ("🌐 Genel", {
        "background":   "Arka Plan",
        "text_color":   "Metin Rengi",
        "font_family":  "Font Ailesi",
        "font_size":    "Font Boyutu",
        "border_color": "Kenarlık Rengi",
        "border_radius":"Köşe Yarıçapı",
    }),
    "buttons": ("🔘 Butonlar", {
        "btn_success_bg":        "Başarılı — Arka Plan",
        "btn_success_hover":     "Başarılı — Üzerine Gelme",
        "btn_primary_bg":        "Birincil — Arka Plan",
        "btn_primary_hover":     "Birincil — Üzerine Gelme",
        "btn_stop_bg":           "Durdur — Arka Plan",
        "btn_stop_hover":        "Durdur — Üzerine Gelme",
        "btn_purple_bg":         "Mor — Arka Plan",
        "btn_purple_hover":      "Mor — Üzerine Gelme",
        "btn_teal_bg":           "Teal — Arka Plan",
        "btn_teal_hover":        "Teal — Üzerine Gelme",
        "btn_info_bg":           "Bilgi — Arka Plan",
        "btn_info_hover":        "Bilgi — Üzerine Gelme",
        "btn_steel_bg":          "Çelik — Arka Plan",
        "btn_steel_hover":       "Çelik — Üzerine Gelme",
        "btn_ocean_bg":          "Okyanus — Arka Plan",
        "btn_ocean_hover":       "Okyanus — Üzerine Gelme",
        "btn_brown_bg":          "Kahverengi — Arka Plan",
        "btn_brown_hover":       "Kahverengi — Üzerine Gelme",
        "btn_deep_purple_bg":    "Koyu Mor — Arka Plan",
        "btn_deep_purple_hover": "Koyu Mor — Üzerine Gelme",
        "btn_pink_bg":           "Pembe — Arka Plan",
        "btn_pink_hover":        "Pembe — Üzerine Gelme",
        "btn_padding":           "İç Boşluk",
        "btn_max_height":        "Maksimum Yükseklik",
    }),
    "inputs": ("✏️ Giriş Alanları", {
        "input_bg":           "Arka Plan",
        "input_text":         "Metin Rengi",
        "input_border":       "Kenarlık",
        "input_focus_border": "Odak Kenarlığı",
        "input_focus_bg":     "Odak Arka Planı",
        "selection_bg":       "Seçim Arka Planı",
        "selection_text":     "Seçim Metin Rengi",
    }),
    "table": ("📊 Tablo", {
        "table_bg":       "Arka Plan",
        "table_text":     "Metin Rengi",
        "table_grid":     "Izgara Rengi",
        "table_border":   "Kenarlık",
        "table_selected": "Seçim Rengi",
        "table_alt_bg":   "Alternatif Satır",
        "header_bg":      "Başlık Arka Planı",
        "header_text":    "Başlık Metin Rengi",
    }),
    "list": ("📋 Liste", {
        "list_bg":       "Arka Plan",
        "list_text":     "Metin Rengi",
        "list_border":   "Kenarlık",
        "list_selected": "Seçim Arka Planı",
        "list_sel_text": "Seçim Metin Rengi",
        "list_hover":    "Üzerine Gelme",
    }),
    "progress": ("⏳ İlerleme Çubuğu", {
        "progress_bg":         "Arka Plan",
        "progress_grad_start": "Gradient Başlangıç",
        "progress_grad_mid1":  "Gradient Orta-1",
        "progress_grad_mid2":  "Gradient Orta-2",
        "progress_grad_end":   "Gradient Bitiş",
        "progress_height":     "Yükseklik",
    }),
    "tabs": ("📑 Sekmeler", {
        "tab_bg":           "Pasif Sekme Arka Plan",
        "tab_text":         "Pasif Sekme Metin",
        "tab_active_start": "Aktif Sekme Gradient Baş.",
        "tab_active_end":   "Aktif Sekme Gradient Bit.",
        "tab_active_text":  "Aktif Sekme Metin",
        "tab_hover_bg":     "Üzerine Gelme",
        "pane_bg":          "Panel Arka Planı",
        "pane_border":      "Panel Kenarlığı",
    }),
    "scrollbar": ("↕️ Kaydırma Çubuğu", {
        "scrollbar_bg":     "Arka Plan",
        "scrollbar_handle": "Tutamaç",
        "scrollbar_hover":  "Tutamaç Üzerine Gelme",
        "scrollbar_width":  "Genişlik",
    }),
    "menubar": ("🗂️ Menü Çubuğu", {
        "menubar_bg":    "Menü Çubuğu Arka Planı",
        "menubar_text":  "Menü Çubuğu Metni",
        "menu_bg":       "Menü Arka Planı",
        "menu_text":     "Menü Metni",
        "menu_selected": "Seçili Öğe Arka Planı",
        "menu_sel_text": "Seçili Öğe Metni",
        "menu_border":   "Menü Kenarlığı",
    }),
    "statusbar": ("📌 Durum Çubuğu", {
        "statusbar_bg":     "Arka Plan",
        "statusbar_text":   "Metin Rengi",
        "statusbar_border": "Üst Kenarlık",
    }),
    "groupbox": ("📦 Grup Kutusu", {
        "groupbox_border": "Kenarlık",
        "groupbox_title":  "Başlık Rengi",
    }),
}

# Renk içeren token key'leri (renk picker açılır; diğerleri metin kutusu)
COLOR_KEYS = {k for cat_data in CATEGORY_META.values() for k in cat_data[1].keys()
              if not k.endswith(("_padding", "_height", "_width", "_size", "_family", "_radius"))}


def _is_color_key(key: str) -> bool:
    return not any(key.endswith(sfx) for sfx in
                   ("_padding", "_height", "_width", "_font_size", "_font_family",
                    "border_radius", "font_size", "font_family", "btn_padding",
                    "btn_max_height", "progress_height", "scrollbar_width"))


def _color_pixmap(hex_color: str, size: int = 16) -> QPixmap:
    """Verilen renk için küçük kare pixmap oluşturur."""
    pm = QPixmap(size, size)
    try:
        color = QColor(hex_color)
        if not color.isValid():
            color = QColor("#888888")
    except Exception:
        color = QColor("#888888")
    pm.fill(color)
    return pm


# Renk örneği kutusu
class ColorSwatch(QLabel):
    """Tıklanabilir renk örneği kutusu."""
    clicked = pyqtSignal(str)  # hex renk

    def __init__(self, hex_color: str = "#000000", parent=None):
        super().__init__(parent)
        self._color = hex_color
        self.setFixedSize(22, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Renk seç")
        self._update_style()

    def set_color(self, hex_color: str):
        self._color = hex_color
        self._update_style()

    def get_color(self) -> str:
        return self._color

    def _update_style(self):
        self.setStyleSheet(
            f"background-color: {self._color}; border: 1px solid #666; border-radius: 3px;"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._color)
        super().mousePressEvent(event)


# önizleme bölümü
class PreviewCard(QFrame):
    """
    Tema önizleme kartı.
    Seçilen token'ın ana kanallarını (arka plan, metin, vurgu rengi vb.)
    görsel bir kart üzerinde anlık gösterir.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(180)
        self._tokens: dict = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("🎨 Önizleme")
        title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(title)

        # Ana renkler satırı
        self._swatch_layout = QHBoxLayout()
        self._swatches: dict[str, QLabel] = {}
        for tag, label in [
            ("background", "Arka Plan"),
            ("text_color",  "Metin"),
            ("input_bg",    "Giriş"),
            ("tab_active_start", "Vurgu"),
            ("progress_grad_start", "İlerleme"),
        ]:
            col = QVBoxLayout()
            sw = QLabel()
            sw.setFixedSize(32, 32)
            sw.setStyleSheet("border: 1px solid #555; border-radius: 4px;")
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 7pt;")
            col.addWidget(sw, alignment=Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl)
            self._swatch_layout.addLayout(col)
            self._swatches[tag] = sw
        layout.addLayout(self._swatch_layout)

        # Küçük mock-UI
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #555;")
        layout.addWidget(sep)

        self._mock_label = QLabel("Örnek Metin")
        self._mock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._mock_label)

        self._mock_btn = QPushButton("Örnek Buton")
        self._mock_btn.setEnabled(False)
        layout.addWidget(self._mock_btn)

        layout.addStretch()

    def update_preview(self, tokens: dict):
        """Token sözlüğüne göre önizlemeyi günceller."""
        self._tokens = tokens
        g = tokens.get("general", {})
        i = tokens.get("inputs",  {})
        tb = tokens.get("tabs",   {})
        p  = tokens.get("progress", {})

        bg   = g.get("background", "#1E1E2E")
        txt  = g.get("text_color", "#CDD6F4")
        inbg = i.get("input_bg",   "#181825")
        acc  = tb.get("tab_active_start", "#89B4FA")
        prg  = p.get("progress_grad_start", "#48CAE4")

        mapping = {
            "background": bg,
            "text_color": txt,
            "input_bg":   inbg,
            "tab_active_start": acc,
            "progress_grad_start": prg,
        }
        for tag, color in mapping.items():
            if tag in self._swatches:
                try:
                    qc = QColor(color)
                    if qc.isValid():
                        self._swatches[tag].setStyleSheet(
                            f"background-color: {color}; border: 1px solid #555; border-radius: 4px;"
                        )
                except Exception:
                    pass

        # Mock UI stilleri
        self.setStyleSheet(f"background-color: {bg}; border: 1px solid #444; border-radius: 6px;")
        self._mock_label.setStyleSheet(f"color: {txt}; font-size: 9pt;")
        self._mock_btn.setStyleSheet(
            f"background-color: {acc}; color: {bg}; border-radius: 4px; "
            f"padding: 4px 10px; font-weight: bold;"
        )


# Tema Yönetici Diyalog
class ThemeManagerDialog(QDialog):
    """Ana Tema Yöneticisi Diyalogu."""

    theme_applied = pyqtSignal(str)   # varsayılan tema değiştiğinde yeni tema adı

    def __init__(self, current_theme: str = "dark", parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎨 Tema Yöneticisi")
        self.resize(1000, 680)
        self.setMinimumSize(800, 560)

        self._current_theme = current_theme   # aktif uygulama teması
        self._selected_theme: str = ""        # listede seçili tema
        self._tokens: dict = {}               # düzenlenen token kopyası
        self._dirty: bool = False             # kaydedilmemiş değişiklik var mı

        self._build_ui()
        self._load_theme_list()
        
        # Mevcut uygulanan temayı seçili hale getir
        for i in range(self.theme_list.count()):
            item = self.theme_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == self._current_theme:
                self.theme_list.setCurrentRow(i)
                break

    # UI Oluşturma

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSizeConstraint(QVBoxLayout.SizeConstraint.SetNoConstraint)

        # Başlık
        title = QLabel("🎨 Tema Yöneticisi")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        root.addWidget(title)

        # Ana splitter: sol liste | orta tree | sağ edit+önizleme
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sol Panel: Tema Listesi
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(4)

        list_label = QLabel("📂 Temalar")
        list_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        left_layout.addWidget(list_label)

        self.theme_list = QListWidget()
        self.theme_list.setMinimumWidth(180)
        self.theme_list.currentRowChanged.connect(self._on_theme_selected)
        left_layout.addWidget(self.theme_list)

        # Sol butonlar
        btn_grid = QVBoxLayout()
        btn_grid.setSpacing(3)
        for label, slot in [
            ("➕ Yeni Tema",        self._create_new_theme),
            ("📋 Farklı Kaydet",   self._save_as),
            ("⬆️ Dışa Aktar",      self._export_theme),
            ("⬇️ İçe Aktar",       self._import_theme),
            ("🗑 Sil",              self._delete_theme),
            ("✅ Varsayılan Yap",  self._set_as_default),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(f"btn_{label.replace(' ', '_')}")
            btn.clicked.connect(slot)
            btn_grid.addWidget(btn)
        left_layout.addLayout(btn_grid)

        splitter.addWidget(left_widget)

        # Orta Panel: TreeWidget
        mid_widget = QWidget()
        mid_layout = QVBoxLayout(mid_widget)
        mid_layout.setContentsMargins(4, 0, 4, 0)
        mid_layout.setSpacing(4)

        tree_label = QLabel("🌳 Tema Kategorileri")
        tree_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        mid_layout.addWidget(tree_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Öğe", "Değer"])
        self.tree.setMinimumWidth(260)
        self.tree.header().setDefaultSectionSize(160)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        mid_layout.addWidget(self.tree)

        splitter.addWidget(mid_widget)

        # Sağ Panel: Düzenleyici + Önizleme
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(6)

        # Önizleme Kartı
        self.preview_card = PreviewCard()
        right_layout.addWidget(self.preview_card)

        # Seçili token düzenleyicisi
        editor_group = QGroupBox("✏️ Token Düzenleyici")
        editor_form = QFormLayout(editor_group)
        editor_form.setSpacing(8)

        self._token_name_label = QLabel("—")
        self._token_name_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        editor_form.addRow("Token:", self._token_name_label)

        # Renk seçici satırı
        color_row = QHBoxLayout()
        self._color_swatch = ColorSwatch("#888888")
        self._color_swatch.clicked.connect(self._open_color_picker)
        self._color_input = QLineEdit()
        self._color_input.setPlaceholderText("#RRGGBB veya değer...")
        self._color_input.textChanged.connect(self._on_color_text_changed)
        color_row.addWidget(self._color_swatch)
        color_row.addWidget(self._color_input)
        editor_form.addRow("Değer:", color_row)

        apply_btn = QPushButton("✔ Değişiklikleri Uygula")
        apply_btn.clicked.connect(self._apply_token_edit)
        editor_form.addRow("", apply_btn)

        right_layout.addWidget(editor_group)

        # Tema başlığı düzenleyicisi
        name_group = QGroupBox("🏷️ Tema Bilgisi")
        name_form = QFormLayout(name_group)
        name_form.setSpacing(6)
        self._theme_label_edit = QLineEdit()
        self._theme_label_edit.setPlaceholderText("Görünür tema adı...")
        name_form.addRow("Tema Adı:", self._theme_label_edit)
        right_layout.addWidget(name_group)

        right_layout.addStretch()
        splitter.addWidget(right_widget)

        splitter.setSizes([160, 240, 420])
        root.addWidget(splitter, 1)

        # Alt Buton Çubuğu
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self._save_btn = QPushButton("💾 Kaydet")
        self._save_btn.setStyleSheet(
            "background-color: #2E7D32; color: white; font-weight: bold; "
            "padding: 6px 16px; border-radius: 4px;"
        )
        self._save_btn.clicked.connect(self._save_current_theme)

        self._save_as_btn = QPushButton("📋 Farklı Kaydet")
        self._save_as_btn.setStyleSheet(
            "background-color: #1565C0; color: white; font-weight: bold; "
            "padding: 6px 16px; border-radius: 4px;"
        )
        self._save_as_btn.clicked.connect(self._save_as)

        cancel_btn = QPushButton("✖ Kapat")
        cancel_btn.setStyleSheet("padding: 6px 16px; border-radius: 4px;")
        cancel_btn.clicked.connect(self._on_close)

        btn_bar.addStretch()
        btn_bar.addWidget(self._save_btn)
        btn_bar.addWidget(self._save_as_btn)
        btn_bar.addWidget(cancel_btn)
        root.addLayout(btn_bar)

        # Editor state
        self._active_cat: str = ""
        self._active_key: str = ""

    # Tema Listesi

    def _load_theme_list(self):
        """Sol listeyi yeniler."""
        self.theme_list.clear()
        for info in list_themes():
            label = info["label"]
            if info["name"] == self._current_theme:
                label += "  ✅"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, info["name"])
            if info["builtin"]:
                item.setForeground(QColor("#89B4FA"))
            self.theme_list.addItem(item)
            
        # Eğer aktif bir tema daha önceden seçiliyken liste yenilenirse, onu tekrar seç:
        if self._selected_theme:
            for i in range(self.theme_list.count()):
                if self.theme_list.item(i).data(Qt.ItemDataRole.UserRole) == self._selected_theme:
                    self.theme_list.blockSignals(True)
                    self.theme_list.setCurrentRow(i)
                    self.theme_list.blockSignals(False)
                    break

    def _on_theme_selected(self, row: int):
        """Listeden tema seçildiğinde çalışır."""
        if row < 0:
            return
        item = self.theme_list.item(row)
        if not item:
            return

        # Kaydedilmemiş değişiklik kontrolü
        if self._dirty and self._selected_theme:
            ans = QMessageBox.question(
                self, "Kaydedilmemiş Değişiklik",
                "Değişiklikler kaydedilmedi. Yine de devam edilsin mi?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ans == QMessageBox.StandardButton.No:
                # Önceki seçime geri dön
                self._reselect_current()
                return

        name = item.data(Qt.ItemDataRole.UserRole)
        self._selected_theme = name
        self._tokens = load_theme_tokens(name)
        self._dirty = False

        # Label bilgisini doldur
        themes = {t["name"]: t for t in list_themes()}
        self._theme_label_edit.setText(themes.get(name, {}).get("label", name))
        self._theme_label_edit.setReadOnly(name in BUILTIN_THEMES)

        # TreeView'u doldur
        self._populate_tree()

        # Önizlemeyi güncelle
        self.preview_card.update_preview(self._tokens)

        # Kaydet butonu: yerleşik temalar için devre dışı
        self._save_btn.setEnabled(name not in BUILTIN_THEMES)

    def _reselect_current(self):
        """Önceki seçili temaya geri döner."""
        for i in range(self.theme_list.count()):
            item = self.theme_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == self._selected_theme:
                self.theme_list.blockSignals(True)
                self.theme_list.setCurrentRow(i)
                self.theme_list.blockSignals(False)
                break

    # TreeWidget

    def _populate_tree(self):
        """TreeWidget'ı token sözlüğüyle doldurur."""
        self.tree.clear()
        for cat_key, (cat_label, keys_meta) in CATEGORY_META.items():
            cat_item = QTreeWidgetItem([cat_label, ""])
            cat_item.setData(0, Qt.ItemDataRole.UserRole, ("__cat__", cat_key))
            cat_item.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))
            cat_tokens = self._tokens.get(cat_key, {})

            for key, human_label in keys_meta.items():
                value = cat_tokens.get(key, "")
                child = QTreeWidgetItem([human_label, value])
                child.setData(0, Qt.ItemDataRole.UserRole, (cat_key, key))
                child.setToolTip(0, key)
                # Renk ise küçük ikon ekle
                if _is_color_key(key) and value.startswith("#"):
                    try:
                        child.setIcon(1, QIcon(_color_pixmap(value, 14)))
                    except Exception:
                        pass
                cat_item.addChild(child)

            self.tree.addTopLevelItem(cat_item)
        self.tree.expandAll()

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """TreeWidget öğesine tıklandığında editörü doldurur."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] == "__cat__":
            return
        cat_key, key = data
        self._active_cat = cat_key
        self._active_key = key

        human = CATEGORY_META.get(cat_key, ("", {}))[1].get(key, key)
        self._token_name_label.setText(f"{cat_key} → {human}")

        value = self._tokens.get(cat_key, {}).get(key, "")
        self._color_input.blockSignals(True)
        self._color_input.setText(value)
        self._color_input.blockSignals(False)

        if _is_color_key(key):
            self._color_swatch.set_color(value if value.startswith("#") else "#888888")
            self._color_swatch.setVisible(True)
        else:
            self._color_swatch.setVisible(False)

    def _on_color_text_changed(self, text: str):
        """Renk girişi değiştiğinde swatch'ı günceller."""
        if text.startswith("#") and len(text) in (4, 7, 9):
            try:
                qc = QColor(text)
                if qc.isValid():
                    self._color_swatch.set_color(text)
            except Exception:
                pass

    def _open_color_picker(self, current: str):
        """QColorDialog açar ve seçilen rengi input'a yazar."""
        try:
            init_color = QColor(current)
        except Exception:
            init_color = QColor("#888888")
        color = QColorDialog.getColor(init_color, self, "Renk Seç",
                                      QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            hex_color = color.name(QColor.NameFormat.HexRgb)
            self._color_input.setText(hex_color)
            self._color_swatch.set_color(hex_color)

    def _apply_token_edit(self):
        """Düzenlenen değeri token sözlüğüne uygular ve önizlemeyi günceller."""
        if not self._active_cat or not self._active_key:
            return
        value = self._color_input.text().strip()
        if not value:
            return

        if self._active_cat not in self._tokens:
            self._tokens[self._active_cat] = {}
            
        old_val = self._tokens[self._active_cat].get(self._active_key, "N/A")
        self._tokens[self._active_cat][self._active_key] = value
        self._dirty = True
        
        app_logger.debug(f"Tema token'ı güncellendi: {self._active_cat} -> {self._active_key} = {value} (Eski: {old_val})")

        # TreeView'daki değeri güncelle
        self._update_tree_item(self._active_cat, self._active_key, value)
        # Önizlemeyi güncelle
        self.preview_card.update_preview(self._tokens)
        
        # Eğer düzenlenen tema uygulamanın mevcut temasıysa, aktif önizleme yap (Anında uygula)
        if self._selected_theme == self._current_theme:
            try:
                from core.theme_engine import tokens_to_qss
                from PyQt6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    app.setStyleSheet(tokens_to_qss(self._tokens))
            except Exception as e:
                app_logger.error(f"Canlı önizleme uygulanırken hata: {e}")

    def _update_tree_item(self, cat_key: str, key: str, value: str):
        """Token değerini TreeWidget'ta günceller."""
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            data = top.data(0, Qt.ItemDataRole.UserRole)
            if data and data[1] == cat_key:
                for j in range(top.childCount()):
                    child = top.child(j)
                    cdata = child.data(0, Qt.ItemDataRole.UserRole)
                    if cdata and cdata[1] == key:
                        child.setText(1, value)
                        if _is_color_key(key) and value.startswith("#"):
                            try:
                                child.setIcon(1, QIcon(_color_pixmap(value, 14)))
                            except Exception:
                                pass
                        return

    # Tema İşlemleri

    def _create_new_theme(self):
        """Yeni boş tema oluşturur (dark tabanında)."""
        name, ok = QInputDialog.getText(
            self, "Yeni Tema", "Tema adı girin (boşluksuz, İngilizce):",
            text="my_theme"
        )
        if not ok or not name.strip():
            return
        name = name.strip().lower().replace(" ", "_")
        if name in BUILTIN_THEMES:
            QMessageBox.warning(self, "Hata", "Bu isim yerleşik bir tema için ayrılmıştır.")
            return

        label, ok2 = QInputDialog.getText(
            self, "Yeni Tema", "Temaya görünür bir etiket verin:",
            text=name.replace("_", " ").title()
        )
        if not ok2:
            return

        # dark tabanında başlat
        from core.theme_engine import _deep_copy, DEFAULT_DARK_TOKENS
        tokens = _deep_copy(DEFAULT_DARK_TOKENS)
        if save_custom_theme(name, label.strip() or name, "dark", tokens):
            self._load_theme_list()
            # Yeni temayı seç
            for i in range(self.theme_list.count()):
                item = self.theme_list.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == name:
                    self.theme_list.setCurrentRow(i)
                    break
        else:
            QMessageBox.critical(self, "Hata", "Tema oluşturulamadı.")

    def _save_current_theme(self):
        """Mevcut seçili temayı kaydeder (yalnızca özel temalar)."""
        app_logger.info(f"Tema kaydetme isteği: {self._selected_theme}")
        
        if not self._selected_theme or self._selected_theme in BUILTIN_THEMES:
            QMessageBox.information(self, "Bilgi", "Yerleşik temalar kaydedilemez.\n'Farklı Kaydet' seçeneğini kullanın.")
            app_logger.warning(f"Yerleşik tema kaydedilmeye çalışıldı: {self._selected_theme}")
            return
            
        label = self._theme_label_edit.text().strip() or self._selected_theme
        
        # Tema kaydı
        if save_custom_theme(self._selected_theme, label, "dark", self._tokens):
            self._dirty = False
            self._load_theme_list()
            app_logger.info(f"Tema başarıyla kaydedildi: {self._selected_theme} ({label})")
            
            # Eğer kaydedilen tema, uygulamadaki aktif temaysa, anında uygula.
            if self._selected_theme == self._current_theme:
                app_logger.info(f"Aktif tema güncellendi, canlı önizleme/uygulama için sinyal gönderiliyor: {self._selected_theme}")
                self.theme_applied.emit(self._selected_theme)
                
            QMessageBox.information(self, "Kaydedildi", f"'{label}' teması başarıyla kaydedildi.")
        else:
            app_logger.error(f"Tema kaydedilirken hata oluştu: {self._selected_theme}")
            QMessageBox.critical(self, "Hata", "Tema kaydedilemedi. Klasör izinlerini kontrol edin.")

    def _save_as(self):
        """Aktif temayı yeni isimle kaydeder."""
        if not self._selected_theme:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir tema seçin.")
            return

        name, ok = QInputDialog.getText(
            self, "Farklı Kaydet", "Yeni tema adını girin (boşluksuz):",
            text=f"{self._selected_theme}_kopya"
        )
        if not ok or not name.strip():
            return
        name = name.strip().lower().replace(" ", "_")
        if name in BUILTIN_THEMES:
            QMessageBox.warning(self, "Hata", "Bu isim yerleşik bir tema için ayrılmıştır.")
            return

        label, ok2 = QInputDialog.getText(
            self, "Farklı Kaydet", "Temaya görünür etiket verin:",
            text=self._theme_label_edit.text() + " (Kopya)"
        )
        if not ok2:
            return

        import copy as _copy
        tokens_copy = _copy.deepcopy(self._tokens)
        app_logger.info(f"Farklı kaydet isteği: '{self._selected_theme}' -> '{name}'")
        
        if save_custom_theme(name, label.strip() or name, "dark", tokens_copy):
            self._dirty = False
            self._load_theme_list()
            app_logger.info(f"Tema başarıyla farklı kaydedildi: {name}")
            
            QMessageBox.information(self, "Kaydedildi", f"'{label}' adıyla başarıyla farklı kaydedildi.")
            # Yeni temayı seç
            for i in range(self.theme_list.count()):
                item = self.theme_list.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == name:
                    self.theme_list.setCurrentRow(i)
                    break
        else:
            app_logger.error(f"Farklı kaydetme başarısız: {name}")
            QMessageBox.critical(self, "Hata", "Farklı kaydetme başarısız. Klasör izinlerini kontrol edin.")

    def _delete_theme(self):
        """Seçili temayı siler."""
        if not self._selected_theme:
            return
        if self._selected_theme in BUILTIN_THEMES:
            QMessageBox.warning(self, "Silinemez",
                                "Yerleşik temalar (dark, light) silinemez!")
            return
        ans = QMessageBox.question(
            self, "Temayı Sil",
            f"'{self._selected_theme}' teması kalıcı olarak silinecek. Emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            if delete_theme(self._selected_theme):
                self._selected_theme = ""
                self._tokens = {}
                self._dirty = False
                self.tree.clear()
                self.preview_card.update_preview({})
                self._load_theme_list()
            else:
                QMessageBox.critical(self, "Hata", "Tema silinemedi.")

    def _set_as_default(self):
        """Seçili temayı app_settings.json'da varsayılan yapar."""
        if not self._selected_theme:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir tema seçin.")
            return
        try:
            from ui.app_settings_dialog import load_app_settings, save_app_settings
            settings = load_app_settings()
            settings["theme"] = self._selected_theme
            save_app_settings(settings)
            self._current_theme = self._selected_theme
            self._load_theme_list()
            self.theme_applied.emit(self._selected_theme)
            QMessageBox.information(
                self, "Varsayılan Ayarlandı",
                f"'{self._selected_theme}' varsayılan tema olarak ayarlandı.\n"
                "Değişikliğin tam etkisi için uygulamayı yeniden başlatın."
            )
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Varsayılan ayarlanamadı:\n{e}")

    def _export_theme(self):
        """Seçili temayı JSON dosyası olarak dışa aktarır."""
        if not self._selected_theme:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir tema seçin.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Temayı Dışa Aktar",
            os.path.join(os.path.expanduser("~"), "Desktop", f"{self._selected_theme}.json"),
            "JSON Tema Dosyası (*.json);;Tüm Dosyalar (*)"
        )
        if path:
            if export_theme(self._selected_theme, path):
                QMessageBox.information(self, "Dışa Aktarıldı", f"Tema dışa aktarıldı:\n{path}")
            else:
                QMessageBox.critical(self, "Hata", "Dışa aktarma başarısız.")

    def _import_theme(self):
        """JSON tema dosyasını içe aktarır."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Tema İçe Aktar", "",
            "JSON Tema Dosyası (*.json);;Tüm Dosyalar (*)"
        )
        if path:
            result = import_theme(path)
            if result:
                self._load_theme_list()
                QMessageBox.information(self, "İçe Aktarıldı",
                                        f"'{result}' teması içe aktarıldı.")
            else:
                QMessageBox.critical(self, "Hata", "İçe aktarma başarısız. Dosya geçersiz olabilir.")

    def _on_close(self):
        """Kapatma düğmesine basıldığında kaydedilmemiş değişiklik kontrolü."""
        if self._dirty:
            ans = QMessageBox.question(
                self, "Kaydedilmemiş Değişiklik",
                "Kaydedilmemiş değişiklikler var. Yine de çıkılsın mı?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ans == QMessageBox.StandardButton.No:
                return
            else:
                # İptal edilirse uygulamaya geri yükle (canlı önizlemeyi geri al)
                self.theme_applied.emit(self._current_theme)
        self.accept()

    def closeEvent(self, event):
        if self._dirty:
            ans = QMessageBox.question(
                self, "Kaydedilmemiş Değişiklik",
                "Kaydedilmemiş değişiklikler var. Yine de çıkılsın mı?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ans == QMessageBox.StandardButton.No:
                event.ignore()
                return
            else:
                # İptal edilirse uygulamaya geri yükle (canlı önizlemeyi geri al)
                self.theme_applied.emit(self._current_theme)
        event.accept()
