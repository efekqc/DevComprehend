# Başlangıç backlog'u
Bu tablo planlı işleri içerir; GitHub issue nesneleri henüz oluşturulmadı.

| ID | İş | Önerilen kişi | Bağımlılık | Kabul sonucu |
|---|---|---|---|---|
| DC-001 | Kapsam ve pilot ölçütleri | Murathan | Yok | MVP ve pilot eşikleri ekipçe onaylı |
| DC-002 | Stack, ortam ve veri sözleşmesi | Efe | DC-001 | ADR, sürümler, şema ve yerel komutlar |
| DC-003 | Repo seçim ve soru ekranları | Ahmet | DC-002 | Mock veriyle boş/hata/başarılı akış |
| DC-004 | GitHub erişimi ve bounded diff | Derviş | DC-002 | Yetkili repo, sabit SHA, boyut sınırı |
| DC-005 | Kullanıcı ve analiz saklama | Efe | DC-002 | Migration ve kullanıcı izolasyonu |
| DC-006 | Kavram, soru ve rubrik üretimi | Murathan | DC-004 | Kaynak kanıtlı, şema geçerli çıktı |
| DC-007 | Cevap değerlendirme ve tekrar | Murathan + Derviş | DC-005, DC-006 | Rubrik, belirsizlik ve tekrar tarihi |
| DC-008 | Entegrasyon ve maliyet kontrolleri | Efe | DC-003–007 | Uçtan uca akış ve token sınırı |
| DC-009 | Pilot ve geri bildirim | Tüm ekip | DC-008 | Ölçüm raporu ve devam kararı |
