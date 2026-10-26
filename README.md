# github-trello-sync

GitHub Action untuk mencatat progress pekerjaan dari commit ke board Trello secara otomatis. Setiap kali kamu `git push`, kartu Trello yang disebut di pesan commit dipindah ke list yang sesuai dan diberi komentar berisi daftar commit. Commit tanpa nomor kartu dirangkum menjadi satu kartu baru di list Done, jadi backlog dan laporan progress (misalnya untuk logbook magang atau sprint Scrum) tetap terisi tanpa diketik ulang.

Cocok untuk tim yang memakai Trello sebagai board Scrum (Backlog, In Progress, Done) dan GitHub sebagai repo kode.

## Fitur

- **Pindah kartu dari pesan commit.** Tulis `TR-12` (nomor kartu di board) atau tempel URL kartu `https://trello.com/c/AbCd1234`. Kartu dipindah ke list Done dan diberi komentar commit.
- **Status sedang dikerjakan.** Tambahkan `[wip]` di pesan commit untuk memindah kartu ke list In Progress, bukan Done.
- **Ringkasan otomatis.** Commit tanpa nomor kartu dikumpulkan menjadi satu kartu di list Done, lengkap dengan waktu, branch, nama developer, dan rincian commit.
- **Filter penulis.** Hanya catat commit dari orang tertentu (nama, email, atau username GitHub).
- **Kategori judul.** Beri awalan seperti `[FE]` atau `[DB]` berdasarkan kata kunci di pesan commit.
- **Installer interaktif** untuk Windows, macOS, dan Linux. Token tidak pernah ditulis ke file, hanya disimpan sebagai GitHub Secrets.
- **Tanpa dependensi.** Hanya butuh Python bawaan runner GitHub. Tidak ada server atau layanan pihak ketiga selain API Trello.

## Persyaratan

| Kebutuhan | Keterangan |
|---|---|
| Akun Trello | Punya akses ke board yang ingin dipakai |
| API key dan token Trello | Cara membuatnya ada di [Tutorial](docs/TUTORIAL.md#1-membuat-api-key-trello) |
| Repo GitHub | Kamu harus admin repo untuk menyimpan secret |
| Git | Untuk menjalankan installer dari folder repo |
| GitHub CLI (`gh`) | Sudah login (`gh auth login`), dipakai installer untuk menyimpan secret |
| Python 3.8+ | Hanya untuk installer di komputermu; di GitHub Actions sudah tersedia |

## Instalasi cepat

Buka terminal di **folder repo** yang ingin disinkronkan, lalu jalankan salah satu perintah berikut.

**Windows (PowerShell):**

```powershell
irm https://raw.githubusercontent.com/dasrams31/github-trello-sync/main/install.ps1 | iex
```

**macOS, Linux, atau Git Bash:**

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/dasrams31/github-trello-sync/main/install.sh)"
```

Installer akan:

1. Memeriksa `git` dan `gh`.
2. Meminta API key dan token Trello lalu memvalidasinya.
3. Menampilkan daftar board dan list untuk dipilih.
4. Menyimpan `TRELLO_KEY` dan `TRELLO_TOKEN` sebagai GitHub Secrets.
5. Membuat `.github/workflows/trello-sync.yml`.

Setelah selesai, commit dan push file workflow tersebut:

```bash
git add .github/workflows/trello-sync.yml
git commit -m "ci: sinkron commit ke Trello"
git push
```

Panduan langkah demi langkah dengan penjelasan setiap layar ada di **[docs/TUTORIAL.md](docs/TUTORIAL.md)**.

## Instalasi manual

1. Simpan secret `TRELLO_KEY` dan `TRELLO_TOKEN` di **Settings > Secrets and variables > Actions** repo kamu.
2. Salin [examples/trello-sync.yml](examples/trello-sync.yml) ke `.github/workflows/trello-sync.yml`.
3. Isi `board-id`, `done-list-id`, dan `progress-list-id`. Cara mencari ID ada di [Tutorial](docs/TUTORIAL.md#mencari-id-board-dan-list-secara-manual).

## Format pesan commit

| Pesan commit | Hasil di Trello |
|---|---|
| `feat: halaman login TR-12` | Kartu nomor 12 pindah ke Done + komentar commit |
| `[wip] dashboard admin TR-15` | Kartu nomor 15 pindah ke In Progress |
| `fix: validasi form https://trello.com/c/AbCd1234` | Kartu dengan link itu pindah ke Done |
| `feat: TR-3 TR-4 form proposal` | Kartu 3 dan 4 sama-sama dipindah |
| `docs: perbarui README` | Masuk ke kartu ringkasan baru di Done |
| `Merge branch 'main'` | Diabaikan |

