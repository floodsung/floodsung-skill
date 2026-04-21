#!/usr/bin/env python3
"""Distill scraped zhihu content into SKILL reference files.

Produces:
  references/writing_style_examples.md — representative openings & paragraphs
  references/core_views.md             — key takes organized by theme
  references/title_index.md            — browsable index by year
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "zhihu"
REF = ROOT / ".claude" / "skills" / "floodsung" / "references"
REF.mkdir(parents=True, exist_ok=True)


def load(name: str) -> list[dict]:
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def year(ts: int | None) -> str:
    if not ts:
        return "?"
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m")
    except Exception:
        return "?"


def first_paragraph(md: str, max_chars: int = 600) -> str:
    if not md:
        return ""
    md = re.sub(r"!\[.*?\]\(.*?\)", "", md)
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    parts = md.split("\n\n")
    out = []
    total = 0
    for p in parts:
        if total + len(p) > max_chars:
            break
        out.append(p)
        total += len(p)
    return "\n\n".join(out).strip()


def build_style_examples(articles: list[dict], pins: list[dict], answers: list[dict]):
    top_articles = sorted(
        [a for a in articles if a.get("content_md")],
        key=lambda a: -(a.get("voteup_count") or 0),
    )[:12]

    top_answers = sorted(
        [a for a in answers if a.get("content_md") and len(a["content_md"]) > 500],
        key=lambda a: -(a.get("voteup_count") or 0),
    )[:8]

    sample_pins = [p for p in pins if len(p.get("text", "")) > 80][:15]

    lines = ["# Flood Sung 风格样本\n",
             "精选高赞文章开头、代表性回答与想法片段。模仿时请对照语气、句式、转折方式。\n"]

    lines.append("\n## 一、文章开头样本（高赞，按得票排序）\n")
    for a in top_articles:
        lines.append(f"\n### 《{a['title']}》  \n")
        lines.append(f"*{year(a.get('created'))} · {a.get('voteup_count', 0)} 赞 · {a['url']}*\n")
        lines.append("\n```text\n" + first_paragraph(a["content_md"], 500) + "\n```\n")

    lines.append("\n## 二、代表性回答摘录\n")
    for a in top_answers:
        lines.append(f"\n### 问：{a['question']}  \n")
        lines.append(f"*{year(a.get('created'))} · {a.get('voteup_count', 0)} 赞*\n")
        lines.append("\n```text\n" + first_paragraph(a["content_md"], 500) + "\n```\n")

    lines.append("\n## 三、知乎想法样本（短动态）\n")
    for p in sample_pins:
        lines.append(f"- ({year(p.get('created'))}) {p['text'][:220]}")
    (REF / "writing_style_examples.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote style examples: {len(top_articles)} articles + {len(top_answers)} answers + {len(sample_pins)} pins")


THEME_KEYWORDS = {
    "AGI 与奇点": ["AGI", "奇点", "Kurzweil", "库兹韦尔", "通用人工智能"],
    "强化学习 RL": ["强化学习", "RL ", "DQN", "PPO", "AlphaGo", "AlphaZero", "policy gradient"],
    "Meta Learning / Few-Shot": ["meta learning", "Meta Learning", "few-shot", "few shot", "relation network"],
    "具身 / VLA / 机器人": ["具身", "VLA", "humanoid", "人形", "机器人", "sim2real", "WBC", "locomotion", "manipulation"],
    "基础模型 Foundation Model": ["foundation model", "基座", "pretrain", "scaling", "bitter lesson", "scaling law"],
    "Agent / 组织 / MetaBot": ["agent", "Agent", "MetaBot", "晓组织", "Agent Native", "飞书"],
    "创业 / 心力 / taste": ["心力", "taste", "创业", "citation", "使命"],
    "元宇宙 Metaverse": ["元宇宙", "Metaverse", "虚拟世界"],
}


def build_core_views(articles: list[dict], answers: list[dict]):
    corpus = articles + answers
    buckets: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for item in corpus:
        title = item.get("title") or item.get("question") or ""
        body = item.get("content_md") or ""
        if not body:
            continue
        for theme, kws in THEME_KEYWORDS.items():
            if any(k.lower() in title.lower() or k.lower() in body.lower() for k in kws):
                score = item.get("voteup_count") or 0
                buckets[theme].append((title, item.get("url", ""), score))

    lines = ["# Flood Sung 核心观点索引\n",
             "按主题聚合本人写过的相关文章/回答。代替他发言前，先读原文。\n"]
    for theme, items in buckets.items():
        items.sort(key=lambda x: -x[2])
        lines.append(f"\n## {theme}  ({len(items)} 条)\n")
        for title, url, score in items[:20]:
            lines.append(f"- [{title}]({url}) · {score} 赞")
    (REF / "core_views.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote core_views.md: {len(buckets)} themes")


def build_title_index(articles: list[dict], answers: list[dict]):
    by_year: dict[str, list[tuple[str, str, str, int]]] = defaultdict(list)
    for a in articles:
        y = year(a.get("created"))
        by_year[y].append(("ART", a["title"], a.get("url", ""), a.get("voteup_count") or 0))
    for a in answers:
        y = year(a.get("created"))
        by_year[y].append(("ANS", a.get("question", ""), a.get("url", ""), a.get("voteup_count") or 0))

    lines = ["# Flood Sung 全量内容索引（按月倒序）\n"]
    for y in sorted(by_year.keys(), reverse=True):
        items = by_year[y]
        items.sort(key=lambda x: -x[3])
        lines.append(f"\n## {y}  ({len(items)})\n")
        for kind, title, url, score in items:
            lines.append(f"- [{kind}] [{title}]({url}) · {score}")
    (REF / "title_index.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote title_index.md")


def build_search_helper():
    script = """#!/usr/bin/env bash
# Grep Flood Sung's scraped zhihu corpus. Usage: search_zhihu.sh "关键词"
set -e
KEYWORD="${1:?need keyword}"
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"
echo "=== articles hits ==="
grep -n --color=never -i "$KEYWORD" data/zhihu/articles.md | head -40 || true
echo
echo "=== answers hits ==="
grep -n --color=never -i "$KEYWORD" data/zhihu/answers.md | head -30 || true
echo
echo "=== pins hits ==="
grep -n --color=never -i "$KEYWORD" data/zhihu/pins.md | head -20 || true
"""
    p = REF / "search_zhihu.sh"
    p.write_text(script, encoding="utf-8")
    p.chmod(0o755)
    print("wrote search_zhihu.sh")


def main():
    articles = load("articles")
    pins = load("pins")
    answers = load("answers")
    build_style_examples(articles, pins, answers)
    build_core_views(articles, answers)
    build_title_index(articles, answers)
    build_search_helper()


if __name__ == "__main__":
    main()
