import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { TransactionImport } from "@/components/features/assets/transaction-import";
import * as useTransactionsHook from "@/hooks/use-transactions";
import type { TransactionImportResponse } from "@/types/transaction";

jest.mock("@/hooks/use-transactions", () => ({
  ...jest.requireActual("@/hooks/use-transactions"),
  useImportTransactionsCsv: jest.fn(),
}));

const mockedUseImportTransactionsCsv = jest.mocked(
  useTransactionsHook.useImportTransactionsCsv,
);

const mockMutate = jest.fn();

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

function setupImportMock(opts: {
  isPending?: boolean;
  isSuccess?: boolean;
  isError?: boolean;
} = {}) {
  mockedUseImportTransactionsCsv.mockReturnValue({
    mutate: mockMutate,
    isPending: opts.isPending ?? false,
    isSuccess: opts.isSuccess ?? false,
    isError: opts.isError ?? false,
    error: null,
  } as unknown as ReturnType<typeof useTransactionsHook.useImportTransactionsCsv>);
}

const fakeCsvContent =
  "type,quantity,price,traded_at,memo\nbuy,1.5,50000,2026-01-15T10:00:00+09:00,첫 매수\n";

function makeCsvFile(content = fakeCsvContent): File {
  return new File([content], "transactions.csv", { type: "text/csv" });
}

