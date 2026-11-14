# Veri kaynakları — v2.3 işleme ve QA teslimleri

Güncel durum: 21 gerçek kayıt, 18 topoğrafik işlem QA onayı. Local Dünya
GLO-30; regional Dünya yedi sahada SRTMGL30.002, Haughton GLO-90.
Pilot Türkiye/Atacama SRTMGL30, İzlanda GLO-90 kullanır; 8 hücre işlendi.
Kara maskesi ESA WorldCover 2021 v200 ile örnekleme QA kontrolünden geçti.
`source_transition.json` yedi eş pencerenin kaynak duyarlılığını saklar.
Global süreler koşullu senaryolardır; daha geniş tarama yapılmadı.
Aşağıdaki ilk edinim ve ön inceleme notları tarihsel bağlamdır; güncel
bayraklar `real/features.json` ve `pilot/pilot_timing.json` içindedir.

Belge ve veri erişim tarihi: **2026-11-14**. Salda GLO-30 karosu ve Jezero MOLA
altkümesi indirildi, local/regional pencereler işlendi. LOLA güney kutbu verisi de alındı; ayrıntıları aşağıdadır.
Aşağıdaki bağlantılar ürün ve teknik belge kaynaklarıdır. Gerçek teslimin
ürün/sürüm bilgileri bu belgenin sonunda belirtilmiştir. Mock kaynakları yalnızca
analitik sentetik yüzeylerdir, NASA/ESA ölçümü değildir.

