import { render, screen, fireEvent } from "@testing-library/react";
import { HoldingsList } from "@/components/features/portfolio/holdings-list";
import type { HoldingResponse } from "@/types/portfolio";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

const makeHolding = (overrides: Partial<HoldingResponse> = {}): HoldingResponse => ({
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
  realizedPnl: "0.000000",
  latestPrice: "75000.0000",
  latestValue: "750000.00",
  pnlAbs: "50000.00",
  pnlPct: 7.14,
  weightPct: 60,
  lastPriceRefreshedAt: "2026-04-24T09:00:00+09:00",
  isStale: false,
  isPending: false,
  convertedLatestValue: null,
  convertedCostBasis: null,
  convertedPnlAbs: null,
  convertedRealizedPnl: null,
  displayCurrency: null,
  ...overrides,
});

const holding1 = makeHolding({
  userAssetId: 1,
  latestValue: "750000.00",
  weightPct: 60,
});

const holding2 = makeHolding({
  userAssetId: 2,
  assetSymbol: {
    id: 2,
    assetType: "us_stock",
    symbol: "AAPL",
    exchange: "NASDAQ",
    name: "Apple",
    currency: "USD",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
  latestValue: "500000.00",
  pnlAbs: "-10000.00",
  pnlPct: -2.0,
  weightPct: 40,
});

describe("HoldingsList", () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it("빈 holdings 일 때 EmptyState 를 렌더링한다", () => {
    render(<HoldingsList holdings={[]} />);
    expect(screen.getByText("보유 자산이 없습니다.")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "자산 추가하기" });
    expect(link).toHaveAttribute("href", "/assets/new");
  });

  it("holdings 가 있으면 심볼을 표시한다", () => {
    render(<HoldingsList holdings={[holding1, holding2]} />);
    expect(screen.getByText("005930")).toBeInTheDocument();
    expect(screen.getByText("AAPL")).toBeInTheDocument();
  });

  it("종목명이 표시된다", () => {
    render(<HoldingsList holdings={[holding1]} />);
    expect(screen.getByText("삼성전자")).toBeInTheDocument();
  });

  it("평가액이 포맷되어 표시된다", () => {
    render(<HoldingsList holdings={[holding1]} />);
    expect(screen.getByText(/750,000/)).toBeInTheDocument();
  });

  it("양수 손익은 toss-up 클래스로 표시된다", () => {
    render(<HoldingsList holdings={[holding1]} />);
    const pnlElements = document.querySelectorAll(".text-toss-up");
    expect(pnlElements.length).toBeGreaterThan(0);
  });

  it("음수 손익은 toss-down 클래스로 표시된다", () => {
    render(<HoldingsList holdings={[holding2]} />);
    const pnlElements = document.querySelectorAll(".text-toss-down");
    expect(pnlElements.length).toBeGreaterThan(0);
  });

  it("isPending 인 행은 — 로 표시한다", () => {
    const pending = makeHolding({
      userAssetId: 3,
      isPending: true,
      latestValue: null,
      pnlAbs: null,
      pnlPct: null,
    });
    render(<HoldingsList holdings={[pending]} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("행 클릭 시 자산 상세 페이지로 이동한다", () => {
    render(<HoldingsList holdings={[holding1]} />);
    const row = screen.getByRole("button", { name: /005930 상세 보기/ });
    fireEvent.click(row);
    expect(mockPush).toHaveBeenCalledWith("/assets/1");
  });

  it("circular icon 에 심볼 약자가 표시된다", () => {
    render(<HoldingsList holdings={[holding1]} />);
    // symbol "005930" → abbr "00"
    expect(screen.getByText("00")).toBeInTheDocument();
  });

  it("컴포넌트 최상위가 sm:hidden 블록이다 (모바일 전용)", () => {
    const { container } = render(<HoldingsList holdings={[holding1]} />);
    const outer = container.firstChild as HTMLElement;
    expect(outer.className).toContain("block");
    expect(outer.className).toContain("sm:hidden");
  });

  it("정렬 버튼이 렌더링된다", () => {
    render(<HoldingsList holdings={[holding1, holding2]} />);
    const sortBtn = screen.getByRole("button", { name: "정렬 기준 변경" });
    expect(sortBtn).toBeInTheDocument();
  });

  it("정렬 버튼 클릭 시 드롭다운이 열린다", () => {
    render(<HoldingsList holdings={[holding1, holding2]} />);
    const sortBtn = screen.getByRole("button", { name: "정렬 기준 변경" });
    fireEvent.click(sortBtn);
    expect(screen.getByText("평가액")).toBeInTheDocument();
    expect(screen.getByText("손익")).toBeInTheDocument();
    expect(screen.getByText("비중")).toBeInTheDocument();
  });

  it("displayCurrency 있을 때 converted 값을 표시한다", () => {
    const converted = makeHolding({
      userAssetId: 5,
      latestValue: "1752.00",
      convertedLatestValue: "2437280.00",
      displayCurrency: "KRW",
    });
    render(<HoldingsList holdings={[converted]} />);
    expect(screen.getByText(/2,437,280/)).toBeInTheDocument();
  });
});
