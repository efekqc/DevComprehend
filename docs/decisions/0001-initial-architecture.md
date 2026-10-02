# ADR-0001: MVP repository ve teknoloji yaklaşımı
Durum: Öneri
## Bağlam
Dört kişilik ekip, GitHub diff üzerinden öğrenme hipotezini doğrulayacak. Dağıtık servis karmaşıklığı ilk hedef değildir.
## Öneri
- Monorepo; web, api, learning ve sözleşmeler ayrı alanlarda.
- Web için TypeScript + React tabanlı uygulama.
- API ve öğrenme modülü için Python + FastAPI.
- Kalıcı veri için PostgreSQL.
- İlk sürümde Redis, Celery, vektör veritabanı zorunlu değil.
- Önce manuel analiz tetikleme; webhook/GitHub App sonraki karar.
## Sonuç
Ekip paralel çalışabilir; learning modülünün API ile paket sınırı açık tutulur. Framework sürümleri ve paket yöneticileri DC-002'de kesinleşir. Bu belge kurulu bağımlılık veya çalışan servis belirtmez.
## Alternatif
Tüm backend'i TypeScript yapmak: tek dil avantajı; ekibin Python öğrenme motoru deneyimiyle birlikte değerlendirilmeli.
