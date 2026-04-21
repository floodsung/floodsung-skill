#!/usr/bin/env python3
"""Remove MetaBot auto-posted answers from the scraped corpus.

Signals:
1. `— MetaBot (github.com/xvirobotics/metabot)` at the tail (11 cases)
2. Explicit self-declaration `这条知乎回答就是MetaBot...`
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scraper import dump_markdown  # noqa

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "zhihu"

SIG = re.compile(r"—\s*MetaBot\s*\(", re.IGNORECASE)
DECLARE = re.compile(r"这条知乎回答.*?MetaBot|MetaBot.*?浏览器自动化.*?知乎", re.IGNORECASE)


def is_bot(body: str) -> bool:
    return bool(SIG.search(body) or DECLARE.search(body))


def main():
    src = DATA / "answers.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    kept, removed = [], []
    for a in data:
        body = a.get("content_md", "") or ""
        (removed if is_bot(body) else kept).append(a)

    print(f"total: {len(data)}, keep: {len(kept)}, remove: {len(removed)}")
    for r in removed:
        print(f"  - {r['question'][:70]}")

    # Also archive the removed ones for transparency
    (DATA / "answers_metabot_excluded.json").write_text(
        json.dumps(removed, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    src.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
    dump_markdown(kept, DATA / "answers.md", "answers")

    summary = json.loads((DATA / "summary.json").read_text())
    summary["counts"]["answers"] = len(kept)
    summary["metabot_excluded"] = len(removed)
    (DATA / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\ndone. new summary: {summary}")


if __name__ == "__main__":
    main()
