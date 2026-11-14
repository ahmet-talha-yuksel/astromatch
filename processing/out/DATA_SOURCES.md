# Veri kaynakları — ilk gerçek Salda/Jezero teslimi

Belge ve veri erişim tarihi: **2026-11-14**. Salda GLO-30 karosu ve Jezero MOLA
altkümesi indirildi, local/regional pencereler işlendi. LOLA güney kutbu verisi de alındı; ayrıntıları aşağıdadır.
Aşağıdaki bağlantılar ürün ve teknik belge kaynaklarıdır. Gerçek teslimin
ürün/sürüm bilgileri bu belgenin sonunda belirtilmiştir. Mock kaynakları yalnızca
analitik sentetik yüzeylerdir, NASA/ESA ölçümü değildir.

| Kaynak | Resmi bağlantı | Ürün/sürüm durumu |
|---|---|---|
| Copernicus GLO-30 / GLO-90 | [Copernicus Data Space](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) | GLO-30 Public, 2021 sürümü; N37 E029 karosu alındı; GLO-90 alınmadı |
| Copernicus teknik belge | [Product Handbook i5.0](https://dataspace.copernicus.eu/sites/default/files/media/files/2024-06/geo1988-copernicusdem-spe-002_producthandbook_i5.0.pdf) | WGS84 yatay; EGM2008 düşey; metre (Handbook §1.2.1) |
| MOLA MEGDR | [PDS Geosciences](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html) | MEGT44N000HB, product version 2.0; 128 ppd topoğrafya ve counts etiketi incelendi |
| MOLA coğrafi referans uyarısı | [PDS MEGDR/ENVI notu](https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/extras/mola_envi.htm) | GDAL ile çevrilen eski MEGDR ürünlerinin referansında kayma/ölçek farkı bildiriliyor; gerçek ürün kontrolü zorunlu |
| LOLA gridded/polar | [PDS LOLA GDRDEM](https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/Lunar%20Reconnaissance%20Orbiter%20%28LRO%29/LOLA/GDR/GDRDEM.htm) | LDEM_75S_240M V2.0, 2017 polar ürünü alındı; global ürün alınmadı |
| Raster okuma/warp | [Rasterio WarpedVRT](https://rasterio.readthedocs.io/en/stable/api/rasterio.vrt.html) | Kurulu sürüm processing/requirements.txt içinde sabit |

## Mevcut işlem parametreleri

- Local 10 km / 500 m; regional 50 km / 1000 m; açıkça kabalaştırılabilir.
- Merkezli LAEA; kaynak CRS'nin küre/elipsoidi korunur. Analiz metre biriminde.
- Average resampling; kaynak piksel boyutundan daha ince örnekleme reddedilir.
- Etiket/band scale ve offset uygulanır; maskeli NoData dönüşüm dışında kalır.
- Eğim: metrik gradyan. TRI: Riley sekiz komşu kare farkları toplamının karekökü,
  iç piksellerde medyan. Rölyef: p95-p5. Standart sapma: popülasyon.
- En fazla %5 NoData: başlangıç işlem kalite eşiği; v2.3 kapsam değişikliği değil,
  kayıtta taşınan muhafazakâr uygulama parametresi.
- Gerçek üründe kaynak kalite ve georeferencing doğrulaması tamamlanmadan
  `resolution_validated` açılmaz. Karşılaştırma için aynı ölçek/yöntemde uygun
  Dünya ve hedef kaydı da gereklidir.

Yerel batch çalıştığında bu dosya yerine çıktı dizinindeki `DATA_SOURCES.md`
her kaydın URL, ürün sürümü, beyan edilen erişim tarihi ve parametreleriyle üretilir.
Hazırlık belgesini korumak için ilk gerçek çalıştırmada ayrı `--output` kullanın.


## Gerçek teslim (2026-11-14)

- Dosyalar: `salda_jezero/features.json`, `earth_grid.parquet`, `coverage.geojson`,
  `heightmaps/` ve `retrieval.json`.
- Copernicus kaynağı: [resmi Data Space ürün portalı](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM),
  [izin verilen AWS dağıtım kaydı](https://registry.opendata.aws/copernicus-dem/).
  GLO-30 Public 2021 release, `Copernicus_DSM_COG_10_N37_00_E029_00_DEM`.
  AWS son değiştirilme tarihi 2022-05-09; gerçek ETag/SHA-256 retrieval dosyasında.
  Karodaki WGS84 referansı ve yaklaşık 1 arc-second piksel aralığı okundu.
  Salda merkez seçimi 37.55°K, 29.67°D; bu bir analiz merkezi, ölçüm istasyonu değildir.
- Jezero merkez seçimi plandaki 18.38°K, 77.58°D'dir; rover iniş noktası değildir.
  PDS3 `MEGT44N000HB` topography ve `MEGC44N000HB` counts kullanıldı.
  Dataset `MGS-M-MOLA-5-MEGDR-L3-V1.0`, product version 2.0.
  Metre, GMM3 (mgm1025) derece/sıra 50 areoidi; planetocentric doğu-pozitif koordinatlar.
  Etiket küre yarıçapı **3396000 m** (genel varsayılan Mars yarıçapı kullanılmadı).
- MOLA'nın 2° çevre altkümesi HTTP byte-range ile alındı; tam 130 MB karo indirilmedi.
  1/128° ızgara köşeleri doğrudan etiketin sınırlarından hesaplandı, PDS'nin düzeltilmiş
  ENVI piksel aralığı ile karşılaştırıldı: yaklaşık **463.0576672 m**.
  ENVI header içindeki `data ignore value = 0` aktarılmadı; 0 m topoğrafya geçerlidir.
- MOLA altkümesinin tamamında ölçümlü kaynak hücresi oranı yaklaşık %31,47.
  Gerçek analiz pencerelerinde counts > 0 destek payı local %37,51 ve regional %34,59.
  Local 400 hücrenin 106'sında, regional 2500 hücrenin 583'ünde doğrudan ölçüm desteği yok.
  Interpolasyon raster boşluğunu kapatır; gerçek çözünürlüğü doğrulamaz.
- Bu nedenle dört kaydın tamamı `derived` fakat eşleşmiş çözünürlük kalite kontrolü
  henüz geçmediğinden `resolution_validated=false`, topoğrafik `comparable=false`.
  Sıralama motorunda skora alınmamalıdır. Bir sonraki bilimsel adım: daha kaba ortak
  analiz ölçeğinin, MOLA ölçüm aralığı ve eğim/TRI kararlılığıyla değerlendirilmesi.
- Copernicus DSM, bitki/yapı ve düzleştirilmiş su yüzeyini içerebilir; Salda göl tabanı
  veya batimetriyi temsil etmez. Uyarı kayıtlarda taşınır; mineral analojisi iddia edilmez.
- Ham dosyalar yalnızca Git dışında tutulan `processing/raw/salda_jezero/` içindedir.
  Küçük işlenmiş teslimler ve HTTP erişim/byte-range/SHA-256 manifesti paylaşılabilir.


## Ölçek incelemesi (2026-11-14)

Tekrar üretilebilir rapor: `salda_jezero/sampling_review.json`.
Counts desteği olmayan hücre sayısı:

| Ölçek | Analiz çözünürlüğü (m) → desteksiz hücre / tüm hücreler |
|---|---|
| Local | 500 → 106/400; 1000 → 9/100; 1250 → 1/64; 2000 → 0/25; 2500 → 0/16 |
| Regional | 1000 → 583/2500; 1250 → 277/1600; 2000 → 55/625; 2500 → 20/400; 5000 → 0/100 |

Bu sonuçlar, 2000/5000 m'nin bilimsel olarak doğrulandığı anlamına gelmez.
Ölçüt duyarlılıkları raporda bulunur; TRI'nin ölçeğe bağımlılığı ve küçük local
örneklem nedeniyle otomatik yakınsama/karşılaştırılabilirlik kararı verilmedi.
Varsayılan local/regional çözünürlükler ve comparable=false bayrakları korundu.

## LOLA güney kutbu (2026-11-14)

- [Resmi ürün etiketi](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_75s_240m.lbl)
- [Resmi polar projeksiyon kataloğu](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/catalog/dsmap_polar.cat)
- `LRO-L-LOLA-4-GDR-V1.0`, `LDEM_75S_240M`, product V2.0, oluşturma 2017-06-15.
- 3812×3812, signed little-endian int16, 240 m/piksel; polar stereografik,
  -90° merkez, 0° meridyen, 1737400 m küre, DE421 mean Earth/polar axis çerçevesi.
- Doğrulanan dönüşüm: yükseklik = DN × 0.5 m. Etiketteki +1737400 m OFFSET
  yalnızca gezegensel yarıçap dönüşümüne aittir; yükseklik bandına eklenmedi.
- Etiketin tam MAP_SCALE'i ve projeksiyon kataloğunun merkezli piksel kaydı
  kullanıldı. GDAL PDS okuyucusuyla sol üst köşe ve piksel boyutu eşleşti.
- Shackleton analiz merkezi -89.67°, 129.78°; [IAU/USGS koordinat kaydı](https://planetarynames.wr.usgs.gov/Feature/5450).
  Katalogda farklı kontrol ağlarına ait eski merkezler de bulunur; kullanılan
  merkez kayıt/config içinde açıkça saklanır, kesin saha sınırı iddia edilmez.
- Local 10 km / 500 m, regional 50 km / 1000 m; her iki pencerede raster NoData=0.
  Ürün ground-track interpolasyonu içerir; örnekleme/etkin çözünürlük kalite
  incelemesi beklediği için source_quality_verified=false ve comparable=false.
- İndirme boyutları, HTTP ETag/Last-Modified ve SHA-256:
  `lola_shackleton/retrieval.json`. Ham label/IMG/catalog ve yükseklik GeoTIFF'i
  Git dışında `processing/raw/lola_shackleton/` içinde tutulur.
- Ortak altı kayıtlı çıktı: `real/`; Ay özel çıktısı: `lola_shackleton/`.
  Her ikisi de küçük işlenmiş dosyalardır; gerçek NASA ölçümünden hesaplanmış
  derived özellikler içerir. Hazır skor veya bilimsel doğrulama sonucu değildir.


## Minimum dört Dünya sahası — genişleme (2026-11-14)

Salda'ya Kula, Hassa ve Atacama/Yungay eklendi. Resmi Copernicus Data Space
ürününün AWS GLO-30 Public 2021 dağıtımı kullanıldı. Yedi gerçek COG karosu
indirildi; 52 km tamponlu çerçevelerde kırpılıp mozaiklendi. Karoların tam URL,
ETag, Last-Modified, byte boyutu ve SHA-256 bilgileri `earth_sites/retrieval.json`
içindedir; işlem sonucu mozaiklerin hash ve koordinat kaynakları da kaydedilir.

| Saha | Analiz merkezi (enlem, boylam) | Konum dayanağı |
|---|---|---|
| Kula | 38.58, 28.52 | [Smithsonian GVP](https://volcano.si.edu/volcano.cfm?vn=213000), volkanik saha referansı |
| Hassa | 36.80, 36.55 | Operatör seçimi; [Hassa lav tünelleri araştırması](https://dergipark.org.tr/tr/download/article-file/4045946) bölgesel bağlam sağlar, bu koordinatı doğrulamaz |
| Atacama/Yungay | -24.0637778, -69.8805 | [Özgün saha çalışması, Materials and Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC8859261/), tek örnekleme alanı |

Hassa bir mağara girişi noktası olarak sunulmaz ve Ay güney kutbu için lav tüpü
varsayılmaz. Atacama kontrol sahası doğrulanmış negatif analog sınıfı değildir.
Copernicus DSM verisinden kimyasal/mineral veya biyolojik eşdeğerlik çıkarılmaz.

Üç yeni sahanın iki ölçeğinde NoData=0: 10 km/500 m, 50 km/1000 m. Aynı metrik
fonksiyonları, average reprojeksiyon ve EGM2008/metre yükselti birimi kullanıldı.
GLO-30 regional sonuçlar detay saha karşılaştırma örnekleridir; global P0-lite
SRTMGL30/GLO-90 ızgarası henüz üretilmedi. Kaynak farkı global pilottan önce
karşılaştırılmalı ve uyarılara yazılmalıdır.

`out/real/` artık 12 gerçek kayıt, 4 regional Dünya Parquet satırı, 4 Dünya
kapsama geometrisi ve 12 PNG+metadata çifti içerir. Gerekli MOLA/LOLA kalite
kontrolü tamamlanmadığı için kayıtların comparable bayrakları false kalır.
Hazır dosyalar modül entegrasyonunda okunabilir; skor üretmek için kullanılamaz.
