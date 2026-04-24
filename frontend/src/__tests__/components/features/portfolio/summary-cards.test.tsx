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
};

describe("SummaryCards", () => {
  it("3개의 카드를 렌더링한다", () => {
    render(<SummaryCards summary={baseSummary} />);
    expect(screen.getByText("총평가액")).toBeInTheDocument();
    expect(screen.getByText("미실현 손익")).toBeInTheDocument();
    expect(screen.getByText("실현 손익")).toBeInTheDocument();
    expect(screen.getByText("갱신 정보")).toBeInTheDocument();
  });

  it("양수 손익은 녹색 클래스가 적용된다", () => {
    const { container } = render(<SummaryCards summary={baseSummary} />);
    const pnlEl = container.querySelector(".text-green-600");
    expect(pnlEl).toBeInTheDocument();
  });

  it("음수 손익은 destructive 클래스가 적용된다", () => {
    const negativeSummary: PortfolioSummary = {
      ...baseSummary,
      pnlByCurrency: { KRW: { abs: "-500000.00", pct: -4.55 } },
    };
    const { container } = render(<SummaryCards summary={negativeSummary} />);
    const pnlEl = container.querySelector(".text-destructive");
    expect(pnlEl).toBeInTheDocument();
  });

  it("0 손익은 muted-foreground 클래스가 적용된다", () => {
    const zeroSummary: PortfolioSummary = {
      ...baseSummary,
      pnlByCurrency: { KRW: { abs: "0", pct: 0 } },
    };
    const { container } = render(<SummaryCards summary={zeroSummary} />);
    const pnlEl = container.querySelector(".text-muted-foreground");
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
    // 구분자 · 가 포함된 텍스트 존재 확인
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
    // 환산값이 메인으로 렌더링되어 있어야 함 (KRW 포맷)
    expect(screen.getByText(/51,380,000/)).toBeInTheDocument();
  });

  it("displayCurrency 있을 때 per-currency 원본값을 서브텍스트로 표시한다", () => {
    const convertedSummary: PortfolioSummary = {
      ...baseSummary,
      convertedTotalValue: "51380000.00",
      convertedTotalCost: "41104000.00",
      convertedPnlAbs: "10276000.00",
      convertedRealizedPnl: "369000.00",
      displayCurrency: "KRW",
    };
    const { container } = render(<SummaryCards summary={convertedSummary} />);
    // 서브텍스트 요소가 존재해야 함
    const subTexts = container.querySelectorAll(".text-xs.text-muted-foreground");
    expect(subTexts.length).toBeGreaterThanOrEqual(1);
  });

  it("displayCurrency 없을 때 환산 서브텍스트가 없다", () => {
    const { container } = render(<SummaryCards summary={baseSummary} />);
    // text-xs.text-muted-foreground 는 없어야 함
    const subTexts = container.querySelectorAll("p.text-xs.text-muted-foreground");
    expect(subTexts).toHaveLength(0);
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
});
