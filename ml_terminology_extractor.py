import os
import re
import json
import argparse
import logging
from collections import defaultdict, Counter

import jieba
import jieba.analyse

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MLExtractor")

# Proje içerisindeki llm_provider modülünü dahil et
try:
    from llm_provider import create_provider_from_config
except ImportError as e:
    logger.error("llm_provider.py bulunamadı. Lütfen aracın yznvltranslate-main klasöründe olduğundan emin olun.")
    raise e


EXTRACT_PROMPT = """Ekteki Çince kaynak metni ve Türkçe çevirisini analiz et.
Makine öğrenmesi tabanlı TF-IDF analizi sonucunda aşağıdaki potansiyel terim/özel isim adaylarını çıkardım:

ADAY TERİMLER:
{candidates}

LÜTFEN ŞUNU YAP:
1. Bu aday terimlerin Türkçe çeviride KESİN OLARAK nasıl çevrildiğini bul.
2. Yalnızca metinde karşılığı NET olan terimleri dahil et. Bağlamdan emin değilsen listeye ekleme.
3. Terimleri SADECE 'Çince Kaynak → Türkçe Çeviri' formatında listele. Başka açıklama yapma.

KAYNAK METİN KESİTİ (Çince):
{source_text}

ÇEVİRİ METNİ KESİTİ (Türkçe):
{target_text}

YANIT FORMATI:
source_term → target_translation
"""

