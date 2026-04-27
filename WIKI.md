# Novel Çeviri Aracı (NCA) - Adım Adım Kullanım Rehberi (Wiki)

Novel Çeviri Aracı'na (kısaca NCA) hoş geldiniz! 

Eğer daha önce hiç böyle bir program kullanmadıysanız, siyah ekranlar (kod ekranları) veya İngilizce terimler (API, Token vs.) gözünüzü korkutmasın. Bu rehber, **teknolojiyle arası hiç olmayan birinin bile** yabancı dildeki bir romanı (novel) internetten indirip tek tıklamayla çevirebileceği şekilde, hiçbir adımı atlamadan, olabildiğince basit ve anlaşılır bir dille hazırlanmıştır.

---

## 1. NCA Nedir ve Ne İşe Yarar?

NCA, internette yabancı dilde (İngilizce, Çince, Korece vb.) yayınlanan hikayeleri ve web romanlarını tek tek kopyala-yapıştır yapmanıza gerek kalmadan:
1. **İnternetten sizin için otomatik indirir**,
2. **Yapay zeka (Google Gemini vb.) kullanarak sizin için Türkçeye çevirir**,
3. Tüm bölümleri birleştirip size telefonunuzda veya tabletinizde okuyabileceğiniz bir **E-Kitap (EPUB)** veya düz yazı (TXT) olarak teslim eder.

---

## 2. İlk Adım: Kurulum ve Programı Açma

Programı kullanabilmek için bilgisayarınızın temel birkaç şeye ihtiyacı vardır.

### Bilgisayarda Olması Gerekenler:
1. **Python Programı**: NCA bu programlama diliyle yazıldığı için Python'un yüklü olması şarttır. İnternetten "Python 3.13 indir" yazarak resmi sitesinden indirip normal bir program gibi kurabilirsiniz. (Kurarken ekranda beliren "Add Python to PATH" kutucuğunu işaretlemeyi **asla** unutmayın!)
2. **Google Chrome Tarayıcısı**: Programın kitap indirirken bazı inatçı sitelere girebilmesi için bilgisayarınızda Google Chrome kurulu olmalıdır.

### Programı İlk Kez Çalıştırma:
1. İndirdiğiniz NCA klasörünü açın.
2. Klasörün içinde boş bir yere sağ tıklayın ve "Burada Komut İstemi Aç" veya "Terminalde Aç" (Open in Terminal) seçeneğine tıklayın. (Karşınıza siyah bir ekran çıkacak).
3. Bu siyah ekrana şunu yazıp klavyeden `Enter` tuşuna basın: 
   `pip install -r requirements.txt` 
   *(Bu işlem programın ihtiyaç duyduğu ek dosyaları internetten indirir. Sadece ilk seferde yapmanız yeterlidir, yazılar akacak ve bitmesini bekleyin).*
4. İşlem bitince, aynı siyah ekrana programı açmak için şunu yazıp `Enter`'a basın:
   `python main_window.py`

