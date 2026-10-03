# Katkı akışı
Herkes aynı anda kendi alanında ve görev branch'inde çalışır. [Paralel rehber](docs/team/parallel-work.md) branch, staging, push ve birleştirme adımlarını içerir.
1. main'i güncelle; görev branch'i aç.
2. Alanın fixture/mock adapter'ıyla başla; diğer modülü bekleme.
3. Yalnız ilgili dosyaları stage et; kısa commit oluştur.
4. Branch'i push et; main'e PR aç.
5. En az bir başka ekip üyesi incelesin; kontrollerden sonra squash merge önerilir.
6. Main değişikliklerini görev branch'ine merge ederek al.

Sözleşmeleri Efe koordine eder; kök/shared dosyaları haber vermeden değiştirme. main'e force push yapılmaz.
Definition of Done: kabul kriteri, test/demo kanıtı, güncel README/sözleşme, gizli bilgi olmaması, çözülmüş inceleme geri bildirimi.
Branch protection ayrıca ayarlanmalıdır; bu belge otomatik kural kurulumu değildir.
