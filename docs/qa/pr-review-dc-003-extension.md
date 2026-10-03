# DevComprehend — PR İnceleme Raporu: DC-003 Extension UI & Entegrasyon

> **İncelenen PR:** `feat/DC-003-extension`  
> **İncelenen Commit:** `c8ae31f`  
> **PR Sahibi:** Ahmet (Extension & UI Mühendisi)  
> **İnceleyen:** Efe (Sözleşme, Altyapı ve Kalite Güvencesi)  
> **Değerlendirme Tarihi:** 2026-10-03  
> **Sonuç:** ⚠️ **Şartlı Onay / Değişiklik Talebi (Changes Requested)**

---

## 1. Genel Değerlendirme Özeti

Ahmet'in `c8ae31f` commit'iyle sunduğu VS Code & Cursor extension iskeleti, webview mimarisi ve Git diff toplama altyapısı temel fonksiyonları başarıyla kurmaktadır. Ancak API (Derviş) ile İstemci (Ahmet) arasında tespit edilen **iki kritik sözleşme farkı** ve **DC-008-B Kalite Kapısı test adımlarındaki eksikler** nedeniyle canlı sürüme çıkış öncesi aşağıdaki maddelerin giderilmesi gerekmektedir.

---

## 2. Tespit Edilen Sözleşme Farkları ve Alınan Önlemler

### 🔴 Madde 1: HTTP 200 vs 202 Analiz Kabul Uyumsuzluğu
- **Sorun:** Mevcut extension kodu analiz başlatma isteğine (`POST /v1/analyses`) her zaman `200 OK` dönmesini ve anında soru listesini getirmesini bekliyor. Ancak backend API asenkron kuyruk mimarisinde `202 Accepted` ile `QUEUED` durumunu ve `retry_after_ms` alanını dönmektedir.
- **Efe Tarafından Yapılan Sözleşme Güncellemesi:**
  - `contracts/v1/message.schema.json` şeması hem senkron (`200 OK` / `READY`) hem de asenkron (`202 Accepted` / `QUEUED`) yanıtları destekleyecek şekilde esnetildi.
  - `contracts/README.md` dokümanına 200 vs 202 durum kodu politikası eklendi.
- **Ahmet'in Yapması Gereken (Action Item):**
  - İstemcide dönen durum kodunu kontrol et:
    - Eğer `status == "QUEUED"` veya HTTP 202 ise: Webview'da "Analiz hazırlanıyor..." yükleme durumunu göster ve `payload.retry_after_ms` aralığıyla `GET /v1/analyses/{id}` adresini sorgula (polling).
    - Eğer `status == "READY"` veya HTTP 200 ise: Polling yapmadan doğrudan soruları webview'a render et.

---

### 🔴 Madde 2: Standart Hata Kodları ve Şema Eksikliği
- **Sorun:** Extension istemcisi API'den gelen hataları genel metin olarak yakalamakta; kullanıcıya yönlendirici aksiyon sunabilmek için gereken standart hata kodları (`error_code`, `http_status`) sözleşmede ve istemcide bulunmamaktaydı.
- **Efe Tarafından Yapılan Sözleşme Güncellemesi:**
  - `message.schema.json` şemasına `error.response` event_type'ı ve aşağıdaki standart hata nesnesi tanımlandı:
    ```json
    {
      "error_code": "EMPTY_DIFF | PAYLOAD_TOO_LARGE | STALE_SNAPSHOT | RATE_LIMIT_EXCEEDED | INVALID_MODEL_OUTPUT",
      "http_status": "400 | 409 | 413 | 429 | 502",
      "message": "Açıklayıcı kullanıcı mesajı",
      "details": { "opsiyonel": "ek bilgi nesnesi" }
    }
    ```
  - `contracts/v1/examples/error-response.json` sentetik fixture'ı eklendi ve `tests/contract/test_schemas.py` ile doğrulandı.
  - `tests/e2e/test_edge_cases_and_resilience.py` içine istemci-sunucu hata ayrıştırma testleri (`TestExtensionApiErrorAndStatusHandling`) eklendi.
