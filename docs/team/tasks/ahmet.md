# Ahmet - Extension görev planı v2

VS Code extension, yerel Git ve sidebar

Kullanıcının editor içinde kendi Git değişikliklerini analiz edip soru cevaplayabildiği extension'ı geliştirmek. Web sitesi ilk teslim değildir.

## Alan ve branch

- Alan: apps/extension/

- Branch: feat/DC-003-extension

- İnceleme: Efe

## İlk gün

1. apps/extension/ için extension iskeleti ve geliştirme host’u kur.

2. Analyze Changes komutu ile sidebar/webview aç.

3. analysis-ready.json fixture'ını mock API adapter üzerinden göster.

4. İlk PR’da açılan sidebar, örnek sorular ve debug komutunu teslim et.

## İş paketleri

### DC-003-A / Extension host ve komut

Komut, aktivasyon, host/webview mesaj arayüzü ve mock API adapter oluştur. Sidebar'a güvenli veri aktar; ilk günden fixture ile çalış.

Teslim: src/host/; src/webview/; package yapılandırması; README debug yönergesi.

Kabul: Extension geliştirme host'unda komut çalışır; webview yalnız izinli mesajları gönderir; mock modu açıkça belirtilir.

### DC-003-B / Yerel Git ve önizleme

Workspace ve staged/unstaged kapsamını seçtir. Sınırlı diff/ilgili bağlam al; snapshot hash üret. Gönderilecek içerik için önizleme/onay ekle.

Teslim: host/git/; snapshot ve dosya filtresi; no-Git/empty/multi-root durumları.

Kabul: Onaydan önce veri gönderilmez; .env/binary/generated dosyalar hariç; büyük diff açıklanır; base SHA ve snapshot karıştırılmaz.

### DC-003-C / API, soru ve cevap

Mock adapter'ı gerçek API client ile değiştir. queued/fetching/generating/ready/failed ekranlarını ve cevap formunu bağla. Kaynak satırını editor'de aç.

Teslim: api client; sidebar soru/cevap/feedback bileşenleri; kaynak navigasyonu.

Kabul: Çift gönderim kontrollü; hata sonrası cevap korunur; stale snapshot uyarısı vardır; klavye ve etiketli form kullanılabilir.

### DC-003-D / Tekrar, paket ve uyumluluk

Tekrar tarihini ve geri bildirimini göster. Geliştirme VSIX paketi oluştur; temiz VS Code kurulumunda test et. Cursor'u ayrı doğrula.

Teslim: README install/test/package komutları; VSIX demo kanıtı; uyumluluk notu.

Kabul: Üretim anahtarı pakete gömülmez; test edilmemiş Cursor desteği vaat edilmez; Marketplace yayını ayrı karardır.

## Entegrasyon

- Efe → Ahmet: Sözleşme v1, örnek JSON, hata ve tarih biçimleri.

- Ahmet → Derviş: Bounded analysis_request; snapshot; seçilmiş bağlam; submission_id.

- Derviş → Ahmet: Analiz/durum ve evaluation response; kimlik/kota hataları.

- Murathan → Ahmet: Rubrik geri bildirimi ve uncertain/değerlendirilmedi metinleri.

## Push

```bash

# Repo zaten bilgisayarındaysa:
cd DevComprehend
git switch main
git pull --ff-only origin main
git switch -c feat/DC-003-extension

# İlgili dosyaları değiştir, sonra:
git status
git add apps/extension/
git commit -m "feat: add first module increment"
git push -u origin feat/DC-003-extension

```

[Ortak paralel çalışma rehberi](../parallel-work.md)

## Dalga çıktıları

1. Komut/sidebar ve fixture tabanlı mock akış.

2. Yerel Git, snapshot, önizleme ve dosya sınırları.

3. Derviş API’si; cevap/feedback/tekrar görünümü.

4. VSIX, erişilebilirlik ve pilot kullanılabilirlik düzeltmeleri.
