#!/usr/bin/env bash
# Stop hook — turn 종료 시 memory/MEMORY.md 기록 리마인더
# Claude Code UI 에 표시되어 사용자(및 Claude 본인)가 자동 기록 여부를 점검.
set -euo pipefail

echo "🧠 [Memory] 이 턴에 중요한 결정(기술·아키텍처·라이브러리·/rule·버그해결·교훈) 이 있었다면 memory/MEMORY.md 에 날짜별 항목을 추가하세요." >&2
