import sys
from PyQt6.QtWidgets import QDialog, QLineEdit, QFormLayout, QDialogButtonBox, QMessageBox, QLabel, QApplication, QTextEdit
from PyQt6.QtGui import QIntValidator
from PyQt6.QtCore import Qt

class NewProjectDialog(QDialog):
    """Yeni proje adı, linki, maksimum sayfa ve API anahtarı almak için özel bir diyalog penceresi."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Proje Oluştur")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)
        self.projectNameInput = QLineEdit(self)
        self.projectNameInput.setPlaceholderText("Proje adını giriniz...")
        self.projectLinkInput = QLineEdit(self)
        self.projectLinkInput.setPlaceholderText("Başlangıç linkini giriniz (örn: https://example.com/page1)...")
        
        self.maxPagesInput = QLineEdit(self)
        self.maxPagesInput.setPlaceholderText("İndirilecek maksimum sayfa sayısı (isteğe bağlı)")
        self.maxPagesInput.setValidator(QIntValidator(1, 999999)) # Sadece sayı girişi
        
        self.api_key_input = QLineEdit(self)
        self.api_key_input.setPlaceholderText("Gemini API Anahtarınızı giriniz (AIzaSy...)")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal) # API anahtarını gizle
        self.api_key_input.setText("TEST_KEY")  # Varsayılan API anahtarı

        self.startpromtinput = QTextEdit(self)
        self.startpromtinput.setPlaceholderText("Başlangıç Promtu giriniz...")
        #self.startpromtinput.setEchoMode(QLineEdit.EchoMode.Normal) # Başlangıç promtu doğrudan göster
        self.startpromtinput.setText("TEST_PROMT \n\n")  # Varsayılan başlangıç istemi

        layout.addRow("Proje Adı:", self.projectNameInput)
        layout.addRow("Proje Linki:", self.projectLinkInput)
        layout.addRow("Maksimum Sayfa:", self.maxPagesInput)
        layout.addRow("Gemini API Key:", self.api_key_input)
        layout.addRow("Başlangıç Promtu:", self.startpromtinput)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        max_pages_text = self.maxPagesInput.text()
        max_pages = int(max_pages_text) if max_pages_text.isdigit() else None
        return self.projectNameInput.text(), self.projectLinkInput.text(), max_pages, self.api_key_input.text(), self.startpromtinput.toPlainText()


class ProjectSettingsDialog(QDialog):
    """Mevcut proje ayarlarını düzenlemek için özel bir diyalog penceresi."""
    def __init__(self, project_name, project_link, max_pages, api_key, start_promt, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"'{project_name}' Proje Ayarları")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)

        # Proje Adı - Genellikle düzenlenmemelidir, aksi takdirde klasör yeniden adlandırma gibi karmaşık mantık gerekir.
        # Şimdilik sadece gösterim amaçlı okunabilir yapalım.
        self.projectNameLabel = QLabel(project_name)
        self.projectNameLabel.setContentsMargins(0, 5, 0, 5) # Dikey boşluk
        self.projectNameLabel.setStyleSheet("font-weight: bold;") # Kalın yazı tipi

        self.projectLinkInput = QLineEdit(self)
        self.projectLinkInput.setPlaceholderText("Proje linkini giriniz...")
        self.projectLinkInput.setText(project_link)
        
        self.maxPagesInput = QLineEdit(self)
        self.maxPagesInput.setPlaceholderText("İndirilecek maksimum sayfa sayısı (isteğe bağlı)")
        self.maxPagesInput.setValidator(QIntValidator(1, 999999))
        if max_pages is not None:
            self.maxPagesInput.setText(str(max_pages))
        
        self.api_key_input = QLineEdit(self)
        self.api_key_input.setPlaceholderText("Gemini API Anahtarınızı giriniz (AIzaSy...)")
        self.api_key_input.setText(api_key)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal) # API anahtarını doğrudan göster

        self.startpromtinput = QTextEdit(self)
        self.startpromtinput.setPlaceholderText("Başlangıç Promtu giriniz...")
        self.startpromtinput.setText(start_promt)
        #self.startpromtinput.setEchoMode(QLineEdit.EchoMode.Normal) # Başlangıç promtu doğrudan göster
        
        layout.addRow("Proje Adı:", self.projectNameLabel)
        layout.addRow("Proje Linki:", self.projectLinkInput)
        layout.addRow("Maksimum Sayfa:", self.maxPagesInput)
        layout.addRow("Gemini API Key:", self.api_key_input)
        layout.addRow("Başlangıç Promtu:", self.startpromtinput)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        max_pages_text = self.maxPagesInput.text()
        max_pages = int(max_pages_text) if max_pages_text.isdigit() else None
        
        return {
            "link": self.projectLinkInput.text(),
            "max_pages": max_pages,
            "api_key": self.api_key_input.text(),
            "Startpromt": self.startpromtinput.toPlainText()
        }

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # New Project Dialog Test
    # dialog = NewProjectDialog()
    # if dialog.exec():
    #     name, link, max_pages, api_key = dialog.get_data()
    #     print(f"Yeni Proje -> Adı: {name}, Link: {link}, Max Sayfa: {max_pages}, API Key: {api_key}")
    # else:
    #     print("Yeni Proje oluşturma iptal edildi.")

    # Project Settings Dialog Test
    current_name = "Test Proje"
    current_link = "https://example.com/test"
    current_max_pages = 50
    current_api_key = "AIzaSyD_TEST_KEY_123"

    settings_dialog = ProjectSettingsDialog(current_name, current_link, current_max_pages, current_api_key)
    if settings_dialog.exec():
        updated_data = settings_dialog.get_data()
        print(f"Ayarlar güncellendi -> Link: {updated_data['link']}, Max Sayfa: {updated_data['max_pages']}, API Key: {updated_data['api_key']}")
    else:
        print("Ayarlar düzenleme iptal edildi.")

    sys.exit(app.exec())
