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


def is_old_project_structure(base_dir: str, project_name: str) -> bool:
    """Projenin eski dosya yapısında olup olmadığını tespit eder."""
    if not project_name:
        return False

    old_root = os.path.join(base_dir, project_name)
    new_root = os.path.join(base_dir, "Project", project_name)

    # 1. Eski kök dizinde mi?
    if os.path.exists(old_root) and not os.path.exists(new_root):
        return True

    # 2. Subfolder'larında eski isimler var mı?
    p_path = new_root if os.path.exists(new_root) else (old_root if os.path.exists(old_root) else None)
    if p_path and os.path.exists(p_path):
        for old_sub in ["dwnld", "trslt", "tr", "cmplt"]:
            sub_p = os.path.join(p_path, old_sub)
            if os.path.exists(sub_p) and os.path.isdir(sub_p):
                return True
    return False


def migrate_project_structure(base_dir: str, project_name: str) -> tuple[bool, str]:
    """
    Eski dosya yapısındaki projeyi kayıpsız olarak yeni standart yapıya dönüştürür:
    - Base dizindeki <project_name> -> Project/<project_name>
    - dwnld -> download
    - trslt / tr -> translate
    - cmplt -> completed
    """
    import shutil
    try:
        if not project_name:
            return False, "Proje adı geçersiz."

        old_root = os.path.join(base_dir, project_name)
        new_root = os.path.join(base_dir, "Project", project_name)

        # 1. Root klasörü taşı/birleştir
        if os.path.exists(old_root) and old_root != new_root:
            os.makedirs(os.path.dirname(new_root), exist_ok=True)
            if not os.path.exists(new_root):
                shutil.move(old_root, new_root)
            else:
                for item in os.listdir(old_root):
                    src = os.path.join(old_root, item)
                    dst = os.path.join(new_root, item)
                    if os.path.isdir(src):
                        if not os.path.exists(dst):
                            shutil.move(src, dst)
                        else:
                            for sub_item in os.listdir(src):
                                sub_src = os.path.join(src, sub_item)
                                sub_dst = os.path.join(dst, sub_item)
                                if not os.path.exists(sub_dst):
                                    shutil.move(sub_src, sub_dst)
                    else:
                        if not os.path.exists(dst):
                            shutil.move(src, dst)
                try:
                    shutil.rmtree(old_root)
                except Exception:
                    pass

        target_dir = new_root if os.path.exists(new_root) else old_root
        if not os.path.exists(target_dir):
            return False, "Proje klasörü bulunamadı."

        # 2. Alt klasörleri standart isimlere kayıpsız taşı
        sub_mappings = [
            ("download", ["dwnld"]),
            ("translate", ["trslt", "tr"]),
            ("completed", ["cmplt"]),
        ]

        for std_name, aliases in sub_mappings:
            std_path = os.path.join(target_dir, std_name)
            os.makedirs(std_path, exist_ok=True)

            for alias in aliases:
                old_sub = os.path.join(target_dir, alias)
                if os.path.exists(old_sub) and old_sub != std_path and os.path.isdir(old_sub):
                    for item in os.listdir(old_sub):
                        src = os.path.join(old_sub, item)
                        dst = os.path.join(std_path, item)
                        if not os.path.exists(dst):
                            shutil.move(src, dst)
                        else:
                            base_n, ext = os.path.splitext(item)
                            dst_alt = os.path.join(std_path, f"{base_n}_migrated{ext}")
                            if not os.path.exists(dst_alt):
                                shutil.move(src, dst_alt)
                    try:
                        shutil.rmtree(old_sub)
                    except Exception:
                        pass

        return True, "Proje yapısı yeni formata başarıyla aktarıldı."
    except Exception as e:
        return False, f"Hata oluştu: {str(e)}"
