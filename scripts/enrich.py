#!/usr/bin/env python3
"""Fetch full content for each article/answer/pin from Zhihu detail APIs."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scraper import ZhihuClient, clean_html_to_md, dump_markdown  # noqa: E402

from bs4 import BeautifulSoup


def enrich_articles(client: ZhihuClient, items: list[dict]) -> list[dict]:
    out = []
    for i, a in enumerate(items):
        aid = a["id"]
        url = f"https://www.zhihu.com/api/v4/articles/{aid}"
        try:
            d = client.get(url)
            a["content_md"] = clean_html_to_md(d.get("content", ""))
            a["excerpt"] = d.get("excerpt", a.get("excerpt", ""))
        except Exception as e:
            print(f"  [{i+1}/{len(items)}] FAIL {aid}: {e}")
        else:
            print(f"  [{i+1}/{len(items)}] {a['title'][:50]} → {len(a['content_md'])} chars")
        out.append(a)
        time.sleep(0.6)
    return out


def enrich_answers(client: ZhihuClient, items: list[dict]) -> list[dict]:
    out = []
    for i, a in enumerate(items):
        ans_id = a["id"]
        url = f"https://www.zhihu.com/api/v4/answers/{ans_id}?include=content,excerpt"
        try:
            d = client.get(url)
            a["content_md"] = clean_html_to_md(d.get("content", ""))
            a["excerpt"] = d.get("excerpt", "")
        except Exception as e:
            print(f"  [{i+1}/{len(items)}] FAIL ans{ans_id}: {e}")
        else:
            print(f"  [{i+1}/{len(items)}] {a['question'][:50]} → {len(a['content_md'])} chars")
        out.append(a)
        time.sleep(0.6)
    return out


def enrich_pins(client: ZhihuClient, items: list[dict]) -> list[dict]:
    out = []
    for i, p in enumerate(items):
        pid = p["id"]
        url = f"https://www.zhihu.com/api/v4/pins/{pid}"
        try:
            d = client.get(url)
            blocks = d.get("content", []) or []
            texts = []
            for b in blocks:
                if b.get("type") == "text":
                    html = b.get("content", "")
                    texts.append(BeautifulSoup(html, "lxml").get_text(" ", strip=True))
            p["text"] = "\n".join(t for t in texts if t) or p.get("text", "")
        except Exception as e:
            print(f"  [{i+1}/{len(items)}] FAIL pin{pid}: {e}")
        else:
            print(f"  [{i+1}/{len(items)}] pin{pid} → {len(p['text'])} chars")
        out.append(p)
        time.sleep(0.4)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--kinds", default="articles,pins,answers")
    args = ap.parse_args()

    cookie = os.environ.get("ZHIHU_COOKIE", "").strip()
    if not cookie:
        print("ERROR: export ZHIHU_COOKIE", file=sys.stderr)
        sys.exit(1)

    client = ZhihuClient(cookie)
    d = Path(args.dir)
    kinds = [k.strip() for k in args.kinds.split(",")]

    for kind in kinds:
        path = d / f"{kind}.json"
        if not path.exists():
            print(f"skip {kind}, no file")
            continue
        items = json.loads(path.read_text(encoding="utf-8"))
        print(f"\n=== enrich {kind} ({len(items)}) ===")
        fn = {"articles": enrich_articles, "pins": enrich_pins, "answers": enrich_answers}[kind]
        items = fn(client, items)
        path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        dump_markdown(items, d / f"{kind}.md", kind)
        print(f"saved {kind}")


if __name__ == "__main__":
    main()
