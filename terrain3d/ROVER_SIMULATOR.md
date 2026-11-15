# AstroMatch rover simülatörü

Explore surface içindeki **Rover**, kaynak DEM üzerinde altı tekerlekli sürüş
sağlar. NASA MER kaynaklarından alınan araç referansları ile simülasyonda
varsayılan parametreler aşağıda ayrı belirtilmiştir. Bilimsel arazi özellikleri,
measured-only maskeler ve karşılaştırma skorları değiştirilmez.

## Kullanım

**W/S:** ileri/geri. **A/D:** direksiyon. **Space:** fren. **Shift:** eğitim
profilinde düşük hız. **P:** duraklat/devam et. Ekrandaki düğmeler basılı tutmayı
destekler. Kamera sürüklenebilir; Chase ve Mast görüşleri arasında geçilebilir.
Recover rover aracı parsel içindeki ölçülmüş bir alana dik olarak geri koyar.
Gezegen değiştirildiğinde fizik dünyası ilgili yerçekimiyle yeniden oluşturulur.
Arka plana geçen sekme duraklatılır.

| Ayar | Davranış |
| --- | --- |
| MER reference | 0.05 m/s hedef hız sınırı; duruşta hill hold |
| Training (açılış profili, 1×) | 1.8 m/s hedef hız sınırı; Shift ile 0.3 m/s |
| Time | 1× / 5× / 10× / 20×; hız göstergesi her zaman fiziksel m/s |
| Grip | Firm 0.95 / Regolith 0.65 / Loose 0.35; ölçülmüş zemin katsayısı değildir |
| TCS | İstenen çekiş kuvvetini tahmini tekerlek normal yüküyle sınırlar |

Gaz ve hız hedefi kademeli değişir. Tuş bırakılınca motor frenlemesi aracı
yavaşlatır; duruşta hill hold devreye girer. Ters yön tuşu basılı tutulduğunda
önce kontrollü duruş, ardından geri/ileri kalkış gerçekleşir. Hız aşımı tam
freni açıp kapatmak yerine sürekli motor kuvveti düzeltmesiyle karşılanır.

## Fizik ve arazi

- Rapier 0.21.0, sabit **1/120 s** adımla çalışır. Ekran kareleri arasında konum
  ve yönelim yumuşatılır. Zaman hızlandırma fizik adımını büyütmez.
- Fizik dünyası metre, kilogram ve saniye kullanır. Görüntü için normalize
  edilen DEM koordinatları fizik kurulurken gerçek metreye geri çevrilir.
  Rover'ın boyutları ve hızı parselin görüntü ölçeğine bağlı değildir.
- Kaynak DEM üçgenleri sabit çarpışma yüzeyidir. Rover modunda düşey büyütme
  **1×** olur; yükseklik verisinin kendisi değiştirilmez.
- Altı ayrı aşağı yönlü tekerlek ışını; yay/sönümleyici destek; ön ve arka
  tekerleklerde direksiyon; serbest gövde yatış/devrilme hareketi vardır.
  Zemine zorla yapıştırma veya her karede yüksekliği eşitleme uygulanmaz.
- Dünya/Mars/Ay yerçekimi sırasıyla 9.80 / 3.73 / 1.62 m/s² olarak alınır.
  Tekerlek normal yükü değiştiğinden çekiş ve fren davranışı da değişir.
- Parsel ve NoData denetimi fiziksel bir duvar değildir: geçersiz hareketi son
  güvenli konuma döndüren açık bir geofence kuralıdır. Aracın çevresindeki
  koruyucu kare ayak izi altındaki kaynak hücreleri de denetlenir.
- Görsel olarak doldurulan boşluklar, rastgele çevre parselleri, kaya süsleri ve
  milimetre ölçeğindeki malzeme detayı çarpışma geometrisine eklenmez.

## Kaynaklı parametreler ve varsayımlar

| Parametre | Kullanılan değer | Dayanak |
| --- | --- | --- |
| Kütle | 185 kg | JPL tekerlek karşılaştırması, MER sütunu |
| Tekerlek çapı | 26.2 cm | Aynı tabloda dişler dahil çap |
| Tekerlek genişliği | 21.5 cm | Aynı tablo |
| Diş sayısı | 25 düz diş | Aynı tablo; görsel modelde uygulanır |
| Referans üst hız | 5 cm/s | PDS Spirit instrument-host açıklaması |
| 6 tekerlek, 4 direksiyon | Ön/arka tekerlekler | PDS araç açıklaması |
| Süspansiyon ve gövde | Bağımsız elastik destek, basitleştirilmiş gövde | Mühendislik yaklaşımı |
| Motor, atalet, sürtünme, fren | Simülasyon parametreleri | Görev telemetrisine kalibre edilmemiştir |

MER'in gerçek rocker-bogie bağlantı mekanizması burada birebir çözülmez.
Kayma göstergesi, talep edilen kuvvetin mevcut tutunmaya oranıdır; ölçülmüş
tekerlek kayma oranı değildir. Ray-cast tekerlekler hacimsel lastik/taş teması,
zemine batma, kum akışı veya zemin deformasyonunu çözmez. Özellikle bölgesel,
seyrek DEM'lerde tekerlek boyutundaki engeller kaynak veride bulunmaz.

