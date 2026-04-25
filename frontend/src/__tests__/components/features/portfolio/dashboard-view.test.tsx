import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { DashboardView } from "@/components/features/portfolio/dashboard-view";
import * as portfolioHook from "@/hooks/use-portfolio";
import * as useSampleSeedHook from "@/hooks/use-sample-seed";
import type { PortfolioSummary, HoldingResponse } from "@/types/portfolio";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("@/hooks/use-portfolio", () => ({
  ...jest.requireActual("@/hooks/use-portfolio"),
  usePortfolioSummary: jest.fn(),
  usePortfolioHoldings: jest.fn(),
}));

jest.mock("@/hooks/use-sample-seed", () => ({
  useSampleSeed: jest.fn(),
}));

// sub-components that make additional hook/fetch calls — stub them out
jest.mock("@/components/features/portfolio/summary-cards", () => ({
  SummaryCards: () => <div data-testid="summary-cards" />,
}));
jest.mock("@/components/features/portfolio/allocation-donut", () => ({
  AllocationDonut: () => <div data-testid="allocation-donut" />,
}));
jest.mock("@/components/features/portfolio/holdings-table", () => ({
  HoldingsTable: () => <div data-testid="holdings-table" />,
}));
jest.mock("@/components/features/portfolio/portfolio-history-chart", () => ({
  PortfolioHistoryChart: () => <div data-testid="portfolio-history-chart" />,
}));
jest.mock("@/components/features/portfolio/currency-switcher", () => ({
  CurrencySwitcher: () => <div data-testid="currency-switcher" />,
}));

const mockedUsePortfolioSummary = jest.mocked(portfolioHook.usePortfolioSummary);
const mockedUsePortfolioHoldings = jest.mocked(portfolioHook.usePortfolioHoldings);
const mockedUseSampleSeed = jest.mocked(useSampleSeedHook.useSampleSeed);

const mockSeedMutate = jest.fn();

const fakeSummary: PortfolioSummary = {
  totalValueByCurrency: { KRW: "10000000.00" },
  totalCostByCurrency: { KRW: "9000000.00" },
  pnlByCurrency: { KRW: { abs: "1000000.00", pct: 11.11 } },
  realizedPnlByCurrency: { KRW: "0.00" },
  allocation: [{ assetType: "kr_stock", pct: 100 }],
  lastPriceRefreshedAt: "2026-04-24T09:00:00Z",
  pendingCount: 0,
  staleCount: 0,
  convertedTotalValue: null,
  convertedTotalCost: null,
  convertedPnlAbs: null,
  convertedRealizedPnl: null,
  displayCurrency: null,
};

const fakeHolding: HoldingResponse = {
  userAssetId: 1,
  assetSymbol: {
    id: 1,
    assetType: "kr_stock",
    symbol: "005930",
    exchange: "KRX",
    name: "삼성전자",
    currency: "KRW",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
  quantity: "10.0000",
  avgCost: "70000.0000",
  costBasis: "700000.00",
  realizedPnl: "0.00",
  latestPrice: "75000.0000",
  latestValue: "750000.00",
  pnlAbs: "50000.00",
  pnlPct: 7.14,
  weightPct: 100,
  lastPriceRefreshedAt: "2026-04-24T09:00:00Z",
  isStale: false,
  isPending: false,
};

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardView />
    </QueryClientProvider>,
  );
}

function setupSeedMock(isPending = false) {
  mockedUseSampleSeed.mockReturnValue({
    mutate: mockSeedMutate,
    isPending,
    isError: false,
    isSuccess: false,
    error: null,
  } as unknown as ReturnType<typeof useSampleSeedHook.useSampleSeed>);
}

function setupQueryMocks(
  summary: PortfolioSummary | undefined,
  holdings: HoldingResponse[],
  isLoading = false,
  isError = false,
) {
  mockedUsePortfolioSummary.mockReturnValue({
    data: summary,
    isLoading,
    isError,
    error: isError ? new Error("Error") : null,
    isSuccess: !isLoading && !isError,
  } as unknown as ReturnType<typeof portfolioHook.usePortfolioSummary>);

  mockedUsePortfolioHoldings.mockReturnValue({
    data: holdings,
    isLoading,
    isError,
    error: isError ? new Error("Error") : null,
    isSuccess: !isLoading && !isError,
  } as unknown as ReturnType<typeof portfolioHook.usePortfolioHoldings>);
}

describe("DashboardView", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupSeedMock();
  });

  describe("로딩 상태", () => {
    it("로딩 중일 때 스켈레톤을 표시한다", () => {
      setupQueryMocks(undefined, [], true);
      renderDashboard();
      expect(screen.getByLabelText("대시보드 로딩 중")).toBeInTheDocument();
    });
  });

  describe("에러 상태", () => {
    it("에러 시 에러 메시지를 표시한다", () => {
      setupQueryMocks(undefined, [], false, true);
      renderDashboard();
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  describe("빈 상태 (EmptyPortfolio)", () => {
    it("holdings 가 비었을 때 빈 상태 UI 를 표시한다", () => {
      setupQueryMocks(undefined, []);
      renderDashboard();
      expect(
        screen.getByText("포트폴리오에 자산이 없습니다. 첫 번째 자산을 추가해보세요."),
      ).toBeInTheDocument();
    });

    it("자산 추가하기 링크를 표시한다", () => {
      setupQueryMocks(undefined, []);
      renderDashboard();
      expect(
        screen.getByRole("link", { name: /자산 추가하기/ }),
      ).toHaveAttribute("href", "/assets/new");
    });

    it("샘플 데이터로 시작 버튼이 렌더링된다", () => {
      setupQueryMocks(undefined, []);
      renderDashboard();
      expect(
        screen.getByRole("button", { name: "샘플 데이터로 시작" }),
      ).toBeInTheDocument();
    });

    it("샘플 버튼 클릭 시 mutation 이 호출된다", async () => {
      setupQueryMocks(undefined, []);
      const user = userEvent.setup();
      renderDashboard();

      await user.click(screen.getByRole("button", { name: "샘플 데이터로 시작" }));
      expect(mockSeedMutate).toHaveBeenCalledTimes(1);
    });

    it("시드 pending 중 버튼이 disabled 되고 텍스트가 변경된다", () => {
      setupQueryMocks(undefined, []);
      setupSeedMock(true);
      renderDashboard();
      const btn = screen.getByRole("button", { name: "샘플 데이터로 시작" });
      expect(btn).toBeDisabled();
      expect(btn).toHaveTextContent("추가 중...");
    });
  });

  describe("데이터 있음", () => {
    it("holdings 가 있을 때 포트폴리오 요약 UI 를 표시한다", () => {
      setupQueryMocks(fakeSummary, [fakeHolding]);
      renderDashboard();
      expect(screen.getByTestId("summary-cards")).toBeInTheDocument();
      expect(screen.getByTestId("holdings-table")).toBeInTheDocument();
    });
  });
});
