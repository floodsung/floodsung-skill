#!/usr/bin/env bash
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
