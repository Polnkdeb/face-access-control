import json
from pathlib import Path

from verifier import AccessVerifier


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def main():

    events_path = (
        DATA_DIR / "demo_events.json"
    )

    with events_path.open(
        "r",
        encoding="utf-8"
    ) as file:

        events = json.load(file)

    audit_path = (
        BASE_DIR / "audit.jsonl"
    )

    # Удаляем старый demo-log перед запуском
    if audit_path.exists():
        audit_path.unlink()

    verifier = AccessVerifier(
        employees_path=(
            DATA_DIR / "employees.json"
        ),
        audit_log_path=audit_path
    )

    for event in events:

        result = verifier.verify(event)

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2
            )
        )

        print("-" * 50)


if __name__ == "__main__":
    main()