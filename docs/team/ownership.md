# Extension-first görev dağılımı
03.10.2026 · v2.0. Mevcut web-first görev dağılımının yerini alır.

| Kişi | Birincil sorumluluk | Sahip olduğu alan | İlk branch |
|---|---|---|---|
| Murathan | Ürün ve öğrenme motoru | services/learning/, docs/product/ | feat/DC-006-learning-engine |
| Ahmet | VS Code extension, Git adapter, sidebar | apps/extension/ | feat/DC-003-extension |
| Derviş | Backend ve kimlik/analiz API | services/api/ | feat/DC-004-analysis-api |
| Efe | Sözleşme, DB, altyapı ve kalite | contracts/, infra/, tests/, .github/workflows/ | feat/DC-002-contracts-infra |

Herkes ilk gün kod yazar. Ahmet fixture ile UI/host, Derviş fake learning adapter ile API, Murathan fixture ile motor, Efe şema/DB ve test altyapısıyla başlar. Gerçek entegrasyon bağımlılıkları geliştirmeye başlama engeli değildir.

## Ortak alanlar
README/CONTRIBUTING ve docs/team/ değişikliklerini Murathan koordine eder. Sözleşmeyi Efe değiştirir; Ahmet, Derviş ve Murathan tüketici incelemesi yapar. Kök yapılandırma ve workflow değişikliklerinde Efe koordinasyonu gerekir. Sahiplik katkı yasağı değildir; çatışmayı önleyen koordinasyondur.

## İnceleme
Ahmet ↔ Efe; Derviş ↔ Murathan. Entegrasyon PR'larında ilgili tüketici de inceler. Önce sözleşme, sonra adapter, sonra dikey akış birleştirilir.

## GitHub hesapları
Repo sahibi @Anonymbordo doğrulanmıştır. Ahmet, Derviş ve Efe'nin kullanıcı adları bekleniyor. İsimler hesap adı değildir; path-specific CODEOWNERS ve kişi atamaları hesaplar doğrulanınca eklenir.

[Push ve paralel çalışma rehberi](parallel-work.md)

## Kişisel görev planları
- [Murathan](tasks/murathan.md)
- [Ahmet](tasks/ahmet.md)
- [Derviş](tasks/dervis.md)
- [Efe](tasks/efe.md)
