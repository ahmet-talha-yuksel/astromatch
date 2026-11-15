# Ölçülmüş örneklerden morfoloji özellikleri

`measured-only-morphology-v1`, mevcut hedef, Dünya sahası ve ızgara
kayıtlarına üç özellik ekler. Bu teslim **yalnızca veri zenginleştirmesidir**:
motorun altı ölçütü, ağırlıkları, referans dağılımları ve mevcut kalite kararları
korunur. Yeni alanlar skor yapılandırmasına eklenmez.

## Pencere ve ölçüm desteği

Her kaydın mevcut merkezli LAEA penceresi, CRS'i ve analiz çözünürlüğü kullanılır:
local 10×10 km / 500 m, regional 50×50 km / 1000 m. Hesaplama, görüntüleme
PNG'lerinden veya görsel olarak doldurulmuş araziden yapılmaz; kaynak hash'i
doğrulanan, kalibre edilmiş ham DEM kullanılır.

Mars ve Ay için kaynak bini **reprojeksiyondan önce `counts > 0`** ile
maskelenir. Analiz hücresi yalnızca ölçülmüş kaynak binlerinin alan ortalamasını
içerir; hiç ölçüm katkısı olmayan hücre NaN kalır. Dünya için kaynak DEM'in
geçerli örnekleri kullanılır; bu işlem ek enterpolasyon veya boşluk doldurma
yapmaz. Kaynak ürünün kendi üretim yöntemini değiştirmez.
Gerçek Mars/Ay girdisinde counts maskesi yoksa yeni alanlar null/false kalır.

3×3 ve 15×15 komşuluklar aynı analiz penceresinden alınır; pencerenin dışından
örnek alınmaz. Bu nedenle fiziksel komşuluk boyutu local ve regional ölçekler
arasında farklıdır. Karşılaştırmada aynı ölçek, pencere, çözünürlük, yöntem ve
ölçüm desteği protokolü aranmalıdır.

## Tanımlar

| Alan | Hesaplama | Birim |
| --- | --- | --- |
| `hypsometric_integral` | `(mean(z) − min(z)) / (max(z) − min(z))`; penceredeki tüm sonlu ölçülmüş hücreler | boyutsuz |
| `roughness_ratio` | Ölçülmüş merkezlerde eşleşen `std(3×3) / std(15×15)` oranlarının medyanı | boyutsuz |
| `curvature_std_per_km` | Yerel karesel yüzey uyumlarından bulunan `z_xx + z_yy` değerlerinin standart sapması × 1000; z, x, y metre | km⁻¹ |

Standart sapmalar popülasyon tanımıyla hesaplanır (`ddof=0`).

Pürüz oranında merkez ölçülmüş olmalı, 3×3 içinde en az 6/9, 15×15 içinde en az
150/225 ölçülmüş örnek bulunmalı ve büyük pencerenin standart sapması pozitif
olmalıdır. Eksikler ve pencere dışı konumlar gözlem sayısına katılmaz.
Önce her merkezde oran alınır, sonra medyanla tek kayıt değeri üretilir.

Eğrilikte ölçülmüş her merkezin 3×3 komşuluğunda en az altı ölçüm gerekir.
`z = ax² + bxy + cy² + dx + ey + f` uyumu altı bağımsız katsayıyı
belirleyebilmelidir; rankı yetersiz komşuluklar elenir. Yerel Laplasyen
`2(a+c)` olup en az iki geçerli merkez gereklidir. Bu tanım eğimle normalize
edilmiş ortalama eğrilik değildir; katsayılar metre koordinatlarına çevrilir.

`curvature_std_per_km` doğrudan tepe sayısı değildir: sabit eğrilikli ideal
bir paraboloidde sıfıra yakın olabilir. Yalnızca düz taban içeren iki aynı
pencerenin ova mı, krater mi olduğunu bu özellikler tek başına belirleyemez;
kenar/topografya analiz penceresine girmelidir.

## Veri sözleşmesi

Sonlu hesaplamalar `data_status: derived`, `comparable: true` olarak eklenir.
Sabit yükseklikte hipsometrik oran ve `0/0` pürüz oranı tanımsızdır; yetersiz
ölçüm desteği de değer üretmez. Bu durumlar `value: null`, `data_status: derived`,
`comparable: false` olur. Sıfır gerçek bir sonuç olabilir: düz yüzeyde eğrilik
standart sapması sıfırdır.

Yeni özelliklerin karşılaştırılabilirlik bayrağı, kaydın
`resolution_validated` durumunu veya altı eski ölçütün onayını değiştirmez.
Eski QA kanıtlarının kapsamı bu altı ölçüttür; yeni alanlar için skorlama
doğrulaması yapılmış sayılmaz.

JSON'da değerler `features`, yöntem ve destek bilgisi `quality.morphology`
altındadır. Parquet'te her alan için nullable double, `__status` ve
`__comparable` sütunları; ayrıca `morphology_metadata_json` bulunur. Metadata
ölçülmüş hücre/merkez sayılarını ve null nedenlerini taşır.

## Güncel çıktılar ve yeniden üretim

- `out/real/features.json` ve `out/features.json`: 21 saha/hedef kaydı.
- `out/mars_measured/features.json`: 3 measured-only Mars hedefi.
- `out/pilot_expanded/features.json`, kök ve pilot Parquet: 408 ızgara penceresi.
- `out/global_expansion/features.json` ve Parquet: 604 ek pencere; birleşik
  Parquet 1012 kayıt.
- `out/validation_sample/features.json` ve `out/earth_grid_validation.parquet`:
  405 doğrulama penceresi.
- `out/real/earth_grid.parquet`: 8 seçilmiş regional Dünya sahası.

Tüm bu kayıtlara üç alan da eklenmiştir. Pilotun 152 sabit yükseklikli
penceresinde hipsometrik ve pürüz oranları null'dır; diğer özellik değerleri
sonludur. Dosya bazında sayılar `out/morphology_report.json` içindedir.
Eski teslim/QA anlık görüntüleri korunur.

Ham dosyalar `raw/` altında mevcutken repo kökünden:

```sh
# Önce kaynakları ve değişecek çıktıları doğrula; dosya yazma.
processing/.venv/bin/python -m processing.scripts.enrich_morphology

# Eski alanları ve Parquet sütunlarını koruyarak güncel çıktıları zenginleştir.
processing/.venv/bin/python -m processing.scripts.enrich_morphology --write
processing/.venv/bin/python -m processing.scripts.package_handoff

processing/.venv/bin/python -m pytest processing/tests -q
```

Zenginleştirme tüm girdileri yazmaya başlamadan doğrular; kaynak hash'i veya
ölçüm maskesi eşleşmezse durur. Tekrar çalıştırma aynı sonucu üretir. Mevcut
hedef QA kararları korunur; dosya hash bağı, eski alanların değişmediği
doğrulandıktan sonra yeni dosyaya taşınır ve önceki hash ayrıca saklanır.

Yeni DEM ve pilot üretim akışları da bu üç alanı üretir. Sentetik kaynaklar
`mock` kalır; gerçek ölçüm olarak etiketlenmez.
