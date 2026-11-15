# AstroMatch AI — 4 Kişilik Teknik Geliştirme Roadmap'i

**Proje:** AstroMatch AI — NASA Space Apps Challenge 2026  
**Ekip:** Ahmetson, David, Melis, Abonman  
**Çalışma modeli:** Paralel geliştirme, bağımsız Git branch'leri  
**Hedef:** Mars ve Ay bölgelerine topografik açıdan benzeyen Dünya bölgelerini gerçek DEM verileriyle keşfetmek, sıralamak ve 3D olarak karşılaştırmak.

---

## 1. EKİP VE GÖREV DAĞILIMI

| Kişi | İsim | Sorumluluk | Branch | Süre |
|---|---|---|---|---|
| 1 | Ahmet | NASA Data Processing & Terrain Features | `feature/data` | 6–8 saat |
| 2 | Davut | Similarity Engine & Ranking | `feature/engine` | 5–6 saat |
| 3 | Melis | Global Discovery & Earth Analogs | `feature/discovery` | 6–7 saat |
| 4 | Mustafa | 3D Terrain & Scientific Validation | `feature/terrain3d` | 6,5 saat |

**Önemli:** Ana frontend geliştirme bu görevlerin kapsamında değildir. Her ekip üyesi kendi modülünü bağımsız geliştirecek ve entegrasyona hazır teslim edecektir.

## 2. PROJENİN AMACI

AstroMatch AI, Mars ve Ay üzerindeki hedef bölgelerin dijital yükseklik modellerini (DEM) Dünya üzerindeki bölgelerle karşılaştıran bir analog keşif sistemidir.

Sistem:

1. NASA ve Dünya DEM verilerini işler.
2. Eğim, pürüzlülük ve rölyef özelliklerini hesaplar.
3. Dünya üzerindeki analog adaylarını belirler.
4. Gaussian similarity ile kriter bazlı benzerlik skorları üretir.
5. Weighted geometric mean ile toplam skor hesaplar.
6. En uygun Dünya analoglarını sıralar.
7. Benzerlik nedenlerini açıklar.
8. Mars/Ay hedefi ile Dünya analogunu 3D görüntüler.
9. Çevrimdışı demo çalıştırabilir.

Topografik benzerlik, jeolojik eşdeğerlik veya görev güvenliği kanıtı değildir.

---

# 3. AHMET — NASA DATA PROCESSING & TERRAIN FEATURES

**Sorumlu:** Ahmetson  
**Branch:** `feature/data`  
**Klasör:** `processing/`  
**Tahmini süre:** 6–8 saat  
**Teknolojiler:** Python, NumPy, Rasterio, GDAL/PROJ, JSON

## Hedef

NASA ve Dünya DEM verilerini ortak fiziksel ölçekte işleyerek diğer modüllerin kullanabileceği topoğrafik özellikler ve yükseklik verileri üretmek.

## Aşama 1 — Veri kaynakları (60 dk)

- [ ] Mars için NASA MOLA DEM kaynağını doğrula.
- [ ] Ay için NASA LOLA DEM kaynağını doğrula.
- [ ] Dünya için SRTM veya Copernicus DEM kaynağını belirle.
- [ ] Mars Jezero Crater koordinatlarını doğrula.
- [ ] Mars pit/skylight hedefini belirle.
- [ ] Ay güney kutbu hedefini belirle.
- [ ] Marius Hills pit koordinatlarını doğrula.
- [ ] DEM ürünlerinin çözünürlüklerini kaydet.
- [ ] Koordinat sistemlerini ve yükseklik referanslarını belgele.

**Çıktı:** Doğrulanmış DEM kaynakları ve örnek raster dosyaları.

## Aşama 2 — DEM preprocessing (90 dk)

- [ ] Rasterio ile DEM dosyalarını aç.
- [ ] Hedef koordinatlara göre pencere kırp.
- [ ] Gerekli projeksiyon dönüşümlerini uygula.
- [ ] Ortak fiziksel pencere boyutu belirle.
- [ ] Ortak analiz çözünürlüğü belirle.
- [ ] DEM verilerini yeniden örnekle.
- [ ] NoData alanlarını maskele.
- [ ] Geçerli veri oranını hesapla.
- [ ] Yatay mesafe birimlerini metre olarak doğrula.

