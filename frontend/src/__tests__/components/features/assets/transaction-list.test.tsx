import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { TransactionList } from "@/components/features/assets/transaction-list";
import * as useTransactionsHook from "@/hooks/use-transactions";
import type { TransactionResponse } from "@/types/transaction";

jest.mock("@/hooks/use-transactions", () => ({
  ...jest.requireActual("@/hooks/use-transactions"),
  useTransactions: jest.fn(),
  useDeleteTransaction: jest.fn(),
}));

const mockedUseTransactions = jest.mocked(useTransactionsHook.useTransactions);
const mockedUseDeleteTransaction = jest.mocked(
  useTransactionsHook.useDeleteTransaction,
);

const mockDeleteMutate = jest.fn();

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

const fakeTx: TransactionResponse = {
  id: 1,
  userAssetId: 10,
  type: "buy",
  quantity: "1.5000000000",
  price: "50000.000000",
  tradedAt: "2026-04-23T10:00:00Z",
  memo: "테스트 메모",
  tag: null,
  createdAt: "2026-04-23T10:01:00Z",
};

function setupMocks(
  txData: TransactionResponse[] | null = null,
  opts: {
    isLoading?: boolean;
    isError?: boolean;
    error?: Error | null;
  } = {},
) {
  mockedUseTransactions.mockReturnValue({
    data: txData ?? undefined,
    isLoading: opts.isLoading ?? false,
    isError: opts.isError ?? false,
    error: opts.error ?? null,
    isSuccess: !opts.isLoading && !opts.isError,
  } as unknown as ReturnType<typeof useTransactionsHook.useTransactions>);

  mockedUseDeleteTransaction.mockReturnValue({
    mutate: mockDeleteMutate,
    isPending: false,
    isSuccess: false,
    isError: false,
  } as unknown as ReturnType<typeof useTransactionsHook.useDeleteTransaction>);
}

describe("TransactionList", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(window, "confirm").mockReturnValue(true);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("로딩 중이면 스켈레톤이 표시된다", () => {
    setupMocks(null, { isLoading: true });
    const { Wrapper } = makeWrapper();
    render(<TransactionList userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.getByRole("status")).toHaveAttribute(
      "aria-label",
      "거래 내역 로딩 중",
    );
  });

  it("에러 시 에러 메시지가 표시된다", () => {
    setupMocks(null, { isError: true, error: new Error("네트워크 오류") });
    const { Wrapper } = makeWrapper();
    render(<TransactionList userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.getByRole("alert")).toHaveTextContent("네트워크 오류");
  });

  it("빈 배열이면 빈 상태 메시지가 표시된다", () => {
    setupMocks([]);
    const { Wrapper } = makeWrapper();
    render(<TransactionList userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.getByText("거래 내역이 없습니다.")).toBeInTheDocument();
  });

  it("거래 목록이 렌더링된다", () => {
    setupMocks([fakeTx]);
    const { Wrapper } = makeWrapper();
    render(<TransactionList userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.getByText("매수")).toBeInTheDocument();
    expect(screen.getByText(/1\.5000000000/)).toBeInTheDocument();
  });

  it("삭제 버튼 클릭 → confirm → mutate 호출", async () => {
    setupMocks([fakeTx]);
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<TransactionList userAssetId={10} />, { wrapper: Wrapper });

    await user.click(screen.getByLabelText("거래 #1 삭제"));

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalledWith(
        "이 거래 기록을 삭제하시겠습니까?",
      );
      expect(mockDeleteMutate).toHaveBeenCalledWith({
        userAssetId: 10,
        txId: 1,
      });
    });
  });

  it("confirm 취소 시 mutate 가 호출되지 않는다", async () => {
    jest.spyOn(window, "confirm").mockReturnValue(false);
    setupMocks([fakeTx]);
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<TransactionList userAssetId={10} />, { wrapper: Wrapper });

    await user.click(screen.getByLabelText("거래 #1 삭제"));

    expect(mockDeleteMutate).not.toHaveBeenCalled();
  });

  it("sell 타입 거래는 '매도' 배지를 표시한다", () => {
    setupMocks([{ ...fakeTx, type: "sell" }]);
    const { Wrapper } = makeWrapper();
    render(<TransactionList userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.getByText("매도")).toBeInTheDocument();
  });

  it("onEdit prop 이 있으면 편집 버튼이 렌더링된다", () => { // ADDED
    setupMocks([fakeTx]);
    const mockOnEdit = jest.fn();
    const { Wrapper } = makeWrapper();
    render(<TransactionList userAssetId={10} onEdit={mockOnEdit} />, { wrapper: Wrapper });

    expect(screen.getByLabelText("거래 #1 편집")).toBeInTheDocument();
  });

  it("onEdit prop 이 없으면 편집 버튼이 렌더링되지 않는다", () => { // ADDED
    setupMocks([fakeTx]);
    const { Wrapper } = makeWrapper();
    render(<TransactionList userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.queryByLabelText("거래 #1 편집")).not.toBeInTheDocument();
  });

  it("편집 버튼 클릭 시 onEdit 콜백이 해당 거래와 함께 호출된다", async () => { // ADDED
    setupMocks([fakeTx]);
    const mockOnEdit = jest.fn();
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<TransactionList userAssetId={10} onEdit={mockOnEdit} />, { wrapper: Wrapper });

    await user.click(screen.getByLabelText("거래 #1 편집"));

    expect(mockOnEdit).toHaveBeenCalledWith(fakeTx);
  });
});

describe("TransactionList — tag 표시", () => {
  beforeEach(() => jest.clearAllMocks());

  it("tag 가 있는 거래에 태그 뱃지가 렌더링된다", () => {
    const taggedTx: TransactionResponse = { ...fakeTx, tag: "DCA" };
    setupMocks([taggedTx]);
    const { Wrapper } = makeWrapper();
    render(<TransactionList userAssetId={10} />, { wrapper: Wrapper });

    const badge = screen.getByLabelText("태그 DCA 필터 적용");
    expect(badge).toHaveTextContent("DCA");
  });

  it("tag 가 null 이면 뱃지가 렌더링되지 않는다", () => {
    setupMocks([fakeTx]);
    const { Wrapper } = makeWrapper();
    render(<TransactionList userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.queryByLabelText(/태그.*필터 적용/)).not.toBeInTheDocument();
  });

  it("태그 뱃지 클릭 시 onTagClick 콜백이 호출된다", async () => {
    const user = userEvent.setup();
    const onTagClick = jest.fn();
    const taggedTx: TransactionResponse = { ...fakeTx, tag: "스윙" };
    setupMocks([taggedTx]);
    const { Wrapper } = makeWrapper();
    render(
      <TransactionList userAssetId={10} onTagClick={onTagClick} />,
      { wrapper: Wrapper },
    );

    await user.click(screen.getByLabelText("태그 스윙 필터 적용"));
    expect(onTagClick).toHaveBeenCalledWith("스윙");
  });

  it("activeTag 가 주어지면 useTransactions 에 전달된다", () => {
    setupMocks([]);
    const { Wrapper } = makeWrapper();
    render(
      <TransactionList userAssetId={10} activeTag="DCA" />,
      { wrapper: Wrapper },
    );

    expect(mockedUseTransactions).toHaveBeenCalledWith(10, "DCA");
  });
});
