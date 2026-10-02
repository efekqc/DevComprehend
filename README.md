# DevComprehend
**AI writes the code. You understand what it builds.**

DevComprehend, geliştiricinin kendi repository değişikliklerinden öğrenmesini sağlayan bir AI Coding Comprehension Platform projesidir. Git diff ve ilgili kod bağlamından kavramlar çıkarır, projeye özel sorular sorar ve cevaplardan öğrenme geçmişi oluşturur.

> Durum: Proje başlangıç yapısı. Henüz çalışan ürün, GitHub OAuth entegrasyonu veya LLM servisi yoktur.

## İlk sürüm
1. İzin verilen repository ve commit/PR seçilir.
2. Diff ve gerekli dosya parçaları alınır.
3. Kaynak referanslarıyla 2–5 kavram çıkarılır.
4. 3–5 bağlama özel soru üretilir.
5. Kullanıcı kendi cümleleriyle cevaplar.
6. Rubrik üzerinden geri bildirim ve tekrar planı oluşturulur.

Puanlar yalnızca değerlendirilen cevaplara ait tahminlerdir. Commit sayısı, kod sahipliği veya teknoloji kullanımı yetkinlik kanıtı değildir. Test edilmeyen kavramlar **değerlendirilmedi** olarak gösterilir.

## Repository haritası
| Yol | Sorumluluk |
|---|---|
| apps/web/ | Kullanıcı arayüzü |
| services/api/ | API, yetkilendirme, GitHub entegrasyonu |
| services/learning/ | Kavram çıkarımı, soru, değerlendirme ve tekrar |
| contracts/ | Servisler arası veri sözleşmeleri |
| infra/ | Yerel ortam ve dağıtım tanımları |
| tests/ | Entegrasyon ve uçtan uca senaryolar |
| docs/ | Kapsam, mimari, ekip ve teslim rehberleri |
| scripts/ | Repository kontrolleri |

## Nereden başlamalı?
- [Ekip ve görev alanları](docs/team/ownership.md)
- [Kurulum ve ilk katkı](docs/guides/getting-started.md)
- [Katkı ve PR kuralları](CONTRIBUTING.md)
- [MVP kapsamı](docs/product/mvp.md)
- [Mimari](docs/architecture/overview.md)
- [İş listesi](docs/planning/backlog.md)
- [Yol haritası](docs/planning/roadmap.md)

## Kontrol
```bash
python3 scripts/check_repository.py
```
Bu kontrol repository yapısını ve yerel Markdown bağlantılarını doğrular; uygulama testi değildir.

## Ekip
Murathan · Ahmet · Derviş · Efe. Görev dağılımı başlangıç önerisidir; GitHub kullanıcı adları doğrulanınca CODEOWNERS güncellenecektir.

## Lisans
Henüz açık kaynak lisansı seçilmedi. Repository'nin public olması kullanım lisansı verildiği anlamına gelmez.
