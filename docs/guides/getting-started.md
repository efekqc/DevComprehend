# İlk katkı
```bash
git clone https://github.com/Anonymbordo/DevComprehend.git
cd DevComprehend
git switch main
git pull --ff-only
git switch -c docs/DC-001-scope
python3 scripts/check_repository.py
git add docs/product/mvp.md
git commit -m "docs(product): clarify MVP scope"
git push -u origin docs/DC-001-scope
```
Sonra GitHub üzerinde PR açın. Örnekteki dosyayı yalnızca gerçekten değiştirdiyseniz stage edin.

Şu an yalnızca Python 3 standart kütüphanesiyle repository kontrolü çalışır. Web/API geliştirme komutları henüz yoktur. Framework kurulumu DC-002 kararından sonra ayrı PR ile yapılır; ilgili servis README'sine kesin sürümler ve komutlar eklenir.
