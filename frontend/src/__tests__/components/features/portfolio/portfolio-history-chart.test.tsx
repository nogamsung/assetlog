import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { PortfolioHistoryChart } from "@/components/features/portfolio/portfolio-history-chart";
import * as usePortfolioHistoryHook from "@/hooks/use-portfolio-history";
import type { PortfolioHistoryResponse } from "@/types/portfolio-history";

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

jest.mock("@/hooks/use-portfolio-history", () => ({
  ...jest.requireActual("@/hooks/use-portfolio-history"),
  usePortfolioHistory: jest.fn(),
}));

const mockedUsePortfolioHistory = jest.mocked(
  usePortfolioHistoryHook.usePortfolioHistory,
);

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return { Wrapper };
}

const fakeHistoryData: PortfolioHistoryResponse = {
  currency: "KRW",
  period: "1M",
  bucket: "DAY",
  points: [
    {
      timestamp: new Date("2026-03-25T00:00:00Z"),
      value: "1234567.000000",
      costBasis: "1000000.000000",
    },
    {
      timestamp: new Date("2026-03-26T00:00:00Z"),
      value: "1300000.000000",
      costBasis: "1000000.000000",
    },
  ],
};

function setupHistoryMock(opts: {
  data?: PortfolioHistoryResponse;
  isLoading?: boolean;
  isError?: boolean;
  error?: Error | null;
} = {}) {
  mockedUsePortfolioHistory.mockReturnValue({
    data: opts.data,
    isLoading: opts.isLoading ?? false,
    isError: opts.isError ?? false,
    error: opts.error ?? null,
    isSuccess: !opts.isLoading && !opts.isError && !!opts.data,
  } as unknown as ReturnType<typeof usePortfolioHistoryHook.usePortfolioHistory>);
}

describe("PortfolioHistoryChart", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupHistoryMock({ data: fakeHistoryData });
  });

  it("로딩 중이면 스켈레톤이 표시된다", () => {
    setupHistoryMock({ isLoading: true });
    const { Wrapper } = makeWrapper();
    render(<PortfolioHistoryChart currency="KRW" />, { wrapper: Wrapper });

    expect(screen.getByRole("status", { name: "차트 로딩 중" })).toBeInTheDocument();
  });

  it("에러 시 에러 메시지가 표시된다", () => {
    setupHistoryMock({ isError: true, error: new Error("차트 오류") });
    const { Wrapper } = makeWrapper();
    render(<PortfolioHistoryChart currency="KRW" />, { wrapper: Wrapper });

    expect(screen.getByRole("alert")).toHaveTextContent("차트 오류");
  });

  it("데이터가 없으면 빈 상태 메시지가 표시된다", () => {
    setupHistoryMock({ data: { ...fakeHistoryData, points: [] } });
    const { Wrapper } = makeWrapper();
    render(<PortfolioHistoryChart currency="KRW" />, { wrapper: Wrapper });

    expect(screen.getByText("해당 기간에 데이터가 없습니다.")).toBeInTheDocument();
  });

  it("데이터가 있으면 차트가 렌더링된다", () => {
    const { Wrapper } = makeWrapper();
    render(<PortfolioHistoryChart currency="KRW" />, { wrapper: Wrapper });

    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
  });

  it("role='img' aria-label='포트폴리오 시계열 차트' 가 있다", () => {
    const { Wrapper } = makeWrapper();
    render(<PortfolioHistoryChart currency="KRW" />, { wrapper: Wrapper });

    expect(
      screen.getByRole("img", { name: "포트폴리오 시계열 차트" }),
    ).toBeInTheDocument();
  });

  it("기간 탭 그룹이 렌더링된다", () => {
    const { Wrapper } = makeWrapper();
    render(<PortfolioHistoryChart currency="KRW" />, { wrapper: Wrapper });

    expect(screen.getByRole("group", { name: "차트 기간 선택" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "1일 기간 선택" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "1개월 기간 선택" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "전체 기간 선택" })).toBeInTheDocument();
  });

  it("기간 탭 전환 시 usePortfolioHistory 가 새 period 로 호출된다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<PortfolioHistoryChart currency="KRW" />, { wrapper: Wrapper });

    await user.click(screen.getByRole("button", { name: "1일 기간 선택" }));

    await waitFor(() => {
      expect(mockedUsePortfolioHistory).toHaveBeenCalledWith(
        expect.objectContaining({ period: "1D", currency: "KRW" }),
      );
    });
  });

  it("currency prop 이 usePortfolioHistory 에 전달된다", () => {
    const { Wrapper } = makeWrapper();
    render(<PortfolioHistoryChart currency="USD" />, { wrapper: Wrapper });

    expect(mockedUsePortfolioHistory).toHaveBeenCalledWith(
      expect.objectContaining({ currency: "USD" }),
    );
  });

  it("1M 이 기본 period 다", () => {
    const { Wrapper } = makeWrapper();
    render(<PortfolioHistoryChart currency="KRW" />, { wrapper: Wrapper });

    expect(mockedUsePortfolioHistory).toHaveBeenCalledWith(
      expect.objectContaining({ period: "1M" }),
    );
  });
});