| Kaynak | Resmi bağlantı | Ürün/sürüm durumu |
|---|---|---|
| Copernicus GLO-30 / GLO-90 | [Copernicus Data Space](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) | Public 2021; GLO-30 local sahalar, GLO-90 kapsam dışı Haughton ve İzlanda pilotu; diğer regional sahalar için kaynak karşılaştırması |
| SRTMGL30.002 | [NASA Earthdata](https://www.earthdata.nasa.gov/data/catalog/lpcloud-srtmgl30-002) | Kullanıcının Earthdata ZIP'lerinden 4 karo CRC/SHA-256 ile içe alındı; 7 regional sahada ve 6 pilot hücresinde etkin; EGM96, 30 arc-second |
| Copernicus teknik belge | [Product Handbook i5.0](https://dataspace.copernicus.eu/sites/default/files/media/files/2024-06/geo1988-copernicusdem-spe-002_producthandbook_i5.0.pdf) | WGS84 yatay; EGM2008 düşey; metre (Handbook §1.2.1) |
| MOLA MEGDR | [PDS Geosciences](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html) | MEGT44N000HB, product version 2.0; 128 ppd topoğrafya ve counts etiketi incelendi |
| MOLA coğrafi referans uyarısı | [PDS MEGDR/ENVI notu](https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/extras/mola_envi.htm) | GDAL ile çevrilen eski MEGDR ürünlerinin referansında kayma/ölçek farkı bildiriliyor; gerçek ürün kontrolü zorunlu |
| LOLA gridded/polar | [PDS LOLA GDRDEM](https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/Lunar%20Reconnaissance%20Orbiter%20%28LRO%29/LOLA/GDR/GDRDEM.htm) | LDEM_75S_240M V2.0, polar 120 m QA referansı ve LDEM_128 V3.0 Marius Hills altkümesi/counts alındı |
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
Bu ilk teslimde SRTMGL30/GLO-90 ızgarası henüz üretilmemişti. Kaynak farkı global pilottan önce
karşılaştırılmalı ve uyarılara yazılmalıdır.

`out/real/` artık 12 gerçek kayıt, 4 regional Dünya Parquet satırı, 4 Dünya
kapsama geometrisi ve 12 PNG+metadata çifti içerir. Kalite incelemesi öncesindeki
ilk teslimde tüm comparable bayrakları false tutulmuştu. Güncel out/real
paketinde aşağıdaki LOLA işlem QA incelemesine göre Dünya–Shackleton açıldı;
Jezero kapalı kalır. Önceki kararlar quality_review/preliminary_features.json
anlık görüntüsünde saklanır.

## Gerçek bölgesel 0,5° ön pilot (2026-11-14)

- Öncelikli kaynak: [NASA SRTMGL30.002](https://www.earthdata.nasa.gov/data/catalog/lpcloud-srtmgl30-002),
  [DOI](https://doi.org/10.5067/MEaSUREs/SRTM/SRTMGL30.002).
  Resmi CMR granül araması Türkiye ve Atacama için indirme bağlantısı döndürdü;
  her iki arşiv isteği HTTP 401 ile erişilemedi. Kullanılan katalog URL'leri,
  cevap hash'leri, indirme adresleri ve erişim sonuçları `pilot/retrieval.json`
  içindedir. NASA DEM rasteri bu pilotta indirilmedi.
- Fiilen kullanılan kaynak: Copernicus DEM GLO-90 Public, 2021 release,
  [resmi ürün portalı](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM),
  [AWS dağıtım kaydı](https://registry.opendata.aws/copernicus-dem/),
  [karo/ızgara açıklaması](https://copernicus-dem-90m.s3.amazonaws.com/readme.html).
  Yükseklik EGM2008/metre; kuzey-güney 3 arc-second; doğu-batı aralığı enleme bağlı.
- GLO-90 karolarının URL, ETag, Last-Modified, byte boyutu, SHA-256 ve cache
  durumu erişim manifestinde bulunur. Ham karolar/mozaikler Git dışında
  `processing/raw/pilot/` konumundadır. GLO-30 saha paketleri korunmuştur.
- 408 referans hücre (Türkiye 10×10°, Atacama 1×1°, İzlanda 1×1°); açıkça
  seçilen 8 hücre işlendi, 400 hücre taranmadı. Türkiye/Atacama'da erişilemeyen
  SRTM yerine GLO-90 kullanımı `fallback_dem` ile belirtilir. İzlanda nominal
  SRTM kapsamı dışı örneğidir. Seçilen 8 fiziksel pencerede NoData=0.
- Özellik penceresi 50×50 km merkezli LAEA, analiz 1000 m, average resampling;
  kaynak küre/elipsoidi ve mevcut metrik yöntemi korunur. 0,5° poligon yalnızca
  örnekleme hücresini belirtir. Kaynak dosya hash'i her kayıtta saklanır.
- Kara maskesi elde edilmedi; süre ve land_fraction null'dır. SRTMGL30/GLO-90
  geçiş karşılaştırması yapılmadı. Bu nedenle global süre aralığı/kapsam kararı
  ertelendi; v2.3 kararı verilmiş gibi sunulmaz. Ayrı aşama ölçümleri
  `pilot/pilot_timing.json` ve `pilot_timing.json` içindedir.
- Tüm sayısal özellikler gerçek GLO-90'dan derived, comparable=false'dur.
  Bu ön pilot benzerlik skoru veya doğrulanmış bilimsel keşif değildir.


## Shackleton işlem QA incelemesi — 2026-11-14

- [PDS LDEC_75S_240M etiketi](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldec_75s_240m.lbl):
  V2.1; counts, int16 little endian; aynı 2017-02-02 gözlem bitişi ve 2017-06-15
  oluşturma tarihi. Etiket, karşılık gelen LDEM ile kullanılan gözlem sayısını
  verdiğini açıkça belirtir. Scale=1, offset=0, 0 değeri ölçümsüz bin demektir.
- [PDS LDEM_75S_120M etiketi](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_75s_120m.lbl):
  V2.0; 120 m doğal grid; aynı gözlem dönemi, oluşturma tarihi ve DE421 çerçevesi.
  Yükseklik DN×0.5 m; gezegensel yarıçap offset'i yükseklik hesabına eklenmedi.
- Yeni katmanlar sadece ilgili satır byte-range'leriyle edinildi. URL, SHA-256,
  ETag, Last-Modified ve aralıklar `quality_review/lola_report.json` içindeki
  acquisition bölümünde, orijinal kopya Git dışında raw/lola_qa/retrieval.json'da.
- Her iki Shackleton penceresinde tüm analiz hücrelerinin ölçümlü kaynak-bin
  desteği %100; counts kapsam boşluğu ve DEM NoData sıfırdır.
- Aynı analiz gridinde 240 m/120 m ürün farkları: local eğim medyanı yaklaşık
  0.765°, p90 0.353°, TRI 2.747 m, rölyef 13.820 m; regional karşılıkları
  0.038°, 0.056°, 2.055 m, 0.579 m. Tüm P0 özellikler politikada kayıtlı
  mühendislik tutarlılık bütçesini geçti.
- Politika `configs/lola_qa_policy.json`; bu proje işlem QA parametresidir,
  NASA'nın bağımsız doğruluk standardı veya bilimsel güven aralığı değildir.
  İki ürün aynı altimetri gözlemlerine dayandığı için bağımsız gerçek referans
  doğrulaması olarak sunulmaz. Kontrol onayı yalnızca kayıttaki grid/yönteme aittir.
- Güncel `out/real/` paketi: 8 Dünya + 2 Shackleton kaydında valid topoğrafik
  özellikler comparable=true; 2 Jezero kaydı false. Dosya/ölçek/politika değişince
  kanıt geçersiz sayılır. Rapor paketin quality/ dizininde hash adıyla taşınır.
- Bu inceleme MOLA'nın örnekleme boşluklarını, pilotun kara maskesini veya
  SRTMGL30 erişim sorununu çözmüş sayılmaz. Diğer paketler kendi bayraklarını korur.


## Genişletilmiş teslim ve kara filtresi

Güncel ortak paket 21 kayda genişledi: Meke, Tuz Gölü, Haughton ve Meteor Crater
local/regional; Marius Hills regional eklendi. Dünya regional verileri ayrı
GLO-90 kaynaklarından, local veriler GLO-30'dan üretilir. Marius Hills Pit
merkezi 14.0917°K, 303.2299°D ([LROC atlası](https://lroc.im-ldi.com/atlases/pits/1));
çıktı boylamı -56.7701°'dir. Global LOLA 128 ppd V3.0 height/counts katmanları
kullanıldı; düşük enlem ölçüm boşlukları ve 50 m pitin 1 km gridde çözülmemesi
uyarısı saklanır. MOLA ölçümlü-bin-only duyarlılık raporu quality_review/mola_support.json'dadır.

Pilot kara filtresi ESA WorldCover 2021 v200 sınıf haritasından COG penceresiyle
üretildi. 80 su, diğer geçerli sınıflar kara, 0/bilinmeyen NaN olarak ele alındı.
50/100 m sistematik alt örnekleme farkı ve bilinmeyen alan sınırı kontrol edildi.
Ürün güncel su seviyesi veya batimetri değildir. Kaynaklar pilot/landmask.json
ve [ESA veri sayfası](https://esa-worldcover.org/en/data-access) içinde.
© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium

Global senaryolar 2651 WorldCover karosundaki 95436 olası hücre merkezini üst
aday sayısı olarak kullanır; bunlar kesin kara hücresi sayısı değildir. İki
koşullu iş yükü senaryosu v2.3'ün >8 saat bölgesel dalını önerir. Bu bir kesin
küresel süre tahmini değildir; ön karar ve kısıtlar pilot/global_scenarios.json'dadır.
Kullanıcıdan alınan gerçek SRTMGL30 ZIP'leriyle yedi Dünya sahasında GLO-90
örtüşme karşılaştırması yapılmıştır; sayısal farklar source_transition.json'dadır.
Bu sonraki kaynak katmanı henüz bu teslimin GLO-90 regional kayıtlarının yerine
yayınlanmamıştır; geçiş ayrı kontrol aşamasıdır.

## Canonical published release

# DEM batch provenance

Synthetic fixtures are not NASA/ESA observations. No downloads were performed by this pipeline.

Parameters and CRS are also stored in features.json.

## earth_salda_local

- Status: derived; synthetic: False
- Product/version: copernicus / GLO-30 Public 2021 release; tile last-modified 2022-05-09
- Source: https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N37_00_E029_00_DEM/Copernicus_DSM_COG_10_N37_00_E029_00_DEM.tif
- Accessed on (declared): 2026-11-14
- Input: salda_glo30.tif
- Window: 10 km; analysis: 500 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM2008 orthometric height

## mars_jezero_local

- Status: derived; synthetic: False
- Product/version: mola / MGS-M-MOLA-5-MEGDR-L3-V1.0; product version 2.0
- Source: https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/megt44n000hb.img
- Accessed on (declared): 2026-11-14
- Input: jezero_mola_topography.tif
- Window: 10 km; analysis: 500 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: GMM3 (mgm1025) degree/order 50 areoid

## mars_jezero_regional

- Status: derived; synthetic: False
- Product/version: mola / MGS-M-MOLA-5-MEGDR-L3-V1.0; product version 2.0
- Source: https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/megt44n000hb.img
- Accessed on (declared): 2026-11-14
- Input: jezero_mola_topography.tif
- Window: 50 km; analysis: 1000 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: GMM3 (mgm1025) degree/order 50 areoid

## earth_kula_local

- Status: derived; synthetic: False
- Product/version: copernicus / GLO-30 Public 2021 release; tile identities/ETags in retrieval manifest
- Source: https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM
- Accessed on (declared): 2026-11-14
- Input: kula_glo30.tif
- Window: 10 km; analysis: 500 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM2008 orthometric height

## earth_hassa_local

- Status: derived; synthetic: False
- Product/version: copernicus / GLO-30 Public 2021 release; tile identities/ETags in retrieval manifest
- Source: https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM
- Accessed on (declared): 2026-11-14
- Input: hassa_glo30.tif
- Window: 10 km; analysis: 500 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM2008 orthometric height

## earth_atacama_local

- Status: derived; synthetic: False
- Product/version: copernicus / GLO-30 Public 2021 release; tile identities/ETags in retrieval manifest
- Source: https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM
- Accessed on (declared): 2026-11-14
- Input: atacama_glo30.tif
- Window: 10 km; analysis: 500 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM2008 orthometric height

## earth_meke_local

- Status: derived; synthetic: False
- Product/version: copernicus / GLO-30 Public 2021 release; tile identities/ETags in retrieval manifest
- Source: https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM
- Accessed on (declared): 2026-11-14
- Input: meke_glo30.tif
- Window: 10 km; analysis: 500 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM2008 orthometric height

## earth_tuz_golu_local

- Status: derived; synthetic: False
- Product/version: copernicus / GLO-30 Public 2021 release; tile identities/ETags in retrieval manifest
- Source: https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM
- Accessed on (declared): 2026-11-14
- Input: tuz_golu_glo30.tif
- Window: 10 km; analysis: 500 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM2008 orthometric height

## earth_haughton_local

- Status: derived; synthetic: False
- Product/version: copernicus / GLO-30 Public 2021 release; tile identities/ETags in retrieval manifest
- Source: https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM
- Accessed on (declared): 2026-11-14
- Input: haughton_glo30.tif
- Window: 10 km; analysis: 500 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM2008 orthometric height

## earth_meteor_crater_local

- Status: derived; synthetic: False
- Product/version: copernicus / GLO-30 Public 2021 release; tile identities/ETags in retrieval manifest
- Source: https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM
- Accessed on (declared): 2026-11-14
- Input: meteor_crater_glo30.tif
- Window: 10 km; analysis: 500 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM2008 orthometric height

## earth_salda_regional

- Status: derived; synthetic: False
- Product/version: srtmgl30 / NASA SRTMGL30.002 / SRTM30 v2.1
- Source: https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL30.002/e020n40.SRTMGL30.dem/e020n40.SRTMGL30.dem.zip
- Accessed on (declared): 2026-11-14
- Input: e020n40.tif
- Window: 50 km; analysis: 1000 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM96 orthometric height

## earth_kula_regional

- Status: derived; synthetic: False
- Product/version: srtmgl30 / NASA SRTMGL30.002 / SRTM30 v2.1
- Source: https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL30.002/e020n40.SRTMGL30.dem/e020n40.SRTMGL30.dem.zip
- Accessed on (declared): 2026-11-14
- Input: e020n40.tif
- Window: 50 km; analysis: 1000 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM96 orthometric height

## earth_hassa_regional

- Status: derived; synthetic: False
- Product/version: srtmgl30 / NASA SRTMGL30.002 / SRTM30 v2.1
- Source: https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL30.002/e020n40.SRTMGL30.dem/e020n40.SRTMGL30.dem.zip
- Accessed on (declared): 2026-11-14
- Input: e020n40.tif
- Window: 50 km; analysis: 1000 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM96 orthometric height

## earth_atacama_regional

- Status: derived; synthetic: False
- Product/version: srtmgl30 / NASA SRTMGL30.002 / SRTM30 v2.1
- Source: https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL30.002/w100s10.SRTMGL30.dem/w100s10.SRTMGL30.dem.zip
- Accessed on (declared): 2026-11-14
- Input: w100s10.tif
- Window: 50 km; analysis: 1000 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM96 orthometric height

## earth_meke_regional

- Status: derived; synthetic: False
- Product/version: srtmgl30 / NASA SRTMGL30.002 / SRTM30 v2.1
- Source: https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL30.002/e020n40.SRTMGL30.dem/e020n40.SRTMGL30.dem.zip
- Accessed on (declared): 2026-11-14
- Input: e020n40.tif
- Window: 50 km; analysis: 1000 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM96 orthometric height

## earth_tuz_golu_regional

- Status: derived; synthetic: False
- Product/version: srtmgl30 / NASA SRTMGL30.002 / SRTM30 v2.1
- Source: https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL30.002/e020n40.SRTMGL30.dem/e020n40.SRTMGL30.dem.zip
- Accessed on (declared): 2026-11-14
- Input: e020n40.tif
- Window: 50 km; analysis: 1000 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM96 orthometric height

## earth_haughton_regional

- Status: derived; synthetic: False
- Product/version: copernicus_glo90 / GLO-90 Public 2021 release
- Source: https://dataspace.copernicus.eu/
- Accessed on (declared): 2026-11-14
- Input: earth_haughton_regional.tif
- Window: 50 km; analysis: 1000 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM2008 orthometric height

## earth_meteor_crater_regional

- Status: derived; synthetic: False
- Product/version: srtmgl30 / NASA SRTMGL30.002 / SRTM30 v2.1
- Source: https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL30.002/w140n40.SRTMGL30.dem/w140n40.SRTMGL30.dem.zip
- Accessed on (declared): 2026-11-14
- Input: w140n40.tif
- Window: 50 km; analysis: 1000 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: EGM96 orthometric height

## moon_shackleton_local

- Status: derived; synthetic: False
- Product/version: lola / LRO-L-LOLA-4-GDR-V1.0; LDEM_75S_240M V2.0 (2017)
- Source: https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_75s_240m.img
- Accessed on (declared): 2026-11-14
- Input: lola_polar_height.tif
- Window: 10 km; analysis: 500 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: Height above 1737400 m sphere; not an equipotential surface

- Operational QA policy: lola-grid-qa-1
- Audit report: quality/54aa9ccc836d40d6a83408c540537eeebc244efd539137fd4d50b6136971643d.json
- QA scope: Operational grid/method consistency for terrain comparison; not independent accuracy or mission suitability validation.

## moon_shackleton_regional

- Status: derived; synthetic: False
- Product/version: lola / LRO-L-LOLA-4-GDR-V1.0; LDEM_75S_240M V2.0 (2017)
- Source: https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_75s_240m.img
- Accessed on (declared): 2026-11-14
- Input: lola_polar_height.tif
- Window: 50 km; analysis: 1000 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: Height above 1737400 m sphere; not an equipotential surface

- Operational QA policy: lola-grid-qa-1
- Audit report: quality/54aa9ccc836d40d6a83408c540537eeebc244efd539137fd4d50b6136971643d.json
- QA scope: Operational grid/method consistency for terrain comparison; not independent accuracy or mission suitability validation.

## moon_marius_hills_regional

- Status: derived; synthetic: False
- Product/version: lola / LRO-L-LOLA-4-GDR-V1.0; LDEM_128/LDEC_128 V3.0 (2017)
- Source: https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_128.img
- Accessed on (declared): 2026-11-14
- Input: ldem_128.tif
- Window: 50 km; analysis: 1000 m
- Method: metric-gradient-riley8-p95p5-v1; resampling: average
- Vertical reference: Height above 1737400 m sphere; not an equipotential surface

## MODIS environmental layers

Native global 0.05-degree CMG cells are center-sampled inside each physical LAEA window.
Cosine-latitude weights approximate CMG area; no 500/1000 m temperature or vegetation detail is invented.
Means cover quality-accepted pixels, not an all-weather or whole-month daily-extrema reconstruction.
Per-window acceptance fractions, source QA categories and UTC view hours are in environment.json.
MOD11C3 monthly day/night differences are NOT daily Tmax-minus-Tmin amplitude; temperature comparable=false.
NDVI remains only in earth_filters, with comparable=false. Missing input/data yields null.

- MOD11C3.061: https://doi.org/10.5067/MODIS/MOD11C3.061
  File MOD11C3.A2021152.061.2021190161921.hdf; SHA-256 003e1eaebeb112b7555cdbb86cf5689d82ae99c5738ac284479644634ea82d20; accessed 2026-11-14.
  Period 2021-06-01 through 2021-06-30.
  Product-specific QA/calibration specification: https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD11C3
- MOD13C2.061: https://doi.org/10.5067/MODIS/MOD13C2.061
  File MOD13C2.A2021152.061.2021194035425.hdf; SHA-256 9c238e9a600924794f7c69f520c1c3186e11c81b6782310ac37466c9f544eb01; accessed 2026-11-14.
  Period 2021-06-01 through 2021-06-30.
  Product-specific QA/calibration specification: https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD13C2

## Discovery grid publication

Canonical earth_grid.parquet and coverage.geojson come from pilot_expanded/, with 408 processed grid centers.
features.json and the engine ZIP retain the curated Earth/planetary target release.
Grid acquisition evidence and mask QA: pilot_expanded/retrieval.json and pilot_expanded/landmask.json.
The larger declared regional domain includes explicit not_scanned cells; it is not fully processed.
