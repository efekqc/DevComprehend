# Katkı rehberi
## Akış
1. Önce backlog kimliği veya GitHub issue ile işi tanımla.
2. Güncel main'den kısa ömürlü branch aç: feat/DC-003-repo-selection, fix/DC-004-diff-limit, docs/DC-001-scope.
3. Kendi alanında çalış; ortak sözleşme değişikliğini tüketen servis sahibine bildir.
4. Küçük, açıklanabilir commitler oluştur.
5. PR aç; problemi, sonucu, doğrulamayı ve riskleri yaz.
6. En az bir ekip arkadaşı incelesin. Yazar kendi değişikliğini tek başına onaylamasın.
7. Kontroller geçtikten sonra squash merge önerilir; branch silinir.

main ortak entegrasyon dalıdır. Kişi başına kalıcı branch veya kişi adına kod klasörü oluşturulmaz. Force push main üzerinde kullanılmaz. Bu kurallar süreç önerisidir; GitHub branch protection ayrıca ayarlanmalıdır.

## Commit örnekleri
- feat(api): add bounded diff retrieval
- fix(learning): preserve unassessed concept state
- docs(team): clarify review ownership

## Definition of Done
- İşin kabul kriterleri karşılandı.
- Uygun otomatik kontroller veya somut manuel doğrulama kaydedildi.
- İlgili sözleşme ve dokümantasyon güncellendi.
- Gizli bilgi ve gerçek kullanıcı kaynak kodu commitlenmedi.
- Hata, boş durum ve yetkisiz erişim davranışı değerlendirildi.
- İnceleme geri bildirimleri çözüldü.

## Ortak dosyalar
contracts/, infra/ ve .github/ değişiklikleri ilgili servis sahipleriyle birlikte incelenir. Taşıma veya büyük yeniden düzenleme ayrı PR olmalıdır.