**Çıktı:** Karşılaştırılabilir DEM pencereleri.

## Aşama 3 — Terrain feature extraction (90 dk)

- [ ] Ortalama eğim hesapla.
- [ ] Eğim dağılımını hesapla.
- [ ] Terrain Roughness Index (TRI) hesapla.
- [ ] Local relief hesapla.
- [ ] Yükseklik standart sapmasını hesapla.
- [ ] Geçerli veri oranını kaydet.
- [ ] Metriklerin birimlerini ve hesaplama yöntemlerini belgele.

**Çıktı:** Her bölge için terrain fingerprint.

## Aşama 4 — JSON export (60 dk)

- [ ] `terrain_features.json` oluştur.
- [ ] Hedef ve aday ID'lerini ekle.
- [ ] Veri kaynağı ve çözünürlük metadata'sını ekle.
- [ ] David için örnek feature JSON hazırla.
- [ ] Melis için aday feature formatını hazırla.
- [ ] Abonman için işlenmiş DEM yükseklik verisi sağla.
- [ ] Sentetik verileri açıkça işaretle.

**Çıktı:** Ortak veri sözleşmesine uygun JSON dosyaları.

## Aşama 5 — Test ve teslim (60 dk)

- [ ] DEM boyutlarını doğrula.
- [ ] Fiziksel pencere ölçeğini doğrula.
- [ ] NoData testlerini gerçekleştir.
- [ ] Düz yüzey üzerinde eğim testini yap.
- [ ] Sentetik yüzey üzerinde rölyef testini yap.
- [ ] README hazırla.
- [ ] Örnek verileri Git'e ekle.
- [ ] Pull Request hazırla.

### Ahmet kabul kriterleri

- [ ] En az bir Mars DEM örneği işlenebiliyor.
- [ ] En az bir Ay DEM örneği işlenebiliyor.
- [ ] En az bir Dünya DEM örneği işlenebiliyor.
- [ ] Topografik özellikler hesaplanıyor.
- [ ] JSON çıktısı üretilebiliyor.
- [ ] Diğer modüller verileri okuyabiliyor.

---

# 4. Davut — SIMILARITY ENGINE & RANKING

**Sorumlu:** David  
**Branch:** `feature/engine`  
**Klasör:** `engine/`  
**Tahmini süre:** 5–6 saat  
**Teknolojiler:** Python, NumPy, Pytest, JSON

## Hedef

Mars/Ay hedefleri ile Dünya adaylarının topografik özelliklerini karşılaştıran, açıklanabilir ve ağırlıklandırılabilir benzerlik motoru geliştirmek.

## Aşama 1 — Veri sözleşmesi (30 dk)

- [ ] Ahmetson'un terrain fingerprint formatını incele.
- [ ] Kullanılacak topografik kriterleri belirle.
- [ ] Kriter birimlerini doğrula.
- [ ] Varsayılan ağırlıkları tanımla.
- [ ] Eksik veri kurallarını belirle.

**Çıktı:** Similarity engine giriş sözleşmesi.

## Aşama 2 — Gaussian similarity (90 dk)

Her kriter için:

`S_i = exp(-((x_i - y_i)^2) / (2 * sigma_i^2))`

- [ ] Gaussian similarity fonksiyonunu yaz.
- [ ] Sigma parametrelerini tanımla.
- [ ] Kriter bazlı skorları hesapla.
- [ ] Özdeş değerlerde skorun 1 olduğunu doğrula.
- [ ] Fark arttığında skorun azaldığını doğrula.
- [ ] Geçersiz değerleri kontrol et.

**Çıktı:** `similarity.py`

## Aşama 3 — Weighted geometric mean (60 dk)

Toplam skor:

`S_total = product(S_i ^ w_i)`

Koşul:

`sum(w_i) = 1`

- [ ] Kriter ağırlıklarını normalize et.
- [ ] Ağırlıklı geometrik ortalamayı uygula.
- [ ] Sayısal kararlılık için log-space hesaplama kullan.
- [ ] Negatif ağırlıkları reddet.
- [ ] Tüm ağırlıkların sıfır olduğu durumu kontrol et.
- [ ] Eksik kriterler için açık kural uygula.

