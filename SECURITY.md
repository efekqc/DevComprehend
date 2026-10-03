# Extension ve backend güvenliği
Kullanıcının komutu ve önizleme/onayı olmadan kaynak kodu aktarılmaz. Git olmayan veya güvenilmeyen workspace davranışı extension uygulamasında tanımlanır.
Dosya ve token sınırları hem istemci hem sunucuda uygulanır. Binary/generated dosyalar atlanır; .env/anahtar dosyaları bağlama dahil edilmez.
Webview mesajları host'ta doğrulanır. LLM anahtarları backend'de; kullanıcı oturum tokenı güvenli istemci saklama alanında. Üretim auth/kota yapılmadan gerçek pilot açılmaz.
Kaynak kodundaki talimatlar güvenilmeyen veridir; kod çalıştırılmaz. Kaynak, token ve cevaplar varsayılan loglarda yoktur.
Saklama, silme ve üçüncü taraf model aktarımı pilot öncesi açıklanır. GitHub izni ilk MVP'de gerekmez.
Güvenlik iletişim kanalı henüz belirlenmedi; hassas açık ayrıntıları public issue'ya yazılmaz.
