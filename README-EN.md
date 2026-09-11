# Novel Translation Tool - AI-Assisted Novel Translation and Editing Desktop App
[![GitHub Issues](https://img.shields.io/github/issues/utkucanc/yznvltranslate?label=Open%20Issues)](https://github.com/utkucanc/yznvltranslate/issues)
[![downloads](https://img.shields.io/github/downloads/utkucanc/yznvltranslate/total?label=Total%20Downloads)](https://github.com/utkucanc/yznvltranslate/releases)
[![downloads-latest](https://img.shields.io/github/downloads/utkucanc/yznvltranslate/latest/total?label=Latest%20release)](https://github.com/utkucanc/yznvltranslate/releases/latest)

Discord : Utkucan#5700
# NTT (Novel Translation Tool v3.1.0)

Novel Translation Tool is a modern PyQt6 desktop application designed to organize web novel translation projects locally (especially from Chinese, Korean, English, etc.), perform volume batch translations using AI (Google Gemini, OpenAI/MCP) and classic translation providers (DeepL, Yandex, Google Translate), ensure in-text terminology consistency, and clean and merge output files into EPUB or TXT formats.

## How to Use?
- [![Youtube Video Link](https://img.shields.io/badge/Youtube%20Video%20Link-red?style=for-the-badge&logo=youtube)](https://youtu.be/4HQpAn_qiBU)
- https://youtu.be/4HQpAn_qiBU

---

## 🚀 Key Features

* **Multi-Provider Translation Support (v3.0.0)**:
  - **Artificial Intelligence (LLM / MCP):** Google Gemini (`google-genai`), OpenAI-compatible MCP (Multi-endpoint Connection Provider) server architecture, and rotating API Key Pool.
  - **Classic Translation Services:** DeepL, Yandex Translate, and Proxy-supported (HTTP / HTTPS / SOCKS4 / SOCKS5) Google Translate.
  - **Automatic Key Rotation:** Seamlessly switches to the next available key or endpoint in the pool upon encountering 429 Rate Limit errors.

* **Advanced In-Text Terminology System (v3.0.0 & v3.1.0)**:
  - **In-Text Injection:** Saved terms are injected directly into the source text before sending the API request. The AI recognizes pre-translated terms and naturally integrates them into the sentence flow while cutting token usage by up to 80%.
  - **Chapter Range Terminology Extraction:** ML-driven automatic term extractor detects key proper nouns, locations, and techniques within specified chapter ranges and populates the dictionary.

* **Flexible Settings & Prompt Management (v3.1.0)**:
  - **In-App System Prompt Editor:** Customize system prompts for Prompt Generator and ML Terminology Extractor directly inside App Settings, with one-click reset to default prompt for the active language.
  - **Customizable Separators:** Chapter merge (`export_separator`) and bulk split (`split_separator`) templates can be dynamically configured in settings.

* **New Project Architecture & Backwards Compatibility (v3.1.0)**:
  - New projects are organized cleanly under `Project/<ProjectName>/` with standardized subfolder names (`completed`, `config`, `download`, `translate`).
  - Older projects (`cmplt`, `config`, `dwnld`, `trslt`) remain fully compatible without requiring migration thanks to the `path_resolver` module.

* **Advanced Performance & Workflow Tools**:
  - **Async Translation:** Translate multiple chapters concurrently with configurable parallel workers.
  - **Batch Mode:** Combine multiple chapters into a single API payload (`===CHAPTER_START===` / `===CHAPTER_END===`) to maximize output per RPD (Daily Limit) quota.
  - **Quality & Error Checker:** Detect untranslated files automatically using text similarity matching (%80+) and `langdetect`.
  - **File Operations & EPUB Compilation:** One-click EPUB generator, built-in Text Editor with live editing, and chapter splitter.

---

## 📋 Requirements

To run the application from source code, install the required dependencies:

```bash
pip install -r requirements.txt
```
- Recommended Python version: **Python 3.13**

---

## 🛠️ Installation & Running

### 1- Running in Developer Environment (Python):
After installing requirements, launch the UI from the project root:
```bash
python main_window.py
```

### 2- Building Standalone Executable / Installer for Windows:
You can freeze the project into a standalone Windows executable using `cx_Freeze`:

**Portable Folder Build:**
```bash
python setup.py build
```
Output executable will be generated at `build/NovelCeviriAraci-Portable/CeviriUygulamasi.exe`.

**Windows MSI Installer:**
```bash
python setup.py bdist_msi
```
Installer package will be created in the `dist/` directory as `NovelCeviriAraci-3.0.0-win64.msi`.

---

## 📁 Project Directory Structure

The application stores global configurations and theme assets in `AppConfigs`:
* `AppConfigs/locales/`: Localization files (`tr.json`, `en.json`).
* `AppConfigs/themes/`: Theme templates and QSS styles.
* `AppConfigs/app_settings.json`: Global application settings.
* `AppConfigs/app.log`: Application logging file.

New projects are automatically created under `Project/<ProjectName>/`:
- `download/`: Raw original text files.
- `translate/`: Translated text files.
- `completed/`: Merged `.txt` and `.epub` output files.
- `config/`: Project-specific `config.ini` and `terminology.json`.

---

## 📜 Version History (Changelog)

| Version | Highlights & Changes |
|---------|----------------------|
| 3.1.0 | **New Project Architecture & Backwards Compatibility:** Projects created under `Project/<ProjectName>/` with standardized folders (`completed`, `config`, `download`, `translate`); legacy projects supported seamlessly (`path_resolver`). **In-App Prompt Editing:** Customize system prompts for Prompt Generator and ML Extractor in App Settings. **Dynamic Separators:** Configurable Split & Export separators. **Module Cleanup:** Removed legacy Selenium/Scraper code for a lighter UI. **Full i18n:** Terminology page and new UI elements fully localized (`tr()`). |
| 3.0.0 | **Redesigned Dark UI:** Dashboard, Project details panel, and embedded Terminology/Text Editor pages. **In-Text Terminology Injection:** Injected terms prior to API calls, saving up to 80% tokens. **New Translation Providers:** DeepL, Yandex, Google Translate (SOCKS/HTTP proxy support). Unstable translation cache removed. |
| 2.6.0 | **Translation Error Checking:** Text similarity (%80+) and `langdetect` integration for Latin/English source texts to catch untranslated files. |
| 2.5.0 | **Localization Support:** Initial i18n infrastructure for English and Turkish languages. |
| 2.4.0 | Offline Token Counting, Automatic Theme File Generation, MCP Dialog Enhancements, ML Terminology Chapter Range Selection. |
| 2.3.0 | New UI Redesign & Theme Manager Panel. |
| 2.1.0 | Paragraph-Based Translation, Batch Mode, and Async Parallel Workers. |
| 2.0.0 | MCP Architecture, Prompt Generator, Translation Cache, Terminology Memory, New GenAI SDK, CJK Quality Checker. |
| 1.9.9 | Automated Logging with `logger.py`, performance and token calculation bugfixes. |
