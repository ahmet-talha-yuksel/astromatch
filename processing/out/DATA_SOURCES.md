# Veri kaynakları — ilk gerçek Salda/Jezero teslimi

Belge ve veri erişim tarihi: **2026-11-14**. Salda GLO-30 karosu ve Jezero MOLA
altkümesi indirildi, local/regional pencereler işlendi. Ay verisi henüz indirilmedi.
Aşağıdaki bağlantılar ürün ve teknik belge kaynaklarıdır. Gerçek teslimin
ürün/sürüm bilgileri bu belgenin sonunda belirtilmiştir. Mock kaynakları yalnızca
analitik sentetik yüzeylerdir, NASA/ESA ölçümü değildir.

| Kaynak | Resmi bağlantı | Ürün/sürüm durumu |
|---|---|---|
| Copernicus GLO-30 / GLO-90 | [Copernicus Data Space](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) | GLO-30 Public, 2021 sürümü; N37 E029 karosu alındı; GLO-90 alınmadı |
| Copernicus teknik belge | [Product Handbook i5.0](https://dataspace.copernicus.eu/sites/default/files/media/files/2024-06/geo1988-copernicusdem-spe-002_producthandbook_i5.0.pdf) | WGS84 yatay; EGM2008 düşey; metre (Handbook §1.2.1) |
| MOLA MEGDR | [PDS Geosciences](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html) | MEGT44N000HB, product version 2.0; 128 ppd topoğrafya ve counts etiketi incelendi |
| MOLA coğrafi referans uyarısı | [PDS MEGDR/ENVI notu](https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/extras/mola_envi.htm) | GDAL ile çevrilen eski MEGDR ürünlerinin referansında kayma/ölçek farkı bildiriliyor; gerçek ürün kontrolü zorunlu |
| LOLA gridded/polar | [PDS LOLA GDRDEM](https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/Lunar%20Reconnaissance%20Orbiter%20%28LRO%29/LOLA/GDR/GDRDEM.htm) | Gerçek dosya/sürüm henüz seçilmedi |
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