describe("TransactionImport", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupImportMock();
  });

  it("폼 기본 요소들이 렌더링된다", () => {
    const { Wrapper } = makeWrapper();
    render(<TransactionImport userAssetId={10} />, { wrapper: Wrapper });

    expect(screen.getByLabelText("CSV 파일 선택")).toBeInTheDocument();
    expect(screen.getByLabelText("CSV 파일 가져오기 제출")).toBeInTheDocument();
    expect(screen.getByLabelText("샘플 CSV 다운로드")).toBeInTheDocument();
  });

  it("파일 선택 전 제출 버튼이 disabled 다", () => {
    const { Wrapper } = makeWrapper();
    render(<TransactionImport userAssetId={10} />, { wrapper: Wrapper });

    const submitBtn = screen.getByLabelText("CSV 파일 가져오기 제출");
    expect(submitBtn).toBeDisabled();
  });

  it("파일 선택 후 미리보기 테이블이 렌더링된다", async () => {
    const { Wrapper } = makeWrapper();
    render(<TransactionImport userAssetId={10} />, { wrapper: Wrapper });

    const file = makeCsvFile();
    const input = screen.getByLabelText("CSV 파일 선택");
    await userEvent.upload(input, file);

    await waitFor(() => {
      expect(screen.getByLabelText("CSV 미리보기 테이블")).toBeInTheDocument();
    });
    expect(screen.getByText("type")).toBeInTheDocument();
    expect(screen.getByText("quantity")).toBeInTheDocument();
    expect(screen.getByText("buy")).toBeInTheDocument();
    expect(screen.getByText("1.5")).toBeInTheDocument();
  });

  it("파일 선택 후 제출 버튼이 활성화된다", async () => {
    const { Wrapper } = makeWrapper();
    render(<TransactionImport userAssetId={10} />, { wrapper: Wrapper });

    const file = makeCsvFile();
    const input = screen.getByLabelText("CSV 파일 선택");
    await userEvent.upload(input, file);

    await waitFor(() => {
      expect(screen.getByLabelText("CSV 파일 가져오기 제출")).not.toBeDisabled();
    });
  });

  it("제출 시 useImportTransactionsCsv.mutate 가 올바른 인자로 호출된다", async () => {
    const { Wrapper } = makeWrapper();
    render(<TransactionImport userAssetId={10} />, { wrapper: Wrapper });

    const file = makeCsvFile();
    const input = screen.getByLabelText("CSV 파일 선택");
    await userEvent.upload(input, file);

    await waitFor(() => {
      expect(screen.getByLabelText("CSV 파일 가져오기 제출")).not.toBeDisabled();
    });

    await userEvent.click(screen.getByLabelText("CSV 파일 가져오기 제출"));

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({ userAssetId: 10, file }),
        expect.any(Object),
      );
    });
  });

  it("isPending 시 버튼이 disabled 되고 '가져오는 중...' 이 표시된다", () => {
    setupImportMock({ isPending: true });
    const { Wrapper } = makeWrapper();
    render(<TransactionImport userAssetId={10} />, { wrapper: Wrapper });

    const btn = screen.getByLabelText("CSV 파일 가져오기 제출");
    expect(btn).toBeDisabled();
    expect(btn).toHaveTextContent("가져오는 중...");
  });

  it("422 에러 시 csvErrors 배열이 표시된다", async () => {
    const csvErrors = [
      { row: 2, field: "type", message: "invalid value" },
      { row: 3, field: null, message: "missing required field" },
    ];

    mockedUseImportTransactionsCsv.mockReturnValue({
      mutate: ((_vars: unknown, opts?: { onError?: (e: Error) => void }) => {
        const err = Object.assign(new Error("Unprocessable"), {
          isAxiosError: true,
          response: {
            status: 422,
            data: { detail: "2 rows have errors", errors: csvErrors },
          },
        });
        opts?.onError?.(err);
      }) as unknown as ReturnType<typeof useTransactionsHook.useImportTransactionsCsv>["mutate"],
      isPending: false,
      isSuccess: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof useTransactionsHook.useImportTransactionsCsv>);

    const { Wrapper } = makeWrapper();
    render(<TransactionImport userAssetId={10} />, { wrapper: Wrapper });

    const file = makeCsvFile();
    const input = screen.getByLabelText("CSV 파일 선택");
    await userEvent.upload(input, file);
    await waitFor(() =>
      expect(screen.getByLabelText("CSV 파일 가져오기 제출")).not.toBeDisabled(),
    );

    await userEvent.click(screen.getByLabelText("CSV 파일 가져오기 제출"));

    await waitFor(() => {
      expect(screen.getByLabelText("CSV 오류 목록")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("CSV 오류 상세")).toBeInTheDocument();
    expect(screen.getByText("invalid value")).toBeInTheDocument();
    expect(screen.getByText("missing required field")).toBeInTheDocument();
  });

  it("성공 시 successPreview 테이블이 표시된다", async () => {
    const importResult: TransactionImportResponse = {
      importedCount: 1,
      preview: [
        {
          id: 1,
          userAssetId: 10,
          type: "buy",
          quantity: "1.5",
          price: "50000",
          tradedAt: "2026-01-15T10:00:00+09:00",
          memo: "첫 매수",
          tag: null,
          createdAt: "2026-01-15T01:00:00Z",
        },
      ],
    };

    mockedUseImportTransactionsCsv.mockReturnValue({
      mutate: ((_vars: unknown, opts?: { onSuccess?: (r: TransactionImportResponse) => void }) => {
        opts?.onSuccess?.(importResult);
      }) as unknown as ReturnType<typeof useTransactionsHook.useImportTransactionsCsv>["mutate"],
      isPending: false,
      isSuccess: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof useTransactionsHook.useImportTransactionsCsv>);

    const { Wrapper } = makeWrapper();
    render(<TransactionImport userAssetId={10} />, { wrapper: Wrapper });

    const file = makeCsvFile();
    const input = screen.getByLabelText("CSV 파일 선택");
    await userEvent.upload(input, file);
    await waitFor(() =>
      expect(screen.getByLabelText("CSV 파일 가져오기 제출")).not.toBeDisabled(),
    );

    await userEvent.click(screen.getByLabelText("CSV 파일 가져오기 제출"));

    await waitFor(() => {
      expect(screen.getByLabelText("추가된 거래 미리보기")).toBeInTheDocument();
    });
    expect(screen.getByText("매수")).toBeInTheDocument();
    expect(screen.getByText("50000")).toBeInTheDocument();
  });

  it("성공 시 onSuccess 콜백이 호출된다", async () => {
    const importResult: TransactionImportResponse = {
      importedCount: 1,
      preview: [],
    };
    const mockOnSuccess = jest.fn();

    mockedUseImportTransactionsCsv.mockReturnValue({
      mutate: ((_vars: unknown, opts?: { onSuccess?: (r: TransactionImportResponse) => void }) => {
        opts?.onSuccess?.(importResult);
      }) as unknown as ReturnType<typeof useTransactionsHook.useImportTransactionsCsv>["mutate"],
      isPending: false,
      isSuccess: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof useTransactionsHook.useImportTransactionsCsv>);

    const { Wrapper } = makeWrapper();
    render(
      <TransactionImport userAssetId={10} onSuccess={mockOnSuccess} />,
      { wrapper: Wrapper },
    );

    const file = makeCsvFile();
    const input = screen.getByLabelText("CSV 파일 선택");
    await userEvent.upload(input, file);
    await waitFor(() =>
      expect(screen.getByLabelText("CSV 파일 가져오기 제출")).not.toBeDisabled(),
    );

    await userEvent.click(screen.getByLabelText("CSV 파일 가져오기 제출"));

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalledTimes(1);
    });
  });

  it("샘플 CSV 다운로드 버튼이 클릭 가능하다", async () => {
    // URL.createObjectURL / revokeObjectURL mock
    const mockCreateObjectURL = jest.fn().mockReturnValue("blob:mock");
    const mockRevokeObjectURL = jest.fn();
    const origCreate = URL.createObjectURL;
    const origRevoke = URL.revokeObjectURL;
    URL.createObjectURL = mockCreateObjectURL;
    URL.revokeObjectURL = mockRevokeObjectURL;

    // anchor.click mock — 원본 createElement 를 먼저 저장 후 spy 로 대체
    const mockClick = jest.fn();
    const mockAnchor = { href: "", download: "", click: mockClick };
    const origCreateElement = document.createElement.bind(document);
    const createElementSpy = jest
      .spyOn(document, "createElement")
      .mockImplementation((tag: string) => {
        if (tag === "a") return mockAnchor as unknown as HTMLElement;
        return origCreateElement(tag);
      });

    try {
      const { Wrapper } = makeWrapper();
      render(<TransactionImport userAssetId={10} />, { wrapper: Wrapper });

      await userEvent.click(screen.getByLabelText("샘플 CSV 다운로드"));

      expect(mockCreateObjectURL).toHaveBeenCalledWith(expect.any(Blob));
      expect(mockClick).toHaveBeenCalled();
      expect(mockAnchor.download).toBe("transactions_sample.csv");
    } finally {
      createElementSpy.mockRestore();
      URL.createObjectURL = origCreate;
      URL.revokeObjectURL = origRevoke;
    }
  });

  it("따옴표가 포함된 CSV 도 미리보기에 올바르게 파싱된다", async () => {
    const csvWithQuotes =
      `type,quantity,price,traded_at,memo\n` +
      `buy,1.5,50000,2026-01-15T10:00:00+09:00,"DCA 1월"\n`;

    const { Wrapper } = makeWrapper();
    render(<TransactionImport userAssetId={10} />, { wrapper: Wrapper });

    const file = new File([csvWithQuotes], "q.csv", { type: "text/csv" });
    const input = screen.getByLabelText("CSV 파일 선택");
    await userEvent.upload(input, file);

    await waitFor(() => {
      expect(screen.getByLabelText("CSV 미리보기 테이블")).toBeInTheDocument();
    });
    // 따옴표 벗겨진 값이 표시되어야 함
    expect(screen.getByText("DCA 1월")).toBeInTheDocument();
  });
});
