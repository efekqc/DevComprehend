# DC-001 / DC-009 — Pilot protokolü v1

Tarih: 03 Ekim 2026. Durum: Veri toplamadan önce ekip incelemesine hazır öneri. Ekip onayı ve başlangıç tarihi henüz kaydedilmedi; pilot başlamadı. Sorumlu Murathan; kalite eş incelemesi Efe, entegrasyon Derviş/Ahmet.

## Hipotez ve katılım

10–20 gönüllü AI ile kod geliştiren kullanıcı, kendi onayladığı küçük bir yerel staged/unstaged diff üzerinden soruları cevaplayarak davranış ve mimari belirsizlikleri daha iyi açıklayabilir. Kullanıcı önce yalnız paylaşma yetkisi olan örnekle çalışır. GitHub hesabı, ödeme veya Marketplace kurulumu gerekmez; test edilebilir VSIX gerekir. VS Code ve Cursor sonuçları ayrı kaydedilir, test edilmemiş uyumluluk ilan edilmez.

Önerilen ücretsiz pilot kotası kullanıcı başına günlük 5 analiz ve 20 cevap değerlendirmesi. Kesin hesap/model bütçesi pilot öncesi ekipçe belirlenir; bu belge sunucuda uygulanmış kota değildir. API quota rezervasyonu ve harcama üst sınırı olmadan canlı pilot açılmaz.

## Pilot öncesi kontrol

- VSIX kurulumu, yerel Git seçimi, önizleme iptali ve onay sonrası aktarım test edilmiş olmalı.
- Model adı, prompt/pipeline/politika sürümleri ve maliyet tavanı kayıtlı olmalı.
- Kaynak/snapshot doğruluğu ve 7 sentetik cevapta rubrik tutarlılığı insan tarafından incelenmeli; fake etiket eşleşmesi canlı kalite kanıtı değildir.
- En az 30 kesin değerlendirme, model sonucunu görmeyen iki incelemeci tarafından rubrik ölçütü düzeyinde puanlanıp uzlaştırılmalı. Pilot kalite kapısı, modelin uzlaştırılmış insan rubriğiyle ölçüt bazında en az %85 uyumudur; uncertain sonuçlar bu paydaya girmez ve belirsizlik oranı ayrıca raporlanır.
- Kullanıcı izolasyonu, kalıcılık, silme ve yeniden deneme kontrolleri tamamlanmalı.
- Aşağıdaki eşikler, veri saklama yaklaşımı ve görüşme formu ekipçe kararlaştırılıp tarih/sürümle dondurulmalı. Sonradan değişirse gerekçesi ayrı raporlanmalı.

## Görev oturumu

1. Kullanıcı AI ile değiştirdiği küçük bir kod parçasını seçer. Gözlemci yardım etmeden önce ne yaptığını ve bir kontrol kaldırılırsa ne olacağını açıklamasını ister; 0/1/2 gözlem notu alır.
2. Kullanıcı scope seçer, önizlemeyi inceler; bir kez iptal ederek aktarım olmadığını doğrular, sonra paylaşmak istediği içeriği onaylar.
3. 3–5 soru görünür. Kullanıcı kendi cümleleriyle cevaplar, geri bildirimi inceler. Gözlemci cevabı öğretmez; yardım gerekiyorsa işaretlenir.
4. Kullanıcı aynı kavramın başka bir küçük değişiklik senaryosunu model yardımı olmadan açıklar. Önceki cevapla eşdeğer rubrikte kör değerlendirme yapılır.
5. Tekrar ekranı incelenir; kullanıcı 7 günlük gözlem aralığında geri dönmeye davet edilir. Hatırlatmalı ve kendiliğinden dönüş ayrı raporlanır.

## Olay ve payda tanımları

Ham kod/cevap yerine minimum olay alanları: takma kullanıcı ID, session_id, analysis_id, UTC zaman, editor/sürüm, pipeline/prompt/model sürümü, status/error_code ve token sayıları. Repository dosya yolu, kaynak, cevap, API key ve ham provider yanıtı telemetriye eklenmez. Kullanıcı ID'si sunucu oturumundan gelir.

