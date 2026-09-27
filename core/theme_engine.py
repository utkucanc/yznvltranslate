"""
ThemeEngine — JSON tabanlı tema CRUD ve QSS dönüşüm motoru.

Özellikler:
  - Hem .qss (yerleşik: dark, light) hem .json (özel) temaları yönetir
  - JSON tema → QSS dönüşümü
  - Tema import / export
  - Yerleşik temalar (dark, light) silinemez ve üzerine yazılamaz
"""
from core.localization import tr_log
import os
import json
import shutil
from datetime import datetime
from typing import Optional
from logger import app_logger
THEMES_DIR = os.path.join(os.getcwd(), 'AppConfigs', 'themes')
META_FILE = os.path.join(THEMES_DIR, 'themes_meta.json')
BUILTIN_THEMES = {'dark', 'light'}
DEFAULT_DARK_TOKENS = {'general': {'background': '#1E1E2E', 'text_color': '#CDD6F4', 'font_family': 'Segoe UI Variable, Segoe UI, Inter, Arial, sans-serif', 'font_size': '9pt', 'border_color': '#45475A', 'border_radius': '4px'}, 'buttons': {'btn_success_bg': '#2E7D32', 'btn_success_hover': '#388E3C', 'btn_primary_bg': '#283593', 'btn_primary_hover': '#303F9F', 'btn_stop_bg': '#B71C1C', 'btn_stop_hover': '#C62828', 'btn_purple_bg': '#6A1B9A', 'btn_purple_hover': '#7B1FA2', 'btn_teal_bg': '#00695C', 'btn_teal_hover': '#00796B', 'btn_info_bg': '#0D47A1', 'btn_info_hover': '#1565C0', 'btn_steel_bg': '#37474F', 'btn_steel_hover': '#455A64', 'btn_ocean_bg': '#01579B', 'btn_ocean_hover': '#0277BD', 'btn_brown_bg': '#4E342E', 'btn_brown_hover': '#5D4037', 'btn_deep_purple_bg': '#4527A0', 'btn_deep_purple_hover': '#512DA8', 'btn_pink_bg': '#880E4F', 'btn_pink_hover': '#AD1457', 'btn_padding': '4px 10px', 'btn_max_height': '28px'}, 'inputs': {'input_bg': '#181825', 'input_text': '#CDD6F4', 'input_border': '#45475A', 'input_focus_border': '#89B4FA', 'input_focus_bg': '#1A1A2C', 'selection_bg': '#89B4FA', 'selection_text': '#1E1E2E'}, 'table': {'table_bg': '#181825', 'table_text': '#CDD6F4', 'table_grid': '#2A2A3E', 'table_border': '#313244', 'table_selected': '#3A3A55', 'table_alt_bg': '#1E1E30', 'header_bg': '#252537', 'header_text': '#89B4FA'}, 'list': {'list_bg': '#181825', 'list_text': '#CDD6F4', 'list_border': '#313244', 'list_selected': '#3A3A55', 'list_sel_text': '#89DCEB', 'list_hover': '#2A2A40'}, 'progress': {'progress_bg': '#181830', 'progress_grad_start': '#48CAE4', 'progress_grad_mid1': '#89B4FA', 'progress_grad_mid2': '#CBA6F7', 'progress_grad_end': '#F38BA8', 'progress_height': '10px'}, 'tabs': {'tab_bg': '#252537', 'tab_text': '#A6ADC8', 'tab_active_start': '#89B4FA', 'tab_active_end': '#74C7EC', 'tab_active_text': '#1E1E2E', 'tab_hover_bg': '#313244', 'pane_bg': '#1E1E2E', 'pane_border': '#313244'}, 'scrollbar': {'scrollbar_bg': '#111120', 'scrollbar_handle': '#45475A', 'scrollbar_hover': '#89B4FA', 'scrollbar_width': '6px'}, 'menubar': {'menubar_bg': '#11111B', 'menubar_text': '#CDD6F4', 'menu_bg': '#1E1E2E', 'menu_text': '#CDD6F4', 'menu_selected': '#313244', 'menu_sel_text': '#89B4FA', 'menu_border': '#45475A'}, 'statusbar': {'statusbar_bg': '#11111B', 'statusbar_text': '#A6ADC8', 'statusbar_border': '#252537'}, 'groupbox': {'groupbox_border': '#313244', 'groupbox_title': '#89B4FA'}}
DEFAULT_LIGHT_TOKENS = {'general': {'background': '#F5F5F9', 'text_color': '#2C2C3A', 'font_family': 'Segoe UI Variable, Segoe UI, Inter, Arial, sans-serif', 'font_size': '9pt', 'border_color': '#C5C7D2', 'border_radius': '4px'}, 'buttons': {'btn_success_bg': '#388E3C', 'btn_success_hover': '#43A047', 'btn_primary_bg': '#3949AB', 'btn_primary_hover': '#3F51B5', 'btn_stop_bg': '#C62828', 'btn_stop_hover': '#D32F2F', 'btn_purple_bg': '#7B1FA2', 'btn_purple_hover': '#8E24AA', 'btn_teal_bg': '#00796B', 'btn_teal_hover': '#00897B', 'btn_info_bg': '#1565C0', 'btn_info_hover': '#1976D2', 'btn_steel_bg': '#546E7A', 'btn_steel_hover': '#607D8B', 'btn_ocean_bg': '#0277BD', 'btn_ocean_hover': '#0288D1', 'btn_brown_bg': '#5D4037', 'btn_brown_hover': '#6D4C41', 'btn_deep_purple_bg': '#512DA8', 'btn_deep_purple_hover': '#5E35B1', 'btn_pink_bg': '#AD1457', 'btn_pink_hover': '#C2185B', 'btn_padding': '4px 10px', 'btn_max_height': '28px'}, 'inputs': {'input_bg': '#FFFFFF', 'input_text': '#2C2C3A', 'input_border': '#C5C7D2', 'input_focus_border': '#1565C0', 'input_focus_bg': '#FAFAFE', 'selection_bg': '#1565C0', 'selection_text': '#FFFFFF'}, 'table': {'table_bg': '#FFFFFF', 'table_text': '#2C2C3A', 'table_grid': '#E8E8F0', 'table_border': '#D0D0DC', 'table_selected': '#DDEEFF', 'table_alt_bg': '#F5F5FF', 'header_bg': '#EEEEF8', 'header_text': '#1565C0'}, 'list': {'list_bg': '#FFFFFF', 'list_text': '#2C2C3A', 'list_border': '#D0D0DC', 'list_selected': '#DDEEFF', 'list_sel_text': '#0D47A1', 'list_hover': '#EEF2FF'}, 'progress': {'progress_bg': '#E8E8F4', 'progress_grad_start': '#1976D2', 'progress_grad_mid1': '#7E57C2', 'progress_grad_mid2': '#AB47BC', 'progress_grad_end': '#EC407A', 'progress_height': '10px'}, 'tabs': {'tab_bg': '#E8E8F0', 'tab_text': '#6C6F85', 'tab_active_start': '#1565C0', 'tab_active_end': '#1976D2', 'tab_active_text': '#FFFFFF', 'tab_hover_bg': '#D8D8E8', 'pane_bg': '#F5F5F9', 'pane_border': '#D0D0DC'}, 'scrollbar': {'scrollbar_bg': '#F0F0F8', 'scrollbar_handle': '#C5C7D2', 'scrollbar_hover': '#1565C0', 'scrollbar_width': '6px'}, 'menubar': {'menubar_bg': '#EEEEF8', 'menubar_text': '#2C2C3A', 'menu_bg': '#FFFFFF', 'menu_text': '#2C2C3A', 'menu_selected': '#DDEEFF', 'menu_sel_text': '#1565C0', 'menu_border': '#D0D0DC'}, 'statusbar': {'statusbar_bg': '#EEEEF8', 'statusbar_text': '#6C6F85', 'statusbar_border': '#D0D0DC'}, 'groupbox': {'groupbox_border': '#D0D0DC', 'groupbox_title': '#1565C0'}}

