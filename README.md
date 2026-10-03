# DevComprehend
**AI writes the code. You understand what it builds.**

DevComprehend, yerel Git değişikliklerinden projeye özel sorular üreten bir **VS Code extension** projesidir. Extension kullanıcı arayüzüdür; backend model çağrılarını, değerlendirmeyi ve öğrenme geçmişini yönetir. Cursor uyumluluğu ayrıca doğrulanacaktır.

> Durum: Plan ve başlangıç sözleşmeleri hazır; çalışan extension veya backend henüz yoktur. Önceki web-first MVP planı ADR-0002 ile değiştirilmiştir.

## MVP akışı
Kullanıcı komutu → seçilen Git workspace ve diff → gönderilecek bağlamın önizlemesi/onayı → backend analizi → sidebar'da 3–5 soru → cevap ve rubrik geri bildirimi → tekrar planı.

İlk hedef yerel Git'tir; GitHub OAuth veya PR bağlantısı başlangıç için zorunlu değildir. Model API anahtarları backend'de kalır. Kullanıcının ChatGPT aboneliği bu uygulamanın API kullanım bütçesi sayılmaz.

## Dört kişi aynı anda başlar
| Kişi | Alan | Başlangıç verisi |
|---|---|---|
| Ahmet | Extension host, Git adapter, sidebar | Ortak fixture, mock API |
| Derviş | API, kimlik, analiz akışı | Mock learning adapter |
| Murathan | Kavram, soru, rubrik, tekrar | Sentetik diff ve fake provider |
| Efe | Sözleşme, DB, ortam, kalite | Fixture ve API/motor arayüzü |

- [Görevler ve dosya sahipliği](docs/team/ownership.md)
- [Paralel çalışma ve push rehberi](docs/team/parallel-work.md)
- [MVP ve ürün modeli](docs/product/mvp.md)
- [Mimari](docs/architecture/overview.md)
- [Başlangıç sözleşmesi](contracts/README.md)
- [Backlog](docs/planning/backlog.md)
- [İlk katkı](docs/guides/getting-started.md)

## Alanlar
apps/extension/ · services/api/ · services/learning/ · contracts/ · infra/ · tests/

apps/web/ gelecekteki yönetim/ödeme portalı için ayrılmıştır; ilk MVP işi değildir.

## Kontroller
```bash
python3 scripts/check_repository.py
python3 scripts/check_contract_examples.py
```
İkincisi geliştirme için jsonschema gerektirir. Uygulama kontrolleri gerçek kod eklendikçe tanımlanacaktır.

Puan yalnız değerlendirilen cevabın rubrik sonucudur. Test edilmeyen alan **değerlendirilmedi** olarak kalır. Git diff tek başına AI yazarlığını veya geliştirici yetkinliğini kanıtlamaz.

## Lisans
Henüz açık kaynak lisansı seçilmedi.
