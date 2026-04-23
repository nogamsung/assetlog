#!/usr/bin/env bash
# UserPromptSubmit hook — 프롬프트 제출 시 memory/MEMORY.md 최근 내용을
# hookSpecificOutput.additionalContext 로 주입해서 모델 컨텍스트에 재공급.
# SessionStart 로드만으로는 장시간 세션에서 휘발되므로 매 턴 refresh.
set -euo pipefail

MEMORY_FILE="memory/MEMORY.md"

if [ ! -f "$MEMORY_FILE" ]; then
  exit 0
fi

tail -n 60 "$MEMORY_FILE" | jq -Rs '{
  hookSpecificOutput: {
    hookEventName: "UserPromptSubmit",
    additionalContext: (
      "[auto-injected: memory/MEMORY.md tail (최근 60줄)]\n\n"
      + .
      + "\n\n---\n\n[Auto-memory directive] 직전 턴에 다음 중 하나라도 발생했다면 이번 응답 시작 부분에서 먼저 memory/MEMORY.md 에 `## YYYY-MM-DD: 제목` 형식 항목을 추가하세요:\n"
      + "  • 기술 스택/아키텍처/라이브러리 도입·변경 결정\n"
      + "  • 버그의 근본 원인 발견 + 해결\n"
      + "  • /rule 추가로 얻은 영구 가드레일\n"
      + "  • 반복 가능한 교훈 (다시 만들 실수 회피 가이드)\n"
      + "MEMORY.md 는 '왜'(결정·히스토리·맥락), CLAUDE.md 는 '어떻게'(규칙). 중복 기록 금지."
    )
  }
}'