def _load_meta() -> dict:
    """themes_meta.json dosyasını yükler."""
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            app_logger.warning(tr_log('core.theme_engine', 247, f'themes_meta.json okunamadı: {e}'))
    return {'themes': {}}

def _save_meta(meta: dict):
    """themes_meta.json dosyasına meta verisini kaydeder."""
    os.makedirs(THEMES_DIR, exist_ok=True)
    try:
        with open(META_FILE, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
    except Exception as e:
        app_logger.error(tr_log('core.theme_engine', 258, f'themes_meta.json kaydedilemedi: {e}'))

def list_themes() -> list[dict]:
    """
    Tüm temaları (yerleşik + özel) listeler.
    Döndürür: [{"name": str, "label": str, "builtin": bool, "base": str}, ...]
    """
    themes = []
    builtin_labels = {'dark': 'Karanlık Mod (Varsayılan)', 'light': 'Aydınlık Mod (Varsayılan)'}
    for (name, label) in builtin_labels.items():
        themes.append({'name': name, 'label': label, 'builtin': True, 'base': name})
    meta = _load_meta()
    for (name, info) in meta.get('themes', {}).items():
        themes.append({'name': name, 'label': info.get('label', name), 'builtin': False, 'base': info.get('base', 'dark'), 'created': info.get('created', '')})
    return themes

def load_theme_tokens(name: str) -> dict:
    """
    Tema token'larını yükler.
    - Yerleşik (dark/light): DEFAULT_DARK/LIGHT_TOKENS döndürür
    - Özel JSON tema: dosyadan okur
    """
    if name == 'dark':
        return _deep_copy(DEFAULT_DARK_TOKENS)
    if name == 'light':
        return _deep_copy(DEFAULT_LIGHT_TOKENS)
    theme_file = os.path.join(THEMES_DIR, f'{name}.json')
    if os.path.exists(theme_file):
        try:
            with open(theme_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            tokens = data.get('tokens', {})
            base = data.get('base', 'dark')
            base_tokens = _deep_copy(DEFAULT_DARK_TOKENS if base == 'dark' else DEFAULT_LIGHT_TOKENS)
            for (cat, vals) in base_tokens.items():
                if cat not in tokens:
                    tokens[cat] = vals
                else:
                    for (k, v) in vals.items():
                        tokens[cat].setdefault(k, v)
            return tokens
        except Exception as e:
            app_logger.error(tr_log('core.theme_engine', 317, f'Tema yüklenemedi ({name}): {e}'))
    return _deep_copy(DEFAULT_DARK_TOKENS)

def save_custom_theme(name: str, label: str, base: str, tokens: dict) -> bool:
    """
    Özel temayı JSON olarak kaydeder.
    Yerleşik temaları (dark, light) kaydedemez → False döner.
    """
    if name in BUILTIN_THEMES:
        app_logger.warning(tr_log('core.theme_engine', 327, f'Yerleşik tema kayıt edilemez: {name}'))
        return False
    os.makedirs(THEMES_DIR, exist_ok=True)
    theme_file = os.path.join(THEMES_DIR, f'{name}.json')
    data = {'name': name, 'label': label, 'base': base, 'tokens': tokens}
    try:
        with open(theme_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        app_logger.error(tr_log('core.theme_engine', 341, f'Tema kaydedilemedi ({name}): {e}'))
        return False
    meta = _load_meta()
    if 'themes' not in meta:
        meta['themes'] = {}
    meta['themes'][name] = {'label': label, 'base': base, 'created': meta.get('themes', {}).get(name, {}).get('created', datetime.now().isoformat()), 'modified': datetime.now().isoformat()}
    _save_meta(meta)
    app_logger.info(tr_log('core.theme_engine', 354, f'Özel tema kaydedildi: {name} ({label})'))
    return True

def delete_theme(name: str) -> bool:
    """
    Özel temayı siler.
    Yerleşik tema (dark/light) silinemez → False döner.
    """
    if name in BUILTIN_THEMES:
        app_logger.warning(tr_log('core.theme_engine', 364, f'Yerleşik tema silinemez: {name}'))
        return False
    theme_file = os.path.join(THEMES_DIR, f'{name}.json')
    if os.path.exists(theme_file):
        try:
            os.remove(theme_file)
        except Exception as e:
            app_logger.error(tr_log('core.theme_engine', 371, f'Tema dosyası silinemedi ({name}): {e}'))
            return False
    meta = _load_meta()
    meta.get('themes', {}).pop(name, None)
    _save_meta(meta)
    app_logger.info(tr_log('core.theme_engine', 377, f'Özel tema silindi: {name}'))
    return True

def export_theme(name: str, export_path: str) -> bool:
    """
    Temayı belirtilen yola ihraç eder (.json formatında).
    Yerleşik temalar için token bilgilerini de dışa aktarır.
    """
    tokens = load_theme_tokens(name)
    meta = _load_meta()
    theme_info = meta.get('themes', {}).get(name, {})
    label = theme_info.get('label', name) if name not in BUILTIN_THEMES else 'Karanlık Mod (Varsayılan)' if name == 'dark' else 'Aydınlık Mod (Varsayılan)'
    base = theme_info.get('base', name) if name not in BUILTIN_THEMES else name
    export_data = {'name': name, 'label': label, 'base': base, 'tokens': tokens, 'exported_at': datetime.now().isoformat()}
    try:
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        app_logger.info(tr_log('core.theme_engine', 403, f'Tema dışa aktarıldı: {name} → {export_path}'))
        return True
    except Exception as e:
        app_logger.error(tr_log('core.theme_engine', 406, f'Tema dışa aktarılamadı ({name}): {e}'))
        return False

def import_theme(import_path: str) -> Optional[str]:
    """
    JSON tema dosyasını içe aktarır.
    Başarıyla kaydedilirse tema adını, başarısız olursa None döner.
    İmport edilen tema yerleşik bir isim taşıyorsa _imported suffix eklenir.
    """
    try:
        with open(import_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        app_logger.error(tr_log('core.theme_engine', 420, f'Tema içe aktarma hatası: {e}'))
        return None
    name = data.get('name', 'imported_theme')
    label = data.get('label', name)
    base = data.get('base', 'dark')
    tokens = data.get('tokens', {})
    if name in BUILTIN_THEMES:
        name = f'{name}_imported'
        label = f'{label} (İçe Aktarıldı)'
    success = save_custom_theme(name, label, base, tokens)
    return name if success else None

def tokens_to_qss(tokens: dict) -> str:
    """
    Token sözlüğünü QSS string'ine dönüştürür.
    """
    g = tokens.get('general', {})
    b = tokens.get('buttons', {})
    i = tokens.get('inputs', {})
    t = tokens.get('table', {})
    l = tokens.get('list', {})
    p = tokens.get('progress', {})
    tb = tokens.get('tabs', {})
    sc = tokens.get('scrollbar', {})
    m = tokens.get('menubar', {})
    st = tokens.get('statusbar', {})
    gb = tokens.get('groupbox', {})

    def c(d, key, fallback=''):
        return d.get(key, fallback)
    qss = f"""\n/* -- Otomatik oluşturuldu: ThemeEngine -- */\n\nQWidget {{\n    font-family: {c(g, 'font_family', 'Segoe UI, Arial, sans-serif')};\n    font-size: {c(g, 'font_size', '9pt')};\n    letter-spacing: 0.01em;\n}}\n\nQMainWindow {{ background-color: {c(g, 'background')}; }}\n\nQDialog {{\n    background-color: {c(g, 'background')};\n    color: {c(g, 'text_color')};\n}}\n\n/* -- QPushButton -- */\nQPushButton {{\n    border-radius: 5px;\n    padding: {c(b, 'btn_padding', '4px 10px')};\n    font-size: {c(g, 'font_size', '9pt')};\n    font-weight: 500;\n    letter-spacing: 0.02em;\n    min-height: 14px;\n    max-height: {c(b, 'btn_max_height', '28px')};\n}}\nQPushButton:disabled {{ opacity: 0.45; }}\n\nQPushButton[class="btn-success"] {{ background-color: {c(b, 'btn_success_bg')}; color: #ffffff; border: none; }}\nQPushButton[class="btn-success"]:hover {{ background-color: {c(b, 'btn_success_hover')}; }}\nQPushButton[class="btn-primary"] {{ background-color: {c(b, 'btn_primary_bg')}; color: #ffffff; border: none; }}\nQPushButton[class="btn-primary"]:hover {{ background-color: {c(b, 'btn_primary_hover')}; }}\nQPushButton[class="btn-info"] {{ background-color: {c(b, 'btn_info_bg')}; color: #ffffff; border: none; }}\nQPushButton[class="btn-info"]:hover {{ background-color: {c(b, 'btn_info_hover')}; }}\nQPushButton[class="btn-stop"] {{ background-color: {c(b, 'btn_stop_bg')}; color: #ffffff; border: none; }}\nQPushButton[class="btn-stop"]:hover {{ background-color: {c(b, 'btn_stop_hover')}; }}\nQPushButton[class="btn-purple"] {{ background-color: {c(b, 'btn_purple_bg')}; color: #ffffff; border: none; }}\nQPushButton[class="btn-purple"]:hover {{ background-color: {c(b, 'btn_purple_hover')}; }}\nQPushButton[class="btn-teal"] {{ background-color: {c(b, 'btn_teal_bg')}; color: #ffffff; border: none; }}\nQPushButton[class="btn-teal"]:hover {{ background-color: {c(b, 'btn_teal_hover')}; }}\nQPushButton[class="btn-brown"] {{ background-color: {c(b, 'btn_brown_bg')}; color: #ffffff; border: none; }}\nQPushButton[class="btn-brown"]:hover {{ background-color: {c(b, 'btn_brown_hover')}; }}\nQPushButton[class="btn-deep-purple"] {{ background-color: {c(b, 'btn_deep_purple_bg')}; color: #ffffff; border: none; }}\nQPushButton[class="btn-deep-purple"]:hover {{ background-color: {c(b, 'btn_deep_purple_hover')}; }}\nQPushButton[class="btn-pink"] {{ background-color: {c(b, 'btn_pink_bg')}; color: #ffffff; border: none; }}\nQPushButton[class="btn-pink"]:hover {{ background-color: {c(b, 'btn_pink_hover')}; }}\nQPushButton[class="btn-steel"] {{ background-color: {c(b, 'btn_steel_bg')}; color: #ffffff; border: none; }}\nQPushButton[class="btn-steel"]:hover {{ background-color: {c(b, 'btn_steel_hover')}; }}\nQPushButton[class="btn-ocean"] {{ background-color: {c(b, 'btn_ocean_bg')}; color: #ffffff; border: none; }}\nQPushButton[class="btn-ocean"]:hover {{ background-color: {c(b, 'btn_ocean_hover')}; }}\nQPushButton[class="btn-clear"] {{\n    background-color: transparent; color: #6C7086;\n    border: 1px solid {c(g, 'border_color')}; border-radius: 4px;\n    padding: 2px 5px; font-size: 8pt;\n    max-width: 22px; min-width: 22px; max-height: 22px; min-height: 22px;\n}}\n\n/* -- Input Alanları -- */\nQLineEdit, QTextEdit, QPlainTextEdit {{\n    background-color: {c(i, 'input_bg')};\n    color: {c(i, 'input_text')};\n    border: 1px solid {c(i, 'input_border')};\n    border-radius: {c(g, 'border_radius', '4px')};\n    padding: 3px 6px;\n    font-size: {c(g, 'font_size', '9pt')};\n    selection-background-color: {c(i, 'selection_bg')};\n    selection-color: {c(i, 'selection_text')};\n}}\nQLineEdit {{ min-height: 14px; max-height: 28px; }}\nQTextEdit, QPlainTextEdit {{ min-height: 60px; }}\nQLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{\n    border: 1px solid {c(i, 'input_focus_border')};\n    background-color: {c(i, 'input_focus_bg')};\n}}\n\n/* -- Tablo -- */\nQTableWidget {{\n    background-color: {c(t, 'table_bg')};\n    color: {c(t, 'table_text')};\n    gridline-color: {c(t, 'table_grid')};\n    border: 1px solid {c(t, 'table_border')};\n    border-radius: 5px;\n    selection-background-color: {c(t, 'table_selected')};\n    alternate-background-color: {c(t, 'table_alt_bg')};\n    font-size: 10pt;\n}}\nQTableWidget::item {{ padding: 3px 5px; }}\nQTableWidget::item:selected {{ background-color: {c(t, 'table_selected')}; color: {c(t, 'table_text')}; }}\nQHeaderView::section {{\n    background-color: {c(t, 'header_bg')}; color: {c(t, 'header_text')};\n    border: none; border-bottom: 2px solid {c(g, 'border_color')};\n    padding: 4px 6px; font-weight: 600; font-size: 8pt;\n}}\n\n/* -- Liste -- */\nQListWidget {{\n    background-color: {c(l, 'list_bg')};\n    color: {c(l, 'list_text')};\n    border: 1px solid {c(l, 'list_border')};\n    border-radius: 4px; outline: none; font-size: 10pt;\n}}\nQListWidget::item {{ padding: 4px 7px; border-radius: 2px; }}\nQListWidget::item:selected {{ background-color: {c(l, 'list_selected')}; color: {c(l, 'list_sel_text')}; }}\nQListWidget::item:hover {{ background-color: {c(l, 'list_hover')}; }}\n\n/* -- ComboBox -- */\nQComboBox {{\n    background-color: {c(i, 'input_bg')};\n    color: {c(i, 'input_text')};\n    border: 1px solid {c(i, 'input_border')};\n    border-radius: {c(g, 'border_radius', '4px')};\n    padding: 3px 8px; font-size: {c(g, 'font_size', '9pt')};\n    min-height: 14px; max-height: 26px;\n}}\nQComboBox:hover {{ border-color: {c(i, 'input_focus_border')}; }}\nQComboBox QAbstractItemView {{\n    background-color: {c(g, 'background')};\n    color: {c(g, 'text_color')};\n    border: 1px solid {c(i, 'input_border')};\n    selection-background-color: {c(l, 'list_selected')};\n    selection-color: {c(l, 'list_sel_text')};\n    outline: none; font-size: {c(g, 'font_size', '9pt')};\n}}\n\n/* -- Progress Bar -- */\nQProgressBar {{\n    background-color: {c(p, 'progress_bg')};\n    border: none; border-radius: 5px;\n    text-align: center; font-size: 7pt; font-weight: 600;\n    color: {c(g, 'text_color')};\n    min-height: {c(p, 'progress_height', '10px')};\n    max-height: {c(p, 'progress_height', '10px')};\n}}\nQProgressBar::chunk {{\n    background: qlineargradient(\n        x1: 0, y1: 0, x2: 1, y2: 0,\n        stop: 0.0 {c(p, 'progress_grad_start')},\n        stop: 0.4 {c(p, 'progress_grad_mid1')},\n        stop: 0.8 {c(p, 'progress_grad_mid2')},\n        stop: 1.0 {c(p, 'progress_grad_end')}\n    );\n    border-radius: 5px;\n}}\n\n/* -- ScrollBar -- */\nQScrollBar:vertical {{\n    background-color: {c(sc, 'scrollbar_bg')};\n    width: {c(sc, 'scrollbar_width', '6px')}; border-radius: 3px; margin: 0;\n}}\nQScrollBar::handle:vertical {{\n    background-color: {c(sc, 'scrollbar_handle')}; border-radius: 3px; min-height: 20px;\n}}\nQScrollBar::handle:vertical:hover {{ background-color: {c(sc, 'scrollbar_hover')}; }}\nQScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: none; }}\nQScrollBar:horizontal {{\n    background-color: {c(sc, 'scrollbar_bg')};\n    height: {c(sc, 'scrollbar_width', '6px')}; border-radius: 3px; margin: 0;\n}}\nQScrollBar::handle:horizontal {{\n    background-color: {c(sc, 'scrollbar_handle')}; border-radius: 3px; min-width: 20px;\n}}\nQScrollBar::handle:horizontal:hover {{ background-color: {c(sc, 'scrollbar_hover')}; }}\nQScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; background: none; }}\n\n/* -- Tab Widget -- */\nQTabWidget::pane {{\n    border: 1px solid {c(tb, 'pane_border')};\n    border-radius: 5px; background-color: {c(tb, 'pane_bg')}; top: -1px;\n}}\nQTabBar::tab {{\n    background-color: {c(tb, 'tab_bg')}; color: {c(tb, 'tab_text')};\n    padding: 5px 14px; border-top-left-radius: 4px;\n    border-top-right-radius: 4px; margin-right: 2px; font-size: 8pt;\n}}\nQTabBar::tab:selected {{\n    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,\n        stop: 0 {c(tb, 'tab_active_start')}, stop: 1 {c(tb, 'tab_active_end')});\n    color: {c(tb, 'tab_active_text')}; font-weight: 700;\n}}\nQTabBar::tab:hover:!selected {{\n    background-color: {c(tb, 'tab_hover_bg')}; color: {c(g, 'text_color')};\n}}\n\n/* -- GroupBox -- */\nQGroupBox {{\n    border: 1px solid {c(gb, 'groupbox_border')};\n    border-radius: 6px; margin-top: 8px;\n    padding: 8px 6px 6px 6px; font-size: 8pt;\n}}\nQGroupBox::title {{\n    color: {c(gb, 'groupbox_title')};\n    subcontrol-origin: margin; left: 8px; padding: 0 3px; font-weight: 600;\n}}\n\n/* -- MenuBar -- */\nQMenuBar {{\n    background-color: {c(m, 'menubar_bg')}; color: {c(m, 'menubar_text')};\n    border-bottom: 1px solid {c(g, 'border_color')}; padding: 1px; font-size: {c(g, 'font_size', '9pt')};\n}}\nQMenuBar::item {{ padding: 3px 8px; border-radius: 3px; }}\nQMenuBar::item:selected {{ background-color: {c(m, 'menu_selected')}; color: {c(m, 'menu_sel_text')}; }}\nQMenu {{\n    background-color: {c(m, 'menu_bg')}; color: {c(m, 'menu_text')};\n    border: 1px solid {c(m, 'menu_border')}; border-radius: 5px;\n    padding: 3px; font-size: {c(g, 'font_size', '9pt')};\n}}\nQMenu::item {{ padding: 4px 22px 4px 10px; border-radius: 3px; }}\nQMenu::item:selected {{ background-color: {c(m, 'menu_selected')}; color: {c(m, 'menu_sel_text')}; }}\nQMenu::separator {{ height: 1px; background-color: {c(m, 'menu_selected')}; margin: 3px 6px; }}\n\n/* -- Label / Checkbox / SpinBox -- */\nQLabel {{ color: {c(g, 'text_color')}; font-size: {c(g, 'font_size', '9pt')}; }}\nQCheckBox {{ color: {c(g, 'text_color')}; spacing: 5px; font-size: {c(g, 'font_size', '9pt')}; }}\nQCheckBox::indicator {{\n    width: 13px; height: 13px;\n    border: 1px solid {c(i, 'input_border')};\n    border-radius: 2px; background-color: {c(i, 'input_bg')};\n}}\nQCheckBox::indicator:hover {{ border-color: {c(i, 'input_focus_border')}; }}\nQCheckBox::indicator:checked {{\n    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,\n        stop: 0 {c(tb, 'tab_active_start')}, stop: 1 {c(tb, 'tab_active_end')});\n    border-color: {c(i, 'input_focus_border')};\n}}\nQSpinBox {{\n    background-color: {c(i, 'input_bg')}; color: {c(i, 'input_text')};\n    border: 1px solid {c(i, 'input_border')}; border-radius: {c(g, 'border_radius', '4px')};\n    padding: 2px 6px; font-size: {c(g, 'font_size', '9pt')};\n    min-height: 14px; max-height: 26px;\n}}\nQSpinBox:hover {{ border-color: {c(i, 'input_focus_border')}; }}\nQSpinBox:focus {{ border-color: {c(i, 'input_focus_border')}; background-color: {c(i, 'input_focus_bg')}; }}\n\n/* -- Status Bar -- */\nQStatusBar {{\n    background-color: {c(st, 'statusbar_bg')}; color: {c(st, 'statusbar_text')};\n    border-top: 1px solid {c(st, 'statusbar_border')}; padding: 1px 6px; font-size: 8pt;\n}}\nQStatusBar::item {{ border: none; }}\n\n/* -- ScrollArea -- */\nQScrollArea {{ border: none; background-color: transparent; }}\nQScrollArea > QWidget > QWidget {{ background-color: transparent; }}\n\n/* -- Novel Translator Pro Modern UI Bileşenleri -- */\n#topbar   {{ background-color: {c(g, 'background')}; border-bottom: 1px solid {c(g, 'border_color')}; }}\n#connbar  {{ background-color: {c(tb, 'pane_bg', c(g, 'background'))}; border-bottom: 1px solid {c(g, 'border_color')}; }}\n#sidebar  {{ background-color: {c(g, 'background')}; border-right: 1px solid {c(g, 'border_color')}; }}\n#statusbar {{ background-color: {c(tb, 'pane_bg', c(g, 'background'))}; border-top: 1px solid {c(g, 'border_color')}; }}\n\n#card, #innerCard, #statCard, #featureCard, #activeProject {{\n    background-color: {c(tb, 'pane_bg', c(g, 'background'))};\n    border: 1px solid {c(g, 'border_color')};\n    border-radius: 10px;\n}}\n#innerCard {{ background-color: {c(i, 'input_bg')}; }}\n#cardTitle {{ color: {c(g, 'text_color')}; font-size: 14px; font-weight: 700; }}\n\n#styleCard {{\n    background-color: {c(i, 'input_bg')};\n    border: 1px solid {c(g, 'border_color')};\n    border-radius: 8px;\n}}\n#styleCardActive {{\n    background-color: {c(l, 'list_selected')};\n    border: 1px solid {c(tb, 'tab_active_start', '#3b82f6')};\n    border-radius: 8px;\n}}\n\n#navBtn {{\n    text-align: left; background: transparent; border: none;\n    color: {c(tb, 'tab_text')}; border-radius: 8px; font-size: 13px; padding: 8px 10px;\n}}\n#navBtn:hover {{ background-color: {c(tb, 'tab_hover_bg')}; color: {c(g, 'text_color')}; }}\n#navBtnActive {{\n    text-align: left; background-color: {c(l, 'list_selected')};\n    border: 1px solid {c(tb, 'tab_active_start', '#3b82f6')};\n    color: {c(l, 'list_sel_text', '#3b82f6')};\n    border-radius: 8px; font-size: 13px; font-weight: 600; padding: 8px 10px;\n}}\n\n#ghostBtn {{ background: transparent; border: none; color: {c(tb, 'tab_text')}; font-size: 12px; }}\n#ghostBtn:hover {{ color: {c(g, 'text_color')}; }}\n#winBtn {{ background: transparent; border: none; color: {c(tb, 'tab_text')}; }}\n#winBtn:hover {{ background-color: {c(tb, 'tab_hover_bg')}; }}\n#iconBtn {{\n    background-color: {c(i, 'input_bg')}; border: 1px solid {c(g, 'border_color')};\n    border-radius: 6px; max-width: 30px; padding: 4px;\n}}\n\n#smallBtn {{\n    background-color: {c(i, 'input_bg')}; border: 1px solid {c(g, 'border_color')};\n    border-radius: 6px; font-size: 11px; padding: 5px 10px;\n}}\n#smallBtnFull {{\n    background-color: {c(i, 'input_bg')}; border: 1px solid {c(g, 'border_color')};\n    border-radius: 6px; font-size: 12px; padding: 8px;\n}}\n#primaryBtn, #newProjectBtn {{\n    background-color: {c(b, 'btn_primary_bg', '#3b82f6')}; border: none; color: #ffffff;\n    border-radius: 6px; font-weight: 600; padding: 6px 14px;\n}}\n#primaryBtn:hover, #newProjectBtn:hover {{ background-color: {c(b, 'btn_primary_hover', '#2563eb')}; }}\n\n#purpleBtn {{\n    background-color: {c(b, 'btn_purple_bg', '#880e4f')}; border: none; color: #ffffff;\n    border-radius: 6px; font-size: 11px; padding: 5px 10px;\n}}\n#greenBtn {{\n    background-color: {c(b, 'btn_success_bg', '#2e7d32')}; border: none; color: #ffffff;\n    border-radius: 6px; font-weight: 700; padding: 9px;\n}}\n#dangerBtn {{\n    background-color: {c(b, 'btn_stop_bg', '#b71c1c')}; border: none; color: #ffffff;\n    border-radius: 6px; font-size: 11px; padding: 5px 10px;\n}}\n#orangeBtn {{\n    background-color: {c(b, 'btn_workflow', '#ff6f00')}; border: none; color: #ffffff;\n    border-radius: 6px; font-size: 11px; padding: 5px 10px;\n}}\n#linkBtn {{ background: transparent; border: none; color: {c(tb, 'tab_active_start', '#3b82f6')}; font-size: 11px; }}\n#pageBtn {{\n    background-color: {c(i, 'input_bg')}; border: 1px solid {c(g, 'border_color')};\n    border-radius: 6px; font-size: 11px; padding: 4px 10px;\n}}\n#pageBtnActive {{\n    background-color: {c(b, 'btn_primary_bg', '#3b82f6')}; border: none; color: #ffffff;\n    border-radius: 6px; font-size: 11px; padding: 4px 10px; font-weight: 700;\n}}\n\nQCheckBox#toggleSwitch {{ spacing: 0px; }}\nQCheckBox#toggleSwitch::indicator {{\n    width: 36px; height: 20px; border-radius: 10px;\n    background-color: {c(g, 'border_color')}; border: 1px solid {c(g, 'border_color')};\n}}\nQCheckBox#toggleSwitch::indicator:checked {{\n    background-color: {c(b, 'btn_primary_bg', '#3b82f6')}; border: 1px solid {c(b, 'btn_primary_bg', '#3b82f6')};\n}}\n"""
    return qss

def _deep_copy(d: dict) -> dict:
    """dict kopyası (basit iç içe dict için)."""
    return json.loads(json.dumps(d))