**Çıktı:** `weights.py`

## Aşama 4 — Ranking engine (60 dk)

- [ ] Dünya adaylarının toplam skorlarını hesapla.
- [ ] Adayları büyükten küçüğe sırala.
- [ ] Top 5 aday listesi oluştur.
- [ ] Ağırlık değiştiğinde sıralamayı güncelle.
- [ ] Eşit skorlar için deterministik sıralama uygula.
- [ ] Kriter bazlı skorları sonuçta koru.

**Çıktı:** `ranking.py`

## Aşama 5 — Explainability (60 dk)

- [ ] En güçlü benzerlik kriterini belirle.
- [ ] En zayıf benzerlik kriterini belirle.
- [ ] Kriter bazlı açıklamalar üret.
- [ ] Toplam skorun nasıl oluştuğunu göster.
- [ ] Eksik veri uyarılarını ekle.
- [ ] Bilimsel sınırlama açıklaması ekle.

**Çıktı:** `explanations.py`

## Aşama 6 — Test ve teslim (60 dk)

- [ ] Gaussian similarity testleri yaz.
- [ ] Ağırlık normalizasyonunu test et.
- [ ] Ranking doğruluğunu test et.
- [ ] Eksik veri senaryolarını test et.
- [ ] Deterministik sonuçları doğrula.
- [ ] `similarity_results.json` üret.
- [ ] README hazırla.
- [ ] Pull Request hazırla.

### Davut kabul kriterleri

- [ ] Kriter bazlı skorlar hesaplanıyor.
- [ ] Toplam benzerlik skoru hesaplanıyor.
- [ ] Ağırlıklar değiştirilebiliyor.
- [ ] Top 5 sıralaması üretiliyor.
- [ ] Benzerlik nedenleri açıklanıyor.
- [ ] Otomatik testler başarılı.

---

# 5. Melis Çolak — GLOBAL DISCOVERY & EARTH ANALOGS

**Sorumlu:** Melis  
**Branch:** `feature/discovery`  
**Klasör:** `discovery/`  
**Tahmini süre:** 6–7 saat  
**Teknolojiler:** Python, NumPy, Rasterio, GeoJSON

## Hedef

Dünya üzerindeki potansiyel analog bölgeleri keşfetmek, Türkiye'deki öncelikli adayları hazırlamak ve sonuçları benzerlik motoruna aktarılabilir hâle getirmek.

## Öncelikli Türkiye analogları

- Lake Salda
- Kula Volcanic Geopark
- Meke / Acıgöl
- Hassa volcanic terrain
- Tuz Gölü

Bu bölgeler başlangıç adaylarıdır. Bilimsel benzerlikleri verilerle değerlendirilmelidir.

## Aşama 1 — Analog araştırması (60 dk)

- [ ] Salda Gölü koordinatlarını doğrula.
- [ ] Kula koordinatlarını doğrula.
- [ ] Meke / Acıgöl koordinatlarını doğrula.
- [ ] Hassa koordinatlarını doğrula.
- [ ] Tuz Gölü koordinatlarını doğrula.
- [ ] Her bölge için DEM kaynağı belirle.
- [ ] Bölge sınırlarını tanımla.
- [ ] Topografik ve jeolojik benzerlikleri ayır.
- [ ] Bilimsel kaynakları ve sınırlamaları belgele.

**Çıktı:** `turkey_analogs.json`

## Aşama 2 — Global grid (90 dk)

- [ ] Dünya için 0.5° kaba keşif gridi oluştur.
- [ ] Grid hücre merkezlerini hesapla.
- [ ] Kara/su maskesini uygula.
- [ ] Hücrelerin fiziksel boyutlarını hesapla.
- [ ] Enleme bağlı hücre genişliği farklarını dikkate al.
- [ ] Eksik DEM alanlarını işaretle.

**Çıktı:** `global_grid.py`

**Not:** 0.5° grid yalnızca kaba aday keşfi için kullanılmalıdır. Ayrıntılı karşılaştırma eşit fiziksel pencereler üzerinden yapılmalıdır.

