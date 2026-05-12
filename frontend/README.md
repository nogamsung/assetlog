This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## 로컬 개발 환경 설정

### Node 버전

이 프로젝트는 Node.js 20.9.0 이상이 필요합니다. nvm 사용 시:

```bash
nvm install 20.11.0
nvm use
# .nvmrc 에 명시된 20.11.0 이 자동으로 선택됩니다
```

### 환경 변수

```bash
cp .env.local.example .env.local
# .env.local 을 열어 백엔드 API URL 을 확인/수정하세요
# 기본값: NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 의존성 설치 및 개발 서버 실행

```bash
npm install
npm run dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000) 을 열면 됩니다.

### 테스트

```bash
# 단위 테스트 실행
npm run test

# 커버리지 포함 CI 모드
npm run test:ci
```

### 타입 검사 및 린트

```bash
npx tsc --noEmit
npx eslint
```

## 외부 거래내역 가져오기 (UI)

설정 페이지(`/settings`) 에 두 가지 import 카드가 있습니다.

### 거래소 동기화 (Upbit)
- 백엔드 환경변수 `UPBIT_ACCESS_KEY` / `UPBIT_SECRET_KEY` 필요 (read-only).
- "지금 동기화" 클릭 → `POST /api/integrations/upbit/sync` → 매매 기록 자동 import + 캐시 무효화 + 결과 카운트 표시.
- 일 1회 자동 동기화도 백엔드 스케줄러에서 실행.

### 파일에서 거래내역 가져오기 (토스증권)
- 토스 앱 → 고객센터 → "거래내역서" PDF 발급 → 설정 페이지에서 업로드.
- 흐름: source 선택 → 파일 드롭/선택 → (옵션) PDF 비밀번호 → **미리보기** (dry-run) → 결과 확인 → **가져오기**.
- 매매 / 배당 / 이자입금 자동 import. 합성 dedupe 키로 동일 PDF 재업로드는 안전.

## 시간 표기 정책

모든 시간 표시는 **`src/lib/datetime.ts`** 헬퍼 (`formatDateTimeKST`, `formatDateKST`, `formatTimeKST`, `formatChartTickKST`) 를 통해서만 출력합니다 — Asia/Seoul + 24시간 강제. 컴포넌트에서 `toLocaleString` 직접 호출 금지.
