"""D137: config/eval_odds.yaml loader (placeholder = not measured, validation, lookup, text)."""

import yaml

from app import eval_odds as E

ERA = {"pass": 70, "bust": 30, "stuck": 2, "open": 0, "days": 44}
ERA2 = {"pass": 55.5, "bust": 45, "stuck": 0, "open": 0, "days": 40}


def _cell(on, off):
    return {"all": on, "is": on, "j": off}


def _doc(study="real study"):
    t = {"contracts": 1, "brake": None, "eod_on": _cell(ERA, ERA2), "eod_off": _cell(ERA2, ERA)}
    return {"version": 1, "study": study, "source": "x", "plans": {"lucid_pro_25k": {"regular": t}}}


def _file(tmp_path, doc):
    p = tmp_path / "o.yaml"
    p.write_text(yaml.safe_dump(doc), encoding="utf-8")
    return p


def test_shipped_file_is_valid_and_complete():
    """config/eval_odds.yaml = the session-21 realistic sim (docs/results/session21/eod_toggle/RESULTS.md)."""
    E.load_odds.cache_clear()
    raw = yaml.safe_load(E.ODDS_PATH.read_text(encoding="utf-8"))
    f = E.OddsFile.model_validate(raw)
    assert not f.study.startswith("PLACEHOLDER") and len(f.plans) == 9
    assert all(set(t) == set(E.TABLES) for t in f.plans.values())
    assert E.load_odds() is not None
    v = E.odds_view("lucid_pro_25k", "regular", False)
    assert (v["pass_pct"], v["bust_pct"], v["last12_pass_pct"], v["last12_bust_pct"]) == (57, 43, 40, 60)
    E.load_odds.cache_clear()


def test_missing_invalid_and_placeholder_files_are_none(tmp_path):
    assert E.load_odds(tmp_path / "nope.yaml") is None
    bad = tmp_path / "bad.yaml"
    bad.write_text("version: 1\nplans: 3\n", encoding="utf-8")
    assert E.load_odds(bad) is None
    broken = tmp_path / "broken.yaml"
    broken.write_text("a: [", encoding="utf-8")
    assert E.load_odds(broken) is None
    assert E.load_odds(_file(tmp_path, _doc("PLACEHOLDER — not measured"))) is None


def test_lookup_text_and_view(tmp_path, monkeypatch):
    f = E.load_odds(_file(tmp_path, _doc()))
    assert f is not None
    monkeypatch.setattr(E, "load_odds", lambda: f)
    on, off = E.odds("lucid_pro_25k", "regular", True), E.odds("lucid_pro_25k", "regular", False)
    assert on is not None and off is not None and on.all.pass_ == 70 and off.all.pass_ == 55.5
    assert E.odds("lucid_pro_25k", "high", True) is None and E.odds("nope", "regular", True) is None
    assert E.odds_text(on, True) == "pass 70% / bust 30% · last 12 mo 56/45 · EOD toggle ON".replace("56", "55.5")
    assert E.odds_text(None, False) == "not measured yet"
    v = E.odds_view("lucid_pro_25k", "regular", False)
    assert v["text"].endswith("EOD toggle OFF") and (v["pass_pct"], v["last12_pass_pct"]) == (55.5, 70)
    assert E.odds_view("lucid_pro_25k", "high", False)["pass_pct"] is None


def test_table_for():
    assert E.table_for(True, True) == "high" and E.table_for(False, True) == "suggested"
    assert E.table_for(False, False) == "regular"