## Aşama 3 — Candidate discovery (90 dk)

- [ ] Dünya adaylarının topoğrafik özelliklerini oku.
- [ ] Ahmetson'un feature sözleşmesini kullan.
- [ ] David'in similarity engine'ine uygun girdi üret.
- [ ] Adaylar için benzerlik skorlarını hesapla.
- [ ] Ön eleme uygula.
- [ ] En yüksek potansiyelli adayları belirle.
- [ ] Seçilen adayları ayrıntılı DEM analizine yönlendir.

**Çıktı:** `candidate_search.py`

## Aşama 4 — Türkiye analogları (60 dk)

- [ ] Türkiye adaylarının DEM pencerelerini tanımla.
- [ ] Her bölge için metadata oluştur.
- [ ] Mars/Ay hedefleriyle olası ilişkilerini belgele.
- [ ] Bilimsel sınırlamaları ekle.
- [ ] Öncelikli adayları belirle.
- [ ] Türkiye analog JSON dosyasını tamamla.

**Çıktı:** `turkey_analogs.json`

## Aşama 5 — GeoJSON export (45 dk)

- [ ] Adayları GeoJSON'a dönüştür.
- [ ] Koordinat sırasını doğrula.
- [ ] Hedef ID'lerini ekle.
- [ ] Benzerlik skorlarını ekle.
- [ ] Kaynak metadata'sını ekle.
- [ ] Veri kalitesi alanlarını ekle.

**Çıktı:** `global_candidates.geojson`

## Aşama 6 — Test ve teslim (60 dk)

- [ ] Koordinat geçerliliğini test et.
- [ ] Tekrarlanan adayları temizle.
- [ ] Eksik verili bölgeleri kontrol et.
- [ ] Ranking kararlılığını incele.
- [ ] Kaba ve ayrıntılı sonuçları ayır.
- [ ] README hazırla.
- [ ] Pull Request hazırla.

### Melis kabul kriterleri

- [ ] Türkiye analog listesi hazır.
- [ ] Global kaba keşif algoritması çalışıyor.
- [ ] Aday koordinatları doğrulanıyor.
- [ ] GeoJSON üretiliyor.
- [ ] Adaylar David'in motoruna aktarılabiliyor.
- [ ] Bilimsel sınırlamalar belgelenmiş.

---

# 6. Mustafa — 3D TERRAIN & SCIENTIFIC VALIDATION

**Sorumlu:** Abonman  
**Branch:** `feature/terrain3d`  
**Klasörler:** `terrain3d/`, `validation/`  
**Tahmini süre:** 6 saat 30 dakika  
**Teknolojiler:** React, TypeScript, Vite, Three.js, React Three Fiber, Drei, Python, Rasterio, NumPy

## Hedef

Mars/Ay hedefleri ile Dünya analoglarını gerçek DEM yükseklik verilerinden üretilen 3D yüzeylerde yan yana görüntülemek.

Ana frontend'den bağımsız, yeniden kullanılabilir bileşenler geliştirilecektir.

## Aşama 1 — Bağımsız 3D ortam (30 dk)

- [ ] Terrain3D Docker servisini çalıştır.
- [ ] React ve Vite ortamını doğrula.
- [ ] Three.js canvas oluştur.
- [ ] WebGL desteğini doğrula.
- [ ] Tanılama küpü ve axes helper ile render testini yap.
- [ ] Kamera ve mesh görünürlüğü sorunlarını gider.
- [ ] Basit arazi mesh'ini görünür hâle getir.
- [ ] OrbitControls ile döndürme, kaydırma ve zoom testini yap.

**Mevcut durum:** React/Vite sayfası ve canvas oluşturuluyor ancak 3D yüzeyler henüz görünmüyor. Bu sorun çözülmeden aşama tamamlanmış sayılmamalıdır.

**Çıktı:** Çalışan bağımsız 3D demo.

## Aşama 2 — TerrainData sözleşmesi (60 dk)

