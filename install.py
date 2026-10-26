"""Installer interaktif github-trello-sync.

Jalankan dari dalam folder repo GitHub yang ingin disinkronkan:

    python install.py

Installer akan:
  1. memeriksa git dan GitHub CLI (gh) sudah login;
  2. meminta API key dan token Trello, lalu memvalidasinya;
  3. menampilkan board dan list Trello untuk dipilih;
  4. menyimpan TRELLO_KEY dan TRELLO_TOKEN sebagai GitHub Secrets (tidak ditulis ke file);
  5. membuat file workflow .github/workflows/trello-sync.yml.
"""

from __future__ import annotations

import argparse
import getpass
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.trello.com/1"
DEFAULT_ACTION = "dasrams31/github-trello-sync@v1"
KEY_URL = "https://trello.com/power-ups/admin"


def say(text: str = "") -> None:
    print(text, flush=True)


def fail(text: str) -> None:
    say(f"\n[x] {text}")
    sys.exit(1)


def run(cmd: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, input=stdin, capture_output=True, text=True)


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or default


def choose(title: str, items: list[dict], allow_empty: bool = False) -> dict | None:
    say(f"\n{title}")
    for index, item in enumerate(items, start=1):
        say(f"  {index}. {item['name']}")
    if allow_empty:
        say("  0. (lewati)")
    while True:
        answer = input("Pilih nomor: ").strip()
        if allow_empty and answer == "0":
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(items):
            return items[int(answer) - 1]
        say("Nomor tidak valid, coba lagi.")


