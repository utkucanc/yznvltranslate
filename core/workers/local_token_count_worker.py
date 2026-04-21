"""
LocalTokenCountWorker — API gerektirmeden yerel token sayımı yapan worker.

GPT-2 tokenizer (transformers) veya karakter tabanlı yaklaşık hesap kullanır.
"""

import os
from PyQt6.QtCore import QThread, pyqtSignal

from core.workers.token_counter import get_local_token_count_approx
from logger import app_logger


class LocalTokenCountWorker(QThread):
    """Seçili dosyaları yerel olarak (API'sız) sayar."""

    progress = pyqtSignal(int, int)   # (tamamlanan, toplam)
    finished = pyqtSignal(dict)        # results dict (token_counter formatıyla uyumlu)
    error = pyqtSignal(str)

    def __init__(self, project_path: str, selected_files: list[str],
                 download_folder: str, translated_folder: str):
        """
        Args:
            project_path: Projenin kök dizini
            selected_files: Sayılacak dosya adları listesi (ör. ['ch001.txt', 'translated_ch001.txt'])
            download_folder: dwnld klasörü tam yolu
            translated_folder: trslt klasörü tam yolu
        """
        super().__init__()
        self.project_path = project_path
        self.selected_files = selected_files
        self.download_folder = download_folder
        self.translated_folder = translated_folder
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        try:
            file_token_data = {}
            total_original = 0
            total_translated = 0

            files = self.selected_files
            total = len(files)

            for i, file_name in enumerate(files):
                if self._stop_flag:
                    break

                # Dosyanın nerede olduğunu bul
                file_path = None
                is_translated = file_name.startswith("translated_")

                if is_translated:
                    candidate = os.path.join(self.translated_folder, file_name)
                    if os.path.exists(candidate):
                        file_path = candidate
                else:
                    candidate = os.path.join(self.download_folder, file_name)
                    if os.path.exists(candidate):
                        file_path = candidate

                if not file_path:
                    app_logger.warning(f"LocalTokenCountWorker: Dosya bulunamadı: {file_name}")
                    self.progress.emit(i + 1, total)
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    token_count = get_local_token_count_approx(content)
                    app_logger.debug(f"Yerel token sayımı: {file_name} → {token_count}")
                except Exception as e:
                    app_logger.warning(f"LocalTokenCountWorker dosya okuma hatası ({file_name}): {e}")
                    self.progress.emit(i + 1, total)
                    continue

                if is_translated:
                    file_token_data.setdefault(file_name, {})
                    file_token_data[file_name]["translated_tokens"] = token_count
                    total_translated += token_count
                else:
                    file_token_data.setdefault(file_name, {})
                    file_token_data[file_name]["original_tokens"] = token_count
                    total_original += token_count

                self.progress.emit(i + 1, total)

            results = {
                "file_token_data": file_token_data,
                "total_original_tokens": total_original,
                "total_translated_tokens": total_translated,
                "total_combined_tokens": total_original + total_translated,
            }
            self.finished.emit(results)

        except Exception as e:
            app_logger.error(f"LocalTokenCountWorker genel hata: {e}")
            self.error.emit(str(e))