- [ ] `TerrainData` TypeScript tipini tanımla.
- [ ] `id` alanını ekle.
- [ ] `name` alanını ekle.
- [ ] `body` alanını ekle.
- [ ] `width` ve `height` alanlarını ekle.
- [ ] `heights` dizisini tanımla.
- [ ] `cellSizeMeters` alanını ekle.
- [ ] `source` alanını ekle.
- [ ] `resolutionMeters` alanını ekle.
- [ ] `verticalExaggeration` alanını ekle.
- [ ] Satır-sütun sırasını belirle.
- [ ] Yükseklik birimini metre olarak sabitle.
- [ ] NoData maskesi kuralını oluştur.
- [ ] Fiziksel pencere metadata'sını ekle.
- [ ] Ahmetson ile veri sözleşmesini doğrula.
- [ ] Sentetik demo JSON oluştur.

**Çıktı:** `terrain.ts` ve örnek JSON.

## Aşama 3 — DEM → JSON converter (90 dk)

- [ ] Rasterio ile GeoTIFF oku.
- [ ] Koordinat sistemini doğrula.
- [ ] Yükseklik birimini kontrol et.
- [ ] Gerekli pencereyi kırp.
- [ ] Ortak fiziksel ölçekte yeniden örnekle.
- [ ] 128×128 veya 256×256 yükseklik matrisi üret.
- [ ] NoData değerlerini maskele.
- [ ] Kaynak metadata'sını kaydet.
- [ ] Çözünürlük metadata'sını kaydet.
- [ ] Gerçek Mars DEM dosyasıyla test yap.
- [ ] Gerçek Ay DEM dosyasıyla test yap.
- [ ] Gerçek Dünya DEM dosyasıyla test yap.

**Çıktı:** `dem_to_json.py` ve terrain JSON dosyaları.

## Aşama 4 — TerrainViewer (90 dk)

- [ ] BufferGeometry tabanlı arazi mesh'i oluştur.
- [ ] Yükseklik değerlerini vertex'lere uygula.
- [ ] Vertex normal hesapla.
- [ ] Kamerayı arazi boyutuna göre konumlandır.
- [ ] OrbitControls ekle.
- [ ] Zoom ve pan kontrollerini doğrula.
- [ ] Dikey abartma kontrolü ekle.
- [ ] Yüksekliğe göre renk paleti uygula.
- [ ] Veri kaynağını göster.
- [ ] Çözünürlüğü göster.
- [ ] Fiziksel ölçeği göster.
- [ ] JSON yükleme durumunu yönet.
- [ ] Hata durumlarını yönet.
- [ ] Geometry cleanup uygula.

**Çıktı:** `TerrainViewer.tsx`

## Aşama 5 — TerrainComparison (60 dk)

- [ ] Mars/Ay hedefini sol panelde göster.
- [ ] Dünya analogunu sağ panelde göster.
- [ ] İki panelde aynı yatay fiziksel ölçeği kullan.
- [ ] Dikey abartma bilgisini göster.
- [ ] Kaynak ve çözünürlük bilgilerini göster.
- [ ] Farklı yükseklik referanslarını doğru ele al.
- [ ] Zaman kalırsa senkronize kamera ekle.

**Çıktı:** `TerrainComparison.tsx`

## Aşama 6 — Entegrasyon ve test (60 dk)

- [ ] `TerrainViewer` bileşenini export et.
- [ ] `TerrainComparison` bileşenini export et.
- [ ] `TerrainData` tipini export et.
- [ ] `src/index.ts` public API oluştur.
- [ ] Bağımsız React import testi yap.
- [ ] Geçersiz JSON testleri ekle.
- [ ] NoData testleri ekle.
- [ ] Büyük mesh performansını kontrol et.
- [ ] Çevrimdışı demo testini yap.
- [ ] Bilimsel sınırlamalar belgesini hazırla.
- [ ] README hazırla.
- [ ] Pull Request hazırla.

### Mustafa kabul kriterleri

- [ ] Gerçek DEM'den JSON üretilebiliyor.
- [ ] Mars, Ay ve Dünya verileri destekleniyor.
- [ ] 3D arazi görünür.
- [ ] Arazi döndürülebiliyor.
- [ ] Yakınlaştırma ve kaydırma çalışıyor.
- [ ] İki arazi yan yana gösteriliyor.
- [ ] Fiziksel ölçek korunuyor.
- [ ] NoData doğru ele alınıyor.
- [ ] Ana frontend'e import edilebiliyor.
- [ ] Çevrimdışı demo çalışıyor.

