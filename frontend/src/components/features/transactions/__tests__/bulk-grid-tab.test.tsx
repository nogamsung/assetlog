import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BulkGridTab } from "../bulk-grid-tab";
import * as bulkHook from "@/hooks/use-bulk-import-transactions";
import * as assetsHook from "@/hooks/use-assets";

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

jest.mock("@/hooks/use-assets", () => ({
  useUserAssets: jest.fn(),
}));

jest.mock("@/hooks/use-bulk-import-transactions", () => ({
  ...jest.requireActual("@/hooks/use-bulk-import-transactions"),
  useBulkImportTransactions: jest.fn(),
}));

const mockMutateAsync = jest.fn();
const mockMutation = {
  mutateAsync: mockMutateAsync,
  isPending: false,
};

(bulkHook.useBulkImportTransactions as jest.Mock).mockReturnValue(
  mockMutation as unknown as ReturnType<typeof bulkHook.useBulkImportTransactions>,
);

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return Wrapper;
}

function renderComponent(onSuccess?: () => void) {
  const Wrapper = makeWrapper();
  return render(
    <Wrapper>
      <BulkGridTab onSuccess={onSuccess} />
    </Wrapper>,
  );
}

describe("BulkGridTab", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(bulkHook, "useBulkImportTransactions").mockReturnValue(
      mockMutation as unknown as ReturnType<typeof bulkHook.useBulkImportTransactions>,
    );
    jest.mocked(assetsHook.useUserAssets).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof assetsHook.useUserAssets>);
  });

  it("기본 5행이 렌더링된다", () => {
    renderComponent();
    const grid = screen.getByRole("grid", { name: "거래 입력 그리드" });
    const rows = within(grid).getAllByRole("row");
    // 헤더 1 + 데이터 5 = 6
    expect(rows).toHaveLength(6);
  });

  it("행 추가 버튼 클릭 → 1행 추가된다", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByRole("button", { name: "행 추가" }));

    const grid = screen.getByRole("grid", { name: "거래 입력 그리드" });
    const rows = within(grid).getAllByRole("row");
    expect(rows).toHaveLength(7); // 헤더 + 6행
  });

  it("행 삭제 버튼 클릭 → 해당 행 제거된다", async () => {
    const user = userEvent.setup();
    renderComponent();

    const deleteButtons = screen.getAllByRole("button", { name: /행 삭제/ });
    await user.click(deleteButtons[0]);

    const grid = screen.getByRole("grid", { name: "거래 입력 그리드" });
    const rows = within(grid).getAllByRole("row");
    expect(rows).toHaveLength(5); // 헤더 + 4행
  });

  it("마지막 1행일 때 삭제 버튼이 비활성화된다", async () => {
    const user = userEvent.setup();
    renderComponent();

    // 4행 삭제하여 1행만 남김
    for (let i = 0; i < 4; i++) {
      const deleteButtons = screen.getAllByRole("button", { name: /행 삭제/ });
      await user.click(deleteButtons[0]);
    }

    const deleteButton = screen.getByRole("button", { name: /행 삭제/ });
    expect(deleteButton).toBeDisabled();
  });

  it("quantity ≤ 0 입력 시 셀 인라인 에러가 표시된다", async () => {
    const user = userEvent.setup();
    renderComponent();

    // 필수 필드 채우기
    const symbolInputs = screen.getAllByLabelText(/행 종목 코드/);
    const exchangeInputs = screen.getAllByLabelText(/행 거래소/);
    const quantityInputs = screen.getAllByLabelText(/행 수량/);
    const priceInputs = screen.getAllByLabelText(/행 단가/);

    await user.clear(symbolInputs[0]);
    await user.type(symbolInputs[0], "BTC");
    await user.clear(exchangeInputs[0]);
    await user.type(exchangeInputs[0], "UPBIT");
    await user.clear(quantityInputs[0]);
    await user.type(quantityInputs[0], "0");
    await user.clear(priceInputs[0]);
    await user.type(priceInputs[0], "85000000");

    await user.click(screen.getByRole("button", { name: "저장" }));

    await waitFor(() => {
      const alerts = screen.getAllByRole("alert");
      const hasQuantityError = alerts.some((el) =>
        el.textContent?.includes("0보다 큰 값"),
      );
      expect(hasQuantityError).toBe(true);
    });
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it("정상 입력 후 저장 → mutateAsync 가 json 모드로 호출된다", async () => {
    const user = userEvent.setup();
    const onSuccess = jest.fn();
    mockMutateAsync.mockResolvedValueOnce({ imported_count: 1, preview: [] });
    renderComponent(onSuccess);

    const symbolInputs = screen.getAllByLabelText(/행 종목 코드/);
    const exchangeInputs = screen.getAllByLabelText(/행 거래소/);
    const quantityInputs = screen.getAllByLabelText(/행 수량/);
    const priceInputs = screen.getAllByLabelText(/행 단가/);

    // 첫 번째 행만 유효하게 채우고 나머지는 모두 채워야 하므로
    // 기본 5행이 있어서 비어있는 행들도 검증됨 → 모든 행 채우기
    const rows = 5;
    for (let i = 0; i < rows; i++) {
      await user.clear(symbolInputs[i]);
      await user.type(symbolInputs[i], "BTC");
      await user.clear(exchangeInputs[i]);
      await user.type(exchangeInputs[i], "UPBIT");
      await user.clear(quantityInputs[i]);
      await user.type(quantityInputs[i], "0.5");
      await user.clear(priceInputs[i]);
      await user.type(priceInputs[i], "85000000");
    }

    await user.click(screen.getByRole("button", { name: "저장" }));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ mode: "json" }),
      );
    });

    const callArg = mockMutateAsync.mock.calls[0][0] as {
      mode: string;
      rows: { symbol: string }[];
    };
    expect(callArg.mode).toBe("json");
    expect(callArg.rows[0].symbol).toBe("BTC");
  });

  it("422 응답 시 해당 행에 에러가 표시된다", async () => {
    const user = userEvent.setup();

    const axiosErr = Object.assign(new Error("Unprocessable"), {
      isAxiosError: true,
      response: {
        status: 422,
        data: {
          detail: "Bulk validation failed",
          errors: [{ row: 1, field: "symbol", message: "Unknown symbol" }],
        },
      },
      toJSON: () => ({}),
    });
    mockMutateAsync.mockRejectedValueOnce(axiosErr);

    renderComponent();

    const symbolInputs = screen.getAllByLabelText(/행 종목 코드/);
    const exchangeInputs = screen.getAllByLabelText(/행 거래소/);
    const quantityInputs = screen.getAllByLabelText(/행 수량/);
    const priceInputs = screen.getAllByLabelText(/행 단가/);

    const rows = 5;
    for (let i = 0; i < rows; i++) {
      await user.clear(symbolInputs[i]);
      await user.type(symbolInputs[i], "INVALID");
      await user.clear(exchangeInputs[i]);
      await user.type(exchangeInputs[i], "UPBIT");
      await user.clear(quantityInputs[i]);
      await user.type(quantityInputs[i], "0.5");
      await user.clear(priceInputs[i]);
      await user.type(priceInputs[i], "85000000");
    }

    await user.click(screen.getByRole("button", { name: "저장" }));

    await waitFor(() => {
      expect(
        screen.getByRole("alert", { name: "일괄 등록 오류 목록" }),
      ).toBeInTheDocument();
    });

    // 해당 행의 필드 에러도 표시
    await waitFor(() => {
      const alerts = screen.getAllByRole("alert");
      const hasSymbolError = alerts.some((el) =>
        el.textContent?.includes("Unknown symbol"),
      );
      expect(hasSymbolError).toBe(true);
    });
  });
});
