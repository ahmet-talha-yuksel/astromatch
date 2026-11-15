# NASA Data Processing — v2.3

Güncel ekip teslimi: `out/real/features.json` **21 kayıt** içerir (8 Dünya
sahası × 2 ölçek, Jezero × 2, Shackleton × 2, Marius Hills regional).
18 kaydın topoğrafik işlem QA bayrakları açıktır; Jezero ve Marius Hills
skorlamaya kapalıdır. Local Dünya girdileri GLO-30'dur. Regional girdilerde
7 saha SRTMGL30.002, SRTM enlem kapsamı dışındaki Haughton GLO-90 kullanır.
`out/source_transition.json`, 7 eş pencerede SRTM−GLO-90 özellik farklarını
saklar; bu farklar bağımsız doğruluk ölçümü değildir (EGM96/EGM2008 farkı dahil).
Kişi 2 için ham veri gerektirmeyen paket: `out/handoff/kisi2_v2_3.zip`.
ZIP içindeki HANDOFF.md v2.3 okuyucu sözleşmesini açıklar. Motor aynı pencere,
çözünürlük ve yöntemi kontrol etmeli; iki tarafta comparable=true olmayan
ölçütleri dışlamalıdır. JSON zaten v2.3 biçimindedir; elle dönüştürme gerekmez.
Aşağıdaki ilk teslim açıklamaları ve QA anlık görüntüleri denetim bağlamıdır.

Güncel hedef/saha/ızgara dosyalarında `hypsometric_integral`, `roughness_ratio`
ve `curvature_std_per_km` de bulunur. Bunlar aynı analiz penceresinde ölçülmüş
örneklerden türetilir; mevcut skorlar ve altı ölçütün QA kararları korunur.
Tanımlar, ölçüm desteği, null politikası ve yeniden üretim komutları:
[MORPHOLOGY.md](MORPHOLOGY.md).
Measured-only Mars kayıtlarında artık dokuz enterpolasyonlu kontrol ve dokuz
duyarlılık testi vardır; Marius adayı `out/moon_measured/` içindedir. Sıfır pürüz
oranlarına bağlam notları eklenmiştir; sayısal değerler ve eski skorlar korunur.


Bu onay bağımsız doğruluk veya görev uygunluğu doğrulaması değildir. Mock paket
tamamen sentetiktir. `out/salda_jezero/` ve `out/lola_shackleton/` ilk teslim
anlık görüntüleridir; güncel onay durumunu `out/real/` dosyalarından okuyun.
Sözleşme `AstroMatch_AI_Veri_Plani_v2_3.md` §3, §5 ve §7 temelinde uygulanmıştır.

Güncel tarama `out/pilot_expanded/` içindedir: Türkiye'deki başlangıç
10°×10° pilotunun 400 hücresi, Atacama ve İzlanda'da 4'er kontrol hücresi.
408 hücre işlendi; 216 hücre kara maskesi ve ortak topoğrafik karşılaştırma
kontrollerinden geçti. Daha geniş 20–50°D / 25–45°K alanın kalan 2000 hücresi
`not_scanned` olarak açıkça ayrılır. Taranan hücre, otomatik olarak skora uygun
hücre demek değildir; `comparable` ve `quality` ayrıca kontrol edilir.

Türkiye/Atacama SRTMGL30, İzlanda GLO-90 kullanır. Altı aynı pilot penceresinde
kaynak farkı ölçülmüştür (`out/pilot_expanded/source_transition.json`). Yerel
SRTM indirme süresi ölçülmedi; eski GLO-90 süreleri SRTM'ye atanmaz.
`pilot_timing.json` ayrı aşamaları ve üç alanın ölçümlerini içerir.
Global senaryolar koşullu iş yükleridir, kesin süre sınırları değildir.
`operational_decision` muhafazakâr üst senaryodan v2.3 bölgesel kapsamını seçer;
geniş bölgenin veya dünyanın tamamen tarandığı iddia edilmez.
`out/pilot/` önceki 8 hücrelik temel karşılaştırmayı saklar.

Jezero/Marius incelemesi `out/quality_review/target_decisions.json` ve
`out/real/target_quality.json` içindedir. Jezero local'de 106/400, regional'da
583/2500, Marius regional'da 248/2500 analiz hücresinde ölçülmüş kaynak bini
yoktur. Kabalaştırma bu sayıları sıfırlayabilir; kaynak çözünürlüğü ve metrik
kalitesi bu nedenle otomatik doğrulanmaz. Bu üç kayıt kapalı kalır. Kutuptaki
iki Shackleton kaydı dosya/hash bağlı operasyonel QA politikasını geçmiştir.
Shackleton merkezi IAU/USGS katalog merkezidir (−89.67, 129.78); kenar konumu
olarak etiketlenmez. Kaynak polar stereografik, analiz merkezli LAEA ve
1737400 m Ay küresidir. MOLA kaynak küresi 3396000 m korunur.

SRTM dosyaları `raw/` içinde mevcutken yalnızca topoğrafyayı yeniden üretmek
(MODIS katmanını ve tam ortak teslimi yenilemek için aşağıdaki `build_release`
komutunu kullanın):

