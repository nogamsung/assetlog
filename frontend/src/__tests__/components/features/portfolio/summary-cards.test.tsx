import { render, screen } from "@testing-library/react";
import { SummaryCards } from "@/components/features/portfolio/summary-cards";
import type { PortfolioSummary } from "@/types/portfolio";

const baseSummary: PortfolioSummary = {
  totalValueByCurrency: { KRW: "12500000.00" },
  totalCostByCurrency: { KRW: "11000000.00" },
  pnlByCurrency: { KRW: { abs: "1500000.00", pct: 13.64 } },
  realizedPnlByCurrency: { KRW: "0.000000" },
  allocation: [{ assetType: "kr_stock", pct: 100 }],
  lastPriceRefreshedAt: "2026-04-24T00:00:00Z",
  pendingCount: 0,
  staleCount: 0,
  convertedTotalValue: null,
  convertedTotalCost: null,
  convertedPnlAbs: null,
  convertedRealizedPnl: null,
  displayCurrency: null,
  cashTotalByCurrency: {},
};

describe("SummaryCards", () => {
  it("주요 카드 제목을 렌더링한다", () => {
    render(<SummaryCards summary={baseSummary} />);
    expect(screen.getByText("총평가액")).toBeInTheDocument();
    expect(screen.getByText("미실현 손익")).toBeInTheDocument();
    expect(screen.getByText("실현 손익")).toBeInTheDocument();
    expect(screen.getByText("갱신 정보")).toBeInTheDocument();
  });

  it("양수 손익은 toss-up 클래스가 적용된다 (MODIFIED: was text-green-600)", () => {
    const { container } = render(<SummaryCards summary={baseSummary} />);
    // MODIFIED: pnlColor returns text-toss-up for positive
    const pnlEl = container.querySelector(".text-toss-up");
    expect(pnlEl).toBeInTheDocument();
  });

  it("음수 손익은 toss-down 클래스가 적용된다 (MODIFIED: was text-destructive)", () => {
    const negativeSummary: PortfolioSummary = {
      ...baseSummary,
      pnlByCurrency: { KRW: { abs: "-500000.00", pct: -4.55 } },
    };
    const { container } = render(<SummaryCards summary={negativeSummary} />);
    // MODIFIED: pnlColor returns text-toss-down for negative
    const pnlEl = container.querySelector(".text-toss-down");
    expect(pnlEl).toBeInTheDocument();
  });

  it("0 손익은 toss-textWeak 클래스가 적용된다 (MODIFIED: was text-muted-foreground)", () => {
    const zeroSummary: PortfolioSummary = {
      ...baseSummary,
      pnlByCurrency: { KRW: { abs: "0", pct: 0 } },
    };
    const { container } = render(<SummaryCards summary={zeroSummary} />);
    // MODIFIED: pnlColor returns text-toss-textWeak for zero
    const pnlEl = container.querySelector(".text-toss-textWeak");
    expect(pnlEl).toBeInTheDocument();
  });

  it("pending_count > 0 이면 대기 중 메시지를 표시한다", () => {
    const pendingSummary: PortfolioSummary = {
      ...baseSummary,
      pendingCount: 3,
    };
    render(<SummaryCards summary={pendingSummary} />);
    expect(screen.getByText("현재가 대기 중 3건")).toBeInTheDocument();
  });

  it("pending_count === 0 이면 대기 중 메시지를 표시하지 않는다", () => {
    render(<SummaryCards summary={baseSummary} />);
    expect(screen.queryByText(/현재가 대기 중/)).not.toBeInTheDocument();
  });

  it("다중 통화 총평가액을 구분자(·)로 표시한다", () => {
    const multiCurrencySummary: PortfolioSummary = {
      ...baseSummary,
      totalValueByCurrency: { KRW: "12500000.00", USD: "8200.12" },
    };
    render(<SummaryCards summary={multiCurrencySummary} />);
    const totalCard = screen.getByText(/·/);
    expect(totalCard).toBeInTheDocument();
  });

  it("totalValueByCurrency 가 비면 — 를 표시한다", () => {
    const emptySummary: PortfolioSummary = {
      ...baseSummary,
      totalValueByCurrency: {},
      pnlByCurrency: {},
    };
    render(<SummaryCards summary={emptySummary} />);
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it("staleCount > 0 이면 지연 메시지를 표시한다", () => {
    const staleSummary: PortfolioSummary = {
      ...baseSummary,
      staleCount: 2,
    };
    render(<SummaryCards summary={staleSummary} />);
    expect(screen.getByText("지연 2건")).toBeInTheDocument();
  });

  it("displayCurrency 있을 때 convertedTotalValue 를 메인으로 표시한다", () => {
    const convertedSummary: PortfolioSummary = {
      ...baseSummary,
      convertedTotalValue: "51380000.00",
      convertedTotalCost: "41104000.00",
      convertedPnlAbs: "10276000.00",
      convertedRealizedPnl: "369000.00",
      displayCurrency: "KRW",
    };
    render(<SummaryCards summary={convertedSummary} />);
    expect(screen.getByText(/51,380,000/)).toBeInTheDocument();
  });

  it("convertedPnlAbs 양수면 + 부호가 붙어 표시된다", () => {
    const convertedSummary: PortfolioSummary = {
      ...baseSummary,
      convertedTotalValue: "51380000.00",
      convertedTotalCost: "41104000.00",
      convertedPnlAbs: "10276000.00",
      convertedRealizedPnl: "369000.00",
      displayCurrency: "KRW",
    };
    render(<SummaryCards summary={convertedSummary} />);
    const plusElements = screen.getAllByText(/\+/);
    expect(plusElements.length).toBeGreaterThanOrEqual(1);
  });

  it("대형 KRW 값은 컴팩트 표기(억)를 사용한다 (ADDED: compact branch)", () => {
    const largeSummary: PortfolioSummary = {
      ...baseSummary,
      totalValueByCurrency: { KRW: "120000000.00" }, // 1.2억
    };
    render(<SummaryCards summary={largeSummary} />);
    // compact: 1.2억 should be shown
    expect(screen.getByText(/억/)).toBeInTheDocument();
  });
});