- **Ahmet'in Yapması Gereken (Action Item):**
  - İstemcide hata yakalama bloğunu `error.response` yüküne göre güncelle:
    - `EMPTY_DIFF` (400): "Lütfen değişiklik içeren bir dosya seçin veya staged yapın."
    - `PAYLOAD_TOO_LARGE` (413): "Diff 400 satırı aşıyor veya lock dosyası içeriyor. Lütfen atomic commit yapın."
    - `STALE_SNAPSHOT` (409): "Dosya içeriği değişti, lütfen analizi yenileyin."
    - `RATE_LIMIT_EXCEEDED` (429): "Günlük analiz kotanız doldu. Sıfırlanma süresi: ..."

---

## 3. Henüz Yapılmayan DC-008-B Kalite Kapısı Test Adımları

Ahmet'in PR'ında aşağıdaki kabul testleri henüz tamamlanmamış ve kanıtlanmamıştır:

| Test Adımı | Açıklama | Durum | Gerekli Eylem |
|---|---|:---:|---|
| **1. VS Code Temiz Profil Testi** | Eklentinin diğer eklentilerden izole, sıfır bir profilde sorunsuz açılması | ⏳ Eksik | `code --profile DC-QA-Clean --install-extension devcomprehend-*.vsix` komutuyla temiz kurulum yapılıp ekran görüntüsü eklenmeli. |
| **2. VS Code Elle Fonksiyonel Deneme** | Diff onay kutusu, webview soru render, serbest metin cevap yazma akışı | ⏳ Eksik | Manuel test akışı uygulanmalı ve sonuçlar rapora işlenmeli. |
| **3. Cursor Kurulum ve Uyumluluk Testi** | Cursor editöründe `--profile` parametresi ile kurulum ve AI sidebar çakışma kontrolü | ⏳ Eksik | `cursor --profile DC-QA-Cursor --install-extension devcomprehend-*.vsix` çalıştırılmalı, Cursor sağ panel entegrasyonu kanıtlanmalı. |
| **4. Otomatik VSIX Paket Doğrulaması** | Paket bütünlüğü, manifest eksiksizliği ve gizli bilgi/anahtar taraması | ⏳ Bekleniyor | Ahmet `.vsix` dosyasını derledikten sonra `python scripts/verify_vsix_package.py <dosya.vsix>` çalıştırılıp çıktısı rapora eklenmeli. |

---

## 4. Efe Tarafından Hazırlanan Doğrulama Araçları

Ahmet'in paketini doğrudan denetleyebilmesi için aşağıdaki araçlar hazırlandı ve test edildi:

1. **VSIX Denetleme Aracı:**
   ```bash
   python scripts/verify_vsix_package.py path/to/devcomprehend-0.1.0.vsix
   ```
   *Yapılan Kontroller:*
   - Arşiv ve ZIP dosya bütünlüğü
   - `package.json` içinde zorunlu alanlar (`name`, `version`, `publisher`, `engines.vscode`, `contributes.views`)
   - Paket içerisine `.env`, `credentials.json`, private key vb. sızıp sızmadığının taranması
   - JS/TS bundle dosyalarında API key, JWT token veya parola regex taraması
   - Cursor `--profile` kurulum komutu simülasyonu

2. **Bash Doğrulama Scripti:**
   ```bash
   ./scripts/verify_vsix_and_cursor.sh path/to/devcomprehend-0.1.0.vsix
   ```

3. **Sözleşme & E2E Test Paketi:**
   ```bash
   python -m pytest tests/contract/ -v
   python -m pytest tests/e2e/ -v
   ```

---

## 5. Ahmet İçin Yapılacaklar Listesi (Checklist)

- [ ] `message.schema.json` dosyasındaki yeni `error.response` event_type ve hata kodları eşlemesini webview hata yönetim koduna ekle.
- [ ] API yanıtındaki `status: "QUEUED"` (202) ve `status: "READY"` (200) dallarını doğru ele al (polling vs anında render).
- [ ] `vsce package` ile `.vsix` dosyasını üret.
- [ ] `python scripts/verify_vsix_package.py devcomprehend-*.vsix` komutunu çalıştır ve çıktısını bu rapora bağla.
- [ ] VS Code izole profil ve Cursor testlerini tamamlayıp PR'ı onaya sun.
