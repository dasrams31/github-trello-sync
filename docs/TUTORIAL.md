# Tutorial lengkap github-trello-sync

Panduan ini membawa kamu dari nol sampai setiap `git push` otomatis tercatat di board Trello. Perkiraan waktu: 10 sampai 15 menit.

Isi:

1. [Membuat API key Trello](#1-membuat-api-key-trello)
2. [Membuat token Trello](#2-membuat-token-trello)
3. [Menyiapkan board Trello](#3-menyiapkan-board-trello)
4. [Menyiapkan komputer](#4-menyiapkan-komputer)
5. [Menjalankan installer](#5-menjalankan-installer)
6. [Memakai sehari-hari](#6-memakai-sehari-hari)
7. [Pemecahan masalah](#7-pemecahan-masalah)
8. [Memasang untuk satu tim](#8-memasang-untuk-satu-tim)

---

## 1. Membuat API key Trello

Trello memberikan API key lewat halaman admin Power-Up.

1. Login ke Trello, lalu buka **https://trello.com/power-ups/admin**.
2. Klik **New** untuk membuat Power-Up atau integrasi baru.
3. Isi formulir:
   - **New Power-Up or Integration name:** misalnya `github-trello-sync`.
   - **Workspace:** pilih workspace tempat board kamu berada.
   - **Email, Support contact, Author:** isi email dan namamu.
   - **Iframe connector URL:** boleh dikosongkan.
4. Klik **Create**.
5. Di halaman Power-Up yang baru dibuat, buka tab **API key**, lalu klik **Generate a new API key**.
6. Salin nilai **API key**. Nilai ini yang nanti diminta installer.

> API key bukan rahasia besar, tetapi tetap jangan ditempel di file repo. Installer menyimpannya sebagai GitHub Secret.

## 2. Membuat token Trello

Token adalah izin agar action boleh membaca dan mengubah board atas namamu.

Kamu tidak perlu membuatnya sendiri: installer akan menampilkan link seperti ini setelah kamu memasukkan API key:

```
https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&name=github-trello-sync&key=API_KEY_KAMU
```

1. Buka link tersebut di browser yang sudah login Trello.
2. Klik **Allow**.
3. Salin token panjang yang muncul, lalu tempel ke installer.

Alternatifnya, di tab **API key** halaman Power-Up ada link **Token** di samping API key yang menghasilkan token yang sama.

> **Jaga token seperti password.** Siapa pun yang memegang token bisa mengubah semua board di akunmu. Bila bocor, cabut di **https://trello.com/my/account** bagian aplikasi yang terhubung, lalu buat token baru.

## 3. Menyiapkan board Trello

Action ini butuh minimal satu list tujuan. Susunan yang disarankan untuk Scrum:

| List | Dipakai untuk |
|---|---|
| Backlog | Daftar tugas yang belum dikerjakan |
| In Progress | Kartu yang sedang dikerjakan (commit `[wip]`) |
| Done | Kartu selesai dan kartu ringkasan commit |

Setiap kartu Trello punya nomor. Lihat URL kartu: pada `https://trello.com/c/AbCd1234/12-halaman-login`, nomornya **12**. Nomor inilah yang kamu tulis di pesan commit sebagai `TR-12`.

## 4. Menyiapkan komputer

Pastikan tiga alat ini sudah ada:

| Alat | Cek | Cara pasang |
|---|---|---|
| Git | `git --version` | https://git-scm.com/downloads |
| GitHub CLI | `gh --version` | https://cli.github.com |
| Python 3.8+ | `python --version` atau `py --version` | https://www.python.org/downloads/ |

Lalu login GitHub CLI dengan akun yang menjadi **admin** repo:

```bash
gh auth login
```

Pilih `GitHub.com`, `HTTPS`, lalu ikuti login lewat browser. Cek dengan `gh auth status`.

## 5. Menjalankan installer

Buka terminal **di dalam folder repo** yang ingin disinkronkan (folder yang berisi `.git`).

**Windows PowerShell:**

```powershell
cd C:\path\ke\repo-kamu
irm https://raw.githubusercontent.com/dasrams31/github-trello-sync/main/install.ps1 | iex
```

**macOS, Linux, atau Git Bash:**

```bash
cd ~/path/ke/repo-kamu
sh -c "$(curl -fsSL https://raw.githubusercontent.com/dasrams31/github-trello-sync/main/install.sh)"
```

Bila sudah meng-clone repo github-trello-sync, kamu juga bisa menjalankan `python /path/ke/github-trello-sync/install.py` dari folder repo target.

Yang akan ditanyakan installer:

| Pertanyaan | Isi |
|---|---|
| API key Trello | Dari langkah 1 (tidak tampil saat diketik) |
| Token Trello | Dari langkah 2 (tidak tampil saat diketik) |
| Pilih board | Nomor board dari daftar |
| List untuk pekerjaan SELESAI | Biasanya `Done` |
| List untuk commit [wip] | Biasanya `In Progress`, atau `0` untuk lewati |
| Filter penulis commit | Kosongkan agar semua anggota tercatat, atau isi nama/email/username, dipisah koma |
| Awalan nomor kartu | Enter untuk `TR` |
| Branch yang disinkronkan | Enter untuk semua branch (`**`), atau misalnya `main, develop` |
| Kartu ringkasan untuk commit tanpa nomor | `y` agar commit biasa tetap tercatat |
| Kategori | Opsional, misalnya `FE: blade, css, view` lalu `DB: migration, schema`. Enter kosong untuk selesai |

Installer lalu menyimpan secret `TRELLO_KEY` dan `TRELLO_TOKEN` ke repo, dan menulis `.github/workflows/trello-sync.yml`. Terakhir, push file workflow:

```bash
git add .github/workflows/trello-sync.yml
git commit -m "ci: sinkron commit ke Trello"
git push
```

Buka tab **Actions** di GitHub. Job **Trello Sync** seharusnya hijau, dan kartu ringkasan untuk commit tadi muncul di list Done.

### Opsi installer

| Opsi | Fungsi |
|---|---|
| `--repo owner/nama` | Tentukan repo GitHub bila remote `origin` bukan GitHub |
| `--action owner/repo@versi` | Pakai fork atau versi action lain |
| `--output path` | Lokasi file workflow (default `.github/workflows/trello-sync.yml`) |
| `--skip-secrets` | Lewati penyimpanan secret, misalnya bila diatur admin lain |

Contoh: `python install.py --repo tim-saya/proyek --skip-secrets`.

### Mencari ID board dan list secara manual

Bila memasang tanpa installer:

1. Buka board di browser, tambahkan `.json` di akhir URL board, misalnya `https://trello.com/b/AbCd1234/nama-board.json`.
2. Cari `"id"` paling atas: itu **board-id**.
3. Cari bagian `"lists"`: setiap list punya `"id"` dan `"name"`. Salin ID list Done dan In Progress.

## 6. Memakai sehari-hari

Tulis nomor kartu di pesan commit:

```bash
git commit -m "feat: halaman login TR-12"            # kartu 12 ke Done
git commit -m "[wip] dashboard admin TR-15"          # kartu 15 ke In Progress
git commit -m "fix: validasi form TR-3 TR-4"         # kartu 3 dan 4 ke Done
git commit -m "docs: perbarui README"                # masuk kartu ringkasan
git push
```

Hasilnya:

- Kartu yang disebut berpindah list dan mendapat komentar berisi hash dan judul commit.
- Commit tanpa nomor kartu dikumpulkan menjadi satu kartu baru di Done per push, berisi waktu, branch, nama developer, dan daftar commit. Kartu ini berguna sebagai bahan logbook atau laporan sprint.
- Commit merge (`Merge branch ...`) diabaikan.

Tips:

- Satu push bisa berisi banyak commit; kartu yang sama hanya dipindah sekali dan diberi satu komentar.
- Bila commit terakhir untuk sebuah kartu bertanda `[wip]`, kartu berakhir di In Progress.
- Tambahkan `[KODE]` di awal pesan commit, misalnya `[AUTH] login google`, untuk memaksa awalan judul kartu ringkasan.

### Mencoba tanpa mengubah Trello

Tambahkan `dry-run: 'true'` di bagian `with:` workflow. Log Actions akan menampilkan rencana seperti `[dry-run] pindahkan kartu TR-12 ke list ...` tanpa mengubah board.

## 7. Pemecahan masalah

**`Secret TRELLO_KEY atau TRELLO_TOKEN belum diset. Sinkron Trello dilewati.`**
Secret belum ada di repo tempat workflow berjalan. Cek **Settings > Secrets and variables > Actions**, atau jalankan:

```bash
gh secret set TRELLO_KEY
gh secret set TRELLO_TOKEN
```

**`401 Unauthorized`**
Token salah salin, sudah dicabut, atau dibuat dengan API key lain. Buat token baru (langkah 2) lalu simpan ulang dengan `gh secret set TRELLO_TOKEN`. Pastikan juga akun pemilik token adalah anggota board.

**`404 Not Found`**
- ID list atau board salah: cek ulang lewat cara manual di atas.
- Nomor kartu tidak ada di board yang diatur di `board-id`.
- Link kartu menunjuk ke board yang tidak bisa diakses token.

**Job hijau tapi tidak ada kartu baru**
- Filter `authors` tidak cocok. Lihat nama dan email penulis dengan `git log --format='%an <%ae>'`, lalu sesuaikan atau kosongkan `authors`.
- `create-untagged` diset `false` dan commit tidak menyebut nomor kartu.
- Push hanya berisi commit merge.

**Installer berhenti di "GitHub CLI belum login"**
Jalankan `gh auth login`, lalu `gh auth status` untuk memastikan akun yang aktif adalah admin repo.

**PowerShell menolak menjalankan skrip**
Jalankan sekali `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, atau pakai perintah `irm ... | iex` di atas yang tidak membutuhkan file skrip lokal.

**`python` membuka Microsoft Store di Windows**
Pasang Python dari python.org dan centang **Add python.exe to PATH**. Installer otomatis mencoba `py`, `python`, lalu `python3`.

## 8. Memasang untuk satu tim

- Cukup **satu orang admin** menjalankan installer per repo. Anggota tim lain hanya perlu menulis nomor kartu di pesan commit.
- Biarkan `authors` kosong agar commit semua anggota tercatat, dan nama tiap developer akan muncul di kartu ringkasan.
- Bila ingin kartu terpisah per orang, pasang beberapa job di workflow yang sama dengan `authors` berbeda.
- Untuk organisasi, simpan `TRELLO_KEY` dan `TRELLO_TOKEN` sebagai **organization secret** agar bisa dipakai banyak repo sekaligus. Jalankan installer dengan `--skip-secrets` di setiap repo.
