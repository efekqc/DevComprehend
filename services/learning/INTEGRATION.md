# DC-006 / DC-007 entegrasyon teslimi

Durum: Yerel modül ve mock doğrulama hazır; ekip incelemesi, gerçek API/DB bağlantısı ve canlı model doğrulaması bekliyor. Bu belge paylaşım teslimidir; ekip arkadaşlarına mesaj gönderildiği veya onay alındığı anlamına gelmez.

## Derviş — API çağrısı

1. Oturum kullanıcısını doğrula; quota rezervasyonunu ve önizleme/onay akışını uygula. Motor onay kanıtı üretmez.
2. Analiz kaydını kullanıcıya bağlı queued ID ile oluştur. `generate(request, analysis_id=saved_id)` çalıştır; bloklayan HTTP adaptörünü async event loop üzerinde doğrudan çalıştırma.
3. `LearningError` için güvenli hata zarfını ortak HTTP eşlemelerine çevir: INVALID_INPUT → 400, STALE_SNAPSHOT → 409, PAYLOAD_TOO_LARGE → 413. INSUFFICIENT_EVIDENCE ilk aşamada 400 ve kullanıcıya kapsamı değiştirme açıklaması; ortak hata listesi genişletilecekse Efe ile koordine et.
4. Dönen `ready`/`failed` kaydını aynı kullanıcı + analiz ID altında sakla. Payload'dan gelen repository_id yetki kanıtı değildir.
5. Cevapta analiz ve question_id sahipliğini kontrol et; **soruyu ve rubriği sunucu kaydından yükle**. İstemcinin değiştirdiği rubrikle puan verme.
6. `submission_id` için aynı kullanıcı/analiz içinde aynı isteği tekrar çağırma; farklı cevap metniyle aynı ID gelirse çakışmayı ele al. `evaluate(saved_question, answer_request)` sonucunu cevapla birlikte atomik kaydet.
7. `due_at != null` ve `uncertain == false` olduğunda tekrar kaydını güncelle. Belirsiz deneme eski güvenilir kaydı silmez. Sonucun hangi soruya ait olduğunu göster.

API sahipliği ayrıca kimlik doğrulama, kullanıcı izolasyonu, günlük analiz/cevap kotası, quota rezervasyonu, `submission_id` idempotency, kalıcılık ve silme/retention davranışını kapsar. Bunlar öğrenme motorunda uygulanmış değildir; canlı pilot öncesi Derviş ve Efe doğrulamalıdır.

Motor process içi cache veya DB içermez. Fingerprint sunucu idempotency'sinin yerine geçmez. V1 `submission_id` değerlendirme cevabında taşınmadığı için ilişki API çağrı bağlamında kurulmalıdır.

## Efe — sözleşme, kalıcılık ve kalite

Ortak schema ve beş örnek değiştirilmedi. Üretim `analysis_result`; değerlendirme `evaluation_result` biçiminde. Kavramlar v1'de soru üzerindeki `concept` alanlarının farklı değerleridir, ek `concepts` alanı eklenmedi.

Yan kayıt gereksinimi: analysis_id, submission_id, user_id (sunucu), pipeline sürümü, `on_usage` verisi, tekrar politika sürümü `repetition-2`. Prompt/model bilgisi v1 mesajlarına eklenmedi. `due_at` timezone bilgili UTC ISO-8601 veya null; DB timestamp with time zone eşlemesi beklenir. Motor migration oluşturmaz.

Retention süresi ve kullanıcı silme akışı henüz kararlaştırılıp uygulanmadı. Kaynak diff'i ve cevaplar için asgari saklama, erişim ve silme kuralları API/DB tesliminde belirlenmeli; bu modül kalıcı veri tutmaz.

Snapshot özeti yalnız diff'i kapsar. Kullanıcı dosyayı değiştirirse extension eski kaynakları yeni dosyaya sessizce bağlamamalı. Bağlam parçalarını ofsetli taşımak veya silinen satırlara soru bağlamak için v2/koordineli sözleşme değişikliği gerekir. Şimdilik context tam dosyadır, atıflar yalnız yeni diff hunk'larına yapılır.

CI'ye eklenmesi önerilen alan komutları README'dedir; ortak CI dosyası değiştirilmedi. Testler mevcut ortak fixture'ları doğrudan okur. Şema geçerliliği, doğru/yararlı geri bildirim kanıtı değildir.

## Ahmet — sidebar dili

Extension, filtrelenmiş diff'i ve ilişkili bağlamı önizleme/onaydan önce eşleştirmeli, 400 satır veya 16.000 karakter sınırını aşan seçimi göndermeden durdurup kullanıcıya daha küçük staged/unstaged parçası seçmesini söylemelidir. Filtre sonrası snapshot tam gönderilecek diff üzerinden hesaplanır; motor bu onayı kendisi vermez.

| Backend durumu | Kullanıcı metni / davranış |
|---|---|
| Henüz cevap yok | Değerlendirilmedi |
| uncertain=true | Bu cevap güvenilir biçimde değerlendirilemedi; açıklamanı genişletebilir veya yeniden deneyebilirsin. |
| developing | Bu cevapta eksik kalan noktalar var. Rubrik geri bildirimini göster. |
| demonstrated | Bu soruda beklenen anlayışı gösterdin. |
| due_at=null | Yeni tekrar tarihi oluşturulmadı; “bugün” veya sıfır puan gösterme. |
| failed analysis | Güvenli error.message; retryable=true ise kullanıcı kontrollü tekrar deneme. |

Rubrik cevaplanmadan gösterilirse kullanıcı cevabı kopyalayabilir; soru ekranı beklenen cevapları gizlemeli. Kaynaklar snapshot'a bağlıdır; canlı dosya uyuşmazsa salt okunur kayıt/önizleme göster. Model metnini çalıştırılabilir HTML gibi render etme. Genel teknoloji yüzdesi, badge ve AI yazarlığı oranı üretme.

## Kalan kabul işleri

- Canlı modelle kaynak doğruluğu ve feedback/rubrik tutarlılığı: Murathan + Efe.
- Kimlik/kota/idempotency, kayıt ve due_at persistence: Derviş + Efe.
- Gerçek extension → preview → API → motor → kayıt akışı, VSIX ve Cursor testi: Ahmet + ekip.
- Pilot sonuçları, yanlış değerlendirme örnekleri ve devam kararı: gerçek veri toplandıktan sonra ekip.
