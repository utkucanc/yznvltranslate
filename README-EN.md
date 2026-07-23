# Novel Translation Tool - AI-Powered Novel Translation and Editing Application
[![GitHub Issues](https://img.shields.io/github/issues/utkucanc/yznvltranslate?label=Open%20Issues)](https://github.com/utkucanc/yznvltranslate/issues)
[![downloads](https://img.shields.io/github/downloads/utkucanc/yznvltranslate/total?label=Total%20Downloads)](https://github.com/utkucanc/yznvltranslate/releases)
[![downloads-latest](https://img.shields.io/github/downloads/utkucanc/yznvltranslate/latest/total?label=Latest%20release)](https://github.com/utkucanc/yznvltranslate/releases/latest)

Discord : Utkucan#5700
# NCA

This project is a PyQt6-based desktop application designed to download web novels in foreign languages (especially English, Korean, Chinese, etc.), perform bulk translation locally using the Google Gemini API, and then clean and merge these texts into EPUB or similar formats.

## How to Use?
- [![Youtube Video Link](https://img.shields.io/badge/Youtube%20Video%20Link-red?style=for-the-badge&logo=youtube)](https://youtu.be/4HQpAn_qiBU)
- https://youtu.be/4HQpAn_qiBU

## Features

* **Bulk Downloading**: 
  - Standard Web Scraping (Requests/BS4)
  - JavaScript-enabled downloading (Selenium Webdriver integration for Novelfire, Booktoki, and 69shuba)
* **Advanced Translation System**: 
  - **MCP (Multi-endpoint Connection Provider)** architecture supporting OpenAI-compatible servers and Google Gemini (`google-genai`).
  - Key Pool support with a rotating, unlimited number of API Keys.
  - Automatic **Translation Cache** and **Terminology Memory** for cost savings and term consistency.
  - **Prompt Generator (PromtGen)** that automatically extracts project-specific translation prompts (Literal/Natural/Balanced) using AI.
  - **Translation Error and Quality Control (v2.5.0):** Integration of **Text Similarity Ratio (>=80%)** (`difflib`) and **`langdetect` Language Detection** along with Chinese/Korean CJK character scanning. Automatically detects files saved without translation.
  - **Paragraph-Based Translation (v2.1.0):** Every file is automatically split into paragraphs and translated/merged independently, regardless of whether the cache is enabled. This improves token efficiency for large files.
  - **Asynchronous Translation (v2.1.0):** A parallel translation system where the number of threads can be configured in the project settings. It allows multiple files to be translated simultaneously. (Recommended worker count for Gemini is 3, yielding an RPM of 11-12.)
  - **Bulk Translation / Batch Mode (v2.1.0 - Beta):** Packages multiple chapters into a single API request using `===CHAPTER_START===` / `===CHAPTER_END===` separators. This allows translating more chapters with the same RPD quota. It automatically falls back to single mode if parsing fails.
  - **Advanced Terminology System (v2.4.0):** Section range selection dialog added to the terminology extraction process. The last processed information is saved and displayed in the terminology window, making it easier to manage TPM limits and extract terminology for the entire story.
* **File Manipulation**:
  - `Bulk Chapter Split`: Automatically splits large `.txt` files into individual chapters based on the "## Chapter - X ##" separator.
  - In-app text editing via double-clicking to open the built-in Text Editor for quick adjustments.
  - Merging translated chapters into a single `.txt` or `.epub` file.
* **Token and Limit Counter**: Smart status bar for cost calculation, speed tracking, and persistent API usage statistics. View API request count history as charts and tables.

## Requirements

To run the application from source code, you need to install the following dependencies on your system:

```bash
pip install -r requirements.txt
```
- Recommended Python version:
```bash
Python 3.13 
```
  
Note: To use JavaScript-based Booktoki and 69shuba downloaders (Selenium), Google Chrome must be installed on your computer. `webdriver-manager` will automatically handle ChromeDriver matching.

## Installation and Execution

### 1- Running with Developer Environment (Python):
After installing the required dependencies, run the following command in the project directory:
```bash
python main_window.py
```
to start the user interface.

### 2- Packaging Ready-to-Use .EXE (Build) for Windows:
You can compile the project using `cx_Freeze` to create an executable file that runs on Windows devices without Python installed.

To create the build directory:
```bash
python setup.py build
```
The compiled files will appear under the `build/` folder as `CeviriUygulamasi.exe`.

If you want to create an MSI Installer:
```bash
python setup.py bdist_msi
```
Once the process is complete, you can find the installer in the `dist/` folder.

## Project Structure

The application saves configuration and persistent files under the `AppConfigs` directory:
* `AppConfigs/APIKeys/`: Stores Gemini API Keys in `.txt` format used for new projects or the general application.
* `AppConfigs/Promts/`: Stores AI prompt templates used for translation and text adjustments.

When you create a "New Project", the application creates project-specific subfolders (`dwnld`, `trslt`, `cmplt`, etc.) in the project directory, so downloads and translations are organized and do not overlap.

## Using JS Files Manually in Browser
By clicking the **JS Save** menu on the top navigation bar, you can easily save Booktoki.js and 69shuba.js script files to your Desktop. If you prefer using a browser instead of the downloader tool, open the chapter reading page of the novel, open Developer Tools (`F12`), paste the copied JS script into the **Console** tab, and press enter. The script will automatically scrape all chapters and download them as a text file.

## Logging System
As of version 1.9.9, the application logs all important events, warnings, and errors to `AppConfigs/app.log`. If you encounter any issues, you can review this file to find the root cause. The log file is updated (appended) every time the application starts.

## Directory Tree
```text
yznvltranslate-main/
├── AppConfigs/         # App configuration and logs
├── cache/             # Translation cache management
├── core/              # Core business logic
│   └── workers/       # Async workers for translation tasks
├── terminology/       # Terminology memory management
├── ui/                # UI components and dialogs
├── main_window.py     # Main Entry Point
├── dialogs.py         # General dialogs
├── logger.py          # Logger configuration
├── 69shuba.js         # Scraper script
├── booktoki.js        # Scraper script
├── novelfire.js       # Scraper script
├── requirements.txt   # Dependencies
├── setup.py           # cx_Freeze setup script
└── file-tree.md       # Project file tree documentation
```

## API Pool and MCP Endpoint Rotation Flowchart
```text
429 Rate Limit Exceeded Error Received
    │
    ▼
CAS: Did another thread already rotate?
    ├─ Yes → continue with current endpoint/key (True)
    └─ No (first reporter)
          │
          ▼
    Step 1: provider.rotate_key()
          ├─ True → same endpoint, new key (K0→K1→K2) ✓
          └─ False (pool exhausted)
                │
                ▼
          Step 2: _all_endpoints[next_idx] → new MCP endpoint ✓
                └─ All exhausted → is_running=False, stop
```

## Version History

| Version | Changes |
|-------|--------------| 
| 2.6.0 | **Advanced Translation Error Check:** Integrated **Text Similarity Ratio (>=80%)** and **`langdetect` Language Detection** for English and other Latin alphabet source languages. Compares original files with translations to identify and report untranslated chapters. |
| 2.5.0 | **Localization work started:** English and Turkish language options added. Currently incomplete — some areas may still be missing translations. When the language option is changed, the selected language is treated as the target translation language. |
| 2.4.0 | **Count Tokens** button switched to local (offline) counting without requiring an API. **Theme files** are now automatically generated during build (`dark.qss`, `light.qss`, etc.). **MCP Dialog** improved: when Gemini is selected, model list is shown and URL field is hidden; added "Import API from API Editor" button. **File List** sorting fixed: merged (cmplt) files are now displayed at the top of the list. Added chapter range selection dialog to **ML Terminology** extraction, and the last processed session is saved and shown. |
| 2.3.0 | New UI and various improvements for a more stable and faster experience. Added theme customization panel. |
| 2.1.0 | **SRP** restructuring. **Paragraph-Based Translation** made default (cache-independent). **Bulk Translation (Batch Mode)** added: packages multiple chapters into a single API request to translate more chapters under the same RPD limit. Added **Asynchronous Translation** allowing parallel API requests for faster translation. |
| 2.0.0 | Major update! MCP Architecture, Prompt Generator, Translation Cache, Terminology Memory, new GenAI SDK, CJK Translation Quality Check, and advanced Text Editor added. |
| 1.9.9 | Logging system added via `logger.py`. Fixed UI freezing issue after token counting. Fixed token counter reset (data loss) issue on partial counting. |
| 1.9.8 | General bug fixes (retry_count, statusLabel wordwrap, cx_Freeze base). |
| 1.9.7 | Added Bulk Chapter Split (`split_worker.py`) feature. |
| 1.9.6 | Added JS Save menu to save scraper scripts locally. |
| 1.9.5 | Added saving selected files as EPUB. |
| 1.9.4 | Added chapter translation limits (`file_limit`). |
| 1.9.3 | Added chapter title check. |
