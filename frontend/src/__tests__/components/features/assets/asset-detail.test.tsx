import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { AssetDetail } from "@/components/features/assets/asset-detail";
import * as usePortfolioHook from "@/hooks/use-portfolio";
import * as useTransactionsHook from "@/hooks/use-transactions";
import type { HoldingResponse } from "@/types/portfolio";
import type { TransactionResponse } from "@/types/transaction"; // ADDED

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("@/hooks/use-portfolio", () => ({
  ...jest.requireActual("@/hooks/use-portfolio"),
  usePortfolioHoldings: jest.fn(),
}));

jest.mock("@/hooks/use-transactions", () => ({
  ...jest.requireActual("@/hooks/use-transactions"),
  useAssetSummary: jest.fn(),
  useCreateTransaction: jest.fn(),
  useUpdateTransaction: jest.fn(), // ADDED
  useDeleteTransaction: jest.fn(),
  useTransactions: jest.fn(),
  useImportTransactionsCsv: jest.fn(),
}));

const mockedUsePortfolioHoldings = jest.mocked(usePortfolioHook.usePortfolioHoldings);
const mockedUseAssetSummary = jest.mocked(useTransactionsHook.useAssetSummary);
const mockedUseCreateTransaction = jest.mocked(useTransactionsHook.useCreateTransaction);
const mockedUseUpdateTransaction = jest.mocked(useTransactionsHook.useUpdateTransaction); // ADDED
const mockedUseDeleteTransaction = jest.mocked(useTransactionsHook.useDeleteTransaction);
const mockedUseTransactions = jest.mocked(useTransactionsHook.useTransactions);
const mockedUseImportTransactionsCsv = jest.mocked(useTransactionsHook.useImportTransactionsCsv);

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return { Wrapper };
}

const fakeHolding: HoldingResponse = {
  userAssetId: 10,
  assetSymbol: {
    id: 1,
    assetType: "crypto",
    symbol: "BTC",
    exchange: "BINANCE",
    name: "Bitcoin",
    currency: "USD",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
  quantity: "1.5000000000",
  avgCost: "50000.000000",
  costBasis: "75000.00",
  realizedPnl: "0.000000",
  latestPrice: "55000.000000",
  latestValue: "82500.00",
  pnlAbs: "7500.00",
  pnlPct: 10.0,
  weightPct: 100,
  lastPriceRefreshedAt: "2026-04-24T09:00:00Z",
  isStale: false,
  isPending: false,
};

function setupAllMocks(opts: {
  holdingLoading?: boolean;
  holdingError?: boolean;
  holdings?: HoldingResponse[];
} = {}) {
  mockedUsePortfolioHoldings.mockReturnValue({
    data: opts.holdings ?? [fakeHolding],
    isLoading: opts.holdingLoading ?? false,
    isError: opts.holdingError ?? false,
    error: null,
    isSuccess: !opts.holdingLoading && !opts.holdingError,
  } as unknown as ReturnType<typeof usePortfolioHook.usePortfolioHoldings>);

  mockedUseAssetSummary.mockReturnValue({
    data: {
      userAssetId: 10,
      totalBoughtQuantity: "1.5",
      totalSoldQuantity: "0",
      remainingQuantity: "1.5",
      avgBuyPrice: "50000",
      totalInvested: "75000",
      totalSoldValue: "0",
      realizedPnl: "0",
      transactionCount: 2,
      currency: "USD",
    },
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: true,
  } as unknown as ReturnType<typeof useTransactionsHook.useAssetSummary>);

  mockedUseCreateTransaction.mockReturnValue({
    mutate: jest.fn(),
    isPending: false,
    isSuccess: false,
    isError: false,
    error: null,
  } as unknown as ReturnType<typeof useTransactionsHook.useCreateTransaction>);

  mockedUseUpdateTransaction.mockReturnValue({ // ADDED
    mutate: jest.fn(),
    isPending: false,
    isSuccess: false,
    isError: false,
    error: null,
  } as unknown as ReturnType<typeof useTransactionsHook.useUpdateTransaction>);

  mockedUseDeleteTransaction.mockReturnValue({
    mutate: jest.fn(),
    isPending: false,
    isSuccess: false,
    isError: false,
  } as unknown as ReturnType<typeof useTransactionsHook.useDeleteTransaction>);

  mockedUseTransactions.mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: true,
  } as unknown as ReturnType<typeof useTransactionsHook.useTransactions>);

  mockedUseImportTransactionsCsv.mockReturnValue({
    mutate: jest.fn(),
    isPending: false,
    isSuccess: false,
    isError: false,
    error: null,
  } as unknown as ReturnType<typeof useTransactionsHook.useImportTransactionsCsv>);
}

