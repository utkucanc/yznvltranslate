"""
ProjectManager — Proje yaşam döngüsü yönetimi.

Sorumluluklar:
  - Mevcut projeleri yükleme / listeleme (Project/<Ad> ve kök/<Ad> geriye uyumlu)
  - Yeni proje oluşturma (Project/<Ad>/ klasör yapısı + config.ini)
  - Proje silme
  - Proje config okuma / yazma
"""

import os
import shutil
import configparser
from logger import app_logger
from core.path_resolver import get_project_dir, get_subfolder_path


class ProjectManager:
    """Proje dizin ve konfigürasyon yöneticisi."""

    PROJECT_SUBFOLDERS = ["download", "translate", "completed", "config"]

    def __init__(self, base_dir: str = None):
        """
        Args:
            base_dir: Projelerin aranacağı kök dizin. None ise os.getcwd() kullanılır.
        """
        self.base_dir = base_dir or os.getcwd()

    # --------------- Proje Listeleme ---------------

    def list_projects(self) -> list[str]:
        """config/config.ini dosyası olan tüm klasörleri (Project/ dizininde ve kökte) proje olarak döndürür."""
        projects = set()
        dirs_to_check = [self.base_dir]
        
        project_root = os.path.join(self.base_dir, "Project")
        if os.path.exists(project_root):
            dirs_to_check.append(project_root)

        for scan_dir in dirs_to_check:
            try:
                for item in os.listdir(scan_dir):
                    if item == "Project":
                        continue
                    full_path = os.path.join(scan_dir, item)
                    if os.path.isdir(full_path):
                        config_dir = get_subfolder_path(full_path, "config")
                        config_path = os.path.join(config_dir, "config.ini")
                        if os.path.exists(config_path):
                            projects.add(item)
            except Exception as e:
                app_logger.error(f"Proje listesi taranırken hata ({scan_dir}): {e}")

        return sorted(list(projects))

    # --------------- Proje Oluşturma ---------------

    def create_project(
        self,
        project_name: str,
        project_link: str,
        api_key: str = "",
        deepl_api: str = "",
        yandex_api: str = "",
        startpromt: str = "",
        max_pages: int = None,
        max_retries: int = 3,
        api_key_name: str = "",
        mcp_endpoint_id: str = None,
    ) -> tuple[bool, str]:
        """
        Yeni bir proje klasörü ve config.ini oluşturur.
        Yeni projeler base_dir/Project/<project_name> altında oluşturulur.

        Returns:
            (success, message) tuple
        """
        project_path = get_project_dir(self.base_dir, project_name, create_if_new=True)
        if os.path.exists(project_path):
            return False, f"'{project_name}' adında bir proje zaten mevcut."

        try:
            for folder in self.PROJECT_SUBFOLDERS:
                os.makedirs(os.path.join(project_path, folder), exist_ok=True)

            config = configparser.ConfigParser()
            config["ProjectInfo"] = {"link": project_link}
            if max_pages is not None:
                config["ProjectInfo"]["max_pages"] = str(max_pages)
            config["ProjectInfo"]["max_retries"] = str(max_retries)
            config["API"] = {"gemini_api_key": api_key, "api_key_name": api_key_name}
            config["DEEPL"] = {"deepl_api": deepl_api}
            config["YANDEX"] = {"yandex_api": yandex_api}
            config["Startpromt"] = {"startpromt": startpromt}
            if mcp_endpoint_id:
                config["MCP"] = {"endpoint_id": mcp_endpoint_id}

            config_dir = get_subfolder_path(project_path, "config", create=True)
            config_path = os.path.join(config_dir, "config.ini")
            with open(config_path, "w", encoding="utf-8") as f:
                config.write(f)

            app_logger.info(f"Proje oluşturuldu: {project_name}")
            return True, f"'{project_name}' projesi başarıyla oluşturuldu."

        except OSError as e:
            app_logger.error(f"Proje oluşturma hatası ({project_name}): {e}")
            return False, f"Dizin oluşturulurken bir hata oluştu:\n{e}"
        except Exception as e:
            app_logger.error(f"Proje oluşturma hatası ({project_name}): {e}")
            return False, f"Proje oluşturulurken beklenmeyen bir hata oluştu:\n{e}"

    # --------------- Proje Silme ---------------

    def delete_project(self, project_name: str) -> tuple[bool, str]:
        """
        Projeyi ve tüm içeriğini kalıcı olarak siler.

        Returns:
            (success, message) tuple
        """
        project_path = get_project_dir(self.base_dir, project_name)
        try:
            if os.path.exists(project_path):
                shutil.rmtree(project_path)
            app_logger.info(f"Proje silindi: {project_name}")
            return True, f"'{project_name}' projesi başarıyla silindi."
        except OSError as e:
            app_logger.error(f"Proje silme hatası ({project_name}): {e}")
            return False, f"Proje silinirken bir hata oluştu:\n{e}"
        except Exception as e:
            app_logger.error(f"Proje silme hatası ({project_name}): {e}")
            return False, f"Proje silinirken beklenmeyen bir hata oluştu:\n{e}"

    # --------------- Config Okuma / Yazma ---------------

    def get_project_path(self, project_name: str) -> str:
        return get_project_dir(self.base_dir, project_name)

    def load_config(self, project_name: str) -> configparser.ConfigParser:
        """Proje config.ini'sini okur ve döndürür."""
        config = configparser.ConfigParser()
        project_path = get_project_dir(self.base_dir, project_name)
        config_dir = get_subfolder_path(project_path, "config")
        config_path = os.path.join(config_dir, "config.ini")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config.read_file(f)
            except Exception as e:
                app_logger.error(f"Config okuma hatası ({project_name}): {e}")
        return config

    def save_config(self, project_name: str, config: configparser.ConfigParser) -> bool:
        """Proje config.ini'sini kaydeder."""
        project_path = get_project_dir(self.base_dir, project_name)
        config_dir = get_subfolder_path(project_path, "config", create=True)
        config_path = os.path.join(config_dir, "config.ini")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                config.write(f)
            app_logger.info(f"Config kaydedildi: {project_name}")
            return True
        except Exception as e:
            app_logger.error(f"Config kayıt hatası ({project_name}): {e}")
            return False

