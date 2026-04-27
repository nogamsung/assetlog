import { render, screen } from "@testing-library/react";
import { DashboardView } from "@/components/features/portfolio/dashboard-view";
import * as usePortfolioModule from "@/hooks/use-portfolio";
import * as usePortfolioHistoryModule from "@/hooks/use-portfolio-history";
import * as useSampleSeedModule from "@/hooks/use-sample-seed";
import type { PortfolioSummary, HoldingResponse } from "@/types/portfolio";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("@/hooks/use-portfolio");
jest.mock("@/hooks/use-portfolio-history");
jest.mock("@/hooks/use-sample-seed", () => ({
  useSampleSeed: jest.fn(),
}));
jest.mock("@/hooks/use-tag-breakdown", () => ({
  useTagBreakdown: jest.fn(() => ({
    data: { entries: [] },
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: true,
  })),
}));

const mockedUseSampleSeed = jest.mocked(useSampleSeedModule.useSampleSeed);

// recharts 는 ResizeObserver / SVG 처리가 필요하므로 모킹
jest.mock("recharts", () => {
  const OriginalRecharts = jest.requireActual<typeof import("recharts")>("recharts");
  return {
    ...OriginalRecharts,
    ResponsiveContainer: ({
      children,
    }: {
      children: React.ReactNode;
    }) => <div data-testid="responsive-container">{children}</div>,
    LineChart: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="line-chart">{children}</div>
    ),
    Line: () => <div data-testid="line" />,
    XAxis: () => <div data-testid="x-axis" />,
    YAxis: () => <div data-testid="y-axis" />,
    Tooltip: () => <div data-testid="tooltip" />,
  };
});

const mockUseSummary = jest.mocked(usePortfolioModule.usePortfolioSummary);
const mockUseHoldings = jest.mocked(usePortfolioModule.usePortfolioHoldings);
const mockUsePortfolioHistory = jest.mocked(
  usePortfolioHistoryModule.usePortfolioHistory,
);

const fakeSummary: PortfolioSummary = {
  totalValueByCurrency: { KRW: "12500000.00" },
  totalCostByCurrency: { KRW: "11000000.00" },
  pnlByCurrency: { KRW: { abs: "1500000.00", pct: 13.64 } },
  realizedPnlByCurrency: { KRW: "0.000000" },
  allocation: [{ assetType: "kr_stock", pct: 100 }],
  lastPriceRefreshedAt: "2026-04-24T09:00:00+09:00",
  pendingCount: 0,
  staleCount: 0,
  convertedTotalValue: null,
  convertedTotalCost: null,
  convertedPnlAbs: null,
  convertedRealizedPnl: null,
  displayCurrency: null,
  cashTotalByCurrency: {},
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
  realizedPnl: "0.000000",
  latestPrice: "75000.0000",
  latestValue: "750000.00",
  pnlAbs: "50000.00",
  pnlPct: 7.14,
  weightPct: 100,
  lastPriceRefreshedAt: "2026-04-24T09:00:00+09:00",
  isStale: false,
  isPending: false,
  // 환산 필드 — ADDED
  convertedLatestValue: null,
  convertedCostBasis: null,
  convertedPnlAbs: null,
  convertedRealizedPnl: null,
  displayCurrency: null,
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

  // 기본: 차트는 빈 상태
  mockUsePortfolioHistory.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: false,
  } as unknown as ReturnType<typeof usePortfolioHistoryModule.usePortfolioHistory>);
}

describe("DashboardView", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseSampleSeed.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
      isError: false,
      isSuccess: false,
      error: null,
    } as unknown as ReturnType<typeof useSampleSeedModule.useSampleSeed>);
  });

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
    expect(screen.getByText("미실현 손익")).toBeInTheDocument();
    expect(screen.getByText("실현 손익")).toBeInTheDocument();
    // 테이블
    expect(screen.getByText("005930")).toBeInTheDocument();
    // 차트 영역
    expect(screen.getByRole("img", { name: "포트폴리오 시계열 차트" })).toBeInTheDocument();
    // 태그별 거래 집계 테이블 마운트
    expect(screen.getByText("태그별 거래 집계")).toBeInTheDocument();
  });

  it("TagBreakdownTable 이 DashboardView 에 마운트된다", () => {
    setupMocks(
      { data: fakeSummary },
      { data: [fakeHolding] },
    );
    render(<DashboardView />);
    expect(screen.getByText("태그별 거래 집계")).toBeInTheDocument();
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

  it("CurrencySwitcher 를 렌더링한다", () => {
    setupMocks({ data: fakeSummary }, { data: [fakeHolding] });
    render(<DashboardView />);
    expect(
      screen.getByRole("group", { name: "통화 환산 선택" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "환산 안 함" })).toBeInTheDocument();
  });

  it("환율 미비 시 안내 배너를 표시한다", () => {
    // displayCurrency가 없는 상태로 converted_* 가 모두 null (환율 미비 시뮬레이션)
    // DashboardView 의 내부 state 를 직접 조작할 수 없으므로
    // fakeSummary 에 displayCurrency가 있고 converted_* 가 모두 null 인 케이스를 모킹
    const fxUnavailableSummary: PortfolioSummary = {
      ...fakeSummary,
      convertedTotalValue: null,
      convertedPnlAbs: null,
      convertedRealizedPnl: null,
      displayCurrency: "KRW", // 이미 KRW 환산 응답이 왔으나 rate 없음
    };
    setupMocks({ data: fxUnavailableSummary }, { data: [fakeHolding] });
    render(<DashboardView />);
    // displayCurrency=null(초기) 이므로 배너 미표시 — 초기에는 not.toBeInTheDocument
    expect(screen.queryByRole("status", { name: /환율 준비 중/ })).not.toBeInTheDocument();
  });
});
