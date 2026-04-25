import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { TransactionForm } from "@/components/features/assets/transaction-form";
import * as useTransactionsHook from "@/hooks/use-transactions";
import type { TransactionResponse } from "@/types/transaction";

jest.mock("@/hooks/use-transactions", () => ({
  ...jest.requireActual("@/hooks/use-transactions"),
  useCreateTransaction: jest.fn(),
  useUpdateTransaction: jest.fn(),
  useUserTags: jest.fn(),
}));

const mockedUseCreateTransaction = jest.mocked(
  useTransactionsHook.useCreateTransaction,
);
const mockedUseUpdateTransaction = jest.mocked(
  useTransactionsHook.useUpdateTransaction,
);
const mockedUseUserTags = jest.mocked(useTransactionsHook.useUserTags);

const mockMutate = jest.fn();
const mockUpdateMutate = jest.fn(); // ADDED
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
  tags?: string[];
} = {}) {
  mockedUseCreateTransaction.mockReturnValue({
    mutate: mockMutate,
    isPending: opts.isPending ?? false,
    isSuccess: false,
    isError: opts.isError ?? false,
    error: opts.error ?? null,
  } as unknown as ReturnType<typeof useTransactionsHook.useCreateTransaction>);
  mockedUseUpdateTransaction.mockReturnValue({
    mutate: mockUpdateMutate,
    isPending: false,
    isSuccess: false,
    isError: false,
    error: null,
  } as unknown as ReturnType<typeof useTransactionsHook.useUpdateTransaction>);
  mockedUseUserTags.mockReturnValue({
    data: opts.tags ?? [],
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: true,
  } as unknown as ReturnType<typeof useTransactionsHook.useUserTags>);
}

const fakeInitialTx: TransactionResponse = { // ADDED
  id: 5,
  userAssetId: 10,
  type: "sell",
  quantity: "2.0",
  price: "60000",
  tradedAt: "2026-04-20T12:00:00Z",
  memo: "기존 메모",
  tag: null,
  createdAt: "2026-04-20T12:01:00Z",
};