---

# 7. ORTAK VERİ SÖZLEŞMELERİ

Geliştirmeye başlamadan önce üç temel veri formatı netleştirilecektir.

### 1. terrain_features.json

**Üreten:** Ahmetson  
**Kullanan:** David, Melis

İçerik:

- Target/candidate ID
- Topografik özellikler
- Özellik birimleri
- Veri kaynağı
- Çözünürlük
- Geçerli veri oranı

### 2. similarity_results.json

**Üreten:** David  
**Kullanan:** Melis, backend

İçerik:

- Target ID
- Candidate ID
- Kriter bazlı skorlar
- Toplam skor
- Ağırlıklar
- Ranking
- Açıklamalar

### 3. terrain_heightmap.json

**Üreten:** Ahmetson / Abonman converter  
**Kullanan:** Abonman

İçerik:

- ID ve isim
- Gezegen/gök cismi
- Width ve height
- Heights
- Cell size
- NoData maskesi
- Kaynak
- Çözünürlük
- Fiziksel pencere
- Dikey abartma
- Real/synthetic veri etiketi

---

# 8. EKİP İÇİ ENTEGRASYON

## Entegrasyon 1 — Ahmetson → David

Ahmetson'un terrain fingerprint çıktısı David'in similarity engine'i tarafından okunacaktır.

**Test:** Bir hedef ve bir Dünya adayı için benzerlik skoru hesaplanmalı.

## Entegrasyon 2 — Ahmetson + David → Melis

Melis'nin Dünya adayları Ahmetson'un feature formatını kullanacak ve David'in motoruyla skorlanacaktır.

**Test:** Birden fazla Dünya adayı sıralanmalı.

## Entegrasyon 3 — Ahmetson → Abonman

Ahmetson'un işlediği DEM verileri Abonman'ın 3D modülüne aktarılacaktır.

**Test:** Gerçek yükseklik matrisi 3D mesh olarak görüntülenmeli.

## Entegrasyon 4 — Tüm ekip → Backend

Backend aşağıdaki verileri sunabilmelidir:

- Hedef bölgeler
- Dünya adayları
- Benzerlik skorları
- Açıklamalar
- Terrain JSON verileri

Ana frontend entegrasyonu, ortak API ve modül export'ları üzerinden yapılacaktır.

---

# 9. PARALEL ÇALIŞMA TAKVİMİ

| Zaman | Ahmetson | David | Melis | Abonman |
|---|---|---|---|---|
| 0:00–0:30 | Veri sözleşmesi | Veri sözleşmesi | Veri sözleşmesi | Veri sözleşmesi |
| 0:30–2:00 | DEM preprocessing | Gaussian similarity | Analog araştırması | 3D render ve veri tipi |
| 2:00–3:30 | Feature extraction | Weighted scoring | Global discovery | DEM converter |
| 3:30–5:00 | JSON export | Ranking ve explainability | Türkiye analogları | TerrainViewer |
| 5:00–6:30 | Veri entegrasyonu | Engine testleri | GeoJSON ve testler | TerrainComparison |
| 6:30–8:00 | Son doğrulama | Entegrasyon desteği | Entegrasyon desteği | Test ve teslim |

Süreler hedef niteliğindedir; veri temini ve hata çözümü ek zaman gerektirebilir.

---

# 10. GIT VE ENTEGRASYON KURALLARI

### Ahmetson

Branch: `feature/data`

Yalnızca `processing/` ve üzerinde anlaşılan ortak veri sözleşmelerini düzenler.

### David

Branch: `feature/engine`

Yalnızca `engine/` ve üzerinde anlaşılan ortak veri sözleşmelerini düzenler.

### Melis

Branch: `feature/discovery`

Yalnızca `discovery/` ve üzerinde anlaşılan ortak veri sözleşmelerini düzenler.

### Abonman

Branch: `feature/terrain3d`

Yalnızca `terrain3d/`, `validation/` ve üzerinde anlaşılan dokümantasyon alanlarını düzenler.

### Ortak kurallar