*(Not: Windows kullanıyorsanız ve bu siyah ekranlarla hiç uğraşmak istemiyorsanız, https://github.com/utkucanc/yznvltranslate/releases/latest indirme sayfasından indirebileceğiniz `NovelCeviriAraci-x.x.x-win64-portable.zip yada  NovelCeviriAraci-x.x.x-win64.msi ` dosyasını kullanabilirsiniz.)*

[Görsel-1 - Programın İlk Açılış Ekranı]
> **Görsel Ekleme Talimatı:** Arkada siyah ekran (terminal) kalmış şekilde, uygulamanın ilk açıldığındaki ana tablonun olduğu ekran görüntüsünü buraya ekleyin. Mümkünse terminaldeki "python main_window.py" yazısını kırmızı bir okla gösterin.

---

## 3. Ekranı Tanıyalım (Nerede Ne Var?)

Program açıldığında karşınıza birkaç farklı bölme çıkacak:
- **Orta ve Sol Büyük Boşluk (Proje - Dosya Listesi)**: İndirdiğiniz veya oluşturduğunuz projelerin/dosyaların isimleri burada alt alta listelenir. Tıpkı bilgisayarınızdaki bir klasörün içi gibidir. Yanlarında durum olarak "İndiriliyor", "Çevriliyor", "Tamamlandı" gibi yazılar yazar.
- **Sağ Taraftaki Uzun Kısım (Kontrol Paneli)**: Tüm işleri buradan yönetirsiniz. Link (internet adresi) yapıştırma yeri, "İndir", "Çeviriyi Başlat", "Birleştir" gibi kocaman butonlar hep buradadır.
- **En Üstteki Yazılı Menüler (Dosya, Ayarlar, MCP vs.)**: Programın ince ayarlarını yapacağınız yerdir. Temayı (karanlık/aydınlık) değiştirmek, yapay zekayı programa bağlamak,  gibi işlemleri buradan yaparsınız.

[Görsel-2 - Ana Ekran Panelleri]
> **Görsel Ekleme Talimatı:** Ekranı üçe bölen (Sol Liste, Sağ Panel, Üst Menü) renkli dikdörtgen kalın kutular çizilmiş ve "Burası indirdiğiniz dosyaların listesi", "Burası işlem butonlarının olduğu panel" gibi oklarla yazılar eklenmiş bir ekran görüntüsü koyun.

---

## 4. Yeni Bir Romana Başlamak (Yeni Proje)

Her roman (veya hikaye) için ayrı bir çalışma alanı oluşturmanız gerekir. Yoksa indirdiğiniz farklı romanların bölümleri birbirine karışır.

1. Sol üstteki **"Yeni Proje"** butonuna tıklayın. Karşınıza küçük bir kutu çıkacak.
2. **Proje Adı**: Çevireceğiniz romanın adını yazın. (Örn: *Yuzuklerin_Efendisi*, boşluk bırakmamaya çalışın.) **(Zorunludur.)**
3. **Proje Linki**: Girilecek olan link indirme işleminin başlatılabilmesi için 1. bölümün bağlantı adresi olmalıdır. **(Zorunludur.)**
4. **Maksimum Sayfa**: Hikayenin son bölüm sayısıdır. Opsiyoneldir. **Zorunlu değildir! (Boş bırakılabilir.)**
5. **Maksimum Deneme**: Herhangi bir hata nedeniyle oluşan çeviri hatalarında programın tekrar deneme sayısıdır. 
6. **Yapay Zeka Kaynağı(MCP)**: Özel olarak belirlenmiş belirli bir yapay zeka kaynağı ve modeline bağlanmak için düzenlenmiş ayarların seçilebileceği ayarlar bölümüdür. **(Boş bırakılabilir.)**
7. **API Key Seç** : API Key Editör üzerinden eklediğiniz API Anahtarlarını seçebileceğiniz açılır menü. 
8. **Promt Seç** : Promt Editör üzerinden eklediğiniz Promtları seçebileceğiniz açılır menü. **(Boş bırakılabilir.)**


[Görsel-3 - Yeni Proje Oluşturma Ekranı]
> **Görsel Ekleme Talimatı:** "Yeni Proje" pop-up (küçük) penceresinin görüntüsü. Proje adı girilmiş ve "Gözat" butonuna basılıp bilgisayardan bir hedefin seçilmiş halini gösterin.

---

## 5. Yapay Zekayı Programa Bağlamak (API Anahtarı Nedir?)

Programın içindeki çeviri sistemi aslında Google'ın "Gemini" isimli süper zeki yapay zekasını kullanır. Bu zekayı kullanabilmeniz için Google'dan ücretsiz bir "Kimlik Kartı / Şifre" (buna API Key denir) alıp programa tanıtmanız gerekir.

**Bu adım en önemli adımdır, bu şifreyi girmezseniz program hiçbir şeyi çeviremez!**

1. NCA programında en üst menüden **"MCP Server Ayarları"** seçeneğine tıklayın.
2. Karşınıza yapay zeka ayar ekranı çıkacak.
3. İnternet tarayıcınızdan (Chrome vb.) `aistudio.google.com` adresine gidin ve normal Google/Gmail hesabınızla giriş yapın.
4. Sitede sol tarafta veya üstte "Get API Key" (API Anahtarı Al) yazan yere tıklayın. "Create API Key" (Oluştur) diyerek uzun, karışık harf ve sayılardan oluşan şifrenizi yaratıp kopyalayın. *(Örnek: AIzaSyB_12345abcdefg...)*
5. Kopyaladığınız bu uzun şifreyi, NCA programındaki ekranda bulunan "API Editöründen API Aktar" bölümüne veya boş listeye yapıştırıp kaydedin.
6. Aynı Anahtarı **"API Key Editörü"** Seçeneğine girerek burada da ekleyin. **"AD"** kısmı sizin belirleyeceğiniz bir isimdir, herhangibir isim kullanabilirsiniz. **"Key"** Kısmı ise kopyaladığınız uzun şifredir.

*Not: Google ücretsiz olarak size belli bir hız ve kullanım sınırı verir. Hızlı çeviri yaparken program "Kotayı aştın" (429 Hatası) verirse korkmayın, program çökmez. Sadece 1 dakika bekler ve devam eder. Eğer beklemesini istemiyorsanız, yukarıdaki adımdaki gibi birkaç farklı Gmail hesabından şifre alıp programa eklerseniz, program birinci şifre yorulunca otomatik olarak gizlice ikinci şifreye geçer ve çeviriye durmadan devam eder.*

[Görsel-4 - API Şifresini Girme Ekranı]
> **Görsel Ekleme Talimatı:** Üst menüden açılan MCP ayarları penceresinde "API Editöründen API Aktar" kısmına o karmaşık şifrenin nasıl eklendiğini gösteren, eklendiğinde listede yeşil renkli görünen bir ekran görüntüsü.

---

## 6. İnternetten Roman İndirmek (Link Yapıştırma)

Projemizi açtık, zeki çevirmenimizi (yapay zeka) bağladık. Sıra okuyacağımız romanı programa indirtmekte.

1. Sağ menüdeki "İndirmeyi Başlat" butonuna tıklayın.
2. Tarayıcının açılmasını ve girdiğiniz linkin açılmasını bekleyin.
3. Eğer cloudfire koruması varsa, doğrulamayı yapın ve 1. bölüme geldiğinizden emin olun.
4. Uygulama üzerinden "İçerik 1. Bölümü Açıldı" butonuna tıklayın.
5. İndirmeyi yapacağınız siteyi seçin. indirme otomatik başlayacaktır. Tamamlandığında açılan pencereden "Bölümleri ayır" tıkladığınızda indirilen bölümler ayrı ayrı listelenecektir.


[Görsel-5 - Link Yapıştırma ve İndirme Butonu]
> **Görsel Ekleme Talimatı:** Sağ taraftaki URL yapıştırma çubuğu, altındaki site (kazıyıcı) seçim menüsü ve mavi renkli kocaman "Başlat" butonunun yakından çekilmiş oklarla gösterilmiş bir görüntüsü.

---

## 7. Promt Generator Nedir?
Çeviri yaptırmak için  bir promt'a ihtiyacımız vardır. Promt, yapay zekaya ne yapması gerektiğini söyleyen bir komuttur. Promtunuz yok ise  üzülmeyin. Programın sağ panelinde "Proje Ayarları" içerisinde "Promt Generator" butonu ile oluşturabilirsiniz.

### 7.1. Promt Generator Kullanımı
- **1. Aşama**: "Bölüm örnekleme sayısı" kısmına kaç bölümü okumasını istediğinizi yazın. Başlangıç olarak 2 yazmaktadır. Bu baştan, ortadan ve sondan 2 şey bölüm alarak bunları birleştirip hikayeye uygun promt üretmesini sağlamak için kullanacaktır. Sayı çok fazla olursa fazla token harcayacaktır.
- **2. Aşama**: Promt Üret butonuna tıklayın. 
- **3. Aşama**: Promtlar üretildikten sonra 3 farklı promt üretilecektir (Birebir, Doğal, Dengeli). Bu promtlardan size en uygun olanı seçin.
- **4. Aşama**: "Seçileni Kaydet ve Kullan" butonuna tıklayın. 

Artık hikayeye özel optimize edilmiş promt ile çeviri yapabilirsiniz.
[**İpucu:** Eğer terminoloji çıkarma ile çok sayıda terminoloji çıkartacaksanız, promt içerisindeki 'Terminoloji: ]' kısmını silmeyi unutmayın!]
[Görsel-6 - Promt Generator Ekranı]
> **Görsel Ekleme Talimatı:** Promt Generator penceresinin resmi. "Bölüm örnekleme sayısı" kısmına kaç bölümü okumasını istediğinizi yazın. Başlangıç olarak 2 yazmaktadır. Bu baştan, ortadan ve sondan 2 şey bölüm alarak bunları birleştirip hikayeye uygun promt üretmesini sağlamak için kullanacaktır. Sayı çok fazla olursa fazla token harcayacaktır. "Promt Üret" butonuna tıklayın. 


---

## 8. İsimler Değişmesin Diye Ne Yapmalıyım? (Terminoloji)

Yapay zeka çok zekidir ama roman okumadığı için bağlamı bazen kaçırır. Erkek bir karaktere "O" denildiği için İngilizce metinlerde bazen "kadın" çevirisi yapabilir. Veya "Kılıç Şehri" ismini bir bölümde "Sword City", diğer bölümde "Kılıç Kent" diye çevirip keyfinizi kaçırabilir. Bunu engellemek çok basittir:

1. Sağ menüden **"YZ İle Terminoloji Üret"** Butonuna tıklayın. Burası kitabın "Kişisel Sözlüğüdür".
2. **Peki yüzlerce karakteri ben nasıl yazacağım tutacağım?**: Yazmayacaksınız! "YZ ile Terminoloji Çıkar" butonu, programa "Bana 1. ve 5. bölümler arasını önden bir oku ve içindeki isimleri bul" dersiniz. Yapay zeka tüm karakter ve mekan isimlerini bulup bu sözlüğe kendisi ekler.
3. Artık çeviriyi başlattığınızda program önce bu sözlüğe bakar ve isimleri asla yanlış çevirmez!

**[*(Uyarı: Bu işlem yapay zeka kullanım limitlerinizi tüketir, buna dikkat edin. https://aistudio.google.com/usage adresinden kullanım limitlerinizi kontrol edebilirsiniz.)*]**
[Görsel-7 - Terminoloji (Sözlük) Ekranı]
> **Görsel Ekleme Talimatı:** Terminoloji sekmesindeki tablonun resmi. Sol sütunda "Arthur", sağ sütunda "Artur", Türü kısmında "Karakter" yazan, ayrıca ML (Yapay Zeka) Bulucu butonunun da kırmızı yuvarlak içine alındığı bir tablo eklensin.

---

## 8. Çeviriyi Başlatma (İşin En Zevkli Kısmı)

İndirme bittikten sonra sol taraftaki listede onlarla bölüm göreceksiniz. 

1. Sağ paneldeki **"Çeviriyi Başlat"** butonuna basın.
2. Ekranın en altındaki yeşil çubuk dolmaya başlayacak ve listenin yanında "Çevriliyor..." yazısı belirecektir.
3. Bu esnada arkanıza yaslanıp çayınızı içebilirsiniz. Program büyük dosyaları kendi içinde küçük minik paragraflara böler ki, yapay zekanın kafası karışıp metni uydurmasın.
4. Dosyaların yanındaki yazılar "Tamamlandı" olduğunda o dosya tamamen Türkçeye çevrilmiş demektir!

**[*(İpucu: Eğer gemini-2.5 yada gemini-3.0-flash-preview gibi modelleri kullanıyorsanız "Proje Ayarları"na girip Asenkron Çeviri (Thread) sayısını "2" yapabilirsiniz. Ayrıca eğer gemma-4-30b-it gibi modelleri kullanıyorsanız bu ayarı "10" yapın. Bu sayede program 1. bölüm, 2. bölüm ve 3. bölümü aynı anda çevirerek süreyi inanılmaz kısaltır!)*]**
**[*(İpucu: Eğer daha hızlı çeviri istiyorsanız bölümleri birleştirerek çevirmesini sağlayabilirsiniz. Proje ayarları kısmında "Toplu Çeviri(Batch Mode) aktif edebilirsiniz. girilen sınırlama değerleri doğrultusunda bölümleri birleştirir ve çevirir. Bu sayede program 1. bölüm, 2. bölüm ve 3. bölümü birleştirip çevirir. Böylece çeviri süresi kısalır!)*]**

[Görsel-6 - Çeviri Yapılırken Ekran]
> **Görsel Ekleme Talimatı:** Alt kısımdaki yeşil ilerleme çubuğu dolarken ve listede dosyaların yanında sarı renkli "Çevriliyor" ikonlarının/yazılarının bulunduğu ekranın görüntüsü.

---
## 9. Kitabı Bitirmek ve Çıktı Almak (EPUB Oluşturma)

Bütün bölümlerin yanında "Tamamlandı" yazdığını gördünüz, çeviri harika geçti. Peki bu yüzlerce parça dosyayı telefonunuza nasıl aktaracaksınız?

1. Listeden çevirisi biten (Tamamlandı yazan) tüm bölümleri seçin.
2. Sağ paneldeki **"EPUB Olarak Kaydet"** butonunu göreceksiniz.
3. Buna tıkladığınızda program bu bölümleri arka arkaya ekler, sanki bir matbaa gibi size tek bir "E-Kitap" dosyası verir.
4. Projenin dosyalarının listesinde en üstte birleştirdiğiniz dosyayı bulabilirsiniz. Sağ tıklayıp klasörü aç dediğinizde birleştirilmiş dosyayı görebilirsiniz.

*(Küçük Bir Detay: Eğer çevrilen dosyada gözünüze batan ufak bir harf hatası olursa, listedeki o dosyanın üzerine program içinden çift tıklayın. Sanki Not Defteri açılmış gibi metin açılır, hatayı silip düzeltip kapatabilirsiniz.)*

[Görsel-8 - Dosya Birleştirme Butonları ve Metin Editörü]
> **Görsel Ekleme Talimatı:** Sağ alttaki "EPUB" ve "Birleştir" butonlarını gösteren, aynı zamanda üzerine çift tıklanmış bir dosyanın ortada açılmış "Text Editor" (Metin Düzenleyici) penceresinin olduğu, yazılara müdahale edilebildiğini gösteren bir ekran görüntüsü.

---

## 10. Korkutucu Görünen Basit Sorunlar

**"429 Kota Aşıldı" uyarısı kırmızı yazıyla çıkıyor, program bozuldu mu?**
Hayır, hiç endişe etmeyin! Bu sadece Google'ın "Bugünlük bana çok soru sordun, biraz yavaşla" deme şeklidir. Program bunu anlar, 1-2 dakika bekler ve kendi kendine devam eder. (Daha önce dediğimiz gibi, birden fazla API şifresi girerseniz hiç beklemeden devam da edebilir).

**Uygulama beyazlaştı, "Yanıt Vermiyor" veya "Dondu" gibi duruyor?**
Bilgisayarınız çok eski olabilir veya binlerce sayfalık devasa bir kitabı tek seferde indirmeye çalışıyor olabilirsiniz. Program aslında arka planda çalışmaya devam ediyordur, sadece size görüntüyü veremiyordur. Kapatmayın (çarpıya basmayın), 1-2 dakika bekleyin, işi bitince düzelecektir.

**Siyah ekranda (terminalde) garip yazılar akıp duruyor, hackleniyor muyum?**
Kesinlikle hayır! :) O ekran, programın "İndirmeyi başardım", "Çeviriyi bitirdim", "Dosyayı kaydettim" diye kendi kendine tuttuğu günlüktür (Log). Arka planda kalsın, sizin o ekranla bir işiniz yok.
