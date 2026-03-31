import os

BOOKTOKI_JS_CONTENT = """\
(async () => {
    /**
     * Verilen URL'den sayfa içeriğini çeker, metni temizler ve sonraki bölümün URL'sini bulur.
     * Dikkat önemli!!! 112. satıra son bölüm numarası yazılacak. Son bölüme gelindiğinde durması için bir sınır koyuyoruz.
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

            // === DÜZELTME 1: KORECE ENCODING (UTF-8) ===
            const html = await res.text();
            // === DÜZELTME 1 SONU ===

            const doc = new DOMParser().parseFromString(html, "text/html");

            // === DÜZELTME 2: İÇERİK SEÇİCİSİ ===
            const el = doc.querySelector("#novel_content"); 
            
            if (!el) {
                console.log("'#novel_content' alanı bulunamadı, bu bölüm atlanıyor.", url);
                const nextLinkOnError = doc.querySelector("#goNextBtn");
                const nextUrlOnError = (nextLinkOnError && nextLinkOnError.href) ? new URL(nextLinkOnError.href, url).href : null;
                return { text: null, nextUrl: nextUrlOnError };
            }

            // Metni temizlemek için elementi klonluyoruz.
            const contentEl = el.cloneNode(true);

            // === İSTENMEYEN ELEMENTLERİ KALDIR ===
            
            // Varsa resimlerin bulunduğu div'i kaldır (.view-img)
            const viewImg = contentEl.querySelector(".view-img");
            if (viewImg) viewImg.remove();
            
            // Başlığı (h1) kaldır
            const title = contentEl.querySelector("h1");
            if (title) title.remove();

            // *** ayıracı gibi stil div'lerini kaldır
            const dividers = contentEl.querySelectorAll('div[style*="text-align:center"]');
            dividers.forEach(d => d.remove());
            
            // === DÜZELTME 4: <p> ETİKETLERİ İÇİN SATIR ATLAMASI ===
            // .innerText.trim() kullanmak yerine, kalan tüm <p> etiketlerini buluyoruz.
            const paragraphs = contentEl.querySelectorAll("p");
            
            let textLines = []; // Her bir paragraf metnini tutacak bir dizi
            
            paragraphs.forEach(p => {
                const pText = p.innerText.trim();
                if (pText) { // Boş <p> etiketlerini atla
                    textLines.push(pText);
                }
            });
            
            // Tüm satırları, aralarında birer yeni satır (\n) olacak şekilde birleştir
            const text = textLines.join("\\n");
            // === DÜZELTME 4 SONU ===

            // === DÜZELTME 3: SONRAKİ SAYFA SEÇİCİSİ ===
            const nextLink = doc.querySelector("#goNextBtn");
            let nextUrl = null;
            
            if (nextLink && nextLink.href) {
                 nextUrl = new URL(nextLink.href, url).href;
                 
                 if (nextUrl.includes('javascript:;') || nextUrl === url) {
                     nextUrl = null;
                 }
            }
            // === DÜZELTME 3 SONU ===

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

    while (url) {
        counter++;
        console.log(`📄 ${counter}. bölüm alınıyor: ${url}`);

        const { text, nextUrl } = await getPageContent(url);
        
        if (text) {
            // Bölüm başlığı ve içerik ekle
            allText += `## Bölüm - ${counter} ##\\n\\n${text}\\n\\n`;
        } else {
            console.log(`⚠ ${counter}. bölüm için içerik alınamadı veya içerik boş.`);
            allText += `## Bölüm - ${counter} ##\\n\\nEksik Bölüm\\n\\nBölüm Sonu${counter}\\n\\n`;
            emtyText += `## Bölüm - ${counter} ##\\n\\n`;
        }

        if (!nextUrl) {
            console.log("✅ Son bölüme ulaşıldı!");
            break;
        }
        //Manuel olarak belirlenecek. Son bölüme gelindiğinde durması için bir sınır koyuyoruz. Son Bölüm numarası yazılacak.
        if (counter>= 120){
            console.log(`✅ ${counter} . bölüme ulaşıldı!`);
            break;
        }
        url = nextUrl;
        // Sunucuyu yormamak için bekleme
        await new Promise(r => setTimeout(r, 10000)); 
    }

    if (allText.length === 0) {
        console.log("Hiçbir bölümden metin alınamadı. Dosya oluşturulmuyor.");
        return;
    }

    // Tek büyük TXT dosyası olarak indir
    const blob = new Blob([allText], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    
    // Kitap adını almaya çalış (Örn: "야구단 신입이 너무 잘함 703화 > 북토끼..." -> "야구단 신입이 너무 잘함")
    let bookTitle = document.title.split('>')[0].trim() || "tum_bolumler";
    bookTitle = bookTitle.replace(/\\s*\\d+화$/, "").trim(); // " 703화" gibi bölüm numarasını kaldır
    
    link.download = `${bookTitle || 'tum_bolumler'}.txt`;
    
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
"""

