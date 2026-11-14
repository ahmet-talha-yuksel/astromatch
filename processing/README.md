# NASA Data Processing — v2.3 mock teslimi

Mock paket tamamen sentetiktir. Ayrı `out/salda_jezero/` paketi gerçek
Copernicus/MOLA verilerinden hesaplanmış, kalite incelemesi süren ilk teslimdir.
Sözleşme `AstroMatch_AI_Veri_Plani_v2_3.md` §3, §5 ve §7 temelinde uygulanmıştır.
Planın gerçek veri, pilot zamanlama ve doğrulama teslimleri bu aşamaya dahil değildir.

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
LOLA sonucu, global pilot süre ölçümü ve `pilot_timing.json` henüz üretilmedi.


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

Sıradaki iş MOLA örnekleme boşluklarına uygun daha kaba ortak ölçeği counts
katmanı ve özellik kararlılığıyla değerlendirmek; ardından aynı altyapıyla
LOLA Ay hedefini eklemektir. Pilot/global taramaya henüz başlanmadı.
