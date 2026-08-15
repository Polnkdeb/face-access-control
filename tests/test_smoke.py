import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POC_DIR = ROOT / "poc"

sys.path.insert(
    0,
    str(POC_DIR)
)


from verifier import AccessVerifier


def test_happy_and_risky_paths(
    tmp_path
):

    events_path = (
        POC_DIR
        / "data"
        / "demo_events.json"
    )

    with events_path.open(
        "r",
        encoding="utf-8"
    ) as file:

        events = json.load(file)

    verifier = AccessVerifier(
        employees_path=(
            POC_DIR
            / "data"
            / "employees.json"
        ),

        audit_log_path=(
            tmp_path
            / "audit.jsonl"
        )
    )

    happy = verifier.verify(
        events[0]
    )

    risky = verifier.verify(
        events[1]
    )

    # Happy path

    assert (
        happy["decision"]
        == "allow"
    )

    assert (
        happy["turnstile_command"]
        == "open"
    )

    # Risky path

    assert (
        risky["decision"]
        == "manual_review"
    )

    assert (
        risky["turnstile_command"]
        is None
    )

    assert (
        risky[
            "requires_human_review"
        ]
        is True
    )

    # Audit log

    audit_path = (
        tmp_path
        / "audit.jsonl"
    )

    lines = (
        audit_path
        .read_text(
            encoding="utf-8"
        )
        .strip()
        .splitlines()
    )

    assert len(lines) == 2