# AstroMatch AI — 3D Terrain Modülü Roadmap

**Sorumlu:** Kişi 4  
**Kapsam:** Ana frontend'den bağımsız geliştirilen, React + TypeScript projesine doğrudan entegre edilebilir 3D topoğrafya modülü.  
**Tahmini süre:** 6 saat 30 dakika (DEM verisi hazırsa; veri temini ek süre gerektirebilir).  
**Branch:** `feature/terrain3d`

## Hedef

Gerçek DEM verilerinden üretilen yükseklik matrislerini kullanarak Ay/Mars hedefleri ile Dünya analoglarını yan yana görüntüleyen, döndürülebilen ve yakınlaştırılabilen bir 3D bileşen geliştirmek. **Frontend geliştirme işleri bu görevin kapsamında değildir.** Yalnızca bağımsız demo ve yeniden kullanılabilir bileşenler hazırlanacaktır.

## Teknoloji

- React + TypeScript + Vite
- Three.js, `@react-three/fiber`, `@react-three/drei`
- Python, NumPy ve Rasterio (DEM dönüştürme)
- Önceden hazırlanmış JSON yükseklik verileri; canlı servis bağımlılığı yok

## Klasör yapısı

```text
terrain3d/
├── converter/
│   └── dem_to_json.py
├── src/
│   ├── components/
│   │   ├── TerrainMesh.tsx
│   │   ├── TerrainViewer.tsx
│   │   └── TerrainComparison.tsx
│   ├── types/
│   │   └── terrain.ts
│   └── index.ts
├── demo/
│   └── App.tsx
├── public/
│   └── terrain/
│       ├── mars_jezero.json
│       ├── moon_target.json
│       └── earth_analog.json
├── package.json
└── README.md
```

## Aşama 1 — Bağımsız geliştirme ortamı (30 dk)

- [ ] `feature/terrain3d` branch'ini aç.
- [ ] Vite + React + TypeScript ortamını oluştur.
- [ ] Three.js, React Three Fiber ve Drei paketlerini kur.
- [ ] Basit bir 3D yüzeyin tarayıcıda render edildiğini doğrula.

```bash
npm create vite@latest terrain3d -- --template react-ts
cd terrain3d
npm install
npm install three @react-three/fiber @react-three/drei
npm install -D @types/three
npm run dev
```

**Çıktı:** Bağımsız çalışan demo ortamı.

## Aşama 2 — Ortak yükseklik verisi sözleşmesi (60 dk)

- [ ] `TerrainData` TypeScript tipini tanımla.
- [ ] JSON alanlarını belirle: `id`, `name`, `body`, `width`, `height`, `heights`, `cellSizeMeters`, `source`, `resolutionMeters`, `verticalExaggeration`.
- [ ] `heights` dizisinin satır-sütun sırasını ve yükseklik birimini (metre) sabitle.
- [ ] NoData maskesi/eksik değer kuralını belirle; eksikleri sıfır yükseklik olarak yorumlama.
- [ ] Fiziksel pencere genişliği ve örnekleme aralığı için metadata ekle.
- [ ] Gerçek olmayan küçük bir örnek JSON oluştur ve **synthetic/demo** olarak işaretle.

**Çıktı:** `src/types/terrain.ts`, örnek JSON ve şema açıklaması.

## Aşama 3 — DEM → JSON dönüştürücü (90 dk)

- [ ] Rasterio ile GeoTIFF/uygun raster dosyasını aç.
- [ ] Gerekirse hedef pencereyi kırp; koordinat referansını ve yükseklik birimini doğrula.
- [ ] Ortak fiziksel pencere ve uygun örnekleme aralığına göre yeniden örnekle.
- [ ] Görselleştirme için 128×128 veya 256×256 matris üret.
- [ ] NoData ve geçersiz değerleri açıkça maskele.
- [ ] Kaynak, ürün/sürüm, işlem tarihi, yatay çözünürlük ve düşey abartma metadata'sını kaydet.
- [ ] Varsa gerçek Mars, Ay ve Dünya DEM dosyalarından ayrı JSON'lar üret.

**Çıktı:** `converter/dem_to_json.py` ve `public/terrain/*.json`.

> Not: Kişi 1'in topoğrafik analizine ait metrikleri burada yeniden hesaplama. Bu modülün görevi görselleştirme verisi üretmektir. Gerçek DEM henüz yoksa sentetik veriyle geliştirmeye devam et; bilimsel veriymiş gibi gösterme.

## Aşama 4 — TerrainViewer (90 dk)