def trello(path: str, key: str, token: str, params: dict | None = None) -> dict | list:
    query = urllib.parse.urlencode({"key": key, "token": token, **(params or {})})
    try:
        with urllib.request.urlopen(f"{API}{path}?{query}", timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as err:
        if err.code in (400, 401):
            fail("API key atau token Trello tidak valid. Buat ulang lewat panduan di docs/TUTORIAL.md.")
        fail(f"Trello mengembalikan HTTP {err.code} untuk {path}.")
    except urllib.error.URLError as err:
        fail(f"Tidak bisa menghubungi Trello: {err.reason}")
    return {}


def check_tools(repo: str | None) -> tuple[Path, str]:
    if not shutil.which("git"):
        fail("git belum terpasang.")
    if not shutil.which("gh"):
        fail("GitHub CLI (gh) belum terpasang. Unduh di https://cli.github.com lalu jalankan 'gh auth login'.")
    if run(["gh", "auth", "status"]).returncode != 0:
        fail("GitHub CLI belum login. Jalankan 'gh auth login' terlebih dahulu.")

    top = run(["git", "rev-parse", "--show-toplevel"])
    if top.returncode != 0:
        fail("Jalankan installer dari dalam folder repo git yang ingin disinkronkan.")
    root = Path(top.stdout.strip())

    if not repo:
        view = run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
        if view.returncode != 0 or not view.stdout.strip():
            fail("Repo GitHub tidak terdeteksi. Pastikan remote 'origin' mengarah ke GitHub atau pakai --repo owner/nama.")
        repo = view.stdout.strip()
    return root, repo


def yaml_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def workflow(action: str, branches: str, settings: dict[str, str], categories: list[str]) -> str:
    branch_list = ", ".join(yaml_quote(b.strip()) for b in branches.split(",") if b.strip()) or "'**'"
    lines = [
        "name: Trello Sync",
        "",
        "on:",
        "  push:",
        f"    branches: [{branch_list}]",
        "",
        "permissions:",
        "  contents: read",
        "",
        "jobs:",
        "  trello:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        f"      - uses: {action}",
        "        with:",
        "          trello-key: ${{ secrets.TRELLO_KEY }}",
        "          trello-token: ${{ secrets.TRELLO_TOKEN }}",
    ]
    lines += [f"          {name}: {yaml_quote(value)}" for name, value in settings.items() if value]
    if categories:
        lines.append("          categories: |")
        lines += [f"            {line}" for line in categories]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Pasang sinkron commit GitHub ke Trello pada repo ini.")
    parser.add_argument("--repo", help="owner/nama repo GitHub (default: repo dari remote origin)")
    parser.add_argument("--action", default=DEFAULT_ACTION, help=f"versi action yang dipakai (default: {DEFAULT_ACTION})")
    parser.add_argument("--output", default=".github/workflows/trello-sync.yml", help="lokasi file workflow")
    parser.add_argument("--skip-secrets", action="store_true", help="jangan menyimpan secret (diatur manual)")
    args = parser.parse_args()

    say("=== github-trello-sync installer ===")
    root, repo = check_tools(args.repo)
    say(f"Repo GitHub : {repo}")
    say(f"Folder lokal: {root}")

    say(f"\nLangkah 1: API key Trello. Buat di {KEY_URL} (lihat docs/TUTORIAL.md).")
    key = getpass.getpass("API key Trello (tidak ditampilkan): ").strip()
    if not key:
        fail("API key wajib diisi.")
    token_url = f"https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&name=github-trello-sync&key={key}"
    say(f"\nLangkah 2: buka link ini, klik Allow, lalu salin token yang muncul:\n{token_url}")
    token = getpass.getpass("Token Trello (tidak ditampilkan): ").strip()
    if not token:
        fail("Token wajib diisi.")

    me = trello("/members/me", key, token, {"fields": "username,fullName"})
    say(f"\nTerhubung ke Trello sebagai {me.get('fullName') or me.get('username')}.")

    boards = trello("/members/me/boards", key, token, {"fields": "name", "filter": "open"})
    if not boards:
        fail("Akun ini belum punya board Trello yang terbuka.")
    board = choose("Langkah 3: pilih board", boards)
    lists = trello(f"/boards/{board['id']}/lists", key, token, {"fields": "name", "filter": "open"})
    if not lists:
        fail("Board ini belum punya list. Buat list seperti Backlog, In Progress, Done terlebih dahulu.")
    done = choose("Pilih list untuk pekerjaan SELESAI (mis. Done)", lists)
    progress = choose("Pilih list untuk commit [wip] (mis. In Progress)", lists, allow_empty=True)

    say("\nLangkah 4: pengaturan tambahan (Enter untuk default)")
    authors = ask("Filter penulis commit, pisahkan koma (kosong = semua penulis)")
    prefix = ask("Awalan nomor kartu di pesan commit", "TR")
    branches = ask("Branch yang disinkronkan, pisahkan koma ('**' = semua)", "**")
    create_untagged = ask("Buat kartu ringkasan untuk commit tanpa nomor kartu? (y/n)", "y").lower().startswith("y")
    say("Kategori judul kartu (opsional), format 'KODE: kata1, kata2'. Kosongkan baris untuk selesai.")
    categories = []
    while True:
        line = input("  kategori: ").strip()
        if not line:
            break
        if ":" in line:
            categories.append(line)
        else:
            say("  Format harus 'KODE: kata1, kata2'.")

    if not args.skip_secrets:
        say("\nLangkah 5: menyimpan secret ke GitHub...")
        for name, value in (("TRELLO_KEY", key), ("TRELLO_TOKEN", token)):
            result = run(["gh", "secret", "set", name, "--repo", repo], stdin=value)
            if result.returncode != 0:
                fail(f"Gagal menyimpan secret {name}: {result.stderr.strip()}. Pastikan kamu admin repo {repo}.")
            say(f"  Secret {name} tersimpan.")

    settings = {
        "board-id": board["id"],
        "done-list-id": done["id"],
        "progress-list-id": progress["id"] if progress else "",
        "card-prefix": prefix if prefix != "TR" else "",
        "authors": authors,
        "create-untagged": "" if create_untagged else "false",
    }
    target = root / args.output
    if target.exists() and ask(f"\n{args.output} sudah ada. Timpa? (y/n)", "n").lower() != "y":
        fail("Dibatalkan, file workflow tidak diubah.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(workflow(args.action, branches, settings, categories), encoding="utf-8", newline="\n")

    say(f"\nSelesai. Workflow ditulis ke {args.output}.")
    say("Langkah terakhir:")
    say(f"  git add {args.output}")
    say("  git commit -m \"ci: sinkron commit ke Trello\"")
    say("  git push")
    say(f"\nContoh pesan commit: \"feat: halaman login {prefix}-12\" memindahkan kartu nomor 12 ke list {done['name']}.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("\nDibatalkan.")
        sys.exit(130)
