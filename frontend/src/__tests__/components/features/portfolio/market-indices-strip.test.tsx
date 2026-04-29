import { render, screen } from "@testing-library/react";
import { MarketIndicesStrip } from "@/components/features/portfolio/market-indices-strip";
import * as hook from "@/hooks/use-market-indices";
import type { IndexQuote } from "@/types/market-index";

jest.mock("@/hooks/use-market-indices");
const mockedUseMarketIndices = jest.mocked(hook.useMarketIndices);

type HookReturn = ReturnType<typeof hook.useMarketIndices>;

function makeReturn(overrides: Partial<HookReturn>): HookReturn {
  return {
    data: undefined,
    isLoading: false,
    isError: false,
    isSuccess: false,
    error: null,
    ...overrides,
  } as HookReturn;
}

const sampleQuotes: IndexQuote[] = [
  {
    symbol: "^GSPC",
    name: "S&P 500",
    currency: "USD",
    price: "5123.41",
    change: "12.34",
    changePct: "0.24",
    fetchedAt: "2026-04-24T09:00:00Z",
  },
  {
    symbol: "BTC-KRW",
    name: "BTC",
    currency: "KRW",
    price: "92000000",
    change: "-1500000",
    changePct: "-1.60",
    fetchedAt: "2026-04-24T09:00:00Z",
  },
];

describe("MarketIndicesStrip", () => {
  beforeEach(() => jest.clearAllMocks());

  it("loading 상태에서 스켈레톤을 렌더링한다", () => {
    mockedUseMarketIndices.mockReturnValue(makeReturn({ isLoading: true }));
    render(<MarketIndicesStrip />);
    expect(screen.getByLabelText("지수 로딩 중")).toBeInTheDocument();
  });

  it("정상 데이터 — 지수 이름과 변동률을 표시한다", () => {
    mockedUseMarketIndices.mockReturnValue(
      makeReturn({ data: sampleQuotes, isSuccess: true }),
    );
    render(<MarketIndicesStrip />);
    expect(screen.getByText("S&P 500")).toBeInTheDocument();
    expect(screen.getByText("BTC")).toBeInTheDocument();
    expect(screen.getByText("+0.24%")).toBeInTheDocument();
    expect(screen.getByText("-1.6%")).toBeInTheDocument();
  });

  it("양수 변동은 toss-up, 음수는 toss-down 클래스를 적용한다", () => {
    mockedUseMarketIndices.mockReturnValue(
      makeReturn({ data: sampleQuotes, isSuccess: true }),
    );
    const { container } = render(<MarketIndicesStrip />);
    expect(container.querySelector(".text-toss-up")).toBeInTheDocument();
    expect(container.querySelector(".text-toss-down")).toBeInTheDocument();
  });

  it("에러 또는 빈 데이터일 때 아무것도 렌더링하지 않는다", () => {
    mockedUseMarketIndices.mockReturnValue(makeReturn({ isError: true, error: new Error("x") }));
    const { container: c1 } = render(<MarketIndicesStrip />);
    expect(c1.firstChild).toBeNull();

    mockedUseMarketIndices.mockReturnValue(makeReturn({ data: [], isSuccess: true }));
    const { container: c2 } = render(<MarketIndicesStrip />);
    expect(c2.firstChild).toBeNull();
  });
});
