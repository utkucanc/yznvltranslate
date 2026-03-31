(async () => {
    /**
     * Verilen URL'den sayfa içeriğini çeker, metni temizler ve sonraki bölümün URL'sini bulur.
     * @param {string} url - İçeriği çekilecek sayfanın URL'si.
     * @returns {Promise<{text: string|null, nextUrl: string|null}>} - Temizlenmiş metin ve sonraki bölümün URL'si.
     */
    async function getPageContent(url) {
        try {
            const res = await fetch(url);
            if (!res.ok) {
                console.error(`HTTP hatası! Durum: ${res.status}, URL: ${url}`);
                return { text: null, nextUrl: null };
            }

            const html = await res.text();
            const doc = new DOMParser().parseFromString(html, "text/html");

            // Metnin bulunduğu ana alanı ID ile seçiyoruz.
            const el = doc.querySelector("#content"); 
            
            if (!el) {
                console.log("'#content' alanı bulunamadı, bu bölüm atlanıyor.", url);
                const nextLinkOnError = doc.querySelector(".nextchap[rel='next']");
                const nextUrlOnError = nextLinkOnError ? new URL(nextLinkOnError.getAttribute("href"), url).href : null;
                return { text: null, nextUrl: nextUrlOnError };
            }

            // Metni temizlemek için elementi klonluyoruz.
            const contentEl = el.cloneNode(true);

            // === İSTENMEYEN ELEMENTLERİ KALDIR ===
            
            // Reklam alanlarını kaldır
            const ads = contentEl.querySelectorAll(".nf-ads");
            ads.forEach(ad => ad.remove());

            // Bilgi (tarih/yazar) gibi kısımlar Novelfire'da #content dışında ama yine de kontrol edelim
            
            // === TEMİZ METNİ AL ===
            
            // Paragrafları tek tek alıp aralarına boşluk ekliyoruz (yan yana gelmemeleri için)
            const pTags = contentEl.querySelectorAll("p");
            let text = "";
            if (pTags.length > 0) {
                text = Array.from(pTags)
                    .map(p => p.innerText.trim())
                    .filter(t => t)
                    .join("\n\n");
            } else {
                text = contentEl.innerText.trim();
            }

            // === SONRAKİ SAYFA SEÇİCİSİ ===
            const nextLink = doc.querySelector(".nextchap[rel='next']");
            let nextUrl = null;
            
            if (nextLink) {
                 const href = nextLink.getAttribute("href");
                 if (href && !href.includes('javascript:;')) {
                     nextUrl = new URL(href, url).href;
                 }
            }

            return { text, nextUrl };

        } catch (error) {
            console.error(`Hata oluştu (${url}):`, error);
            return { text: null, nextUrl: null }; // Hata durumunda dur
        }
    }

    let url = location.href;
    let counter = 0;
    let allText = "";
    let emtyText = "";

    // === AYARLAR ===
    const stopAtChapter = 0; // Test için: Kaçıncı bölümde durmasını istiyorsanız buraya yazın (0 = durmaz)

    while (url) {
        counter++;

        // DURDURMA KONTROLÜ
        if (stopAtChapter > 0 && counter > stopAtChapter) {
            console.log(`✅ Manuel sınıra ulaşıldı (${stopAtChapter}. bölüm). İşlem durduruluyor.`);
            break;
        }

        console.log(`📄 ${counter}. bölüm alınıyor: ${url}`);

        const { text, nextUrl } = await getPageContent(url);
        
        if (text) {
            // Bölüm başlığı ve içerik ekle
            allText += `## Bölüm - ${counter} ##\n\n${text}\n\n`;
        } else {
            console.log(`⚠ ${counter}. bölüm için içerik alınamadı veya içerik boş.`);
            allText += `## Bölüm - ${counter} ##\n\nEksik Bölüm\n\nBölüm Sonu${counter}\n\n`;
            emtyText += `## Bölüm - ${counter} ##\n\n`;
        }

        if (!nextUrl) {
            console.log("✅ Son bölüme ulaşıldı!");
            break;
        }
        
        url = nextUrl;
        // Sunucuyu yormamak için bekleme süresini biraz artıralım
        await new Promise(r => setTimeout(r, 2000)); 
    }

    if (allText.length === 0) {
        console.log("Hiçbir bölümden metin alınamadı. Dosya oluşturulmuyor.");
        return;
    }

    // Tek büyük TXT dosyası olarak indir
    const blob = new Blob([allText], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    
    // Kitap adını almaya çalış (opsiyonel)
    let bookTitle = document.querySelector(".booktitle")?.textContent || document.title.split('-')[0] || "tum_bolumler";
    link.download = `${bookTitle.trim()}.txt`;
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    console.log(`🏁 Tüm bölümler indirildi ve '${link.download}' olarak kaydedildi!`);
    if(emtyText){
        console.log('⚠ Boş Bölüm Listesi:');
        console.log(emtyText);
    }else{
        console.log('Eksik Bölüm Yok✅')
    }
})();
