# floodsung-skill

> **开源我自己** — An open-source Claude Code skill that lets any model speak, think, and write as **Flood Sung** (XVI Robotics Founder & CEO, Zhihu: [flood-sung](https://www.zhihu.com/people/flood-sung)).
>
> 全量 152 篇专栏文章 + 178 条想法 + 243 个回答的人格语料，让 Claude Code 变成一个数字分身。你也可以 fork 这个模板，开源你自己。

---

## 这是什么

一个 **Claude Code skill**。触发后，Claude 不再是通用助手，而是以 **Flood Sung** 的身份思考、写作、回答。包含：

| 组件 | 内容 |
|------|------|
| `SKILL.md` | 人设主 prompt：身份、核心技术观点、语气、文体、反模式 |
| `references/` | 从全量语料蒸馏出的：风格样本、核心观点索引、术语词典、签名短语、标题模式、时间线 |
| `data/` | 全量知乎原始语料（JSON + Markdown），共 573 条 / 约 90 万字（已剔除 11 条 MetaBot 自动发的） |
| `scripts/` | 知乎爬虫 + 分析工具 |

## 为什么要做这个

2026 年的现实是：**200 美元的 Claude 订阅费，可以替代一个百万年薪的 research engineer 的大部分工作**。

但通用 AI 有一个问题：**没有 taste，没有立场，没有个人辨识度**。写出来的东西 50% 能用，50% 千篇一律。

解决方案：**用一个人真实的历史创作，把 AI 训成他的数字分身**。

Flood Sung 从 2016 年开始在知乎写作，累积 152 篇专栏文章 + 243 个回答 + 178 条想法（本 repo 已剔除 11 条 MetaBot 自动发的）。这是一个足够大、足够稳定、足够有辨识度的 corpus。这个 repo 把所有原料 + 提炼好的 skill 开源出来，任何人都可以：

1. **直接用**：装上 skill，让 Claude 用 Flood Sung 的方式回答你的问题
2. **当模板**：fork 它，替换成你自己的语料，变成"你自己的 skill"——**开源你自己**

## 怎么用

### Option A: 直接把它装进你的 Claude Code

```bash
git clone https://github.com/floodsung/floodsung-skill.git
mkdir -p ~/.claude/skills/floodsung
cp -r floodsung-skill/SKILL.md floodsung-skill/references/ ~/.claude/skills/floodsung/
# 可选：把 data/ 放到你项目的 data/zhihu/ 下，供 skill 引用
```

然后在 Claude Code 里说："用 floodsung 的风格写一条关于 XXX 的知乎想法" —— skill 会自动触发。

### Option B: Fork 成"你自己的 skill"

```bash
# 1. 爬取你自己的知乎内容
cd floodsung-skill
export ZHIHU_COOKIE="d_c0=...; z_c0=..."  # 从浏览器复制
python3 scripts/scraper.py --user YOUR_ZHIHU_TOKEN --out data/
python3 scripts/enrich.py --dir data/
python3 scripts/build_references.py

# 2. 改写 SKILL.md — 把人设改成你
#    把"Flood Sung"、"XVI Robotics"等关键字替换为你的身份
vim SKILL.md

# 3. 部署到 Claude Code
mkdir -p ~/.claude/skills/you
cp SKILL.md references/ ~/.claude/skills/you/
```

## Skill 能做什么

**A. 写知乎文章** — 按"1 前言 → 2 / 3 / 4 分章节 → 结尾展望"结构，中英混写，典型开头"不谋万世者，不足谋一时"

**B. 发条想法（短动态）** — 30-300 字，带情绪（OMG! 太让人兴奋了！milestone!），hashtag 风

**C. 代回答知乎问题** — 结论先行，直接表态，500-2000 字

**D. 对技术/战略问题给 take** — 结论 + 1-2 核心论据 + 一个 hot take + 落在行动

详见 [`SKILL.md`](SKILL.md)。

## 核心人设速写

- **当下身份**：XVI Robotics 创始人 & CEO，在做通用人形基座模型 Humanoid Foundation Model
- **Slogan**：推进机器人革命，让人类迈向二型文明
- **研究**：Learning to Compare（Relation Network，6k+ 引用），Deep-Learning-Papers-Reading-Roadmap（39k+ stars）
- **核心观点**：
  - **AGI** 已经在到来，奇点不可阻挡
  - **坚定押注 RL + 大模型**，下一代范式是 Meta Foundation Model
  - 具身智能核心：**Large-Scale Whole-Body VLA**（大脑 VLM + 小脑 WBC 分训后联合训练）
  - 2026 bet：**Online Learning + 具身 Scaling Law**
  - 组织形态：**Agent Native Company**（10 人 + N Agent 做 10 亿美金公司）

## 语料统计

| 类型 | 数量 | 总字数 |
|------|------|--------|
| 文章 | 152 | 743,801 |
| 回答 | 243 | ~145,000 |
| 想法 | 178 | 14,756 |
| **合计** | **573** | **~90 万** |

（原始爬取 584 条，其中 11 条回答由 MetaBot 自动发布、非 Flood Sung 亲写，已剔除并归档于 `data/answers_metabot_excluded.json`。）

最早 2016，最新 2026-04。

## 爬虫说明

`scripts/scraper.py` 用 x-zse-96 签名 + cookie 调用知乎官方 API，支持 articles / answers / pins 三类，自动分页。

**重要**：需要登录后的 cookie（`d_c0` + `z_c0`）。爬你自己的账号是 OK 的，请勿滥用。

```bash
export ZHIHU_COOKIE="d_c0=xxx; z_c0=xxx; _xsrf=xxx"
python3 scripts/scraper.py --user YOUR_URL_TOKEN --out data/
python3 scripts/enrich.py --dir data/   # 补全全文（列表接口只给摘要）
python3 scripts/build_references.py     # 从语料蒸馏 references
```

## 哲学声明

这个 repo 想表达的是：**AI 时代，每个有沉淀的创作者都应该把自己"开源"。**

开源自己，不是让 AI 取代你，而是：

1. **放大你的影响力** —— 别人可以通过你的 skill 接触你的思维方式，即使你没空亲自回答
2. **让 AI 生产的内容有 taste** —— 通用 AI 同质化严重，只有"有人格"的 AI 才有记忆点
3. **构建数字遗产** —— 你累积的文字，不应该只躺在社交平台里等消失，它们是你思想的 embedding，应该能被复用、被二次创作、被未来的 AGI 理解

如果你也觉得这件事有意义，**fork 这个 repo，换成你的语料，变成你自己的 skill**。

## License

- 代码（`scripts/`）：MIT
- 内容（`SKILL.md` / `references/` / `data/`）：CC-BY-4.0
- 人格（Flood Sung 本人）：仍然 by Flood Sung 自己

## 相关

- Author：Flood Sung ([@floodsung](https://github.com/floodsung))
- 知乎原号：[flood-sung](https://www.zhihu.com/people/flood-sung)
- 公司：[XVI Robotics](https://xvirobotics.com) — Humanoid Foundation Model
- 开源作品：
  - [Deep-Learning-Papers-Reading-Roadmap](https://github.com/floodsung/Deep-Learning-Papers-Reading-Roadmap) 39k+ stars
  - [MetaBot](https://github.com/floodsung) — Agent Native 基础设施

---

**让我们一起向二型文明进发！**
