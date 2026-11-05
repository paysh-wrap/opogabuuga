"""Static checks on Paytience_Bridge.pine (no Pine compiler is available in CI).

Catches the mistakes that most often break a Pine script: unbalanced brackets/quotes, tabs or odd indentation,
assigning (:=) to a name that was never declared, and drift between the script and the Python contract.
"""

import re
from pathlib import Path

PINE = Path(__file__).resolve().parents[3] / "pine" / "Paytience_Bridge.pine"
SRC = PINE.read_text(encoding="utf-8")
CODE_LINES = [ln for ln in SRC.splitlines() if ln.strip() and not ln.lstrip().startswith("//")]


def _scan(line: str) -> tuple[str, bool]:
    """Replace string literals with '' and drop // comments. Returns (code, string_left_open)."""
    out, q, i = [], None, 0
    while i < len(line):
        ch = line[i]
        if q:
            if ch == "\\":
                i += 2
                continue
            if ch == q:
                q = None
                out.append("''")
        elif ch in "\"'":
            q = ch
        elif line.startswith("//", i):
            break
        else:
            out.append(ch)
        i += 1
    return "".join(out), q is not None


def test_header_and_license_attribution():
    assert SRC.startswith("//@version=6\n")
    for s in ("[LunqFX]", "[BigBeluga]", "PERSONAL USE ONLY", "spec-derived"):
        assert s in SRC


def test_brackets_and_quotes_balanced_per_statement():
    stmt = ""
    for ln in CODE_LINES:
        code, open_str = _scan(ln)
        assert not open_str, f"unterminated string: {ln}"
        stmt += code
        if (
            stmt.count("(") == stmt.count(")")
            and stmt.count("{") == stmt.count("}")
            and stmt.count("[") == stmt.count("]")
        ):
            stmt = ""
    assert stmt == "", f"unbalanced near: {stmt[:120]}"


def test_indentation_is_spaces_in_multiples_of_four():
    prev = ""
    for ln in CODE_LINES:
        assert "\t" not in ln
        ind = len(ln) - len(ln.lstrip(" "))
        continuation = prev.rstrip().endswith(("+", ",", "(", "and", "or", "?", ":")) or ln.lstrip().startswith(
            ("+", "'", '"', ",", ")")
        )
        if not continuation:
            assert ind % 4 == 0, ln
        prev = ln


def test_every_reassigned_name_is_declared():
    declared = set(
        re.findall(r"^\s*(?:var\s+)?(?:int|float|bool|string|array<float>)?\s*([A-Za-z_]\w*)\s*=(?!=)", SRC, re.M)
    )
    declared |= set(re.findall(r"^([A-Za-z_]\w*)\s*\(", SRC, re.M))  # functions
    declared |= set(re.findall(r"for\s+([A-Za-z_]\w*)\s*=", SRC))
    for name in set(re.findall(r"([A-Za-z_]\w*)\s*:=", SRC)) | set(re.findall(r"([A-Za-z_]\w*)\s*\+=", SRC)):
        assert name in declared, f"{name} reassigned but never declared"


def test_contract_matches_python_payload_schema():
    from app.webhook.schemas import FractalFields, MsoFields

    for f in FractalFields.model_fields:
        assert f'"{f}"' in SRC, f"fractal field {f} missing from the bridge"
    for f in MsoFields.model_fields:
        assert f'"{f}"' in SRC, f"mso field {f} missing from the bridge"
    for evt in (
        "HEARTBEAT",
        "C1_SWEPT",
        "CISD",
        "MODEL_CONFIRMED",
        "T1_HIT",
        "T2_HIT",
        "MODEL_FAILED",
        "C3_CLOSED",
        "MSO_CHOCH",
        "MSO_BOS",
        "MSO_DIV",
    ):
        assert f'"{evt}"' in SRC, evt
    assert 'evt + "-" + dir' in SRC  # id carries the direction (collision fix)
    assert "barstate.isconfirmed" in SRC and "lookahead" not in SRC and "request.security" not in SRC
    assert "hC > c1L and hC < c1H" in SRC  # pillar: C2 must close back inside C1
