"""
path_resolver.py — Proje dizin ve alt klasör yolu çözümleyicisi.

Geriye Uyumlu Yapı (Backwards Compatibility):
  - Yeni Projeler: Project/<ProjeAdı>/completed | config | download | translate
  - Eski Projeler: <ProjeAdı>/cmplt | config | dwnld | trslt
"""

import os

SUBFOLDER_ALIASES = {
    "download": ["download", "dwnld"],
    "translate": ["translate", "trslt", "tr"],
    "completed": ["completed", "cmplt"],
    "config": ["config"]
}


def get_project_dir(base_dir: str, project_name: str, create_if_new: bool = False) -> str:
    """
    Proje ana klasör yolunu döndürür.
    Önce base_dir/Project/<project_name> (yeni yapı),
    yoksa base_dir/<project_name> (eski yapı) kontrol edilir.
    Hiçbiri yoksa ve create_if_new=True ise base_dir/Project/<project_name> varsayılır.
    """
    new_path = os.path.join(base_dir, "Project", project_name)
    old_path = os.path.join(base_dir, project_name)

    if os.path.exists(new_path):
        return new_path
    if os.path.exists(old_path):
        return old_path

    if create_if_new:
        return new_path
    return old_path


def get_subfolder_path(project_path: str, folder_type: str, create: bool = False) -> str:
    """
    Belirtilen folder_type ('download', 'translate', 'completed', 'config') için 
    proje dizini altındaki klasör yolunu döndürür.
    Mevcut klasörlerden hangisi varsa onu seçer, yoksa ilk sıradaki varsayılan ismi döner.
    """
    aliases = SUBFOLDER_ALIASES.get(folder_type, [folder_type])

    for alias in aliases:
        cand = os.path.join(project_path, alias)
        if os.path.exists(cand):
            return cand

    default_path = os.path.join(project_path, aliases[0])
    if create:
        os.makedirs(default_path, exist_ok=True)
    return default_path