SHUBA69_JS_CONTENT = """\
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

            // === DÜZELTME 1: GBK ENCODING SORUNU ===
            // Metni .text() olarak değil, .arrayBuffer() olarak alıyoruz (ham baytlar)
            const buffer = await res.arrayBuffer();
            // TextDecoder kullanarak 'gbk' kodlamasıyla baytları metne çeviriyoruz.
            const decoder = new TextDecoder('gbk');
            const html = decoder.decode(buffer);
            // === DÜZELTME 1 SONU ===

            const doc = new DOMParser().parseFromString(html, "text/html");

            // Metnin bulunduğu ana alanı ID yerine CLASS ile seçiyoruz.
            const el = doc.querySelector(".txtnav"); 
            
            if (!el) {
                console.log("'.txtnav' alanı bulunamadı, bu bölüm atlanıyor.", url);
                // Sonraki linki yine de aramayı deneyebiliriz, belki sayfa yapısı değişmiştir
                const nextLinkOnError = Array.from(doc.querySelectorAll("a"))
                    .find(a => a.textContent.includes("下一章"));
                const nextUrlOnError = nextLinkOnError ? new URL(nextLinkOnError.href, url).href : null;
                return { text: null, nextUrl: nextUrlOnError };
            }

            // Metni temizlemek için elementi klonluyoruz.
            const contentEl = el.cloneNode(true);

            // === İSTENMEYEN ELEMENTLERİ KALDIR ===
            
            // Başlığı (h1) kaldır
            const title = contentEl.querySelector("h1.hide720");
            if (title) title.remove();

            // Bilgi (tarih/yazar) kısmını kaldır
            const info = contentEl.querySelector(".txtinfo.hide720");
            if (info) info.remove();

            // Sağdaki reklam alanını kaldır
            const adRight = contentEl.querySelector("#txtright");
            if (adRight) adRight.remove();

            // Alttaki reklam alanını kaldır
            const adBottom = contentEl.querySelector(".bottom-ad");
            if (adBottom) adBottom.remove();

            // Metin içindeki ".contentadv" reklamlarını kaldır (HTML'de görüldü)
            const contentAds = contentEl.querySelectorAll(".contentadv"); 
            contentAds.forEach(ad => ad.remove());
            
            // === TEMİZ METNİ AL ===
            
            // Kalan elementlerin metnini al (innerText, <br> etiketlerini korur)
            const text = contentEl.innerText.trim(); 

            // === DÜZELTME 2: SONRAKİ SAYFA SEÇİCİSİ ===
            // Daha spesifik bir seçici kullanarak doğru linki buluyoruz (.page1 içindeki son <a> etiketi)
            const nextLink = doc.querySelector(".page1 a:last-child");
            let nextUrl = null;
            
            // Linkin gerçekten "sonraki bölüm" linki olduğunu kontrol et
            if (nextLink && nextLink.textContent.includes("下一章")) {
                 nextUrl = new URL(nextLink.href, url).href;
                 
                 // Son sayfa linkleri bazen 'javascript:;' olabilir, bunu kontrol et
                 if (nextUrl.includes('javascript:;')) {
                     nextUrl = null;
                 }
            }
            // === DÜZELTME 2 SONU ===

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

    while (url) {
        counter++;
        console.log(`📄 ${counter}. bölüm alınıyor: ${url}`);

        const { text, nextUrl } = await getPageContent(url);
        
        if (text) {
            // Bölüm başlığı ve içerik ekle
            allText += `## Bölüm - ${counter} ##\\n\\n${text}\\n\\n`;
        } else {
            console.log(`⚠ ${counter}. bölüm için içerik alınamadı veya içerik boş.`);
            allText += `## Bölüm - ${counter} ##\\n\\nEksik Bölüm\\n\\nBölüm Sonu${counter}\\n\\n`;
            emtyText += `## Bölüm - ${counter} ##\\n\\n`;
        }

        if (!nextUrl) {
            console.log("✅ Son bölüme ulaşıldı!");
            break;
        }
        
        // Örnek: Belirli bir bölümde durdurma (isteğe bağlı)
        // if (counter == 570){
        //     console.log("✅ Manuel olarak 570. bölümde durduruldu.")
        //     break; 
        // }

        url = nextUrl;
        // Sunucuyu yormamak için bekleme süresini biraz artıralım
        await new Promise(r => setTimeout(r, 2500)); 
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
    let bookTitle = document.title.split('-')[0] || "tum_bolumler";
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
"""

NOVELFIRE_JS_CONTENT = """\
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
                    .join("\\n\\n");
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
            allText += `## Bölüm - ${counter} ##\\n\\n${text}\\n\\n`;
        } else {
            console.log(`⚠ ${counter}. bölüm için içerik alınamadı veya içerik boş.`);
            allText += `## Bölüm - ${counter} ##\\n\\nEksik Bölüm\\n\\nBölüm Sonu${counter}\\n\\n`;
            emtyText += `## Bölüm - ${counter} ##\\n\\n`;
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
"""

def create_js_file(filename):
    """
    Creates the specified JS file in the current working directory if it does not exist.
    """
    js_content_map = {
        "booktoki.js": BOOKTOKI_JS_CONTENT,
        "69shuba.js": SHUBA69_JS_CONTENT,
        "novelfire.js": NOVELFIRE_JS_CONTENT
    }
    
    if filename in js_content_map:
        file_path = os.path.join(os.getcwd(), filename)
        if not os.path.exists(file_path):
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(js_content_map[filename])
                return True
            except Exception:
                return False
        return True
    return False

def create_all_js_files():
    """
    Creates all known JS files if they don't exist.
    """
    create_js_file("booktoki.js")
    create_js_file("69shuba.js")
    create_js_file("novelfire.js")
