import type { Config } from "jest";
import nextJest from "next/jest.js";

const createJestConfig = nextJest({
  dir: "./",
});

const config: Config = {
  testEnvironment: "jest-environment-jsdom",
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
  testMatch: [
    "<rootDir>/src/**/*.test.ts",
    "<rootDir>/src/**/*.test.tsx",
    "<rootDir>/src/**/*.spec.ts",
    "<rootDir>/src/**/*.spec.tsx",
  ],
  collectCoverageFrom: [
    "src/**/*.{ts,tsx}",
    "!src/**/*.d.ts",
    // 라우팅 전용 파일 (서버 컴포넌트 레이아웃/페이지)
    "!src/app/layout.tsx",
    "!src/app/page.tsx",
    "!src/app/**/layout.tsx",
    "!src/app/**/page.tsx",
    "!src/app/**/loading.tsx",
    "!src/app/**/error.tsx",
    // Provider/설정
    "!src/providers.tsx",
    // 단순 래퍼/스타일 컴포넌트 (통합 테스트 대상)
    "!src/components/ui/card.tsx",
    "!src/components/ui/badge.tsx",
    "!src/components/features/auth/auth-guard.tsx",
    "!src/components/features/home-header.tsx",
    "!src/components/features/assets/asset-type-badge.tsx",
    // API 클라이언트 (통합 테스트 대상)
    "!src/lib/api-client.ts",
    "!src/lib/query-client.ts",
  ],
  coverageThreshold: {
    global: {
      lines: 90,
    },
  },
  coverageReporters: ["json-summary", "text", "lcov"],
  transform: {
    "^.+\\.(t|j)sx?$": [
      "@swc/jest",
      {
        jsc: {
          parser: {
            syntax: "typescript",
            tsx: true,
          },
          transform: {
            react: {
              runtime: "automatic",
            },
          },
        },
      },
    ],
  },
};

export default createJestConfig(config);
