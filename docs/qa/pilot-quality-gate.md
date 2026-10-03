# DevComprehend — Pilot Kalite Kapısı ve Doğrulama Protokolü

> **Belge Sürümü:** 1.0.0  
> **Tarih:** 2026-10-03  
> **Sorumlu:** Efe (Sözleşme & Altyapı)  
> **Durum:** Taslak — Takım incelemesi bekliyor

---

## 1. VSIX / Cursor Kurulum Kontrolü

### 1.1 Ön Koşullar
- VS Code >= 1.90 veya Cursor >= 0.40 kurulu olmalı
- Node.js >= 20 LTS kurulu olmalı
- Git >= 2.40 kurulu olmalı

### 1.2 VSIX Kurulum Doğrulama Adımları

| Adım | Komut / İşlem | Beklenen Sonuç | Kontrol |
|------|---------------|----------------|---------|
| 1 | `code --install-extension devcomprehend-x.y.z.vsix` | Kurulum başarılı mesajı | ☐ |
| 2 | `code --list-extensions \| grep devcomprehend` | Extension listede görünür | ☐ |
| 3 | VS Code → Extensions panel → DevComprehend | Extension aktif ve hatasız | ☐ |
| 4 | Komut paleti → "DevComprehend: Analyze Changes" | Komut mevcut ve çalışır | ☐ |

### 1.3 Cursor Özel Kurulum

| Adım | Komut / İşlem | Beklenen Sonuç | Kontrol |
|------|---------------|----------------|---------|
| 1 | `cursor --install-extension devcomprehend-x.y.z.vsix --profile DevComprehend-Test` | Kurulum başarılı | ☐ |
| 2 | Cursor'ı `--profile DevComprehend-Test` ile başlat | Profil yüklenir | ☐ |
| 3 | Extension'ın Cursor API'leri ile uyumluluğunu doğrula | Webview paneli açılır | ☐ |

### 1.4 İzole Profil Testi
```bash
# Temiz profil ile test (mevcut extension'ları etkilemez)
code --profile "DC-QA-$(date +%s)" --install-extension devcomprehend-x.y.z.vsix

# Cursor için
cursor --profile "DC-QA-$(date +%s)" --install-extension devcomprehend-x.y.z.vsix
```

---

## 2. Veri Sızıntısı Engelleme Denetimi

### 2.1 Maskeleme Regex Kuralları

Aşağıdaki kalıplar tespit edildiğinde otomatik olarak `[REDACTED_SECRET]` ile değiştirilmelidir:

| Kalıp Adı | Regex | Örnek Giriş | Beklenen Çıkış |
|-----------|-------|-------------|----------------|
| API Key | `(?i)(api[_-]?key\|apikey)\s*[=:]\s*["']?[\w\-]{16,}` | `API_KEY=sk-abc123def456ghi` | `[REDACTED_SECRET]` |
| Secret/Password | `(?i)(secret\|password\|passwd\|pwd)\s*[=:]\s*["']?[\S]{8,}` | `password=MyP@ssw0rd!` | `[REDACTED_SECRET]` |
| Bearer Token | `(?i)(token\|bearer)\s*[=:]\s*["']?[\w\-\.]{16,}` | `token=eyJhbGciOiJIUz...` | `[REDACTED_SECRET]` |
| Provider Prefix | `(?i)(sk-\|pk-\|ak-)[a-zA-Z0-9]{20,}` | `sk-1234567890abcdefghij` | `[REDACTED_SECRET]` |
| Private Key | `-----BEGIN (RSA \|EC \|DSA )?PRIVATE KEY-----` | PEM başlığı | `[REDACTED_SECRET]` |

### 2.2 Maskeleme Doğrulama Protokolü

