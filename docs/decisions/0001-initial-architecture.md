# ADR-0001: Başlangıç mimarisi
Durum: Kısmen ADR-0002 ile değiştirildi
Önceki web-first MVP yerini extension-first MVP'ye bıraktı.
Backend için Python + FastAPI, veri için PostgreSQL önerisi korunur; sürümler ve paket yöneticileri DC-002'de ekipçe kesinleşir.
İlk sürümde Redis/Celery/vector DB zorunlu değildir. learning API içinde modül olabilir; ayrı microservice zorunlu değil.
Güncel karar: [ADR-0002](0002-extension-first-parallel-delivery.md).
