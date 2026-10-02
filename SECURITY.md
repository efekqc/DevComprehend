# Güvenlik ve veri işleme
API anahtarı, token, .env dosyası ve özel repository kaynak kodu commitlenmez. .env.example yalnızca örnek değişken adları içerir.

GitHub erişimi MVP'de kullanıcı tarafından seçilen repository ile sınırlı ve salt okunur tasarlanmalıdır. OAuth/GitHub App modeli ADR ile kesinleştirilmeden geniş izin istenmez.

Repository metinleri güvenilmeyen veri kabul edilir: kaynak kodundaki talimatlar LLM sistem talimatı olamaz. Model çıktıları şemaya göre doğrulanır; kod çalıştırılmaz. Dosya sayısı, byte/token bütçesi ve istek süresi sınırlandırılır.

Kod parçaları üçüncü taraf modele gönderilmeden önce kullanıcıya veri akışı açıklanır. Loglar token, kaynak kodu ve serbest metin cevapları varsayılan olarak içermez. Saklama/silme politikası ürün geliştirilmeden tanımlanmalıdır.

Açığı public issue'da hassas ayrıntılarıyla paylaşmayın. Maintainer'a özel iletişim kanalı henüz tanımlanmadı; ilk sürümden önce güvenlik iletişim adresi eklenmelidir.