| Ölçüt | Tanım |
|---|---|
| Başlatılan oturum | Kullanıcının Analyze Changes komutunu çalıştırdığı benzersiz session_id. 30 dakika etkinlik yoksa yeni oturum. Tekrarlanan event ID sayılmaz. |
| Onay dönüşümü | En az bir preview_approved olan ilk oturum / tüm ilk oturumlar. İptal ve boş diff ayrıca sayılır. |
| Teknik başarı | analysis_ready / onaylanmış analiz talepleri; aynı idempotent isteğin retry'ı yeni talep sayılmaz. failed ayrı hata koduyla raporlanır. |
| Oturum tamamlama | İlk ready analizindeki tüm 3–5 soruya boş olmayan cevap verip her biri için güvenilir evaluation_result alan kullanıcı / ilk ready analizine ulaşan kullanıcı. uncertain tamamlanmış sayılmaz, ayrıca oranlanır. |
| Uçtan uca tamamlama | Yukarıdaki tamamlayan kullanıcı / komutu başlatan tüm kullanıcı. Ready öncesi kayıpları gizlememek için ana oranla birlikte raporlanır. |
| 7 günlük tekrar kullanım | İlk ready zamanından 24 saat sonra ve en geç 168 saat içinde başka bir oturumda yeni bir cevap veya tekrar cevabı veren kullanıcı / ilk ready üzerinden en az 168 saat gözlenmiş kullanıcı. Henüz 7 günü dolmayanlar paydaya alınmaz. |
| Yanlış kesin değerlendirme | İnsan rubriğiyle uyuşmayan, uncertain=false model sonuçları / kör incelenmiş uncertain=false sonuçlar. Yanlış demonstrated ayrıca sayılır. İki incelemeci anlaşmazlığı önce uzlaştırır. |
| Belirsizlik oranı | uncertain=true / tüm değerlendirme denemeleri; sağlayıcı hataları ayrıca ayrılır. |
| Açıklama gelişimi | Önce/sonra eşdeğer senaryoda gözlemci rubriği artan kullanıcı / iki ölçümü tamamlayan kullanıcı. 0: yanlış/yok, 1: kısmi, 2: davranış ve sınırı doğru açıklıyor. |
| İlk soru değeri | “Bu soru kendi kodunda daha önce düşünmediğin neyi gösterdi?” cevabı; 1–5 fayda görüşü ayrı kaydedilir, davranış metriğinin yerine konmaz. |

Her oran pay/payda ve mutlak sayıyla raporlanır. 10–20 kişilik örnek istatistiksel genelleme sağlamaz. Önce/sonra iyileşme öğretim, tekrar ve gözlem etkilerini ayıramaz; nedensel öğrenme kanıtı diye sunulmaz.

## Veri öncesi karar eşikleri — öneri

En az 10 kullanıcıda ilk oturum ve en az 10 kullanıcıda olgunlaşmış 7 günlük takip yoksa **karar için veri yetersiz**. Kalite için en az 30 kesin değerlendirme kör incelenmeli; erişilemezse kalite kararı da bekler.

**Devam:** Oturum tamamlama ≥ %70, 7 günlük tekrar kullanım ≥ %40, yanlış kesin değerlendirme ≤ %10 ve açıklama gelişimi ≥ %60. Kaynak/snapshot hatası, onaysız aktarım veya kullanıcı izolasyonu sorunu olmamalı. Uçtan uca tamamlama ayrıca sunulur; hazır analize ulaşamayanlar saklanmaz.

**Daralt ve düzelt:** Yeterli veri varken bu eşiklerden biri karşılanmıyorsa bırakma nedenine göre tek kavram türü, daha küçük diff veya daha kısa oturum denenir; yeni özellik eklemek ilk çözüm sayılmaz.

**Pilotu durdurup düzelt:** Onaysız kaynak aktarımı, başka kullanıcının verisine erişim veya yanlış snapshot'a kaynak bağlama görülürse teknik neden düzeltilip tekrar test edilmeden pilot sürdürülmez.

## Görüşme formu

Katılımcı takma ID: … · Tarih: … · Editor/sürüm: … · Analiz/pipeline: … · Yardım aldı mı: …

1. Seçtiğin değişiklik ne yapıyor? Bir kontrol kaldırılırsa davranış nasıl değişir?
2. Önizlemede gönderilecek içeriği anlayabildin mi? Paylaşmak istemediğin bir şey var mıydı?
3. İlk soru sana ne öğretti? Kodu incelemeden genel bilgiyle cevaplanabilecek kadar genel miydi?
4. Geri bildirimin hangi kısmı doğru/eksik/yanlıştı? İzin varsa sadece sentetikleştirilmiş bir örnek kaydedelim.
5. “Değerlendirilmedi” ile “bu cevapta eksik var” durumlarını nasıl yorumladın?
6. Nerede bırakmak veya yardım almak istedin? Neden?
7. Son senaryodaki davranışı şimdi model yardımı olmadan açıklar mısın?
8. 1–5 fayda görüşün nedir, tekrar kullanmak için ne değişmeli? Bu yanıt satın alma kanıtı değildir.

## Saklama önerisi ve raporlama

Kaynak bağlamını analiz için gerekli süreyle sınırlandırma, kullanıcı geçmişini açık silme kontrolüyle sunma ve takma ID'li pilot olaylarını rapor tamamlandıktan sonra temizleme önerilir. Kesin saklama süreleri ve silme mekanizması Derviş/Efe tarafından uygulanıp kullanıcıya gösterilmeden gerçek kaynakla pilot başlatılmaz. Şu an modül yalnız bellekte işler; kalıcı depolama veya otomatik silme uygulandığı iddia edilmez.

Ürün kararını [rapor şablonunda](pilot-report.md) kaydet. Gerçek kullanıcı kaynak kodu ve cevaplarını repository'ye koyma; hata örneklerini sentetikleştirip yeniden doğrula.
