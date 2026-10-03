# ADR-0002: Extension-first ve paralel teslim
Durum: Kabul edildi (kullanıcı yönlendirmesi, 03.10.2026)
ADR-0001'in web-first dağıtım yaklaşımını değiştirir. Backend teknoloji önerileri ayrı karar olarak kalır.

- İlk kullanıcı yüzeyi apps/extension/ altında VS Code extension'dır.
- İlk veri kaynağı yerel Git staged/unstaged diff; GitHub OAuth başlangıç koşulu değildir.
- Ahmet host + Git adapter + webview; Derviş API; Murathan motor; Efe contracts/DB/CI.
- Herkes ilk gün ortak fixture ve adapter mock ile başlar.
- Sözleşme v1 başlangıç tabanıdır; küçük PR'larla güncellenir.
- apps/web/ gelecek portalı için ayrılmıştır.
- Marketplace yayını, gerçek ödeme ve Cursor uyumluluk iddiası pilot doğrulamasından sonra.