describe("AssetDetail", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupAllMocks();
  });

  it("로딩 중이면 스켈레톤이 표시된다", () => {
    setupAllMocks({ holdingLoading: true });
    const { Wrapper } = makeWrapper();
    render(<AssetDetail userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("에러 시 에러 메시지가 표시된다", () => {
    setupAllMocks({ holdingError: true });
    const { Wrapper } = makeWrapper();
    render(<AssetDetail userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.getByRole("alert")).toHaveTextContent(
      "자산 정보를 불러오지 못했습니다.",
    );
  });

  it("holding 정보가 렌더링된다", () => {
    const { Wrapper } = makeWrapper();
    render(<AssetDetail userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.getByText("BTC")).toBeInTheDocument();
    expect(screen.getByText("Bitcoin")).toBeInTheDocument();
  });

  it("holding 이 없으면 '자산 정보를 찾을 수 없습니다' 가 표시된다", () => {
    setupAllMocks({ holdings: [] });
    const { Wrapper } = makeWrapper();
    render(<AssetDetail userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.getByText(/자산 정보를 찾을 수 없습니다/)).toBeInTheDocument();
  });

  it("'거래 추가' 버튼 클릭 시 TransactionForm 이 표시된다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<AssetDetail userAssetId={10} />, { wrapper: Wrapper });

    await user.click(screen.getByLabelText("거래 추가"));

    await waitFor(() => {
      expect(screen.getByRole("form", { name: "거래 추가 폼" })).toBeInTheDocument();
    });
  });

  it("'닫기' 버튼 클릭 시 TransactionForm 이 숨겨진다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<AssetDetail userAssetId={10} />, { wrapper: Wrapper });

    await user.click(screen.getByLabelText("거래 추가"));
    await waitFor(() => {
      expect(screen.getByRole("form", { name: "거래 추가 폼" })).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("거래 추가 폼 닫기"));
    await waitFor(() => {
      expect(
        screen.queryByRole("form", { name: "거래 추가 폼" }),
      ).not.toBeInTheDocument();
    });
  });

  it("보유 자산 목록으로 링크가 있다", () => {
    const { Wrapper } = makeWrapper();
    render(<AssetDetail userAssetId={10} />, { wrapper: Wrapper });

    expect(
      screen.getByRole("link", { name: "보유 자산 목록으로 돌아가기" }),
    ).toHaveAttribute("href", "/assets");
  });

  it("편집 버튼 클릭 시 거래 수정 폼이 열린다", async () => { // ADDED
    const fakeTx: TransactionResponse = {
      id: 1,
      userAssetId: 10,
      type: "buy",
      quantity: "1.5000000000",
      price: "50000.000000",
      tradedAt: "2026-04-23T10:00:00Z",
      memo: null,
      tag: null,
      createdAt: "2026-04-23T10:01:00Z",
    };
    mockedUseTransactions.mockReturnValue({
      data: [fakeTx],
      isLoading: false,
      isError: false,
      error: null,
      isSuccess: true,
    } as unknown as ReturnType<typeof useTransactionsHook.useTransactions>);

    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<AssetDetail userAssetId={10} />, { wrapper: Wrapper });

    await user.click(screen.getByLabelText("거래 #1 편집"));

    await waitFor(() => {
      expect(screen.getByRole("form", { name: "거래 수정 폼" })).toBeInTheDocument();
    });
  });

  it("'CSV 가져오기' 버튼이 렌더링된다", () => {
    const { Wrapper } = makeWrapper();
    render(<AssetDetail userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.getByLabelText("CSV 가져오기")).toBeInTheDocument();
  });

  it("'CSV 가져오기' 버튼 클릭 시 TransactionImport 패널이 표시된다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<AssetDetail userAssetId={10} />, { wrapper: Wrapper });

    await user.click(screen.getByLabelText("CSV 가져오기"));

    await waitFor(() => {
      expect(screen.getByLabelText("CSV 가져오기 폼")).toBeInTheDocument();
    });
  });

  it("'CSV 가져오기 패널 닫기' 버튼 클릭 시 패널이 닫힌다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<AssetDetail userAssetId={10} />, { wrapper: Wrapper });

    await user.click(screen.getByLabelText("CSV 가져오기"));
    await waitFor(() => {
      expect(screen.getByLabelText("CSV 가져오기 폼")).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("CSV 가져오기 패널 닫기"));
    await waitFor(() => {
      expect(screen.queryByLabelText("CSV 가져오기 폼")).not.toBeInTheDocument();
    });
  });

  it("'CSV 가져오기' 클릭 시 거래 추가 폼이 닫힌다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<AssetDetail userAssetId={10} />, { wrapper: Wrapper });

    // 거래 추가 폼 먼저 열기
    await user.click(screen.getByLabelText("거래 추가"));
    await waitFor(() => {
      expect(screen.getByRole("form", { name: "거래 추가 폼" })).toBeInTheDocument();
    });

    // CSV 가져오기 클릭 → 거래 추가 폼 닫힘
    await user.click(screen.getByLabelText("CSV 가져오기"));
    await waitFor(() => {
      expect(screen.queryByRole("form", { name: "거래 추가 폼" })).not.toBeInTheDocument();
      expect(screen.getByLabelText("CSV 가져오기 폼")).toBeInTheDocument();
    });
  });

  it("거래 수정 폼 닫기 버튼 클릭 시 폼이 닫힌다", async () => { // ADDED
    const fakeTx: TransactionResponse = {
      id: 1,
      userAssetId: 10,
      type: "buy",
      quantity: "1.5000000000",
      price: "50000.000000",
      tradedAt: "2026-04-23T10:00:00Z",
      memo: null,
      tag: null,
      createdAt: "2026-04-23T10:01:00Z",
    };
    mockedUseTransactions.mockReturnValue({
      data: [fakeTx],
      isLoading: false,
      isError: false,
      error: null,
      isSuccess: true,
    } as unknown as ReturnType<typeof useTransactionsHook.useTransactions>);

    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<AssetDetail userAssetId={10} />, { wrapper: Wrapper });

    await user.click(screen.getByLabelText("거래 #1 편집"));
    await waitFor(() => {
      expect(screen.getByRole("form", { name: "거래 수정 폼" })).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("거래 수정 폼 닫기"));
    await waitFor(() => {
      expect(screen.queryByRole("form", { name: "거래 수정 폼" })).not.toBeInTheDocument();
    });
  });
});
