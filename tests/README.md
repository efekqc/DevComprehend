# Kalite ve entegrasyon
Sorumlu: Efe. Modül içi testler modül sahiplerinde kalır.
Planlanan alanlar contract/, integration/, e2e/, fixtures/.
İlk gün ortak fixture testleri; sonra extension → API → motor → DB.
Kritik senaryolar: boş/büyük diff, Git olmayan workspace, stale snapshot, unauthorized analysis, invalid model JSON, quota, duplicate submission.
Canlı LLM kalite seti deterministik CI'dan ayrı, bütçeli çalışır. VSIX kurulumu VS Code'da doğrulanır; Cursor ayrıca kontrol edilir.