class MLTerminologyExtractor:
    """
    Terminoloji çıkarma için 4 aşamalı ML pipeline'ı:
    1. Dosya Eşleştirme: dwnld/ ve trslt/ dosyaları
    2. ML Çıkarımı: jieba TF-IDF ile Çince kaynak metinden özel isim ve terim çıkarma
    3. LLM Doğrulama: LLM üzerinden kaynak-çeviri paralelliğini doğrulama
    4. Sonuç Birleştirme: Tüm sonuçları JSON olarak kaydetme
    """
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.dwnld_dir = os.path.join(project_path, "dwnld")
        self.trslt_dir = os.path.join(project_path, "trslt")
        self.config_dir = os.path.join(project_path, "config")
        self.llm_provider = None
        
        try:
            # Yapılandırılmış LLM Provider'ı yükle
            self.llm_provider = create_provider_from_config(project_path)
            logger.info(f"LLM Provider başarıyla yüklendi: {self.llm_provider.ep_name}")
        except Exception as e:
            logger.error(f"LLM Provider başlatılamadı: {e}")
            
    def _get_matched_files(self, max_files: int = 0) -> list[tuple[str, str]]:
        if not os.path.exists(self.dwnld_dir) or not os.path.exists(self.trslt_dir):
            logger.error(f"Eksik klasör. '{self.dwnld_dir}' veya '{self.trslt_dir}' bulunamadı.")
            return []
            
        dwnld_files = sorted([f for f in os.listdir(self.dwnld_dir) if f.endswith(".txt")])
        matched_pairs = []
        
        for dwnld_file in dwnld_files:
            # Varsayılan dosya adı şablonu: bolum_0001.txt -> translated_bolum_0001.txt
            expected_trslt = f"translated_{dwnld_file}"
            trslt_path = os.path.join(self.trslt_dir, expected_trslt)
            
            if os.path.exists(trslt_path):
                matched_pairs.append((
                    os.path.join(self.dwnld_dir, dwnld_file),
                    trslt_path
                ))
                
        if max_files > 0:
            matched_pairs = matched_pairs[:max_files]
            
        return matched_pairs

    def _extract_ml_candidates(self, source_text: str, top_k: int = 30) -> list[str]:
        """jieba kullanarak TF-IDF yöntemine göre terim adaylarını belirler."""
        # allowPOS: isimler (n), özel isimler (nr), yer isimleri (ns), vd.
        tags = jieba.analyse.extract_tags(
            source_text, 
            topK=top_k, 
            allowPOS=('nr', 'ns', 'nt', 'nz', 'n')
        )
        # Sadece Çince karakter içeren ve uzunluğu >= 2 olan adayları koru
        candidates = [t for t in tags if len(t) >= 2 and re.search(r'[\u4e00-\u9fff]', t)]
        return candidates

    def _parse_llm_response(self, response: str) -> dict[str, str]:
        """LLM çıktısını ayrıştırır ve sözlük döndürür."""
        extracted = {}
        pattern = re.compile(r'^(.+?)\s*(?:→|->|=)\s*(.+?)$')
        for line in response.strip().split('\n'):
            line = line.strip()
            # Başta olabilecek madde imlerini temizle
            line = re.sub(r'^[\-\*•]\s*', '', line).strip()
            match = pattern.match(line)
            if match:
                src, tgt = match.group(1).strip(), match.group(2).strip()
                if len(src) >= 1 and len(tgt) >= 1:
                    extracted[src] = tgt
        return extracted

    def run(self, max_files: int = 10, append: bool = False):
        if not self.llm_provider:
            logger.error("LLM Provider mevcut olmadığı için işleme devam edilemiyor.")
            return
            
        pairs = self._get_matched_files(max_files)
        if not pairs:
            logger.warning("Hiç eşleşen dosya çifti bulunamadı.")
            return
            
        logger.info(f"İşlem başlıyor... Toplam {len(pairs)} dosya çifti değerlendirilecek.")
        
        term_frequencies = defaultdict(list)
        
        for idx, (src_path, tgt_path) in enumerate(pairs, 1):
            file_basename = os.path.basename(src_path)
            logger.info(f"[{idx}/{len(pairs)}] Analiz ediliyor: {file_basename}")
            
            try:
                with open(src_path, 'r', encoding='utf-8') as f:
                    source_text = f.read()
                with open(tgt_path, 'r', encoding='utf-8') as f:
                    target_text = f.read()
                    
                # Aşama 1: Makine Öğrenmesi (TF-IDF) ile adayların çıkarılması
                candidates = self._extract_ml_candidates(source_text, top_k=25)
                if not candidates:
                    logger.warning(f"  > ({file_basename}) ML adayı bulunamadı, bölüm atlanıyor.")
                    continue
                    
                candidates_str = "\n".join([f"- {c}" for c in candidates])
                
                # LLM'e göndermek üzere (çok uzun bağlanmasını engellemek için) metni kırpıyoruz
                # Genellikle novel bölümleri 3000-5000 karakter arası olur, 4000 limit token tasarrufu sağlar.
                prompt = EXTRACT_PROMPT.format(
                    candidates=candidates_str,
                    source_text=source_text[:4000],
                    target_text=target_text[:4000]
                )
                
                # Aşama 2: LLM üzerinden çapraz onaylama (Validation)
                response = self.llm_provider.generate(prompt)
                extracted_dict = self._parse_llm_response(response)
                
                # Aşama 3: Sonuçların kaydedilmesi
                for src, tgt in extracted_dict.items():
                    term_frequencies[src].append(tgt)
                    
                logger.info(f"  > Bulunan onaylanmış terim sayısı: {len(extracted_dict)}")
                
            except Exception as e:
                logger.error(f"  > Hata - {file_basename}: {e}")
                
        # Aşama 4: Toplu istatistik ve filtreleme
        final_terms = []
        for src, tgts in term_frequencies.items():
            # Frekansa göre en çok tekrar edeni seçimi (örn. Zhou Wen -> Zhou Wen x3)
            best_tgt = Counter(tgts).most_common(1)[0][0]
            freq = len(tgts)
            
            final_terms.append({
                "source": src,
                "target": best_tgt,
                "note": f"ml-extracted (freq: {freq})"
            })
            
        logger.info(f"Tüm bölümlerden {len(final_terms)} benzersiz terminoloji çıkarıldı.")
        
        self._save_results(final_terms, append)

    def _save_results(self, new_terms: list, append: bool):
        os.makedirs(self.config_dir, exist_ok=True)
        terms_file = os.path.join(self.config_dir, "terminology.json")
        
        existing_terms = []
        if append and os.path.exists(terms_file):
            try:
                with open(terms_file, 'r', encoding='utf-8') as f:
                    existing_terms = json.load(f)
            except Exception as e:
                logger.warning(f"Mevcut terminoloji okunamadı: {e}")
                
        # Append durumunda mevcut veriye sadık kal
        if append:
            existing_sources = {t["source"].lower() for t in existing_terms}
            added_count = 0
            for nt in new_terms:
                if nt["source"].lower() not in existing_sources:
                    existing_terms.append(nt)
                    added_count += 1
            final_list = existing_terms
            logger.info(f"Mevcut listeye {added_count} adet yeni terim eklendi.")
        else:
            final_list = new_terms
            
        try:
            with open(terms_file, 'w', encoding='utf-8') as f:
                json.dump(final_list, f, indent=2, ensure_ascii=False)
                
            action = "Kayıt mevcut dosyaya EKLENDİ" if append else "YENİ DOSYA YARATILDI"
            logger.info(f"İşlem Tamamlandı: {terms_file} [{action}]")
        except Exception as e:
            logger.error(f"Terminoloji dosyası kaydedilemedi: {e}")


def main():
    parser = argparse.ArgumentParser(description="Çeviri Performans Testi İçin ML-Tabanlı Terminoloji Çıkarma")
    parser.add_argument("--project-path", type=str, default=".", help="Projenin ana dizini yolu (varsayılan: ./)")
    parser.add_argument("--max-files", type=int, default=10, help="Test edilecek max dosya çifti sayısı (0 = Sınırsız, varsayılan: 10)")
    parser.add_argument("--append", action="store_true", help="Mevcut terminology.json dosyasının üzerine yazmak yerine terimleri listeye ekle")
    
    args = parser.parse_args()
    
    extractor = MLTerminologyExtractor(args.project_path)
    extractor.run(max_files=args.max_files, append=args.append)

if __name__ == "__main__":
    main()