```sh
processing/.venv/bin/python -m processing.scripts.apply_srtm_sources
processing/.venv/bin/python -m processing.scripts.assemble_release
processing/.venv/bin/python -m processing.scripts.process_dem processing/configs/real_batch.json --output processing/out/real
processing/.venv/bin/python -m processing.scripts.finish_pilot
processing/.venv/bin/python -m processing.scripts.package_handoff
```

Güncel P1 katmanı Haziran 2021 MOD11C3.061 ve MOD13C2.061 dosyalarından
üretilir. 16 Dünya kaydının 14'ünde kalite filtresini geçen NDVI vardır;
diğer ikisi null'dır. NDVI yalnızca `earth_filters.ndvi_mean` içindedir.
Sıcaklıkta 6 gündüz ve 1 gece aylık değer bulunur; aynı piksellerde kaliteyi
geçen gündüz–gece çifti yoktur. `surface_temp_monthly_overpass_difference_c`
null kalır ve günlük Tmax−Tmin olarak sunulmaz. Tüm sıcaklıkların comparable
bayrağı false'tur; topoğrafik onaydan devralınmaz. MODIS ortalamaları yalnızca
kabul edilen CMG piksellerine aittir; örnek alanın yarısından azı geçiyorsa
`quality.environment` bunu açıklar. Yerel 500 m sıcaklık/NDVI ayrıntısı üretilmez.

Ham DEM, counts, QA ve pilot önbellekleri mevcutken, aynı teslimi MODIS ile
birlikte yeniden üretmek için tek komut:

```sh
processing/.venv/bin/python -m processing.scripts.build_release \
  --lst /path/to/MOD11C3.A2021152.061.2021190161921.hdf \
  --ndvi /path/to/MOD13C2.A2021152.061.2021194035425.hdf \
  --accessed-on YYYY-MM-DD
```

Bu komut indirme yapmaz. JSON/Parquet/GeoJSON, heightmap'ler, QA raporları ve
`environment.json` hem `out/real/` altında hem planın doğrudan `out/` yollarında
yayımlanır; `out/mock/` sentetik örnekleri ve `out/pilot/` tarama örneklerini korur.
Kişi 3 için `out/earth_grid.parquet` gerçek 408 ızgara kaydını, `out/coverage.geojson`
2408 hücrenin durumunu taşır. Kişi 2 için `out/real/features.json` veya küçük
ZIP, seçilmiş 21 saha/hedef kaydını sunar. ZIP ve `out/real/earth_grid.parquet`
8 seçilmiş regional Dünya sahasını içerir; bunlar keşif ızgarası değildir.
Kök `features.json` seçilmiş kayıtları, kök Parquet ise tarama kayıtlarını içerir.
Mevcut `earth_grid_rRRR_cCCC` kimlikleri sabittir; yeni koordinat-ID biçimine
geçirilmez. Yerel σ için istenen 300 rastgele GLO-30 `earth_reference` penceresi
bu teslimde yoktur; regional kayıtlar onun yerine sunulmaz.

