# assetlog — Monorepo

여러 스택 공존 모노레포. Claude Code 는 편집 중인 파일의 **상위 디렉토리 `CLAUDE.md` 를 누적 로드** — 루트 + 해당 스택 CLAUDE.md 가 모두 컨텍스트에 들어옵니다.

| 역할 | 경로 | 스택 | 세부 규칙 |
|------|------|------|-----------|
| backend | `backend` | python | [`backend/CLAUDE.md`](./backend/CLAUDE.md) |
| frontend | `frontend` | nextjs | [`frontend/CLAUDE.md`](./frontend/CLAUDE.md) |

## 단일 진실의 원천 — `.claude/stacks.json`
```json
{
  "mode": "monorepo",
  "stacks": [
    { "role": "backend",  "type": "python", "path": "backend" },
    { "role": "frontend", "type": "nextjs", "path": "frontend" }
  ]
}
```

`/new`, `/plan`, `/test`, `.claude/hooks/*` 는 이 파일을 읽어 스택별로 분기.

## Agents (역할별)
| 역할 | 새 파일 | 수정 | 테스트 |
|------|---------|------|--------|
| backend | `python-generator` | `python-modifier` | `python-tester` |
| frontend | `nextjs-generator` | `nextjs-modifier` | `nextjs-tester` |

공통: `code-reviewer`, `api-designer`, `ui-designer`, `github-actions-designer`.

## 역할 prefix — 대상 스택 지정
| 커맨드 | 예시 |
|--------|------|
| `/new backend api User` | backend 경로에서 REST API 생성 |
| `/new frontend component Button` | frontend 경로에서 컴포넌트 |
| `/plan backend api User` | backend 스택 API 설계 |
| `/plan backend db order` | backend DB 설계 |

prefix 생략 시 — 스택 1개면 자동, 2개 이상이면 확인. `/test`, `/review` 는 파일 경로로 자동 판단.

## 기획 → 구현 워크플로
```
/planner 결제 취소 기능
  → docs/specs/payment-cancel.md (PRD)
  → docs/specs/payment-cancel/{backend,frontend}.md (역할별 프롬프트)
실행: (a) Agent Teams 병렬  또는  (b) 각 역할에서 /new 수동
/review → 2개 역할 일괄 리뷰
/pr
```

## Git 전략
단일 레포와 동일 (`main` / `dev` / `{feature|fix|hotfix|refactor|chore}/{name}`). 각 스택 `CLAUDE.md` 참고.

## 커버리지 게이트
`git push` 시 `.claude/hooks/pre-push.sh` 가 활성 스택 전부 순차 검증. 임계값 **90%**. 한 스택이라도 실패하면 push 차단.

## 주의사항
- **스택 경계 유지** — backend ↛ frontend 디렉토리 직접 참조. API 계약(`docs/api/*.yaml`)으로만 연결
- **의존성 독립** — 각 스택 독립 manifest (`requirements.txt`, `package.json`). 루트 공유 manifest 없음
- **CI 분리** — GitHub Actions `paths-filter` 로 변경된 스택만 실행 (`/new workflow ci` 자동 반영)
- **PR 스코프** — 가능하면 PR 당 1개 스택. 걸치면 커밋 분리

각 스택 `CLAUDE.md` 반드시 읽으세요.
