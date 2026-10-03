# Extension-first backlog
v2.0. Kimlikler plan kimliğidir; henüz GitHub issue numarası değildir.

| ID | İş | Sorumlu | İlk gün başlangıç | Entegrasyon kabulü |
|---|---|---|---|---|
| DC-001 | Kapsam ve pilot | Murathan | Kullanıcı akışı, ölçüm | Ekipçe pilot eşikleri |
| DC-002 | Sözleşme/DB ortamı | Efe | v1 fixture, schema kontrolü | Tüm tüketiciler uyumlu |
| DC-003 | Extension/Git/sidebar | Ahmet | Mock API, fixture | Yerel diff → sidebar → cevap |
| DC-004 | Analiz backend API | Derviş | Fake motor, memory store | Kimlik, quota, idempotency |
| DC-005 | Kalıcı veri | Efe | Migration/seed | Sahiplik ve tekrar kaydı |
| DC-006 | Kavram/soru/rubrik | Murathan | Fixture, fake provider | Şema geçerli kanıtlı çıktı |
| DC-007 | Cevap/tekrar | Murathan + Derviş | Sabit soru/cevap fixture | Değerlendirme + kayıt |
| DC-008 | E2E ve paket kontrolü | Efe; tüm ekip destek | Mock senaryolar | Extension → API → motor → DB |
| DC-009 | Pilot ve karar | Tüm ekip | Görüşme/ölçüm taslağı | Ölçüm ve devam kararı |

DC-003/004/006/002 **aynı anda başlar**. Gerçek bağlantı için ilgili çıktılar gerekir; ilk geliştirme için mock kullanılır.
