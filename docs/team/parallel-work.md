# Aynı anda geliştirme ve push
## İlk gün bağımsız teslim
| Kişi | Diğerini beklemeden yapılacak iş | İlk PR kanıtı |
|---|---|---|
| Ahmet | Extension iskeleti, komut/sidebar, fixture okuyucu | Mock sorular extension host'ta görüntülenir |
| Derviş | API iskeleti, in-memory store, fake learning adapter | Fixture isteğine queued/ready akışı |
| Murathan | Provider arayüzü, fake provider, kavram/soru/rubrik | Sentetik request'ten şema geçerli çıktı |
| Efe | Şema doğrulama, DB migration taslağı, ortam/CI | Fixture kontrolü ve temiz ortam rehberi |

Fake/memory adapter geliştirme içindir; üretim özelliği olarak raporlanmaz. Herkes contracts/v1/ fixture biçimini kullanır. Şema değişikliği PR'ı Efe koordine eder; breaking change sessizce eklenmez.

## Push klasöre değil branch'e yapılır
Git tüm repository değişikliklerini branch'e push eder. Klasörler kod sorumluluk sınırıdır. Aynı main'den dört görev branch'i açılır; dört kişi doğrudan main'e eşzamanlı push yapmaz.

```bash
git switch main
git pull --ff-only origin main
git switch -c feat/DC-003-extension
# Yalnız ilgili dosyaları stage et.
git add apps/extension/
git commit -m "feat(extension): add sidebar shell"
git push -u origin feat/DC-003-extension
```
Ahmet örneği; diğerleri ownership tablosundaki branch ve alanını kullanır. GitHub'da bu branch'ten main'e PR açılır.

## Entegrasyon sırası
1. Sözleşme/fixture değişiklikleri.
2. Her alanın küçük iskelet PR'ları; birbirinden bağımsız birleştirilebilir.
3. API + motor, extension + API bağlantıları.
4. Efe'nin uçtan uca doğrulaması ve pilot.

## Güncelleme
Çalışma dosyalarını commitledikten sonra kendi görev branch'inde:
```bash
git fetch origin
git merge origin/main
```
Çatışmaları ilgili dosyanın sahibiyle çöz; çözüm sonrası alan kontrolünü yeniden çalıştır. Main'e force push yok. Paylaşılmış branch'i rebase ile yeniden yazmak varsayılan akış değildir.

## PR standardı
Problem/sonuç, DC kimliği, değişen alan, test kanıtı, sözleşme etkisi ve kalan işler yazılır. En az bir başka kişi inceler; squash merge önerilir. Süreç kuralları branch protection olarak otomatik uygulanmış değildir.