describe("TransactionForm (create 모드 — 기본값)", () => {
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

describe("TransactionForm (edit 모드)", () => { // ADDED
  beforeEach(() => {
    jest.clearAllMocks();
    setupMutationMock();
  });

  it("edit 모드에서 '수정하기' 버튼과 '거래 수정 폼' aria-label 이 렌더링된다", () => {
    const { Wrapper } = makeWrapper();
    render(
      <TransactionForm userAssetId={10} mode="edit" initialValues={fakeInitialTx} />,
      { wrapper: Wrapper },
    );

    expect(screen.getByRole("form", { name: "거래 수정 폼" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "수정하기" })).toBeInTheDocument();
  });

  it("initialValues 의 값이 폼 초기값으로 설정된다", () => {
    const { Wrapper } = makeWrapper();
    render(
      <TransactionForm userAssetId={10} mode="edit" initialValues={fakeInitialTx} />,
      { wrapper: Wrapper },
    );

    const quantityInput = screen.getByLabelText("거래 수량") as HTMLInputElement;
    const priceInput = screen.getByLabelText("거래 단가") as HTMLInputElement;
    expect(quantityInput.value).toBe("2.0");
    expect(priceInput.value).toBe("60000");
  });

  it("edit 모드 제출 시 useUpdateTransaction.mutate 가 호출된다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(
      <TransactionForm userAssetId={10} mode="edit" initialValues={fakeInitialTx} />,
      { wrapper: Wrapper },
    );

    await user.click(screen.getByRole("button", { name: "수정하기" }));

    await waitFor(() => {
      expect(mockUpdateMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          userAssetId: 10,
          transactionId: 5,
          data: expect.objectContaining({ quantity: "2.0", price: "60000" }),
        }),
        expect.any(Object),
      );
    });
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("409 에러 시 '수정 결과가 보유 수량을 초과합니다' 한글 메시지가 표시된다", async () => {
    const AxiosError = (await import("axios")).AxiosError;
    const conflictErr = new AxiosError("Conflict", "ERR_BAD_RESPONSE");
    conflictErr.response = {
      status: 409,
      data: { detail: "수정 결과가 보유 수량을 초과합니다." },
      headers: {},
      config: {} as import("axios").InternalAxiosRequestConfig,
      statusText: "Conflict",
    };

    mockedUseUpdateTransaction.mockReturnValue({
      mutate: ((_vars: unknown, opts?: { onError?: (e: Error) => void }) => {
        opts?.onError?.(conflictErr);
      }) as unknown as ReturnType<typeof useTransactionsHook.useUpdateTransaction>["mutate"],
      isPending: false,
      isSuccess: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof useTransactionsHook.useUpdateTransaction>);

    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(
      <TransactionForm userAssetId={10} mode="edit" initialValues={fakeInitialTx} />,
      { wrapper: Wrapper },
    );

    await user.click(screen.getByRole("button", { name: "수정하기" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "수정 결과가 보유 수량을 초과합니다.",
      );
    });
  });
});

describe("TransactionForm — SELL 사전 검증", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupMutationMock();
  });

  it("SELL 선택 시 보유 수량 힌트가 노출된다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(
      <TransactionForm userAssetId={10} remainingQuantity="3.5" />,
      { wrapper: Wrapper },
    );

    await user.selectOptions(screen.getByLabelText("거래 유형"), "sell");

    expect(screen.getByText("보유 수량: 3.5")).toBeInTheDocument();
  });

  it("SELL 수량이 보유 수량을 초과하면 제출이 차단된다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(
      <TransactionForm userAssetId={10} remainingQuantity="3" />,
      { wrapper: Wrapper },
    );

    await user.selectOptions(screen.getByLabelText("거래 유형"), "sell");
    await user.type(screen.getByLabelText("거래 수량"), "5");
    await user.type(screen.getByLabelText("거래 단가"), "50000");

    const submitBtn = screen.getByRole("button", { name: "거래 추가" });
    expect(submitBtn).toBeDisabled();
    expect(
      screen.getByText("보유 수량을 초과하여 매도할 수 없습니다."),
    ).toBeInTheDocument();
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("BUY 타입일 때는 remainingQuantity 가 있어도 제한 없이 제출된다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(
      <TransactionForm userAssetId={10} remainingQuantity="3" />,
      { wrapper: Wrapper },
    );

    await user.type(screen.getByLabelText("거래 수량"), "100");
    await user.type(screen.getByLabelText("거래 단가"), "50000");
    await user.click(screen.getByRole("button", { name: "거래 추가" }));

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalled();
    });
  });

  it("remainingQuantity 가 없으면 SELL 에도 힌트·차단이 없다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<TransactionForm userAssetId={10} />, { wrapper: Wrapper });

    await user.selectOptions(screen.getByLabelText("거래 유형"), "sell");
    expect(screen.queryByText(/보유 수량:/)).not.toBeInTheDocument();
  });
});

describe("TransactionForm — tag 입력 및 자동완성", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupMutationMock({ tags: ["DCA", "장기보유"] });
  });

  it("거래 태그 입력 필드가 렌더링된다", () => {
    const { Wrapper } = makeWrapper();
    render(<TransactionForm userAssetId={10} />, { wrapper: Wrapper });
    expect(screen.getByLabelText("거래 태그")).toBeInTheDocument();
  });

  it("기존 태그가 datalist option 으로 노출된다", () => {
    const { Wrapper } = makeWrapper();
    const { container } = render(<TransactionForm userAssetId={10} />, {
      wrapper: Wrapper,
    });
    const datalist = container.querySelector("#tx-tag-suggestions");
    expect(datalist).toBeInTheDocument();
    const options = container.querySelectorAll("#tx-tag-suggestions option");
    expect(options.length).toBe(2);
    expect((options[0] as HTMLOptionElement).value).toBe("DCA");
    expect((options[1] as HTMLOptionElement).value).toBe("장기보유");
  });

  it("tag 입력값이 mutate 페이로드에 포함된다", async () => {
    const user = userEvent.setup();
    const { Wrapper } = makeWrapper();
    render(<TransactionForm userAssetId={10} />, { wrapper: Wrapper });

    await user.type(screen.getByLabelText("거래 수량"), "1");
    await user.type(screen.getByLabelText("거래 단가"), "50000");
    await user.type(screen.getByLabelText("거래 태그"), "DCA");
    await user.click(screen.getByRole("button", { name: "거래 추가" }));

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({ tag: "DCA" }),
        }),
        expect.any(Object),
      );
    });
  });

  it("기존 태그가 없을 때는 datalist 가 렌더되지 않는다", () => {
    setupMutationMock({ tags: [] });
    const { Wrapper } = makeWrapper();
    const { container } = render(<TransactionForm userAssetId={10} />, {
      wrapper: Wrapper,
    });
    expect(container.querySelector("#tx-tag-suggestions")).not.toBeInTheDocument();
  });
});
