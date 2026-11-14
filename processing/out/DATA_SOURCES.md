# Veri kaynakları — altyapı hazırlığı

Belge erişim tarihi: **2026-11-14**. Henüz gerçek DEM indirilmedi/işlenmedi.
Aşağıdaki bağlantılar resmi ürün ve teknik belge kaynaklarıdır; veri teslimi
veya gerçek ürün sürümü doğrulandığı anlamına gelmez. Mock kaynakları yalnızca
analitik sentetik yüzeylerdir, NASA/ESA ölçümü değildir.

| Kaynak | Resmi bağlantı | Ürün/sürüm durumu |
|---|---|---|
| Copernicus GLO-30 / GLO-90 | [Copernicus Data Space](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) | İndirilecek karonun sürümü henüz belirlenmedi |
| Copernicus teknik belge | [Product Handbook i5.0](https://dataspace.copernicus.eu/sites/default/files/media/files/2024-06/geo1988-copernicusdem-spe-002_producthandbook_i5.0.pdf) | Düşey referans/birim ürünle ayrıca kontrol edilecek |
| MOLA MEGDR | [PDS Geosciences](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html) | Gerçek dosya etiketi/sürümü henüz incelenmedi; 128 ppd topoğrafya hedefleniyor |
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
