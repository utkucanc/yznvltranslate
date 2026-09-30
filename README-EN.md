# Novel Translation Tool - AI-Assisted Novel Translation and Editing Desktop App
[![GitHub Issues](https://img.shields.io/github/issues/utkucanc/yznvltranslate?label=Open%20Issues)](https://github.com/utkucanc/yznvltranslate/issues)
[![downloads](https://img.shields.io/github/downloads/utkucanc/yznvltranslate/total?label=Total%20Downloads)](https://github.com/utkucanc/yznvltranslate/releases)
[![downloads-latest](https://img.shields.io/github/downloads/utkucanc/yznvltranslate/latest/total?label=Latest%20release)](https://github.com/utkucanc/yznvltranslate/releases/latest)
## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Futkucanc%2Fyznvltranslate.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Futkucanc%2Fyznvltranslate?ref=badge_large)

Discord : Utkucanc
# NTT (Novel Translation Tool v3.1.1)

Novel Translation Tool is a modern PyQt6 desktop application designed to organize web novel translation projects locally (especially from Chinese, Korean, English, etc.), perform volume batch translations using AI (Google Gemini, OpenAI/MCP) and classic translation providers (DeepL, Yandex, Google Translate), ensure in-text terminology consistency, and clean and merge output files into EPUB or TXT formats.

## How to Use?
- [![Youtube Video Link](https://img.shields.io/badge/Youtube%20Video%20Link-red?style=for-the-badge&logo=youtube)](https://youtu.be/4HQpAn_qiBU)
- https://youtu.be/4HQpAn_qiBU

---

## 🚀 Key Features

* **SQLite Database & High Performance (v3.1.1)**:
  - Project file states and paths are indexed in real time via an SQLite database.
  - Startup time and file list indexing have been accelerated to millisecond speeds by avoiding OS filesystem scans.
  - Legacy projects created without a database are automatically detected and migrated seamlessly upon opening.
  - Completed translations are written directly to the database without delay.

* **Log Localization Infrastructure (v3.1.1)**:
  - System and UI log messages are extracted and localized into Turkish and English (`logger.json` / `loggeren.json`).
  - Log messages containing variables or f-strings use dynamic regex pattern matching to map runtime values to English log templates seamlessly.

* **Enhanced File & User Interactions (v3.1.1)**:
  - **Go to Chapter / Row:** Inputting a chapter number auto-scrolls and highlights the row without filtering out other files from the list.
  - **Dynamic EPUB Naming:** Generated EPUB files are automatically formatted as `[ProjectName]-[StartChapter]-[EndChapter].epub` (e.g., `TestProject-1-500.epub`).
  - **Context Menu File Deletion:** Added right-click context menu deletion with a confirmation dialog box (`QMessageBox.question`).
  - **Refined Dashboard Charts & Splash Screen:** Integrated real-time daily stats graph updates, overall request counter, and a non-blocking background splash loader.

* **Multi-Provider Translation Support (v3.0.0)**:
  - **Artificial Intelligence (LLM / MCP):** Google Gemini (`google-genai`), OpenAI-compatible MCP (Multi-endpoint Connection Provider) server architecture, and rotating API Key Pool.
  - **Classic Translation Services:** DeepL, Yandex Translate, and Proxy-supported (HTTP / HTTPS / SOCKS4 / SOCKS5) Google Translate.
  - **Automatic Key Rotation:** Seamlessly switches to the next available key or endpoint in the pool upon encountering 429 Rate Limit errors.

* **Advanced In-Text Terminology System (v3.0.0 & v3.1.0)**:
  - **In-Text Injection:** Saved terms are injected directly into the source text before sending the API request. The AI recognizes pre-translated terms and naturally integrates them into the sentence flow while cutting token usage by up to 80%.
  - **Chapter Range Terminology Extraction:** ML-driven automatic term extractor detects key proper nouns, locations, and techniques within specified chapter ranges and populates the dictionary.

* **Flexible Settings & Prompt Management (v3.1.0 & v3.1.1)**:
  - **In-App System Prompt Editor:** Customize system prompts for Prompt Generator and ML Terminology Extractor directly inside App Settings.
  - **Customizable Separators:** Chapter merge (`export_separator`) and bulk split (`split_separator`) templates can be dynamically configured in settings.
  - **Langdetect & Line Count Controls:** Customize Langdetect source and target languages for quality checks; detect low-line count translation files with detailed error reporting.

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
Installer package will be created in the `dist/` directory as `NovelCeviriAraci-3.1.1-win64.msi`.

---

## 📁 Project Directory Structure

The application stores global configurations and theme assets in `AppConfigs`:
* `AppConfigs/locales/`: Localization files (`tr.json`, `en.json`, `logger.json`, `loggeren.json`).
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
| 3.1.1 | **SQLite Database Architecture & Auto-Migration:** File tracking moved from OS filesystem scanning to SQLite database for instant file list loads; legacy projects automatically migrated. **Log Localization Infrastructure:** Extracted all system log messages into `tr`/`en` dynamic translation engine with regex f-string parameter mapping. **Smart Row/Chapter Focus:** Added direct "Go to Chapter" auto-scroll and highlight without filtering the list. **Dynamic EPUB Naming:** Combined EPUB outputs named as `[ProjectName]-[StartChapter]-[EndChapter].epub`. **Confirmed File Deletion:** Added right-click context menu file deletion with confirmation dialog. **UI & Dashboard Graph Fixes:** Fixed stats graph rendering, overall daily request counting, splash screen loader, proxy dialog dimensions, and API/MCP prompts. **Quality Control Enhancements:** Added customizable Langdetect source/target languages and low-line count detection with detailed reporting. |
| 3.1.0 | **New Project Architecture & Backwards Compatibility:** Projects created under `Project/<ProjectName>/` with standardized folders (`completed`, `config`, `download`, `translate`); legacy projects supported seamlessly (`path_resolver`). **In-App Prompt Editing:** Customize system prompts for Prompt Generator and ML Extractor in App Settings. **Dynamic Separators:** Configurable Split & Export separators. **Module Cleanup:** Removed legacy Selenium/Scraper code for a lighter UI. **Full i18n:** Terminology page and new UI elements fully localized (`tr()`). |
| 3.0.0 | **Redesigned Dark UI:** Dashboard, Project details panel, and embedded Terminology/Text Editor pages. **In-Text Terminology Injection:** Injected terms prior to API calls, saving up to 80% tokens. **New Translation Providers:** DeepL, Yandex, Google Translate (SOCKS/HTTP proxy support). Unstable translation cache removed. |
| 2.6.0 | **Translation Error Checking:** Text similarity (%80+) and `langdetect` integration for Latin/English source texts to catch untranslated files. |
| 2.5.0 | **Localization Support:** Initial i18n infrastructure for English and Turkish languages. |
| 2.4.0 | Offline Token Counting, Automatic Theme File Generation, MCP Dialog Enhancements, ML Terminology Chapter Range Selection. |
| 2.3.0 | New UI Redesign & Theme Manager Panel. |
| 2.1.0 | Paragraph-Based Translation, Batch Mode, and Async Parallel Workers. |
| 2.0.0 | MCP Architecture, Prompt Generator, Translation Cache, Terminology Memory, New GenAI SDK, CJK Quality Checker. |
| 1.9.9 | Automated Logging with `logger.py`, performance and token calculation bugfixes. |
| 1.9.8 | Fixed general bugs affecting performance (retry_count, statusLabel wordwrap, cx_Freeze base). |
| 1.9.7 | Added the ability to add sections in bulk (`split_worker.py`). |
| 1.9.6 | Added the ability to save JS files (JS Save menu). |
| 1.9.5 | Added the ability to save selected files as an EPUB file. |
| 1.9.4 | Added a limit on the number of files to be translated (`file_limit`). |
| 1.9.3 | Added chapter title validation. |


![alt](https://github.com/utkucanc/yznvltranslate/blob/main/diagram.png?raw=true)
