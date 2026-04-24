import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HoldingsTable } from "@/components/features/portfolio/holdings-table";
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
  latestPrice: "75000.0000",
  latestValue: "750000.00",
  pnlAbs: "50000.00",
  pnlPct: 7.14,
  weightPct: 60,
  lastPriceRefreshedAt: "2026-04-24T09:00:00+09:00",
  isStale: false,
  isPending: false,
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

describe("HoldingsTable", () => {
  it("빈 holdings 일 때 EmptyState 를 렌더링한다", () => {
    render(<HoldingsTable holdings={[]} />);
    expect(screen.getByText("보유 자산이 없습니다.")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "자산 추가하기" });
    expect(link).toHaveAttribute("href", "/assets/new");
  });

  it("holdings 가 있으면 테이블을 렌더링한다", () => {
    render(<HoldingsTable holdings={[holding1, holding2]} />);
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("005930")).toBeInTheDocument();
    expect(screen.getByText("AAPL")).toBeInTheDocument();
  });

  it("caption 이 존재한다 (시맨틱)", () => {
    render(<HoldingsTable holdings={[holding1]} />);
    expect(screen.getByText("보유 자산 목록 — 열 헤더를 클릭하면 정렬됩니다")).toBeInTheDocument();
  });

  it("pending 행에서 평가액·손익·비중 셀이 — 로 표시된다", () => {
    const pendingHolding = makeHolding({
      userAssetId: 3,
      latestPrice: null,
      latestValue: null,
      pnlAbs: null,
      pnlPct: null,
      isPending: true,
    });
    render(<HoldingsTable holdings={[pendingHolding]} />);
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(3);
  });

  it("pending 행에 PendingBadge 가 렌더링된다", () => {
    const pendingHolding = makeHolding({
      userAssetId: 3,
      isPending: true,
      latestPrice: null,
      latestValue: null,
      pnlAbs: null,
      pnlPct: null,
    });
    render(<HoldingsTable holdings={[pendingHolding]} />);
    expect(screen.getByText("가격 대기중")).toBeInTheDocument();
  });

  it("stale 행에 StaleBadge 가 렌더링된다", () => {
    const staleHolding = makeHolding({
      userAssetId: 4,
      isStale: true,
    });
    render(<HoldingsTable holdings={[staleHolding]} />);
    expect(screen.getByText("지연")).toBeInTheDocument();
  });

  it("평가액 헤더를 클릭하면 정렬 방향이 토글된다", async () => {
    const user = userEvent.setup();
    render(<HoldingsTable holdings={[holding1, holding2]} />);

    const valueHeader = screen.getByRole("columnheader", { name: /평가액/ });
    expect(valueHeader).toHaveAttribute("aria-sort", "descending");

    await user.click(valueHeader);
    expect(valueHeader).toHaveAttribute("aria-sort", "ascending");

    await user.click(valueHeader);
    expect(valueHeader).toHaveAttribute("aria-sort", "descending");
  });

  it("비중 헤더를 클릭하면 비중으로 정렬된다", async () => {
    const user = userEvent.setup();
    render(<HoldingsTable holdings={[holding1, holding2]} />);

    const weightHeader = screen.getByRole("columnheader", { name: /비중/ });
    await user.click(weightHeader);
    expect(weightHeader).toHaveAttribute("aria-sort", "descending");
  });

  it("정렬 헤더가 키보드 Enter 로 조작 가능하다", async () => {
    const user = userEvent.setup();
    render(<HoldingsTable holdings={[holding1, holding2]} />);

    const pnlHeader = screen.getByRole("columnheader", { name: /손익/ });
    pnlHeader.focus();
    await user.keyboard("{Enter}");
    expect(pnlHeader).toHaveAttribute("aria-sort", "descending");
  });

  it("다른 열 헤더로 전환하면 정렬 기준이 바뀐다", async () => {
    const user = userEvent.setup();
    render(<HoldingsTable holdings={[holding1, holding2]} />);

    const weightHeader = screen.getByRole("columnheader", { name: /비중/ });
    await user.click(weightHeader);

    const valueHeader = screen.getByRole("columnheader", { name: /평가액/ });
    expect(valueHeader).toHaveAttribute("aria-sort", "none");
    expect(weightHeader).toHaveAttribute("aria-sort", "descending");
  });

  it("행 클릭 시 /assets 로 이동한다", async () => {
    const user = userEvent.setup();
    render(<HoldingsTable holdings={[holding1]} />);

    const row = screen.getByText("005930").closest("tr");
    if (row) await user.click(row);
    expect(mockPush).toHaveBeenCalledWith("/assets");
  });
});
