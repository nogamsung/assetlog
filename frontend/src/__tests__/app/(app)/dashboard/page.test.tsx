import { render, screen } from "@testing-library/react";
import { DashboardView } from "@/components/features/portfolio/dashboard-view";
import * as usePortfolioModule from "@/hooks/use-portfolio";
import type { PortfolioSummary, HoldingResponse } from "@/types/portfolio";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("@/hooks/use-portfolio");

const mockUseSummary = jest.mocked(usePortfolioModule.usePortfolioSummary);
const mockUseHoldings = jest.mocked(usePortfolioModule.usePortfolioHoldings);

const fakeSummary: PortfolioSummary = {
  totalValueByCurrency: { KRW: "12500000.00" },
  totalCostByCurrency: { KRW: "11000000.00" },
  pnlByCurrency: { KRW: { abs: "1500000.00", pct: 13.64 } },
  allocation: [{ assetType: "kr_stock", pct: 100 }],
  lastPriceRefreshedAt: "2026-04-24T09:00:00+09:00",
  pendingCount: 0,
  staleCount: 0,
};

const fakeHolding: HoldingResponse = {
  userAssetId: 12,
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
  latestPrice: "75000.0000",
  latestValue: "750000.00",
  pnlAbs: "50000.00",
  pnlPct: 7.14,
  weightPct: 100,
  lastPriceRefreshedAt: "2026-04-24T09:00:00+09:00",
  isStale: false,
  isPending: false,
};

function setupMocks(
  summaryState: Partial<ReturnType<typeof usePortfolioModule.usePortfolioSummary>>,
  holdingsState: Partial<ReturnType<typeof usePortfolioModule.usePortfolioHoldings>>,
) {
  mockUseSummary.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    ...summaryState,
  } as ReturnType<typeof usePortfolioModule.usePortfolioSummary>);

  mockUseHoldings.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    ...holdingsState,
  } as ReturnType<typeof usePortfolioModule.usePortfolioHoldings>);
}

describe("DashboardView", () => {
  beforeEach(() => jest.clearAllMocks());

  it("로딩 중에 스켈레톤을 렌더링한다", () => {
    setupMocks({ isLoading: true }, { isLoading: true });
    render(<DashboardView />);
    expect(screen.getByRole("status", { name: "대시보드 로딩 중" })).toBeInTheDocument();
  });

  it("에러 시 에러 메시지를 렌더링한다", () => {
    setupMocks(
      { isError: true, error: new Error("API 에러") },
      { isError: false },
    );
    render(<DashboardView />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("holdings 가 비면 EmptyPortfolio 를 렌더링한다", () => {
    setupMocks(
      { data: fakeSummary },
      { data: [] },
    );
    render(<DashboardView />);
    expect(screen.getByText("포트폴리오에 자산이 없습니다. 첫 번째 자산을 추가해보세요.")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "자산 추가하기" });
    expect(link).toHaveAttribute("href", "/assets/new");
  });

  it("happy path: summary + holdings 가 있으면 카드·차트·테이블을 렌더링한다", () => {
    setupMocks(
      { data: fakeSummary },
      { data: [fakeHolding] },
    );
    render(<DashboardView />);
    // 요약 카드
    expect(screen.getByText("총평가액")).toBeInTheDocument();
    expect(screen.getByText("총손익")).toBeInTheDocument();
    // 테이블
    expect(screen.getByText("005930")).toBeInTheDocument();
  });

  it("pending 100% 상태에서도 정상 렌더된다", () => {
    const pendingHolding: HoldingResponse = {
      ...fakeHolding,
      latestPrice: null,
      latestValue: null,
      pnlAbs: null,
      pnlPct: null,
      isPending: true,
    };
    const pendingSummary: PortfolioSummary = {
      ...fakeSummary,
      pendingCount: 1,
    };
    setupMocks({ data: pendingSummary }, { data: [pendingHolding] });
    render(<DashboardView />);
    expect(screen.getByText("가격 대기중")).toBeInTheDocument();
  });
});
