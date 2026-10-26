"""Sync GitHub push commits to Trello cards.

Runs inside the GitHub Action (see action.yml). Only the Python standard library is used, so the
action works on any runner that has python3.

Rules per commit:
  * A card reference moves that card: `TR-12` (card number on the board, needs board-id) or a
    Trello card URL `https://trello.com/c/AbCd1234`. The commit is added as a comment on the card.
  * `[wip]` in the message moves the referenced card to the "in progress" list instead of "done".
  * Commits without a card reference are summarised in one new card on the "done" list
    (turn off with create-untagged: false).
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

API = "https://api.trello.com/1"
URL_RE = re.compile(r"https?://trello\.com/c/([A-Za-z0-9]+)")
WIP_RE = re.compile(r"\[\s*wip\s*\]", re.IGNORECASE)
TAG_RE = re.compile(r"^\s*\[([A-Za-z0-9_\-]+)\]")
NON_CATEGORY_TAGS = {"WIP", "DONE", "FIX", "SKIP"}


class TrelloError(Exception):
    """A Trello API call failed."""


@dataclass
class Config:
    key: str
    token: str
    done_list: str
    progress_list: str = ""
    board: str = ""
    authors: list[str] = field(default_factory=list)
    prefix: str = "TR"
    create_untagged: bool = True
    categories: list[tuple[str, list[str]]] = field(default_factory=list)
    timezone_hours: int = 7
    dry_run: bool = False

    @classmethod
    def from_env(cls, env: dict[str, str]) -> "Config":
        return cls(
            key=env.get("TRELLO_KEY", "").strip(),
            token=env.get("TRELLO_TOKEN", "").strip(),
            done_list=env.get("DONE_LIST_ID", "").strip(),
            progress_list=env.get("PROGRESS_LIST_ID", "").strip(),
            board=env.get("BOARD_ID", "").strip(),
            authors=split_list(env.get("AUTHORS", "")),
            prefix=(env.get("CARD_PREFIX", "TR").strip() or "TR"),
            create_untagged=is_true(env.get("CREATE_UNTAGGED", "true")),
            categories=parse_categories(env.get("CATEGORIES", "")),
            timezone_hours=int(env.get("TIMEZONE_OFFSET", "7") or 7),
            dry_run=is_true(env.get("DRY_RUN", "false")),
        )


@dataclass
class CardMove:
    """Move an existing card and comment the commits that referenced it."""

    ref: str
    by_number: bool
    list_id: str
    lines: list[str]


@dataclass
class NewCard:
    list_id: str
    name: str
    desc: str


def is_true(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def split_list(value: str) -> list[str]:
    return [item.strip().lower() for item in re.split(r"[,\n]", value or "") if item.strip()]


def parse_categories(value: str) -> list[tuple[str, list[str]]]:
    """`KODE: kata1, kata2` per baris -> [(KODE, [kata1, kata2])]."""
    hasil = []
    for baris in (value or "").splitlines():
        if ":" not in baris:
            continue
        kode, kata = baris.split(":", 1)
        if kode.strip():
            hasil.append((kode.strip().upper(), split_list(kata)))
    return hasil


def subject(message: str) -> str:
    return (message or "").strip().splitlines()[0] if (message or "").strip() else "(tanpa pesan)"


def is_from_author(commit: dict, authors: list[str]) -> bool:
    if not authors:
        return True
    author = commit.get("author") or {}
    fields = [str(author.get(key, "")).lower() for key in ("name", "email", "username")]
    return any(wanted in value for wanted in authors for value in fields if value)


def card_refs(message: str, prefix: str) -> list[tuple[str, bool]]:
    """Card references in a commit message: (shortLink, False) or (number, True)."""
    refs: list[tuple[str, bool]] = [(link, False) for link in URL_RE.findall(message or "")]
    number_re = re.compile(rf"(?<![A-Za-z0-9]){re.escape(prefix)}-(\d+)\b", re.IGNORECASE)
    refs += [(number, True) for number in number_re.findall(message or "")]
    seen, unique = set(), []
    for ref in refs:
        if ref not in seen:
            seen.add(ref)
            unique.append(ref)
    return unique


def category(message: str, categories: list[tuple[str, list[str]]]) -> str:
    tag = TAG_RE.match(message or "")
    if tag and tag.group(1).upper() not in NON_CATEGORY_TAGS:
        return tag.group(1).upper()
    lower = (message or "").lower()
    for kode, kata in categories:
        if any(word in lower for word in kata):
            return kode
    return ""


def commit_line(commit: dict) -> str:
    author = (commit.get("author") or {}).get("name", "")
    sha = str(commit.get("id", ""))[:7]
    return f"- `{sha}` {subject(commit.get('message', ''))}" + (f" ({author})" if author else "")


def build_plan(commits: list[dict], config: Config, branch: str, now: datetime) -> list[CardMove | NewCard]:
    """Pure planning step: which cards to move and which card to create."""
    selected = [
        c for c in commits
        if is_from_author(c, config.authors) and not subject(c.get("message", "")).startswith("Merge ")
    ]
    moves: dict[tuple[str, bool], CardMove] = {}
    untagged: list[dict] = []

    for commit in selected:
        message = commit.get("message", "")
        refs = card_refs(message, config.prefix)
        if not refs:
            untagged.append(commit)
            continue
        target = config.progress_list if (WIP_RE.search(message) and config.progress_list) else config.done_list
        for ref, by_number in refs:
            if by_number and not config.board:
                untagged.append(commit)
                break
            move = moves.setdefault((ref, by_number), CardMove(ref, by_number, target, []))
            move.list_id = target
            move.lines.append(commit_line(commit))

    plan: list[CardMove | NewCard] = list(moves.values())

    if untagged and config.create_untagged:
        latest = subject(untagged[-1].get("message", ""))
        kode = category(latest, config.categories)
        authors = sorted({(c.get("author") or {}).get("name", "") for c in untagged} - {""})
        waktu = now.strftime("%d/%m/%Y %H:%M") + f" (UTC{config.timezone_hours:+d})"
        desc = "\n".join([
            "**Status:** Done",
            f"**Waktu:** {waktu}",
            f"**Branch:** `{branch}`",
            f"**Developer:** {', '.join(authors) or '-'}",
            f"**Jumlah commit:** {len(untagged)}",
            "",
            "**Rincian pekerjaan:**",
            *[commit_line(c) for c in untagged],
            "",
            "_Dibuat otomatis oleh github-trello-sync._",
        ])
        plan.append(NewCard(config.done_list, f"[{kode}] {latest}" if kode else latest, desc))

    return plan


class Trello:
    def __init__(self, key: str, token: str) -> None:
        self.auth = {"key": key, "token": token}

    def request(self, method: str, path: str, params: dict | None = None) -> dict | list:
        query = urllib.parse.urlencode({**self.auth, **(params or {})})
        if method == "GET":
            req = urllib.request.Request(f"{API}{path}?{query}", method="GET")
        else:
            req = urllib.request.Request(f"{API}{path}", data=query.encode(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode() or "{}"
                return json.loads(body)
        except urllib.error.HTTPError as err:
            if err.code == 401:
                raise TrelloError("401 Unauthorized: TRELLO_KEY/TRELLO_TOKEN salah, kedaluwarsa, atau tidak punya akses ke board ini.") from None
            if err.code == 404:
                raise TrelloError(f"404 Not Found: {path} tidak ditemukan (cek ID board/list/kartu).") from None
            raise TrelloError(f"HTTP {err.code} pada {method} {path}") from None
        except urllib.error.URLError as err:
            raise TrelloError(f"Tidak bisa menghubungi Trello: {err.reason}") from None


def execute(plan: list[CardMove | NewCard], client: Trello, config: Config) -> None:
    for step in plan:
        if isinstance(step, NewCard):
            if config.dry_run:
                print(f"[dry-run] buat kartu di list {step.list_id}: {step.name}")
                continue
            client.request("POST", "/cards", {"idList": step.list_id, "name": step.name, "desc": step.desc, "pos": "top"})
            print(f"Kartu dibuat: {step.name}")
            continue

        path = f"/boards/{config.board}/cards/{step.ref}" if step.by_number else f"/cards/{step.ref}"
        label = f"{config.prefix}-{step.ref}" if step.by_number else step.ref
        if config.dry_run:
            print(f"[dry-run] pindahkan kartu {label} ke list {step.list_id} + komentar {len(step.lines)} commit")
            continue
        card = client.request("GET", path, {"fields": "name"})
        client.request("PUT", f"/cards/{card['id']}", {"idList": step.list_id, "pos": "top"})
        client.request("POST", f"/cards/{card['id']}/actions/comments", {"text": "Commit terkait:\n" + "\n".join(step.lines)})
        print(f"Kartu {label} ({card.get('name', '')}) dipindah dan diberi komentar.")


def main() -> int:
    config = Config.from_env(dict(os.environ))
    if not config.key or not config.token:
        print("::warning::Secret TRELLO_KEY atau TRELLO_TOKEN belum diset. Sinkron Trello dilewati.")
        return 0
    if not config.done_list:
        print("::error::Input done-list-id wajib diisi.")
        return 1

    try:
        commits = json.loads(os.environ.get("COMMITS_JSON") or "[]") or []
    except json.JSONDecodeError:
        commits = []
    if not commits:
        print("Tidak ada commit pada event ini (bukan push atau push kosong). Selesai.")
        return 0

    now = datetime.now(timezone(timedelta(hours=config.timezone_hours)))
    plan = build_plan(commits, config, os.environ.get("REF_NAME", ""), now)
    if not plan:
        print("Tidak ada commit yang cocok dengan filter penulis. Selesai.")
        return 0

    try:
        execute(plan, Trello(config.key, config.token), config)
    except TrelloError as err:
        print(f"::error::{err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
