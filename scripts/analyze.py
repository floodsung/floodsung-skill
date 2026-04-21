#!/usr/bin/env python3
"""Analyze scraped zhihu data to extract voice/style/belief patterns.

Outputs files under .claude/skills/floodsung/references/:
  - titles.md         all titles grouped by kind, for pattern reference
  - signatures.md     high-frequency signature phrases / opening patterns
  - core_beliefs.md   clusters of strong opinions (by topic keyword)
  - exemplars.md      representative long-form examples (articles/answers/pins)
  - lexicon.md        english terms kept untranslated + catchphrases
  - timeline.md       chronological career/milestone markers from pins
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "zhihu"
REF = ROOT / ".claude" / "skills" / "floodsung" / "references"
REF.mkdir(parents=True, exist_ok=True)


def load():
    return {
        k: json.loads((DATA / f"{k}.json").read_text(encoding="utf-8"))
        for k in ("articles", "pins", "answers")
    }


def ts(epoch):
    try:
        return datetime.utcfromtimestamp(int(epoch)).strftime("%Y-%m-%d")
    except Exception:
        return "?"


# ---------- titles ----------

def build_titles(data):
    lines = ["# Flood Sung — 所有标题（反映选题偏好）\n"]
    lines.append("## 文章（专栏）\n")
    for a in sorted(data["articles"], key=lambda x: x.get("created") or 0, reverse=True):
        date = ts(a.get("created"))
        vote = a.get("voteup_count", 0)
        lines.append(f"- [{date}] {a['title']}  · voteup {vote}")
    lines.append("\n## 回答\n")
    for a in sorted(data["answers"], key=lambda x: x.get("created") or 0, reverse=True):
        lines.append(f"- [{ts(a.get('created'))}] {a['question']}  · voteup {a.get('voteup_count', 0)}")
    (REF / "titles.md").write_text("\n".join(lines), encoding="utf-8")


# ---------- signature phrases ----------

SIGNATURE_CANDIDATES = [
    r"我认为",
    r"我相信",
    r"笔者",
    r"这里我来",
    r"这里我",
    r"share 一下",
    r"不对的地方",
    r"太让人兴奋",
    r"milestone",
    r"OMG",
    r"加入我们",
    r"让我们",
    r"让人类",
    r"二型文明",
    r"奇点",
    r"bet on",
    r"is all you need",
    r"taste",
    r"the bitter lesson",
    r"scaling law",
    r"compositional generalization",
    r"foundation model",
    r"Agent Native",
    r"晓组织",
    r"AGI",
    r"Ilya",
    r"Kurzweil",
    r"Musk",
    r"Hinton",
    r"Sergey Levine",
    r"DeepSeek",
    r"月之暗面",
    r"Kimi",
    r"RL \+",
    r"大模型",
    r"pretrain",
    r"rollout",
    r"Online Learning",
    r"Meta Learning",
    r"Meta RL",
    r"VLA",
    r"VLM",
    r"WBC",
    r"humanoid",
    r"人形机器人",
]


def full_corpus(data):
    parts = []
    for a in data["articles"]:
        parts.append((a.get("title","") or "") + "\n" + (a.get("content_md") or ""))
    for p in data["pins"]:
        parts.append(p.get("text","") or "")
    for a in data["answers"]:
        parts.append((a.get("question","") or "") + "\n" + (a.get("content_md") or ""))
    return "\n\n".join(parts)


def build_signatures(data):
    corpus = full_corpus(data)
    counts = []
    for pat in SIGNATURE_CANDIDATES:
        n = len(re.findall(pat, corpus, re.IGNORECASE))
        counts.append((n, pat))
    counts.sort(reverse=True)
    lines = ["# Flood Sung — 签名短语 / 技术关键词词频\n", "反映他日常最常说、最爱用的词和观点锚点。\n"]
    for n, pat in counts:
        if n > 0:
            lines.append(f"- `{pat}` · {n} 次")
    # opening patterns
    lines.append("\n## 文章开头三行（前 40 篇）\n")
    for a in data["articles"][:40]:
        body = (a.get("content_md") or "").strip().splitlines()
        head = " / ".join(b.strip() for b in body[:3] if b.strip())[:180]
        if head:
            lines.append(f"### {a['title']}\n> {head}\n")
    (REF / "signatures.md").write_text("\n".join(lines), encoding="utf-8")


# ---------- core beliefs by topic ----------

TOPICS = {
    "AGI 时间表 & 奇点": ["奇点", "AGI.*(时代|时间|来|即将|必然|时代|到来)", "库兹韦尔|Kurzweil"],
    "RL + LLM / 大模型 Alignment": ["RLHF", "RL.*(LLM|大模型|alignment|对齐)", "o1|reasoning|self-improve"],
    "Meta Foundation Model": ["Meta Foundation Model", "Meta RL", "Meta Learning"],
    "具身智能 / VLA / WBC": ["具身", "VLA", "WBC", "humanoid|人形", "sim2real|Sim2Real"],
    "Online Learning / Scaling Law": ["Online Learning", "Scaling Law|scaling law"],
    "研究品味 / Bitter Lesson": ["bitter lesson", "taste", "品味"],
    "Agent Native / 组织": ["Agent Native", "晓组织", "10 人|10人.*(Agent|亿)", "MetaBot"],
    "创业 & 心力": ["创业", "心力", "citation", "破万"],
    "2026 预测": ["2026", "2025", "预测|bet"],
    "元宇宙 / Metaverse": ["元宇宙|Metaverse|metaverse"],
    "开源 / DeepSeek": ["开源", "DeepSeek|deepseek"],
    "月之暗面 / Kimi": ["月之暗面|Kimi|kimi"],
}


def extract_around(corpus: str, pat: str, window: int = 220, max_hits: int = 5):
    hits = []
    for m in re.finditer(pat, corpus, re.IGNORECASE):
        s = max(0, m.start() - window // 2)
        e = min(len(corpus), m.end() + window // 2)
        snippet = corpus[s:e].replace("\n", " ").strip()
        if any(self_ref in snippet for self_ref in ("我", "笔者", "Flood")):
            hits.append(snippet)
        if len(hits) >= max_hits:
            break
    return hits


def build_beliefs(data):
    corpus = full_corpus(data)
    lines = ["# Flood Sung — 核心信念（按主题）\n",
             "下列引用是**本人原文**，用来在回答时校准语气和立场。如果用户问题涉及这些主题，这些是必须保持一致的锚点。\n"]
    for topic, pats in TOPICS.items():
        lines.append(f"\n## {topic}\n")
        seen = set()
        for pat in pats:
            for snip in extract_around(corpus, pat):
                key = snip[:80]
                if key in seen:
                    continue
                seen.add(key)
                lines.append(f"- …{snip}…\n")
    (REF / "core_beliefs.md").write_text("\n".join(lines), encoding="utf-8")


# ---------- exemplars ----------

def build_exemplars(data):
    # pick top by voteup in each category + recent
    arts = sorted(
        data["articles"], key=lambda x: (x.get("voteup_count") or 0), reverse=True
    )[:5]
    recent_arts = sorted(
        data["articles"], key=lambda x: (x.get("created") or 0), reverse=True
    )[:5]
    ans = sorted(data["answers"], key=lambda x: (x.get("voteup_count") or 0), reverse=True)[:5]
    pins_long = sorted(data["pins"], key=lambda x: len(x.get("text") or ""), reverse=True)[:10]

    def fmt_article(a, full=False):
        body = a.get("content_md") or ""
        if not full:
            body = body[:1200] + ("\n…[truncated]" if len(body) > 1200 else "")
        return (f"\n### {a['title']}\n"
                f"`{ts(a.get('created'))} · voteup {a.get('voteup_count',0)} · {a['url']}`\n\n{body}\n")

    lines = ["# Flood Sung — 代表作 / exemplars\n",
             "读这里的片段，模仿他实际的文风。不是转述，是**直接学他的原话**。\n"]
    lines.append("\n## 高赞文章 top 5（截取 1200 字）\n")
    for a in arts:
        lines.append(fmt_article(a))
    lines.append("\n## 近期文章 top 5（截取 1200 字）\n")
    for a in recent_arts:
        lines.append(fmt_article(a))
    lines.append("\n## 高赞回答 top 5\n")
    for a in ans:
        body = a.get("content_md") or ""
        body = body[:1200] + ("\n…[truncated]" if len(body) > 1200 else "")
        lines.append(f"\n### Q: {a['question']}\n"
                     f"`{ts(a.get('created'))} · voteup {a.get('voteup_count',0)}`\n\n{body}\n")
    lines.append("\n## 代表性想法（长版）top 10\n")
    for p in pins_long:
        lines.append(f"\n- [{ts(p.get('created'))}] {p['text']}")
    (REF / "exemplars.md").write_text("\n".join(lines), encoding="utf-8")


# ---------- lexicon ----------

# words that appear in english form inside chinese text — likely untranslated
EN_TOKEN_RE = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z0-9\-\+/.]{1,30}(?![A-Za-z])")
STOP = {
    "a", "an", "the", "of", "and", "or", "to", "in", "is", "it", "we", "he",
    "https", "http", "www", "com", "github", "cn", "io", "pdf", "arxiv",
    "s", "ve", "m", "d", "t", "ll", "en", "us", "uk",
    "p", "px", "py", "sh", "md", "json",
}


def build_lexicon(data):
    corpus = full_corpus(data)
    tokens = [t for t in EN_TOKEN_RE.findall(corpus) if t.lower() not in STOP]
    c = Counter(tokens)
    lines = ["# Flood Sung — 英文术语词典（从不翻译）\n",
             "在中文语境中直接嵌入，不要翻成中文。按频次排序。\n"]
    for tok, n in c.most_common(120):
        lines.append(f"- `{tok}` · {n}")
    (REF / "lexicon.md").write_text("\n".join(lines), encoding="utf-8")


# ---------- timeline ----------

def build_timeline(data):
    events = []
    for p in data["pins"]:
        if p.get("created") and (p.get("text") or ""):
            events.append((p["created"], "pin", p["text"][:200]))
    for a in data["articles"]:
        if a.get("created"):
            events.append((a["created"], "article", a["title"]))
    events.sort(reverse=True)
    lines = ["# Flood Sung — 时间线（最近 200 条动态/文章，用来判断他当下关心什么）\n"]
    for ts_, kind, text in events[:200]:
        lines.append(f"- `{ts(ts_)}` **{kind}** · {text}")
    (REF / "timeline.md").write_text("\n".join(lines), encoding="utf-8")


# ---------- title patterns ----------

def build_title_patterns(data):
    titles = [a["title"] for a in data["articles"]]
    patterns = {
        "最前沿：": [t for t in titles if t.startswith("最前沿")],
        "AGI 杂谈系列": [t for t in titles if "杂谈" in t or "AGI" in t and len(t) < 30],
        "玩转 Kimi 系列": [t for t in titles if "Kimi" in t or "玩转" in t],
        "Meta / Foundation Model": [t for t in titles if "Foundation" in t or "Meta" in t],
        "论文解读": [t for t in titles if "Paper" in t.lower() or "paper" in t or "论文" in t],
        "年度总结 / 展望": [t for t in titles if re.search(r"20\d\d", t)],
        "机器人 / 具身": [t for t in titles if re.search(r"机器人|具身|humanoid|VLA|WBC|sim2real", t, re.I)],
        "开源 / 项目发布": [t for t in titles if re.search(r"开源|发布|更新|MetaBot|Agent", t, re.I)],
    }
    lines = ["# Flood Sung — 标题模式 (选题 × 措辞)\n"]
    for k, v in patterns.items():
        if not v:
            continue
        lines.append(f"\n## {k} ({len(v)})\n")
        for t in v[:20]:
            lines.append(f"- {t}")
    (REF / "title_patterns.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    data = load()
    print(f"loaded: articles={len(data['articles'])}, pins={len(data['pins'])}, answers={len(data['answers'])}")
    build_titles(data)
    build_signatures(data)
    build_beliefs(data)
    build_exemplars(data)
    build_lexicon(data)
    build_timeline(data)
    build_title_patterns(data)
    print(f"references written to {REF}")
    for f in sorted(REF.glob("*.md")):
        print(f"  {f.name}: {f.stat().st_size} bytes")


if __name__ == "__main__":
    main()