- [ ] Herkes kendi branch'inde çalışır.
- [ ] Ana frontend koduna müdahale edilmez.
- [ ] Ortak sözleşmeler ekip onayı olmadan değiştirilmez.
- [ ] Büyük DEM dosyaları Git'e eklenmez.
- [ ] API anahtarları ve sırlar commit edilmez.
- [ ] Her modül bağımsız test edilir.
- [ ] Pull Request ile entegrasyon yapılır.
- [ ] Merge öncesi testler çalıştırılır.
- [ ] `main` branch'i çalışır durumda tutulur.

---

# 11. ÖNCELİK SIRASI

## P0 — Mutlaka tamamlanacak

- [ ] Ortak veri sözleşmeleri
- [ ] Gerçek DEM preprocessing
- [ ] Terrain feature extraction
- [ ] Gaussian similarity
- [ ] Weighted geometric mean
- [ ] Top 5 ranking
- [ ] Türkiye analogları
- [ ] Çalışan TerrainViewer
- [ ] TerrainComparison
- [ ] Bir Mars ve bir Ay uçtan uca örneği
- [ ] Çevrimdışı demo

## P1 — Zaman kalırsa

- [ ] Kapsamlı global aday keşfi
- [ ] Ranking stability analizi
- [ ] Gelişmiş açıklamalar
- [ ] Ek gerçek DEM örnekleri
- [ ] Genişletilmiş otomatik testler

## P2 — Opsiyonel

- [ ] Senkronize 3D kameralar
- [ ] Gelişmiş renk paletleri
- [ ] Ek topografik ölçümler
- [ ] Görsel efektler

---

# 12. SON TESLİM KONTROL LİSTESİ

### Ahmetson

- [ ] DEM preprocessing çalışıyor.
- [ ] Mars, Ay ve Dünya verileri işleniyor.
- [ ] Terrain features hesaplanıyor.
- [ ] JSON ve metadata teslim edildi.
- [ ] Testler başarılı.

### David

- [ ] Gaussian similarity çalışıyor.
- [ ] Weighted geometric mean çalışıyor.
- [ ] Ranking çalışıyor.
- [ ] Explainability çalışıyor.
- [ ] Testler başarılı.

### Melis

- [ ] Türkiye analogları hazır.
- [ ] Global kaba keşif çalışıyor.
- [ ] GeoJSON çıktıları hazır.
- [ ] Adaylar similarity engine'e aktarılıyor.
- [ ] Testler başarılı.

### Abonman

- [ ] 3D render çalışıyor.
- [ ] DEM converter çalışıyor.
- [ ] TerrainViewer hazır.
- [ ] TerrainComparison hazır.
- [ ] NoData ve ölçek testleri başarılı.
- [ ] Çevrimdışı demo çalışıyor.

### Ortak proje

- [ ] Dört modül birbirleriyle uyumlu.
- [ ] Backend entegrasyonu çalışıyor.
- [ ] En az bir Mars ve bir Ay senaryosu uçtan uca çalışıyor.
- [ ] Gerçek ve sentetik veriler açıkça ayrılıyor.
- [ ] Bilimsel sınırlamalar belgelenmiş.
- [ ] README ve çalıştırma talimatları hazır.
- [ ] Docker ile demo başlatılabiliyor.
- [ ] Pull Request'ler kontrol edilip birleştirilmiş.

---

# 13. PROJENİN TAMAMLANMA TANIMI

AstroMatch AI, aşağıdaki dört bileşen birlikte çalıştığında teknik olarak tamamlanmış kabul edilecektir:

**Ahmetson:** Gerçek DEM verilerini işler ve topoğrafik özellikleri üretir.

**David:** Hedef ve adayları karşılaştırır, benzerlik skorlarını hesaplar ve sıralar.

**Melis:** Dünya üzerindeki analog adaylarını keşfeder ve haritalanabilir veri üretir.

**Abonman:** Gerçek DEM yükseklik verilerini 3D görüntüler, hedef ve analogları yan yana karşılaştırır ve bilimsel doğrulamayı gerçekleştirir.

**Nihai hedef:** Gerçek verilere dayanan, açıklanabilir, bilimsel sınırlamaları açık ve çevrimdışı gösterilebilen çalışan bir AstroMatch AI demosu.