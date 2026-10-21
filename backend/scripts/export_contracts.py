"""Writes docs/openapi.json and docs/schemas/*.json from the Pydantic models (B2)

Run with --check in CI to fail when committed files drift from the code
"""

import json
import sys
from pathlib import Path

from app.contracts.clients import ClientProfile, FeedItem
from app.contracts.events import Event, EventListItem
from app.contracts.insights import AgentTrace, BankPosition, Insight
from app.main import create_app

DOCS = Path(__file__).resolve().parents[2] / "docs"
SCHEMAS = {
    "Event": Event,
    "EventListItem": EventListItem,
    "ClientProfile": ClientProfile,
    "FeedItem": FeedItem,
    "BankPosition": BankPosition,
    "Insight": Insight,
    "AgentTrace": AgentTrace,
}


def render() -> dict[Path, str]:
    files = {DOCS / "openapi.json": create_app().openapi()}
    for name, model in SCHEMAS.items():
        files[DOCS / "schemas" / f"{name}.json"] = model.model_json_schema()
    return {
        path: json.dumps(data, ensure_ascii=False, indent=2) + "\n" for path, data in files.items()
    }


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    for path, content in render().items():
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(DOCS.parent)}")
    if stale:
        print("Contracts are out of date, run 'make contracts':", *stale, sep="\n  ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