1. **Birim Testi:** `tests/mock_adapters/fake_llm_provider.py` içindeki `mask_secrets()` metodu yukarıdaki tüm kalıpları kapsamalıdır.
2. **Manuel Test:**
   ```bash
   # Test dosyası oluştur
   echo 'API_KEY=sk-test1234567890abcdef' > /tmp/test-secret.txt
   echo 'password=SuperSecret123!' >> /tmp/test-secret.txt
   
   # Maskeleme fonksiyonunu çalıştır ve çıktıyı doğrula
   python -c "
   from tests.mock_adapters.fake_llm_provider import FakeLLMProvider
   p = FakeLLMProvider()
   with open('/tmp/test-secret.txt') as f:
       result = p.mask_secrets(f.read())
   assert '[REDACTED_SECRET]' in result
   assert 'sk-test' not in result
   print('✅ Maskeleme başarılı')
   "
   ```
3. **CI Entegrasyonu:** Her PR'da maskeleme testleri otomatik çalışır (`.github/workflows/ci.yml`).

### 2.3 Veri Akış Güvenlik Kuralları

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  VS Code /  │     │   Maskeleme  │     │   Backend   │
│   Cursor    │────▶│    Katmanı   │────▶│     API     │
│  Extension  │     │  (Yerel)     │     │  (Sunucu)   │
└─────────────┘     └──────────────┘     └─────────────┘
      │                    │                    │
      │ Kullanıcı onayı    │ Regex maskeleme    │ KMS'den
      │ gerekli (UI)       │ uygulanır          │ anahtar alınır
      │                    │                    │
      ▼                    ▼                    ▼
  Yalnızca onaylı     Sızıntı riski        Zero-Client
  diff verisi         minimize              Secret
```

---

## 3. Bütçe ve Kota Denetimi

### 3.1 Günlük Limitler

| Kaynak | Günlük Limit | Aşıldığında Davranış |
|--------|-------------|---------------------|
| Analiz istekleri | 10 analiz/gün | HTTP 429 + `retry_after_ms` |
| Değerlendirme istekleri | 30 değerlendirme/gün | HTTP 429 + `retry_after_ms` |
| Token kullanımı | 50.000 token/gün | HTTP 429 + kalan süre bilgisi |
| Maliyet tavanı | \$5.00/gün | Tüm istekler bloke |

### 3.2 Redis Sliding Window Mekanizması

```
Anahtar Formatı: rate:{user_id}:{resource_type}:{window_date}
Örnek:         rate:usr-42:analysis:2026-10-03