MOD13C2.061 HDF içindeki gerçek SDS `Legend` üç land/water biti (11–13) ve
iki geospatial biti (14–15) tanımlar. Eski LAADS dosya-spec tablosundaki farklı
yerleşim bu dosyaya uygulanmaz. Kalibrasyon NDVI için DN/10000; MOD11C3 için
DN×0.02−273.15'tir. NoData ve valid_range kalibrasyondan önce uygulanır.
HDF-EOS'ta eksik GridOrigin ve PixelRegistration alanlarının varsayılanları
üst-sol ve piksel merkezidir ([HDF Group tanımı](https://docs.hdfgroup.org/archive/support/products/hdf4_tools/hcr-definition.pdf)).

Diviner P1 için henüz yerel ürün ve eş sıcaklık protokolü yoktur; sıcaklık
skorlaması açılmaz. MEDA GTS, EMIT, Sentinel-2 ve yağış katmanları P2'dir,
edinilmedi ve veri varmış gibi işaretlenmez. USGS doğrulama listesi ve sıralama
raporu Kişi 3'ün sorumluluğundadır; bu modül skor veya kesin negatif üretmez.

## Yeni Mars hedefi denemesi (regional)

`out/mars_candidates/review.json` Phoenix (68.2°K, 234.3°D) ve operatörün
seçtiği güney Arcadia çevresi (40°K, 190°D) merkezlerini kapsar. Aynı MOLA
128 ppd / 50×50 km / 1000 m yönteminde Phoenix 198/2500 (%7.92), Arcadia
514/2500 (%20.56) hücrede ölçülmüş bin içermedi. Her iki aday kapalı kaldı;
T-04 eklenmedi. Bunlar yeraltı buzu veya iniş güvenliği değerlendirmesi değildir.
100–150 local referans penceresi de henüz üretilmedi. Havuz olmadan local σ
motor tarafında açıkça `fixed_default` olarak belgelenmelidir; veriyle
hesaplanmış dağılım parametresi gibi sunulmamalıdır.
Kaynak etiketleri, byte-range ve hash kanıtları bu dizinin retrieval.json
manifestindedir. PNG/metadata ve altı özellik de inceleme için paylaşılır.
Yeniden edinim yalnızca küçük resmî PDS altkümelerini indirir:

```sh
processing/.venv/bin/python -m processing.scripts.probe_mars_candidates --accessed-on YYYY-MM-DD
```

Keşif Parquet'inde `kind="earth_grid"`, `cell_id=region_id` bulunur. Kimlik
biçimi değiştirilmedi. Kişi 2'nin güncel girdileri `out/real/features.json`
ve **`out/earth_grid.parquet`** dosyalarıdır; `out/real/earth_grid.parquet`
8 seçilmiş saha içerir ve 408 hücrelik keşif dosyasıyla karıştırılmamalıdır.

## İlk teslimlerden kalan teknik notlar

Aşağıdaki kronolojik uygulama notları eski teslimlerin durumlarını da içerir.
Güncel sayı, karar ve dosya yolları yukarıdaki teslim açıklamasıdır.

## Üretim ve test

Repo kökünden (bu ortamda Python 3.14 ile doğrulandı):

```sh
python3 -m venv processing/.venv
processing/.venv/bin/pip install -r processing/requirements.txt
processing/.venv/bin/python processing/scripts/generate_mock.py
processing/.venv/bin/python -m pytest processing/tests -q
```

Varsayılan çıktı çalışma dizininden bağımsız olarak `processing/out/mock/` olur.
Alternatif: `--output processing/out/another_mock`. Üretim sırasında ağ kullanılmaz.
Bağımlılıklar tekrarlanabilirlik için sabitlenmiştir.

## Ekiplerin doğrudan okuyacağı dosyalar

`out/mock/` altındaki üretilmiş dosyalar paylaşılabilir teslimdir; tüketicilerin
üretim scriptini çalıştırması gerekmez. Depoya commit/merge edildiğinde diğer
branch'lerde de aynı dosyalar kullanılabilir.

- `features.json`: `{schema_version, synthetic, data_plan_verified, records}` zarfı.
  Her kayıtta §7 ortak alanları ve `schema_version: "2.3"` bulunur.
- `earth_grid.parquet`: yalnızca regional Dünya kayıtları; düz kolonlar.
  Örnek: `slope_median_deg`, `slope_median_deg__status`,
  `slope_median_deg__comparable`. Dünya filtreleri de aynı kolon kuralını izler.
  Eksik sıcaklık/yağış değerleri nullable double'dır, sıfırla doldurulmaz.
  Uyarılar `quality_warnings_json` metin kolonunda taşınır.
- `coverage.geojson`: yalnızca Dünya; 0,5° hücrelerde `status` değerleri
  `scanned`, `not_scanned`, `no_data`. `coverage` ayrı bir kalite alanıdır.
  Taranmayan hücrenin kapsamı bilinmediğinden null'dır; `no_data` için `none`.
- `heightmaps/<region_id>.png` ve yanında `.json`: 16-bit gri tonlamalı raster
  ve ayrı metadata. JSON'daki yollar `out/mock/` dizinine göredir.

```python
import json
from pathlib import Path
import pyarrow.parquet as pq
import numpy as np
from PIL import Image

root = Path('processing/out/mock')
records = json.loads((root / 'features.json').read_text())['records']
grid = pq.read_table(root / 'earth_grid.parquet').to_pylist()
record = records[0]
meta = json.loads((root / record['heightmap']['metadata_path']).read_text())
with Image.open(root / meta['path']) as image:
    pixels = np.asarray(image)
valid = pixels != meta['NoData']
elevations_m = np.where(valid, pixels.astype(float) * meta['scale'] + meta['offset'], np.nan)
```

## Veri sözleşmesi ve yöntem

Kayıtların `region_id` alanları benzersizdir; `body` küçük harfle
`earth`, `mars`, `moon` olur. Salda, Kula, Hassa, Atacama, Jezero ve Shackleton
etiketli test kayıtları local ve regional ölçeklerde sunulur. Koordinatlar
bölge bağlamı içindir; yüzeyler bu sahaların gerçek arazisini temsil etmez.
Her kaydın ve özelliğin `data_status` değeri `mock` olur.

Local: 10×10 km / 500 m; regional: 50×50 km / 1000 m.
Analitik yüzey, kayıt merkezindeki gövde yarıçapına uygun küresel LAEA metrik
koordinat sistemi üzerinde tanımlanır; gerçek raster reprojeksiyonu yapılmaz.
0,5° hücreler yalnızca regional örnek merkezlerini gösterir; özellikler hücre
alanından hesaplanmaz. Tam global ızgara üretildiği iddia edilmez.

`features`: `slope_median_deg`, `slope_p90_deg`, `flat_fraction`,
`tri_median_m`, `relief_m`, `elevation_std_m` ve boş sıcaklık örneği.
Eğim metre aralıklı gradyandan, Riley TRI sekiz komşunun kare farkları
toplamının karekökünden (iç piksellerde medyan), rölyef p95-p5'ten hesaplanır.
Yükseklik standart sapması popülasyon standart sapmasıdır. NoData hesaplamadan
önce NaN ile maskelenir; eğim/komşuluk hesaplamasında geçersiz komşuluğa sahip
pikseller ilgili ölçütten dışlanır. Kenarlarda eğim tek taraflı fark kullanır.

Geçerli topoğrafik değerde `resolution_validated=true` otomatik
`comparable=true` üretir. Kula test kayıtları doğrulama başarısızlığı örneğidir:
false bayrağı ve `quality.warnings` gerekçesi taşır. Doğrulama yalnızca sentetik
ortak ölçek/yöntem testini ifade eder; gerçek DEM doğrulaması değildir.
Eksik değer null ve karşılaştırılamazdır. Sıcaklık protokolü geçilmediği için
sıcaklık null ve false kalır; `comparability_note` gerekçesi vardır.
`ndvi_mean`, `precip_mm_yr`, `land_fraction` sadece Dünya `earth_filters`
alanındadır, her zaman skor dışıdır. Diğer gövdelerde `earth_filters=null`.

Heightmap metadata `offset`, `scale`, `NoData`, maske kuralı, `width`, `height`,
piksel boyutları, CRS, sol üst köşe, DEM kaynağı, metre birimi ve dikey abartma
alanlarını taşır. NoData pikseli **önce** maskelenir. Sonra
`elevation_m = pixel * scale + offset` uygulanır. 0,1 m kuantizasyonun azami
hatası 0,05 m'dir. Özellikler kuantize edilmemiş, maskelenmiş float yüzeyden
hesaplanır. PNG kendi başına coğrafi referans taşımaz.

Kaynak `synthetic analytic surface` olarak yazılır; gerçek MOLA/LOLA/Copernicus
kaynağı kullanılmış gibi gösterilmez. `data_plan_verified=true` yalnızca bu
mock teslimin sağlanan v2.3 planıyla karşılaştırıldığını ifade eder.

## Gerçek DEM okuma altyapısı (0.3.0)

Önce mock denetimi tamamlandı. `scripts/metrics.py` mock ve DEM için ortak
metrik tanımlarını sağlar. `scripts/dem.py` yerel GDAL-okunabilir tek bantlı,
north-up rasteri merkezli LAEA penceresine `WarpedVRT` ile getirir; tüm global
rasteri NumPy dizisine yüklemez. `scripts/process_dem.py` konfigürasyonlu batch,
karşılaştırma kontrolü, JSON/Parquet/GeoJSON ve PNG+metadata çıktısını sağlar.
Çalıştırma repo kökünden modül biçimindedir:

```sh
processing/.venv/bin/python -m processing.scripts.process_dem \
  processing/configs/salda_jezero.example.json --output processing/out/salda_jezero
```

Örnek config **hazır gerçek veri içermez**. Önce `processing/raw/` içine yerel
raster/etiket dosyaları sağlanmalı; gerçek sürüm, erişim tarihi, birim, düşey
referans ve kaynak çözünürlüğü ürün etiketinden doğrulanarak config doldurulmalıdır.
Gösterilen Salda merkezi operatör tarafından analiz alanı olarak kontrol
edilmelidir. PDS3'te `.img` yerine yanındaki `.lbl` açılır; ilişkili dosyalar
birlikte tutulur. PDS4 `.xml` ancak yerel GDAL sürücüsü ürünü destekliyorsa açılır;
PDS4 ve gerçek NASA ürünleri henüz doğrulanmadı. GeoTIFF ve sentetik PDS3 etiket+
binary testleri mevcuttur. LOLA için `configs/lola.example.json` başlangıç
örneğidir; karşılaştırma doğrulaması için aynı batch'e Dünya kaydı eklenmelidir.

MOLA topoğrafya ürünü seçilmelidir: radius, areoid ve counts görüntüleri yükselti
olarak kullanılamaz. LOLA shape/radius ürünlerinde de gerçek etiketin scale/offset
ve referans tanımı doğrulanmalıdır. Bu sürüm radius→yükseklik dönüşümünü otomatik
varsaymaz; gerekirse doğrulanmış metre yükselti rasteri hazırlanmalıdır.
`quantity` alanı `elevation` olmalıdır. MOLA'nın eski GDAL dönüşümlerindeki
olası kayma/ölçek farkı için [kaynak notuna](out/DATA_SOURCES.md) bakın.

Gerçek ürünlerde `georeferencing_verified` ve `source_quality_verified`
varsayılan false'tur. Ürün etiketi/örnekleme kalite kontrolü yapıldıktan sonra
true olarak beyan edilir; bu iki bayrak veri indirme veya kontrol işlemi yapmaz.
Tek başına bu bayraklar yeterli değildir: kaynak çözünürlüğü, gövde yarıçapı,
NoData (en fazla %5), metrik mevcudiyeti ve batch içinde aynı pencere/çözünürlük/
yöntemli Dünya–hedef eşleşmesi de kontrol edilir. Sadece başarılı eşleşmelerin
geçerli topoğrafik özellikleri comparable olur. Ölçek farklıysa false kalır.

İşlem kimliği: `metric-gradient-riley8-p95p5-v1`. Kaynak CRS, band scale/offset,
ürün URL/sürüm/erişim tarihi, düşey referans ve işlem parametreleri provenance
alanında tutulur. Yapay örnekler `synthetic=true` ile mock olarak kalır; gerçek
rasterden hesaplanan değerler derived olur. NDVI veya sıcaklık indirme eklenmedi.
Ham rasterler `raw/`, `cache/` ve raster uzantılarıyla Git dışında tutulur.

İlk gerçek batch'i mock çıktı dizinine yazmayın. `earth_grid.parquet` yalnızca
regional Dünya kayıtlarını içerir; sadece local çalışmada boş kimlik şemalı
Parquet üretilir. `coverage.geojson` bu batch'teki regional Dünya pencerelerinin
merkezlerini gösterir; henüz tam 0,5° tarama pilotu değildir. Merkezler global
ızgaraya snap edilmez. İşlenmeyen global alanlar hakkında sınıf atanmaz.
Batch'ler aynı çıktı dosyalarını yeniden yazar; ayrı denemeler için ayrı
`--output` dizinleri kullanın. CLI çalışma yolları örnek config dosyasına göredir.

Gerçek Salda/Jezero local/regional çıktıları artık `out/salda_jezero/` içinde.
LOLA sonucu aşağıdaki Ay teslimi bölümünde yer alır; global pilot süre ölçümü
ve `pilot_timing.json` henüz üretilmedi.


## Gerçek Salda–Jezero teslimi (2026-11-14)

`out/salda_jezero/` doğrudan okunabilir: dört kayıt, bir regional Dünya Parquet
kaydı, GeoJSON, dört 16-bit PNG+metadata çifti ve `retrieval.json` erişim manifesti.
Mock dosyalar değiştirilmeden ayrı tutulur. `data_status=derived`, `synthetic=false`.
Ancak bu teslim henüz **skorlamaya hazır değildir**: MOLA doğrudan ölçüm destek
kontrolü local/regional ölçekte boş destekli hücreler bulduğu için dört kayıtta da
`resolution_validated=false` ve `comparable=false` korunur. Raster NoData oranı
sıfırdır; bu, kaynakta her hücrenin doğrudan ölçüldüğü anlamına gelmez.
Counts > 0 gözlemli kaynak hücrelerini belirtir; kalan MOLA yüzeyi interpolasyon içerir.
Counts diagnostikleri `quality.sampling` alanındadır; karşılaştırma doğrulamasını
otomatik açmaz. Kaynak dosyanın SHA-256 özeti provenance alanında tutulur.

Ham veriyi yeniden edinmek (ağ erişimi gerekir, yaklaşık 50 MB altında):

```sh
processing/.venv/bin/python -m processing.scripts.acquire_salda_jezero --accessed-on YYYY-MM-DD
processing/.venv/bin/python -m processing.scripts.process_dem \
  processing/configs/salda_jezero.real.json --output processing/out/salda_jezero
```

`YYYY-MM-DD` yerine gerçek erişim tarihini yazın. İlk komut gerçek config'i ve
Git dışında `raw/salda_jezero/retrieval.json` erişim manifestini üretir. İkinci komut manifesti config bağlantısıyla okuyup
çıktı dizinine otomatik kopyalar. Yeniden indirme ham dosyaları ve config'i
günceller; mevcut türetilmiş sonuçları ikinci komut yeniden üretir. Mock üretim
komutu ağ kullanmaz; edinim komutu internet kullanır. TLS doğrulaması açıktır.
Sunucu tam byte-range yanıtı vermezse veya yanıt eksik/büyükse edinim durur.

MOLA coğrafi referans düzeltmesi: yuvarlatılmış MAP_SCALE ile GDAL dönüşümü
yerine, etiket sınırları ve tam 128 ppd açısal grid kullanıldı; PDS'nin resmi
ENVI header piksel aralığı ile çapraz kontrol edildi. Rasterin orijinal değerleri
ve 3396000 m kaynak küresi korunur. Etiket ve header ham klasörde saklanır.
Topografyada 0 m geçerlidir; kaynak header'daki sıfır NoData önerisi uygulanmaz.
Copernicus kaynak portalı ve ürün sürümü [DATA_SOURCES.md](out/DATA_SOURCES.md)
içindedir. Ham büyük rasterler Git'e dahil edilmez.

MOLA için ölçek duyarlılığı incelemesi ve LOLA Ay hedefinin ilk çıktıları
aşağıdaki bölümde sunulmuştur. İlk 0,5° ön pilot aşağıdaki bölümde sunulur; global kapsam kararı henüz verilmedi.

## Ölçek duyarlılığı raporu ve Ay teslimi

`out/salda_jezero/sampling_review.json` aynı fiziksel pencerelerde, iki gövdenin
özelliklerini beşer çözünürlükte yeniden hesaplar. Tekrar üretmek için:

```sh
processing/.venv/bin/python -m processing.scripts.review_sampling \
  processing/configs/salda_jezero.real.json
```

Jezero'da test edilen çözünürlükler arasında her analiz hücresinde doğrudan
ölçümlü kaynak bin desteği ilk kez local **2000 m**, regional **5000 m** ile
bulundu. Bu bir doğruluk/onay kararı değildir. Local 2000 m yalnızca 5×5 grid ve
9 iç TRI hücresi verir. Riley TRI metre cinsinden örnekleme aralığıyla değişir;
ham TRI değişiminden yakınsama iddiası yapılamaz. Rapor delta değerlerini ve
ölçüm desteğini gösterir, config veya comparable bayrağını değiştirmez.
Bir sonraki kalite adımı bağımsız yükseklik/örnekleme doğrulaması ve belirsizlik
incelemesidir; sırf tüm hücrelerde en az bir gözlem var diye skora geçilmez.

LOLA için gerçek `LDEM_75S_240M V2.0` polar ürünü (240 m) alındı. Yerel edinim:

```sh
processing/.venv/bin/python -m processing.scripts.acquire_lola --accessed-on YYYY-MM-DD
processing/.venv/bin/python -m processing.scripts.process_dem \
  processing/configs/lola.real.json --output processing/out/lola_shackleton
```

Kaynak etiket yükseklik için `height_m = DN * 0.5`, gezegensel yarıçap için
`radius_m = DN * 0.5 + 1737400` tanımlar. Edinim scripti metre yükselti bandında
scale=0.5, offset=0 saklar. Genel okuyucu LOLA'nın 1737400 m band offset'ini
yükseklik diye yorumlamayı reddeder. NoData/special değer ve byte uzunluğu
kontrol edilir; 0 DN geçerli yükseltidir. Polar stereografik grid PDS katalog
geometrisinden kuruldu ve gerçek etiketi okuyan GDAL ile aynı olduğu kontrol
edildi: sol üst köşe (-457440, +457440) m, piksel 240 m, Ay küresi 1737400 m.

Gerçek Shackleton merkez seçimi [IAU/USGS kaydındaki](https://planetarynames.wr.usgs.gov/Feature/5450)
-89.67°, 129.78° noktasını kullanır; eski mock koordinatı gerçek konum olarak
kullanılmadı. Yükseltiler referans küreye göredir, Ay equipotansiyel yüzeyine göre
topoğrafya veya Dünya ile mutlak rakım eşitliği değildir. LOLA etiketinin tarif
ettiği interpolasyon için yeni ölçüm desteği/tutarlılık kontrolü aşağıdaki QA
bölümünde yer alır. İlk `out/lola_shackleton/` paketi eski kapalı durumuyla
korunur; güncel `out/real/` paketi onaylı Ay karşılaştırmasını içerir.

İlk ortak paket altı kayıt içeriyordu; aşağıdaki Dünya sahası genişlemesiyle
**12 gerçek kayda** ulaşan ortak paket:
`out/real/`. JSON, Parquet, GeoJSON, 12 PNG+metadata çifti ve dört edinim
manifestini bir arada taşıyan `retrieval.json` içerir. Yeniden üretme:

```sh
processing/.venv/bin/python -m processing.scripts.process_dem \
  processing/configs/real_batch.json --output processing/out/real
```

Birincil edinimler ve aşağıdaki LOLA QA adımlarının ham dosyaları yerelde mevcut olmalıdır. Tüketiciler
hazır küçük çıktıları doğrudan okuyabilir. Paket derived ve gerçek veridir;
**karşılaştırma uygunluğu kayıt bazındadır**: Dünya–Shackleton topoğrafyası
QA kapsamında kullanılabilir; Jezero kapalıdır. İki tarafta da uygun değer ve
comparable=true bulunmayan ölçüte skor verilmemelidir. İlk global tarama ön pilotu aşağıdaki bölümde sunulur. Marius Hills global
LOLA ürünü henüz eklenmedi.

## Minimum dört Dünya sahası

Salda'ya ek olarak Kula, Hassa ve Atacama (Yungay) gerçek GLO-30 verisinden aynı
local/regional yöntemle işlendi. Yeni sahalara özel paket `out/earth_sites/`;
güncel ortak paket `out/real/` artık **12 kayıt** içerir: dört Dünya sahası × iki
ölçek, Jezero × iki ölçek, Shackleton × iki ölçek. Regional Dünya Parquet ve
GeoJSON dosyalarında dört saha vardır. Bunlar global 0,5° tarama hücreleri
değil, detay saha merkezleridir; Kişi 3 bunları global tarama tamamlandı diye
sunmamalıdır. Güncel out/real paketinde Dünya–Shackleton QA onayı vardır;
MOLA ve global pilotun karşılaştırılabilirliği henüz açılmadı.

Kaynak karo seçimi 52×52 km fiziksel LAEA çerçevesinden WGS84'e dönüştürülmüş
sınırlarla yapılır. 50 km analiz penceresine tampon bırakılır; tüm kesişen 1°
karolar birleştirilir. Negatif koordinatlar için floor kullanılır. Bu edinim
aracı yalnızca |enlem|<49° ve tarih çizgisinden uzak seçilmiş sahalar içindir;
global/kutup karolarının değişen doğu-batı aralığı ayrıca ele alınmalıdır.
Mozaik yalnızca bu sınırlar için belleğe alınır, tüm dünya rasteri oluşturulmaz.
Tam karolar önce indirilip `raw/earth_sites/tiles/` içinde Git dışında saklanır.
Her yanıtın SHA-256/ETag/Last-Modified bilgisi erişim manifestinde bulunur.
İndirme başarısızsa sahalar işlenmiş gibi gösterilmez; eksik karoya sıfır atanmaz.

```sh
processing/.venv/bin/python -m processing.scripts.acquire_earth_sites --accessed-on YYYY-MM-DD
processing/.venv/bin/python -m processing.scripts.process_dem \
  processing/configs/earth_sites.real.json --output processing/out/earth_sites
processing/.venv/bin/python -m processing.scripts.combine_configs \
  processing/configs/salda_jezero.real.json processing/configs/lola.reviewed.json \
  processing/configs/earth_sites.real.json --output processing/configs/real_batch.json
processing/.venv/bin/python -m processing.scripts.process_dem \
  processing/configs/real_batch.json --output processing/out/real
```

Kula: Smithsonian GVP'nin volkanik saha referans merkezi (38.58, 28.52).
Yungay: yayımlanmış çalışmanın tek saha noktası (-24.0637778, -69.8805);
bütün Atacama çölünü temsil ettiği veya doğrulanmış negatif sınıf olduğu iddia
edilmez. Hassa: operatörün doğu plato çevresi için seçtiği (36.80, 36.55)
analiz merkezi; araştırma kaynağı bu tam koordinatı vermediği için **doğrulanmış
mağara girişi değildir**. Saha konumu uyarısı her kayıtta taşınır. 500 m
analizden mağara ağzı, tünel içi yapı veya barınak uygunluğu çıkarılamaz.
Koordinatların kaynak/notları `configs/earth_sites.json` ve retrieval manifestinde.

`combine_configs` bağımsız edinim config'lerini okuyup yollarını çıktı config'ine
göre düzenler; aynı `region_id` iki kez gelirse çıktıyı değiştirmeden durur.
Hazır küçük paketleri diğer ekipler ham raster indirmeden okuyabilir.

## 0,5° P0-lite ön pilotu

`out/pilot/` Kişi 3'ün tüketebileceği ilk gerçek, merkezleri global 0,5° ızgaraya
hizalanmış pakettir. `configs/pilot.json` içindeki Türkiye referans kutusu
25–35°D / 30–40°K (10×10°) tutulur; bu alanın tamamı işlenmiş değildir.
Atacama ve İzlanda referans alanlarıyla birlikte 408 hücreden 8'i seçilip
50×50 km LAEA / 1000 m çözünürlükte işlendi. Diğer 400 hücre `not_scanned`.
Hücre poligonu 0,5°'dir; özellikler poligondan değil sabit fiziksel pencereden
hesaplanır. `earth_grid_rRRR_cCCC` kimliği güneybatıdan başlayan sabit satır/sütun
indeksidir; Dünya sahası kimliklerinden ayrıdır.

```sh
processing/.venv/bin/python -m processing.scripts.acquire_pilot \
  processing/configs/pilot.json --accessed-on YYYY-MM-DD
processing/.venv/bin/python -m processing.scripts.run_pilot \
  processing/raw/pilot/acquisition.json --output processing/out/pilot
```

Edinim NASA CMR üzerinden önce SRTMGL30.002 indirme bağlantısını bulur ve küçük
bir erişim isteği yapar. 2026-11-14 çalışmasında Türkiye ve Atacama ürünleri
401 döndürdü; bu ortamda kimliği doğrulanmış Earthdata erişimi yoktu. Tercih
edilen veri elde edilmiş gibi gösterilmedi. Pilot GLO-90 alternatifini kullandı;
alçak enlem kayıtlarında `coverage=fallback_dem` ve erişim gerekçesi saklanır.
İzlanda nominal SRTM enlem kapsamı dışındadır. SRTM erişimi mümkünse mevcut edinim
komutu sessizce alternatife geçmez, SRTM adaptörü eklenmesini ister.

GLO-90'ın enleme bağlı farklı doğu-batı piksel aralıkları kontrol edilir;
mozaik daha ince bir doğu-batı ızgarasına zorlanmaz. Ön pilot kutup ve tarih
çizgisi sarma pencerelerini desteklemez. Tile cache'i SHA-256 ile doğrulanır;
cache dosyası değiştirilmişse işlem durur. Cache'den kullanmak yeni bir uzak
indirme/erişim tarihi gibi sunulmaz. Ağ/401/403 hataları veri yokluğuna çevrilmez;
GLO-90 404 karoları işlenmiş sıfır yükselti olarak doldurulmaz.

Paket: `features.json`, düzleştirilmiş `earth_grid.parquet`, `coverage.geojson`,
8 PNG+metadata çifti, `retrieval.json` ve `pilot_timing.json`. Ana zaman raporu
ayrıca `out/pilot_timing.json` konumuna yazılır. `scanned`, `not_scanned`,
`no_data` ayrı durumlardır. Bu gerçek örnekte 8 scanned / 400 not_scanned
vardır; no_data davranışı ayrı testle doğrulanır. Taranmayan alan benzer olmayan
alan değildir. Parquet yalnızca işlenmiş kayıtları taşır.

Zaman raporu indirme, cache yazma/doğrulama, kırpma/mozaik, reprojeksiyon,
özellik çıkarma, kalite/provenance ve PNG dışa aktarmayı ayrı kaydeder. NASA
katalog/erişim sorgusu da ayrıca ölçülür. Kara maskesi henüz sağlanmadığı için
`landmask.duration_s=null`, `earth_filters.land_fraction.value=null` kalır.
Sıfır metre yükselti otomatik deniz sayılmaz. Soğuk/sıcak cache durumları her
karo için yazılır; süreler veri değerleri gibi deterministik olması beklenen
çıktılar değildir. Aynı girdiden özellikler tekrar üretilebilir, süreler değişir.

**Global karar henüz verilmedi:** iki DEM kaynağı arasında ölçülmüş geçiş farkı,
doğrulanmış kara maskesi/kara hücre sayısı ve genişletilmiş örnekleme yoktur.
`estimated_hours_range=null`, karar `deferred` olur. 3/8 saatlik v2.3 karar
kapısı fonksiyon ve sınır testleriyle hazırdır; bu örneğin süresi dünya hücre
sayısıyla çarpılıp kesin tamamlanma tahmini olarak sunulmaz. Tüm pilot özellikler
`derived` ama `comparable=false` kalır. Kod skor/sıralama veya USGS doğrulaması
üretmez; bunlar ilgili ekiplerin sorumluluğundadır.


## Dosyaya ve ölçeğe bağlı LOLA işlem QA kontrolü

`configs/lola_qa_policy.json` v2.3 şemasını değiştirmeden, LOLA için sayısal
kontrol parametrelerini tanımlar. Bu, NASA'nın onayladığı evrensel bir doğruluk
standardı değildir. Eşikler mühendislik amaçlı tutarlılık/regresyon bütçeleridir;
bağımsız gerçek referans veya istatistiksel güven aralığı olarak yorumlanmaz.
MOLA'ya veya sıcaklık protokolüne otomatik uygulanmaz.

Kaynaklar: aynı gözlem dönemi, oluşturma tarihi ve DE421 çerçevesine ait PDS
LDEM_75S_240M V2.0, LDEC_75S_240M V2.1 ve LDEM_75S_120M V2.0. Counts/reference
ürünlerinden sadece Shackleton çevresini kapsayan satır aralıkları alındı.
İki LDEM aynı LOLA gözlemlerini paylaşır; bu **bağımsız doğruluk testi değildir**.
Aynı 10 km/500 m ve 50 km/1000 m analizlerde 240 m/120 m kaynak gridine
hassasiyet, doğrudan ölçümlü bin desteği, NoData ve geometri/yöntem kontrolüdür.

- Her analiz hücresinde ölçümlü kaynak bin payı en az %90, boş counts kapsamı yok.
- NoData en fazla %5; gerçek Shackleton pencerelerinde her iki koşul %100 destek
  ve %0 NoData ile sağlandı.
- Her P0 özellik için `|primary-reference| <= absolute + relative*|reference|`.
  Derece, metre ve oran için eşikler ayrı olup JSON politikada açıkça saklanır.
- Eşit fiziksel pencere, çözünürlük, CRS, yöntem ve düşey referans zorunludur.
- Kaynak GeoTIFF, counts dosyası ve politika SHA-256 özetleri ile analiz
  parametreleri kanıta bağlanır. Kaynak, merkez, çözünürlük, düşey referans,
  metrik, counts veya politika değişirse eski rapor geçersiz olur.
- Kaydedilmiş `passed=true` bayrağına tek başına güvenilmez: kayıtlı sayısal
  kontroller yeniden hesaplanır. Gerçek LOLA için yalnızca boolean ile onay
  verilemez. Aynı ölçekte uygun Dünya karşılığı yoksa comparable yine false olur.

Tekrar üretme (birincil LOLA ve Dünya edinimleri yerelde bulunmalı):

```sh
processing/.venv/bin/python -m processing.scripts.acquire_lola_qa --accessed-on YYYY-MM-DD
processing/.venv/bin/python -m processing.scripts.review_lola_quality
processing/.venv/bin/python -m processing.scripts.combine_configs \
  processing/configs/salda_jezero.real.json processing/configs/lola.reviewed.json \
  processing/configs/earth_sites.real.json --output processing/configs/real_batch.json
processing/.venv/bin/python -m processing.scripts.process_dem \
  processing/configs/real_batch.json --output processing/out/real
```

Rapor `out/quality_review/lola_report.json`; önceki kapalı karşılaştırma
kararlarının JSON anlık görüntüsü `out/quality_review/preliminary_features.json`.
Güncel pakette denetim raporu `out/real/quality/<sha256>.json` içine kopyalanır;
Ay kayıtlarının `quality.qa_validation.report_file` alanı pakete göre doğrudan
okunabilir yolu gösterir. Ham QA rasterleri Git dışında `raw/lola_qa/` içindedir.

Kişi 2 her ölçütte **hedef ve adayın ikisinde de** value dolu ve comparable=true
olmasını kontrol etmelidir. Dünya kayıtları artık Ay ile karşılaştırılabilir
olsa da hedef Jezero seçilince Mars tarafının false bayrağı kullanılmalıdır.
Bu modül sıralama motorunu veya görev güvenliği değerlendirmesini uygulamaz.
