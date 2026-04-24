import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { TransactionForm } from "@/components/features/assets/transaction-form";
import * as useTransactionsHook from "@/hooks/use-transactions";

jest.mock("@/hooks/use-transactions", () => ({
  ...jest.requireActual("@/hooks/use-transactions"),
  useCreateTransaction: jest.fn(),
}));

const mockedUseCreateTransaction = jest.mocked(
  useTransactionsHook.useCreateTransaction,
);

const mockMutate = jest.fn();
const mockOnSuccess = jest.fn();

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

function setupMutationMock(opts: {
  isPending?: boolean;
  isError?: boolean;
  error?: Error | null;
} = {}) {
  mockedUseCreateTransaction.mockReturnValue({
    mutate: mockMutate,
    isPending: opts.isPending ?? false,
    isSuccess: false,
    isError: opts.isError ?? false,
    error: opts.error ?? null,
  } as unknown as ReturnType<typeof useTransactionsHook.useCreateTransaction>);
}

describe("TransactionForm", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupMutationMock();
  });

  it("폼 필드들이 렌더링된다", () => {
    const { Wrapper } = makeWrapper();
    render(<TransactionForm userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.getByLabelText("거래 유형")).toBeInTheDocument();
    expect(screen.getByLabelText("거래 수량")).toBeInTheDocument();
    expect(screen.getByLabelText("거래 단가")).toBeInTheDocument();
    expect(screen.getByLabelText("거래일")).toBeInTheDocument();
    expect(screen.getByLabelText("거래 메모")).toBeInTheDocument();
  });

  it("빈 수량으로 제출 시 유효성 오류가 표시된다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<TransactionForm userAssetId={10} />, { wrapper: Wrapper });

    await user.click(screen.getByRole("button", { name: "거래 추가" }));

    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
    });
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("음수 또는 0 수량은 유효성 오류가 표시된다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<TransactionForm userAssetId={10} />, { wrapper: Wrapper });

    await user.type(screen.getByLabelText("거래 수량"), "0");
    await user.click(screen.getByRole("button", { name: "거래 추가" }));

    await waitFor(() => {
      expect(
        screen.getByText("0보다 큰 값을 입력하세요"),
      ).toBeInTheDocument();
    });
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("유효한 데이터 제출 시 mutate 가 호출된다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<TransactionForm userAssetId={10} onSuccess={mockOnSuccess} />, {
      wrapper: Wrapper,
    });

    await user.type(screen.getByLabelText("거래 수량"), "1.5");
    await user.type(screen.getByLabelText("거래 단가"), "50000");

    await user.click(screen.getByRole("button", { name: "거래 추가" }));

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          userAssetId: 10,
          data: expect.objectContaining({
            type: "buy",
            quantity: "1.5",
            price: "50000",
          }),
        }),
        expect.any(Object),
      );
    });
  });

  it("isPending 시 버튼이 disabled 되고 '등록 중...' 이 표시된다", () => {
    setupMutationMock({ isPending: true });
    const { Wrapper } = makeWrapper();
    render(<TransactionForm userAssetId={10} />, { wrapper: Wrapper });

    const submitBtn = screen.getByRole("button", { name: /등록 중/ });
    expect(submitBtn).toBeDisabled();
  });

  it("isError 시 에러 메시지가 표시된다", () => {
    setupMutationMock({ isError: true, error: new Error("거래 등록에 실패했습니다.") });
    const { Wrapper } = makeWrapper();
    render(<TransactionForm userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.getByRole("alert")).toHaveTextContent("거래 등록에 실패했습니다.");
  });

  it("숫자가 아닌 수량 입력 시 유효성 오류가 표시된다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<TransactionForm userAssetId={10} />, { wrapper: Wrapper });

    await user.type(screen.getByLabelText("거래 수량"), "abc");
    await user.click(screen.getByRole("button", { name: "거래 추가" }));

    await waitFor(() => {
      expect(screen.getAllByText("유효한 숫자를 입력하세요").length).toBeGreaterThan(0);
    });
  });
});