Algoritma:
1. INCR rate:{user_id}:{resource_type}:{date}
2. EXPIRE anahtarı 86400 saniye (24 saat) sonra
3. Mevcut sayaç >= limit ise → HTTP 429 döndür
4. Her istek DB usages tablosuna da loglanır (denetim izi)
```

### 3.3 Kota Aşım Senaryoları

| Senaryo | Tetikleyici | Beklenen HTTP Yanıtı | Kullanıcı Mesajı |
|---------|------------|---------------------|-----------------|
| Analiz limiti | 11. analiz isteği | 429 Too Many Requests | "Günlük analiz limitinize ulaştınız. Yarın tekrar deneyin." |
| Token limiti | >50K token | 429 Too Many Requests | "Günlük token kotanız doldu." |
| Maliyet tavanı | >\$5.00 | 429 Too Many Requests | "Günlük maliyet tavanına ulaşıldı." |
| Pro plan upgrade | Limit aşımı + free plan | 402 Payment Required | "Pro plana yükselterek limitlerinizi artırın." |

---

## 4. Pilot Kabul Kriterleri (Definition of Done — DoD)

### 4.1 Sözleşme & Şema (TASK 1)
- [ ] `message.schema.json` JSON Schema Draft 2020-12 uyumlu
- [ ] 5 sentetik fixture şemaya %100 uyumlu
- [ ] Şema doğrulama testleri yeşil (`pytest tests/contract/`)
- [ ] `contracts/README.md` sürümleme politikasını belgeliyor

### 4.2 Yerel Ortam (TASK 2)
- [ ] `docker-compose up -d` ile PostgreSQL ve Redis sorunsuz başlıyor
- [ ] Healthcheck'ler geçiyor
- [ ] Migration dosyaları `docker-entrypoint-initdb.d` üzerinden otomatik uygulanıyor
- [ ] `.env.example` tüm gerekli değişkenleri içeriyor
- [ ] ADR-0002 takım tarafından incelendi ve onaylandı

### 4.3 Veritabanı (TASK 3)
- [ ] Migration hatasız çalışıyor (`001_initial_schema.sql`)
- [ ] 9 tablo başarıyla oluşturuluyor
- [ ] UNIQUE kısıtlar (idempotency) doğrulandı
- [ ] CASCADE silme davranışları doğrulandı
- [ ] CHECK kısıtları doğrulandı (score 0-100, rating 1-4)
- [ ] Sentetik seed verisi yüklenebiliyor
- [ ] FSRS tabloları (concept_states, spaced_reviews) doğru modellendi

### 4.4 Test & CI (TASK 4)
- [ ] Tüm contract testleri yeşil
- [ ] Tüm DB migration testleri yeşil
- [ ] Fake LLM provider deterministik çıktı üretiyor
- [ ] CI pipeline gerçek API anahtarı olmadan %100 yeşil çalışıyor
- [ ] Pipeline süresi < 5 dakika

### 4.5 Güvenlik & Kalite (TASK 5)
- [ ] Regex maskeleme tüm bilinen secret kalıplarını yakalıyor
- [ ] Maskeleme extension tarafında (yerel) uygulanıyor
- [ ] Redis rate limiting doğru çalışıyor
- [ ] Bütçe aşımı HTTP 429 döndürüyor
- [ ] VSIX kurulumu VS Code ve Cursor'da doğrulandı
- [ ] Veri akış diyagramı takım tarafından incelendi

### 4.6 Canlıya Çıkış Öncesi Son Kontrol
- [ ] Tüm yukarıdaki maddeler işaretli
- [ ] Takım üyeleri (Ahmet, Derviş, Murathan) entegrasyon testlerini onayladı
- [ ] ADR-0002 ACCEPTED durumunda
- [ ] `CHANGELOG.md` güncellendi
- [ ] Branch `feat/DC-002-contracts-infra` → `main` PR oluşturuldu
- [ ] PR en az 2 onay aldı
- [ ] CI pipeline PR üzerinde yeşil

---

## 5. Acil Durum Geri Alma Prosedürü

### 5.1 Veritabanı Geri Alma
```sql
-- Acil durum: Tüm DevComprehend tablolarını kaldır
DROP TABLE IF EXISTS spaced_reviews CASCADE;
DROP TABLE IF EXISTS concept_states CASCADE;
DROP TABLE IF EXISTS usages CASCADE;
DROP TABLE IF EXISTS evaluations CASCADE;
DROP TABLE IF EXISTS answers CASCADE;
DROP TABLE IF EXISTS questions CASCADE;
DROP TABLE IF EXISTS analyses CASCADE;
DROP TABLE IF EXISTS workspaces CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TYPE IF EXISTS analysis_status CASCADE;
DROP TYPE IF EXISTS plan_type CASCADE;
DROP TYPE IF EXISTS fsrs_state CASCADE;
```

### 5.2 Extension Geri Alma
```bash
# VS Code
code --uninstall-extension devcomprehend

# Cursor
cursor --uninstall-extension devcomprehend
```

### 5.3 Docker Ortam Temizliği
```bash
cd infra/local
docker-compose down -v  # Volume'ları da sil
docker system prune -f
```

---

## Ekler

### Ek A: İletişim Matrisi

| Alan | Sorumlu | İletişim |
|------|---------|----------|
| Extension UI | Ahmet | VSIX çıktısı ve webview entegrasyonu |
| Backend API | Derviş | REST endpoint'leri ve orchestration |
| AI Engine | Murathan | LLM prompt'ları ve değerlendirme |
| Contracts & Infra | Efe | Şema, DB, CI, QA |

### Ek B: Referans Belgeleri
- ADR-0002: Sözleşme-Öncelikli Mimari
- contracts/README.md: Sürümleme Politikası
- FSRS Algorithm: https://github.com/open-spaced-repetition/fsrs4anki
