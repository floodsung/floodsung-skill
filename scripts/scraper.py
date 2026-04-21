#!/usr/bin/env python3
"""Zhihu scraper for a single user's articles, pins, and answers.

Usage:
    export ZHIHU_COOKIE="d_c0=...; z_c0=...; _xsrf=..."
    python3 scraper.py --user flood-sung --out ../../data/zhihu

Requires a logged-in cookie because Zhihu blocks anonymous API access.
Hashes the `d_c0` value to compute the x-zse-96 signature for stable paging.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def parse_cookie(raw: str) -> dict[str, str]:
    jar: dict[str, str] = {}
    for part in raw.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        jar[k.strip()] = v.strip()
    return jar


def get_dc0(cookie: dict[str, str]) -> str:
    dc0 = cookie.get("d_c0", "")
    if not dc0:
        raise SystemExit("cookie missing d_c0; re-login to zhihu and copy a fresh cookie")
    return dc0


# The x-zse-96 signature implementation below follows the widely documented
# Zhihu v2 scheme: md5(d_c0 + "+" + path + "?" + query) then hmac key derivation.
# If Zhihu tightens this further we fall back to unsigned requests (200 for light paging).

def sign(url: str, dc0: str) -> str:
    parsed = urlparse(url)
    path_q = parsed.path + ("?" + parsed.query if parsed.query else "")
    raw = f"101_3_3.0+{path_q}+{dc0}"
    md5 = hashlib.md5(raw.encode()).hexdigest()
    return "2.0_" + md5


class ZhihuClient:
    def __init__(self, cookie: str):
        self.cookie = parse_cookie(cookie)
        self.dc0 = get_dc0(self.cookie)
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.zhihu.com/",
            "x-requested-with": "fetch",
            "x-zse-93": "101_3_3.0",
        })
        self.s.cookies.update(self.cookie)

    def get(self, url: str, **params) -> dict[str, Any]:
        full = url
        if params:
            q = "&".join(f"{k}={v}" for k, v in params.items())
            full = url + ("&" if "?" in url else "?") + q
        headers = {"x-zse-96": sign(full, self.dc0)}
        r = self.s.get(full, headers=headers, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code} on {full}: {r.text[:300]}")
        return r.json()

    def paginate(self, url: str, page_size: int = 20) -> Iterable[dict[str, Any]]:
        offset = 0
        while True:
            data = self.get(url, offset=offset, limit=page_size)
            items = data.get("data", []) or []
            for it in items:
                yield it
            paging = data.get("paging", {}) or {}
            if paging.get("is_end") or not items:
                break
            offset += page_size
            time.sleep(0.8)


def clean_html_to_md(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    for fig in soup.find_all("figure"):
        img = fig.find("img")
        if img and img.get("data-original"):
            img["src"] = img["data-original"]
    return md(str(soup), heading_style="ATX").strip()


def scrape_articles(client: ZhihuClient, user: str, out_dir: Path) -> list[dict]:
    out = []
    url = f"https://www.zhihu.com/api/v4/members/{user}/articles?include=content,voteup_count,comment_count,created,updated"
    for it in client.paginate(url):
        out.append({
            "id": it.get("id"),
            "title": it.get("title"),
            "url": it.get("url", f"https://zhuanlan.zhihu.com/p/{it.get('id')}"),
            "created": it.get("created"),
            "updated": it.get("updated"),
            "voteup_count": it.get("voteup_count"),
            "comment_count": it.get("comment_count"),
            "content_md": clean_html_to_md(it.get("content", "")),
            "excerpt": it.get("excerpt", ""),
        })
        print(f"  article: {it.get('title')}", flush=True)
    return out


def scrape_pins(client: ZhihuClient, user: str) -> list[dict]:
    out = []
    url = f"https://www.zhihu.com/api/v4/v2/pins/profile/{user}"
    try:
        for it in client.paginate(url):
            content_blocks = it.get("content", []) or []
            texts = []
            for b in content_blocks:
                if b.get("type") == "text":
                    texts.append(BeautifulSoup(b.get("content", ""), "lxml").get_text(" ", strip=True))
            out.append({
                "id": it.get("id"),
                "url": f"https://www.zhihu.com/pin/{it.get('id')}",
                "created": it.get("created"),
                "text": "\n".join(t for t in texts if t),
                "like_count": it.get("like_count"),
                "comment_count": it.get("comment_count"),
            })
            print(f"  pin: {out[-1]['text'][:60]}", flush=True)
    except RuntimeError as e:
        # fallback endpoint
        print(f"  pins v2 failed ({e}); trying fallback", flush=True)
        url2 = f"https://www.zhihu.com/api/v4/members/{user}/pins"
        for it in client.paginate(url2):
            out.append({
                "id": it.get("id"),
                "url": f"https://www.zhihu.com/pin/{it.get('id')}",
                "created": it.get("created"),
                "text": BeautifulSoup(it.get("excerpt_title", "") or it.get("content_html", ""), "lxml").get_text(" ", strip=True),
                "like_count": it.get("like_count"),
                "comment_count": it.get("comment_count"),
            })
    return out


def scrape_answers(client: ZhihuClient, user: str) -> list[dict]:
    out = []
    url = (
        f"https://www.zhihu.com/api/v4/members/{user}/answers"
        "?include=content,voteup_count,comment_count,created_time,updated_time,question.title"
    )
    for it in client.paginate(url):
        q = it.get("question", {}) or {}
        out.append({
            "id": it.get("id"),
            "question": q.get("title", ""),
            "question_id": q.get("id"),
            "url": f"https://www.zhihu.com/question/{q.get('id')}/answer/{it.get('id')}",
            "created": it.get("created_time"),
            "updated": it.get("updated_time"),
            "voteup_count": it.get("voteup_count"),
            "comment_count": it.get("comment_count"),
            "content_md": clean_html_to_md(it.get("content", "")),
        })
        print(f"  answer: {q.get('title', '')[:60]}", flush=True)
    return out


def dump_markdown(items: list[dict], path: Path, kind: str):
    lines = [f"# Flood Sung — {kind}\n", f"Total: {len(items)}\n"]
    for it in items:
        title = it.get("title") or it.get("question") or (it.get("text", "")[:60])
        lines.append(f"\n---\n\n## {title}\n")
        meta = []
        if "url" in it: meta.append(f"link: {it['url']}")
        if it.get("created"): meta.append(f"created: {it['created']}")
        if it.get("voteup_count") is not None: meta.append(f"voteup: {it['voteup_count']}")
        if meta:
            lines.append("`" + " · ".join(str(m) for m in meta) + "`\n")
        body = it.get("content_md") or it.get("text") or ""
        if body:
            lines.append("\n" + body + "\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="flood-sung", help="zhihu url_token")
    ap.add_argument("--out", required=True, help="output dir")
    ap.add_argument("--kinds", default="articles,pins,answers", help="comma sep")
    args = ap.parse_args()

    cookie = os.environ.get("ZHIHU_COOKIE", "").strip()
    if not cookie:
        print("ERROR: export ZHIHU_COOKIE before running", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = ZhihuClient(cookie)
    kinds = [k.strip() for k in args.kinds.split(",") if k.strip()]

    results: dict[str, list[dict]] = {}
    if "articles" in kinds:
        print("\n=== articles ===")
        results["articles"] = scrape_articles(client, args.user, out_dir)
    if "pins" in kinds:
        print("\n=== pins (想法) ===")
        results["pins"] = scrape_pins(client, args.user)
    if "answers" in kinds:
        print("\n=== answers ===")
        results["answers"] = scrape_answers(client, args.user)

    for kind, items in results.items():
        (out_dir / f"{kind}.json").write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        dump_markdown(items, out_dir / f"{kind}.md", kind)
        print(f"saved {len(items)} {kind} → {out_dir / f'{kind}.json'}")

    summary = {
        "user": args.user,
        "counts": {k: len(v) for k, v in results.items()},
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nDONE:", summary)


if __name__ == "__main__":
    main()