Bir sonraki bilimsel doğrulama aşaması, aynı bölgede yüksek çözünürlüklü stereo
DEM ve Navcam/Pancam ürünlerinin eşleştirilmesi, uygun hareket telemetrisi ve
zemin ölçümleriyle parametre uyarlaması gerektirir. PDS listesi Mobility
ürünlerini arşiv dışı, talep üzerine erişilebilir olarak ayırır. RMC tek başına
motor kuvveti veya toprak parametresi sağlamaz.

## Gerçek PDS referans ürünü

Arayüzdeki arşiv incelemesi **Opportunity / SITE_FRAME 2** ürününden gelir:

- RVF: `mer1_site_002_master.rvf`
- PDS4 etiket: `mer1_site_002_master.xml`
- Normalize edilen 37 koordinat tanımı:
  [merOpportunitySite002.json](src/reference/merOpportunitySite002.json)
- Kaynak/etiket SHA-256 değerleri, ürün LID'si, erişim tarihi, SIS ve koordinat
  birimi kaynakları JSON içindeki `provenance` alanındadır.

İçe aktarıcı, RVF ile etiketin aynı ürüne ait olduğunu, SITE_FRAME referansını,
sonlu koordinatları ve quaternionları denetler. Aynı RMC için dosyadaki çözüm
önceliğini uygular. Yerel XYZ ofsetleri ve quaternionlar korunur; RMC sırası
**site, drive, IDD, PMA, HGA, isteğe bağlı tweak** olarak saklanır.

Bu ürün gözlem zamanı veya sol sağlamadığından `sol` ve `observation_utc`
boştur. `add_date`, çözümün eklenme zamanıdır. Enlem/boylam, DEM kaydı ve
coğrafi dönüşüm üretilmez. Siteleri birleştirmek için uygun SVF ve çerçeve
dönüşümleri gerekir. Yerel noktaları bağlayan referans çizgisi, ara noktaları
bilinen kesintisiz bir sürüş kaydı anlamına gelmez.

MER örneği Jezero, Phoenix, Arcadia veya Dünya/Ay DEM'lerine bindirilmez.
Bu alanlarda rover ile sürüş, seçili arazide yapılan bir simülasyon alıştırmasıdır.

İndirilen RVF ve PDS4 etiketiyle, depo kökünden:

```sh
processing/.venv/bin/python -m processing.scripts.import_mer_rmc \
  processing/raw/mer_reference/mer1_site_002_master.rvf \
  processing/raw/mer_reference/mer1_site_002_master.xml \
  --accessed-on 2026-11-15 \
  --output terrain3d/src/reference/merOpportunitySite002.json
```

## Kaynaklar

- [JPL: Assessing Mars Curiosity Rover Wheel Damage — MER karşılaştırma tablosu](https://robotics.jpl.nasa.gov/media/documents/fmwi-rankin-2022-0225-final.pdf)
- [PDS: Spirit instrument-host açıklaması ve hız referansı](https://atmos.nmsu.edu/data_and_services/atmospheres_data/MARS/MER/spirit/logs/MER2_INSTHOST.pdf)
- [PDS: orijinal Opportunity Site 002 RVF](https://pds-geosciences.wustl.edu/mer/mer1-m-eng-6-rmc-ops-v1/mer1rm_0xxx/data/mer1_site_002_master.rvf)
- [PDS4 ürün etiketi](https://pds-geosciences.wustl.edu/mer/mer1-m-eng-6-rmc-ops-v1/mer1rm_0xxx/data/mer1_site_002_master.xml)
- [PDS: RMC Master File SIS](https://pds-geosciences.wustl.edu/mer/mer1-m-eng-6-rmc-ops-v1/mer1rm_0xxx/document/rmc_sis.htm)
- [PDS: MER kamera SIS — koordinat ofsetlerinin birimleri](https://pds-imaging.jpl.nasa.gov/documentation/MER_camsis_v4_9-25-07.pdf)
- [PDS: MER veri türleri ve Mobility erişim durumu](https://pds-geosciences.wustl.edu/missions/mer/geo_mer_datasets.htm)
- [MER Analyst's Notebook](https://an.rsl.wustl.edu/mer/)
- [NASA: MER görev özeti ve iniş bölgeleri](https://science.nasa.gov/mission/mars-exploration-rovers-spirit-and-opportunity/)

## Doğrulama

`cd terrain3d && npm test`: düz zemin yük dengesi, eğim, bağımsız süspansiyon,
gaz/direksiyon/fren, Ay'da daha uzun duruş mesafesi, devrilme/kurtarma,
NoData/parsel, farklı kare hızları ve farklı DEM ölçekleri.

`processing/.venv/bin/python -m pytest processing/tests`: PDS etiket uyumu,
çözüm önceliği, geçersiz değerler ve teslim edilen gerçek koordinat örneği.

`rover_browser_check.py`: gerçek klavye/dokunma, gösterge paneli, duraklatma,
gezegen geçişi, referans kaydı, mobil yerleşim ve WebGL hataları.
`vehicles_browser_check.py` mevcut manuel iniş akışını da doğrular.
Test parkurlarındaki sık örneklenmiş rampalar ve tümsekler sentetiktir;
NASA'dan ölçülmüş arazi gibi sunulmaz.