Nomor kartu (`12` pada `TR-12`) adalah nomor yang muncul di URL kartu Trello, misalnya `https://trello.com/c/AbCd1234/12-halaman-login`. Awalan `TR` bisa diganti lewat input `card-prefix`.

## Input action

| Input | Wajib | Default | Keterangan |
|---|---|---|---|
| `trello-key` | Ya | | API key Trello, isi dengan `${{ secrets.TRELLO_KEY }}` |
| `trello-token` | Ya | | Token Trello, isi dengan `${{ secrets.TRELLO_TOKEN }}` |
| `done-list-id` | Ya | | ID list untuk pekerjaan selesai |
| `progress-list-id` | Tidak | kosong | ID list untuk commit `[wip]`; kosong berarti ke Done |
| `board-id` | Tidak | kosong | Wajib bila memakai nomor kartu seperti `TR-12` |
| `card-prefix` | Tidak | `TR` | Awalan nomor kartu di pesan commit |
| `authors` | Tidak | kosong | Filter penulis, dipisah koma; kosong berarti semua |
| `create-untagged` | Tidak | `true` | Buat kartu ringkasan untuk commit tanpa nomor kartu |
| `categories` | Tidak | kosong | Baris `KODE: kata1, kata2` untuk awalan judul kartu ringkasan |
| `timezone-offset` | Tidak | `7` | Zona waktu tanggal di kartu (WIB = 7, WITA = 8, WIT = 9) |
| `dry-run` | Tidak | `false` | Tampilkan rencana tanpa mengubah Trello |

## Keamanan

- API key dan token hanya disimpan sebagai GitHub Secrets dan tidak pernah ditulis ke file atau log.
- Token Trello memberi akses baca-tulis ke semua board di akunmu. Pakai akun atau token khusus bila repo dipakai banyak orang, dan cabut token lama di [trello.com/my/account](https://trello.com/my/account) bila bocor.
- Workflow hanya butuh izin `contents: read`.
- Pada repo publik, workflow dari pull request fork tidak mendapat secret, jadi sinkron hanya berjalan untuk push ke repo itu sendiri.

## Pemecahan masalah

| Gejala di log Actions | Penyebab | Solusi |
|---|---|---|
| `Secret TRELLO_KEY atau TRELLO_TOKEN belum diset` | Secret belum dibuat atau namanya beda | Jalankan installer lagi atau buat secret manual |
| `401 Unauthorized` | Token kedaluwarsa, dicabut, atau salah salin | Buat token baru lalu `gh secret set TRELLO_TOKEN` |
| `404 Not Found` | ID list/board salah, atau nomor kartu tidak ada di board | Cek ID dengan cara di Tutorial |
| Tidak ada kartu yang dibuat | Filter `authors` tidak cocok dengan penulis commit | Kosongkan `authors` atau sesuaikan dengan nama/email di `git log` |

Detail lebih lengkap ada di [Tutorial, bagian pemecahan masalah](docs/TUTORIAL.md#7-pemecahan-masalah).

## Pengembangan

```bash
python -m unittest discover -s tests -v
```

Logika sinkron ada di `src/sync.py` (hanya library standar Python). Installer ada di `install.py`, dengan pembungkus `install.sh` dan `install.ps1`.

## Lisensi

[MIT](LICENSE)
