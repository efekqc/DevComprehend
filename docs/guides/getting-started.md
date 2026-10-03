# İlk katkı
```bash
git clone https://github.com/Anonymbordo/DevComprehend.git
cd DevComprehend
git switch main
git pull --ff-only origin main
git switch -c feat/DC-003-extension
python3 scripts/check_repository.py
```
Kişiye özel branch/alan için [paralel çalışma rehberi](../team/parallel-work.md).

Fixture doğrulaması için geliştirme ortamında jsonschema kurulu olmalıdır:
```bash
python3 scripts/check_contract_examples.py
```
Extension/API/motor henüz scaffold edilmedi. İlk PR'da paket yöneticisi, kesin sürüm, kurulum ve run/test komutlarını ilgili README'ye ekleyin. Mock akışla başlayın; gerçek kullanıcı kodu test fixture'ı olarak commitlenmez.
