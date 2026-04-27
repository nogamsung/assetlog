# UI / Mobile Polish — backend 구현 프롬프트

> 대응 PRD: [`../ui-mobile-polish.md`](../ui-mobile-polish.md)
> 대응 스택: python (경로: `backend`)

---

## 결론

**이 기능은 backend 변경이 필요 없습니다. frontend 만 진행합니다.**

### 근거 (스캔 결과)

- 모든 Decimal 필드는 backend 에서 **string 으로 직렬화**되어 전달됨 — 정밀도 손실 없음.
  - 확인 위치: `backend/app/routers/portfolio.py` ("Decimal fields are serialised as strings"), `backend/app/routers/export.py` (`custom_encoder={Decimal: str}`).
- 표시 자릿수 정책은 PRD §9 의 "숫자 포맷 표준" 에 따라 **frontend `lib/format.ts` 에서 결정**.
- 저장/계산 정밀도는 그대로 유지되어야 하므로 backend 가 round/quantize 를 적용해서는 안 됨 (의도된 설계).

### 후속 작업 시 backend 변경이 발생하는 조건

다음 중 하나가 발생할 경우에만 별도 PRD 로 backend 작업 분리:

- 클라이언트가 표시 외 용도로(예: CSV 내보내기 컬럼) **사전 반올림된 값**을 요구할 때
- 새 통화 카테고리(예: 정수 통화)가 추가되어 backend 검증 룰을 손봐야 할 때
- API 응답 스키마 자체에 `displayPrecision` 같은 메타가 필요해질 때

### 이 프롬프트의 처리

- `nextjs-modifier` 만 dispatch.
- backend agent (`python-modifier` / `python-generator`) **dispatch 하지 않음**.
- pre-push 훅의 backend 커버리지 게이트는 backend 변경이 없으므로 영향 없음.
