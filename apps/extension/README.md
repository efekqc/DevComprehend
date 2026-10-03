# VS Code extension (DC-003)
Sorumlu: Ahmet · İnceleme: Efe · Branch: `feat/DC-003-extension`

> Durum: Geliştirme iskeleti çalışıyor (mock mod + geliştirme API'si istemcisi). Pilot doğrulaması, temiz VS Code'da VSIX demo kanıtı ve Cursor testi henüz yapılmadı. Marketplace yayını ayrı karardır.

## Gereksinimler
- VS Code 1.85+ · Node.js 18+ (testler Node 24 ile çalıştırıldı) · Git (PATH içinde)
- Runtime bağımlılığı ve build adımı yok: düz JavaScript (CommonJS). Testler `node:test` kullanır.

## Çalıştırma (debug)
1. VS Code'da **`apps/extension/` klasörünü** açın (repo kökünü değil).
2. F5 → "Run DevComprehend Extension". Extension Development Host açılır.
3. Development Host'ta bir Git deposu açın; Command Palette → **DevComprehend: Analyze Changes**.
4. Klasörü (çoklu workspace'te) ve kapsamı (Staged/Unstaged) seçin → sidebar'da önizleme → onay → sorular.
5. Git olmadan arayüzü görmek için: **DevComprehend: Show Mock Demo Questions**.

Günlükler: Output panel → "DevComprehend". Reddedilen webview mesajları burada görünür.

## Modlar
| `devcomprehend.apiMode` | Davranış |
|---|---|
| `mock` (varsayılan) | Hiçbir veri gönderilmez. Sidebar'da **MOCK MODU** etiketi görünür. Yanıtlar `fixtures/` altındaki contracts/v1 örnekleridir; kaynak snapshot'ı yerel snapshot'a bağlanır. |
| `http` | Onaylanan istek `devcomprehend.apiBaseUrl` adresine gider. Uzak adres için https zorunlu; http yalnız localhost. Token: **DevComprehend: Set API Token** (SecretStorage). |

Yerel API ile deneme ([services/api](../../services/api/README.md), Derviş'in branch'i): `apiMode=http`, `apiBaseUrl=http://127.0.0.1:8000`, token `dev-token`. Fake sağlayıcı yalnız contracts örnek diff'ini kabul eder; gerçek diff için `FAKE_FIXTURE_ONLY` ile "failed" ekranı beklenir.

## Test ve paket
```bash
cd apps/extension
npm test                 # git, API client, controller, mesaj allowlist testleri
npm run sync-fixtures    # contracts/v1/examples değişince fixtures/ kopyasını günceller
npm run package          # dist/devcomprehend-dev.vsix (npx ile @vscode/vsce@3 indirir)
code --install-extension dist/devcomprehend-dev.vsix
```
`vscode:prepublish`, fixtures/ kopyası sözleşmeden saparsa paketlemeyi durdurur. VSIX'e tests/, scripts/, .vscode/ girmez; token veya üretim anahtarı pakete gömülmez.

## Yapı
- `src/extension.js`: aktivasyon, komutlar, mod/token seçimi, workspace ve kapsam seçimi.
- `src/host/controller.js`: akış durumu (idle → preview → sending/polling → ready/failed), çift gönderim kontrolü, stale kontrolü.
- `src/host/git/`: `git` çağrısı (shell yok, external diff/textconv/fsmonitor kapalı), dosya filtresi, sınırlı diff ve bağlam, snapshot.
- `src/host/api/`: mock ve HTTP client, istek oluşturucu, yanıt doğrulama.
- `src/host/messages.js`: webview → host mesaj allowlist'i.
- `src/host/sidebar.js`, `src/webview/`: CSP'li webview (nonce'lu script, inline yok), yalnız `textContent` ile render.
- `src/host/navigation.js`: kaynak satırını editörde açar; depo dışı yolları reddeder.

## Veri ve güvenlik kuralları
- Diff yalnız kullanıcı komutuyla toplanır; önizleme onaylanmadan hiçbir şey gönderilmez.
- Hariç: `.env*`, anahtar/sertifika dosyaları, binary, lock/build/vendor/minified dosyalar. Untracked dosyalar dahil değildir.
- Sınırlar: en fazla 40 dosya, ~40 KB diff, 12 KB bağlam, istek gövdesi ≤ 60 KB (API sınırı 64 KB). Sığmayan dosyalar önizlemede gerekçesiyle listelenir.
- `snapshot_id` = gönderilen diff'in SHA-256'sı; `base_commit_sha` = HEAD. İkisi ayrı alanlardır.
- `repository_id` yerel yoldan türetilmez; makinede saklanan rastgele opak ID'dir.
- Kod kaydedildiğinde snapshot yeniden hesaplanır; değiştiyse "stale" uyarısı gösterilir. Kaynak açılırken de kontrol edilir.
- Yalnız güvenilen (trusted) workspace'lerde çalışır.

## Doğrulama durumu
| Kontrol | Durum |
|---|---|
| Birim/entegrasyon testleri (`npm test`, 25 test) | Geçti |
| HTTP client ↔ services/api (dev token, fake motor): create/ready/evaluate, idempotency, 401/404/409 | Yerelde elle doğrulandı |
| VSIX üretimi | `npm run package` başarılı |
| Extension Development Host'ta UI turu | Yapılmadı: ekip demosunda doğrulanmalı |
| Temiz VS Code kurulumunda VSIX | Yapılmadı |
| Cursor | **Test edilmedi; destek iddiası yok** |

## Açık konular
- Sözleşme: contracts/README `POST /v1/analyses → 202` diyor, API 200 dönüyor; client ikisini de kabul eder. API'nin `SUBMISSION_CONFLICT`, `INSUFFICIENT_EVIDENCE`, `TOKEN_BUDGET_EXCEEDED`, `INTERNAL` kodları sözleşme listesinde yok. Netleştirme: Efe + Derviş.
- Gerçek kimlik akışı (DC-004-B) gelince token komutu yeniden ele alınacak.
- Rubrik/geri bildirim metinleri (değerlendirilmedi/belirsiz) Murathan'ın son metinleriyle güncellenecek.
