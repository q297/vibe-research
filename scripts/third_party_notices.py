"""Generates THIRD_PARTY_NOTICES.md from the lock files

Covers only what ships in the product: runtime Python packages, production npm packages
and base Docker images. Models, datasets and external services are listed by hand in
the section that this script keeps between runs

Run: uv run --project backend python scripts/third_party_notices.py
"""

import json
import re
import subprocess
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "THIRD_PARTY_NOTICES.md"
MANUAL_START = "<!-- manual:start -->"
MANUAL_END = "<!-- manual:end -->"

MANUAL_DEFAULT = """## Модели, датасеты и сервисы

Этот раздел заполняется вручную и сохраняется при перегенерации файла.

| Что | Где используется | Лицензия или условия |
|---|---|---|
| LLM из разрешённого списка организаторов | агент (роль 4) | условия организаторов хакатона |
| Аналитика ЦМИ Альфа-Банка (9 PDF) | база знаний (роль 2) | условия организаторов хакатона |
| Обезличенные данные клиентов (CSV) | профили (роль 3) | условия организаторов хакатона |
| Let's Encrypt | HTTPS на стенде | Let's Encrypt Subscriber Agreement |
"""

# Base images from the Dockerfiles and compose files; keep in sync when they change
IMAGES = [
    ("python:3.12-slim", "образ API", "PSF-2.0 (Python), Debian"),
    ("ghcr.io/astral-sh/uv:0.13.4", "сборка образа API", "MIT OR Apache-2.0"),
    ("node:24.21.0-alpine", "сборка фронта", "MIT (Node.js), Alpine"),
    ("nginx:1.28-alpine", "раздача фронта", "BSD-2-Clause"),
    ("pgvector/pgvector:0.8.0-pg17", "база данных", "PostgreSQL License"),
    ("caddy:2.10.0-alpine", "HTTPS на стенде", "Apache-2.0"),
]


def _license_of(dist: metadata.Distribution) -> str:
    meta = dist.metadata
    expression = meta.get("License-Expression")
    if expression:
        return expression
    classifiers = [
        c.split(" :: ")[-1]
        for c in meta.get_all("Classifier") or []
        if c.startswith("License ::")
    ]
    if classifiers:
        # Classifier names are long and inconsistent with SPDX ids used elsewhere
        short = {
            "MIT License": "MIT",
            "Apache Software License": "Apache",
            "BSD License": "BSD",
        }
        return " OR ".join(short.get(c, c) for c in classifiers)
    text = (meta.get("License") or "").strip()
    # Some packages put the whole license text here, keep only the first line
    return text.splitlines()[0][:60] if text else "не указана"


def python_packages() -> list[tuple[str, str, str]]:
    exported = subprocess.run(
        ["uv", "export", "--no-dev", "--no-hashes", "--format", "requirements-txt"],
        cwd=ROOT / "backend",
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    rows = []
    for line in exported.splitlines():
        match = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s;]+)", line)
        if not match:
            continue
        name, version = match.groups()
        try:
            license_ = _license_of(metadata.distribution(name))
        except metadata.PackageNotFoundError:
            license_ = "не установлен локально"
        rows.append((name, version, license_))
    return sorted(rows, key=lambda r: r[0].lower())


def npm_packages() -> list[tuple[str, str, str]]:
    tree = json.loads(
        subprocess.run(
            ["npm", "ls", "--omit=dev", "--all", "--json"],
            cwd=ROOT / "frontend",
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    found: dict[str, str] = {}

    def walk(deps: dict) -> None:
        for name, info in (deps or {}).items():
            if name not in found and "version" in info:
                found[name] = info["version"]
                walk(info.get("dependencies", {}))

    walk(tree.get("dependencies", {}))
    rows = []
    for name, version in found.items():
        manifest = ROOT / "frontend" / "node_modules" / name / "package.json"
        license_ = "не указана"
        if manifest.exists():
            value = json.loads(manifest.read_text(encoding="utf-8")).get("license")
            license_ = (
                value if isinstance(value, str) else (value or {}).get("type", license_)
            )
        rows.append((name, version, license_))
    return sorted(rows)


def _table(rows: list[tuple[str, str, str]]) -> str:
    lines = ["| Пакет | Версия | Лицензия |", "|---|---|---|"]
    lines += [
        f"| {name} | {version} | {license_} |" for name, version, license_ in rows
    ]
    return "\n".join(lines)


def _manual_section() -> str:
    if OUTPUT.exists():
        text = OUTPUT.read_text(encoding="utf-8")
        if MANUAL_START in text and MANUAL_END in text:
            return (
                text.split(MANUAL_START, 1)[1].split(MANUAL_END, 1)[0].strip("\n")
                + "\n"
            )
    return MANUAL_DEFAULT


def main() -> None:
    images = ["| Образ | Зачем | Лицензия |", "|---|---|---|"]
    images += [f"| `{image}` | {why} | {license_} |" for image, why, license_ in IMAGES]
    parts = [
        "# Сторонние компоненты",
        (
            "Разделы про библиотеки и образы генерируются скриптом"
            " `scripts/third_party_notices.py` из lock-файлов. В список входит только то,"
            " что попадает в продукт; инструменты разработки (pytest, ruff, vite, typescript)"
            " не входят."
        ),
        MANUAL_START + "\n" + _manual_section() + MANUAL_END,
        "## Python (backend, `backend/uv.lock`)\n\n" + _table(python_packages()),
        "## JavaScript (frontend, `frontend/package-lock.json`)\n\n"
        + _table(npm_packages()),
        "## Docker-образы\n\n" + "\n".join(images),
    ]
    OUTPUT.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