- [ ] Yükseklik matrisinden `BufferGeometry` tabanlı mesh oluştur.
- [ ] OrbitControls ile döndürme, kaydırma ve zoom ekle.
- [ ] Kamerayı arazi boyutuna göre başlangıçta konumlandır.
- [ ] Yüksekliğe göre renk paleti uygula (opsiyonel).
- [ ] Yatay ölçekte metre bilgisini koru; dikey abartmayı açıkça göster.
- [ ] JSON yüklenme ve hata durumlarını yönet.

**Çıktı:** `<TerrainViewer terrain={data} />` ve tercihen `<TerrainViewer terrainUrl="/terrain/mars_jezero.json" />`.

## Aşama 5 — TerrainComparison (60 dk)

- [ ] Hedef ve Dünya analogunu yan yana göster.
- [ ] İki panelde aynı yatay fiziksel ölçeği kullan.
- [ ] Veri kaynağı, çözünürlük ve düşey abartma bilgisini göster.
- [ ] Farklı yükseklik referanslarını mutlak rakım eşitliği olarak yorumlama.
- [ ] İki kameranın senkron hareketini yalnızca zaman kalırsa ekle (P2).

**Çıktı:** `<TerrainComparison target={mars} analog={earth} />`.

## Aşama 6 — Entegrasyon, test ve teslim (60 dk)

- [ ] `src/index.ts` içinden bileşenleri ve tipleri export et.
- [ ] Başka bir React + TypeScript projesinde import testi yap.
- [ ] `terrain` prop'u ve `terrainUrl` kullanımını belgele.
- [ ] Geçersiz JSON, NoData, eksik metadata ve büyük veri boyutu senaryolarını test et.
- [ ] Çevrimdışı çalışmayı test et; harici CDN/API zorunluluğu bırakma.
- [ ] Demo ekran görüntüsü veya kısa kayıt ve README hazırla.

**Çıktı:** Entegre edilebilir modül, test sonuçları ve README.

## Kabul kriterleri

- [ ] Gerçek DEM sağlandığında dönüştürücü geçerli 3D JSON üretebiliyor.
- [ ] En az bir Mars, bir Ay ve bir Dünya örneği için veri hazırlanabiliyor.
- [ ] Arazi döndürülebiliyor ve yakınlaştırılabiliyor.
- [ ] İki arazi yan yana, tutarlı yatay ölçekte gösteriliyor.
- [ ] Çözünürlük, veri kaynağı ve düşey abartma kullanıcıya açık.
- [ ] Eksik veri sessizce geçerli yükseklik gibi çizilmiyor.
- [ ] Modül, ana frontend koduna müdahale etmeden import edilebiliyor.
- [ ] Demo önceden hazırlanmış dosyalarla internetsiz çalışıyor.

## Git ve entegrasyon kuralları

- Sadece `terrain3d/` altında çalış; ana frontend'in `App.tsx` dosyasına dokunma.
- `src/index.ts` modülün herkese açık giriş noktası olsun.
- Kişi 1 ile DEM/heightmap veri sözleşmesini erken netleştir.
- Büyük raster dosyalarını doğrudan Git'e ekleme; küçük örnek JSON'ları ve dönüştürme betiğini versiyonla.
- Entegrasyon için Pull Request aç; bağımlılıkları ve örnek kullanımı README'de açıkça belirt.

## Frontend ekibine teslim edilecek kullanım örneği

```tsx
import { TerrainComparison } from './terrain3d';

<TerrainComparison target={marsTerrain} analog={earthTerrain} />;
```

> Not: `terrainUrl` üzerinden yükleme API'si de uygulanırsa bileşen dosyaları kendi yükleyebilir. Bu API'nin gerçekten çalıştığı test edilmeden README'de tamamlanmış olarak işaretlenmemelidir.

## Riskler ve önlemler

| Risk | Önlem |
|---|---|
| Gerçek DEM geç ulaşır | Sentetik veriyle bileşeni geliştir, sonra gerçek DEM ile doğrula |
| Raster CRS/birim farklılığı | Dönüştürücüde açık doğrulama ve metadata |
| Büyük mesh tarayıcıyı yavaşlatır | 128×128 ile başla; gerekirse 256×256'ya çık |
| Görsel ölçek yanıltıcı olur | Fiziksel yatay boyut ve düşey abartmayı açıkça göster |
| Frontend entegrasyonu gecikir | Sabit prop API, `index.ts` export ve bağımsız demo |

**Öncelik:** Önce çalışan dönüştürücü + TerrainViewer + TerrainComparison. Kamera senkronizasyonu ve görsel süslemeler zaman kalırsa.
