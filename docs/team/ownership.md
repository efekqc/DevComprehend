# Ekip ve çalışma alanları
Aşağıdaki dağılım başlangıç önerisidir; ekip yetkinlikleri ve zamanına göre değiştirilebilir.

| Kişi | Birincil alan | Kod yolu | İlk iş | İnceleme ortağı |
|---|---|---|---|---|
| Murathan | Ürün koordinasyonu ve öğrenme motoru | services/learning/, docs/product/ | DC-001, DC-006 | Derviş |
| Ahmet | Web arayüzü ve kullanıcı deneyimi | apps/web/ | DC-003 | Efe |
| Derviş | API ve GitHub entegrasyonu | services/api/ | DC-004 | Murathan |
| Efe | Veri modeli, kalite ve geliştirme ortamı | contracts/, infra/, tests/ | DC-002, DC-008 | Ahmet |

## Kim nereye push yapacak?
Herkes **aynı repository** içinde görev branch'ine push yapar. Örneğin Ahmet feat/DC-003-repo-selection branch'inde apps/web/ üzerinde çalışır. Derviş feat/DC-004-diff-ingestion branch'inde services/api/ üzerinde çalışır. Bunlar kişinin kalıcı branch'i değildir.

Bir alanın sorumlusu o alana tek katkı yapabilen kişi değildir; entegrasyon ve inceleme koordinasyonundan sorumludur. Ortak dosyalarda önce ilgili sorumluyla anlaşılır.

## GitHub kimlikleri
| Kişi | GitHub kullanıcı adı | Durum |
|---|---|---|
| Murathan | Anonymbordo | Repo sahibi hesabı; kişi eşleşmesi kullanıcıyla teyit edilmeli |
| Ahmet | Bekleniyor | CODEOWNERS'a eklenmedi |
| Derviş | Bekleniyor | CODEOWNERS'a eklenmedi |
| Efe | Bekleniyor | CODEOWNERS'a eklenmedi |

Daveti kabul etmeden issue ataması çalışmayabilir. Hiçbir hesap adı tahmin edilmez.

## Haftalık koordinasyon
Kısa toplantı: tamamlanan işler, blokajlar, sonraki teslim. Kararları docs/decisions/ altında ADR ile kaydedin. İşler için Todo → In progress → In review → Done akışı önerilir; GitHub Project henüz oluşturulmadı.
