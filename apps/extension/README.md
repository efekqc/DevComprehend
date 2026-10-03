# VS Code extension
Sorumlu: Ahmet. Çalışan extension henüz yok.
Planlanan alanlar:
- src/host/: komut, Git adapter, snapshot, onay, API client, webview mesaj doğrulama.
- src/webview/: sidebar, soru, cevap, kaynak ve tekrar görünümü.
- tests/: host/UI birim kontrolleri.
- README: debug, test ve VSIX üretim komutları.

İlk iş feat/DC-003-extension: contracts/v1/examples/ fixture ile sidebar. Derviş'i beklemeden mock API adapter kullan.
Git diff yalnız kullanıcı komutuyla toplanır; gönderilecek kapsam önizlenir. Cursor uyumluluğu test edilmeden destek iddiası yok.
