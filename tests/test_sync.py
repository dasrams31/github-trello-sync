import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import sync  # noqa: E402

NOW = datetime(2026, 10, 27, 9, 30, tzinfo=timezone(timedelta(hours=7)))


def commit(message, name="Rama", email="rama@example.com", username="dasrams31", sha="abcdef1234"):
    return {"id": sha, "message": message, "author": {"name": name, "email": email, "username": username}}


def config(**overrides):
    values = {"key": "k", "token": "t", "done_list": "DONE", "progress_list": "WIP", "board": "BOARD"}
    values.update(overrides)
    return sync.Config(**values)


class FakeTrello:
    def __init__(self):
        self.calls = []

    def request(self, method, path, params=None):
        self.calls.append((method, path, params or {}))
        return {"id": "card-id", "name": "Login"} if method == "GET" else {}


class CardRefTest(unittest.TestCase):
    def test_finds_numbers_and_urls_once(self):
        refs = sync.card_refs("feat: login TR-12 tr-12 https://trello.com/c/AbCd1234/5-x TR-7", "TR")
        self.assertEqual(refs, [("AbCd1234", False), ("12", True), ("7", True)])

    def test_prefix_must_stand_alone(self):
        self.assertEqual(sync.card_refs("fix XTR-12 and ATR-3", "TR"), [])
        self.assertEqual(sync.card_refs("fix CARD-3", "card"), [("3", True)])


class FilterTest(unittest.TestCase):
    def test_author_filter_matches_name_email_or_username(self):
        self.assertTrue(sync.is_from_author(commit("x"), ["dasrams"]))
        self.assertTrue(sync.is_from_author(commit("x"), ["example.com"]))
        self.assertFalse(sync.is_from_author(commit("x", "Budi", "budi@x.id", "budi"), ["dasrams"]))
        self.assertTrue(sync.is_from_author(commit("x", "Budi", "budi@x.id", "budi"), []))

    def test_categories_from_tag_or_keywords(self):
        rules = sync.parse_categories("FE: blade, css\nDB: migration, schema\ninvalid line")
        self.assertEqual(rules, [("FE", ["blade", "css"]), ("DB", ["migration", "schema"])])
        self.assertEqual(sync.category("[AUTH] login page", rules), "AUTH")
        self.assertEqual(sync.category("[wip] fix css", rules), "FE")
        self.assertEqual(sync.category("add schema", rules), "DB")
        self.assertEqual(sync.category("docs", rules), "")


class PlanTest(unittest.TestCase):
    def test_referenced_cards_move_and_wip_goes_to_progress(self):
        plan = sync.build_plan([
            commit("feat: login TR-12", sha="1111111aaa"),
            commit("[wip] dashboard https://trello.com/c/Xy9", sha="2222222bbb"),
        ], config(), "main", NOW)

        moves = {step.ref: step for step in plan if isinstance(step, sync.CardMove)}
        self.assertEqual(moves["12"].list_id, "DONE")
        self.assertTrue(moves["12"].by_number)
        self.assertEqual(moves["Xy9"].list_id, "WIP")
        self.assertIn("`1111111` feat: login TR-12 (Rama)", moves["12"].lines[0])
        self.assertFalse(any(isinstance(step, sync.NewCard) for step in plan))

    def test_wip_without_progress_list_falls_back_to_done(self):
        plan = sync.build_plan([commit("[wip] TR-3")], config(progress_list=""), "main", NOW)
        self.assertEqual(plan[0].list_id, "DONE")

    def test_untagged_commits_become_one_summary_card(self):
        plan = sync.build_plan([
            commit("feat: blade view"),
            commit("Merge branch 'main'"),
            commit("fix: css", name="Budi", username="budi", email="b@x.id"),
        ], config(categories=[("FE", ["css", "blade"])]), "magang", NOW)

        self.assertEqual(len(plan), 1)
        card = plan[0]
        self.assertIsInstance(card, sync.NewCard)
        self.assertEqual(card.name, "[FE] fix: css")
        self.assertIn("**Developer:** Budi, Rama", card.desc)
        self.assertIn("**Jumlah commit:** 2", card.desc)
        self.assertIn("27/10/2026 09:30 (UTC+7)", card.desc)
        self.assertNotIn("Merge", card.desc)

    def test_number_refs_without_board_are_summarised(self):
        plan = sync.build_plan([commit("feat TR-9")], config(board=""), "main", NOW)
        self.assertIsInstance(plan[0], sync.NewCard)

    def test_untagged_can_be_disabled_and_authors_filtered(self):
        cfg = config(create_untagged=False, authors=["budi"])
        self.assertEqual(sync.build_plan([commit("feat: x"), commit("TR-1")], cfg, "main", NOW), [])


class ExecuteTest(unittest.TestCase):
    def test_moves_card_by_number_then_comments(self):
        client = FakeTrello()
        plan = [sync.CardMove("12", True, "DONE", ["- `abc` feat"])]
        sync.execute(plan, client, config())

        self.assertEqual(client.calls[0][:2], ("GET", "/boards/BOARD/cards/12"))
        self.assertEqual(client.calls[1], ("PUT", "/cards/card-id", {"idList": "DONE", "pos": "top"}))
        self.assertEqual(client.calls[2][1], "/cards/card-id/actions/comments")

    def test_dry_run_makes_no_calls(self):
        client = FakeTrello()
        plan = [sync.CardMove("Xy9", False, "DONE", ["x"]), sync.NewCard("DONE", "judul", "isi")]
        sync.execute(plan, client, config(dry_run=True))
        self.assertEqual(client.calls, [])


class ConfigTest(unittest.TestCase):
    def test_reads_environment(self):
        cfg = sync.Config.from_env({
            "TRELLO_KEY": " k ", "TRELLO_TOKEN": "t", "DONE_LIST_ID": "D", "AUTHORS": "Rama, dasrams31",
            "CREATE_UNTAGGED": "false", "CARD_PREFIX": "", "DRY_RUN": "yes",
        })
        self.assertEqual((cfg.key, cfg.prefix, cfg.authors), ("k", "TR", ["rama", "dasrams31"]))
        self.assertFalse(cfg.create_untagged)
        self.assertTrue(cfg.dry_run)


if __name__ == "__main__":
    unittest.main()
