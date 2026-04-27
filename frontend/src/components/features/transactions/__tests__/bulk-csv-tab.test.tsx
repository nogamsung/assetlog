import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BulkCsvTab } from "../bulk-csv-tab";
import * as bulkHook from "@/hooks/use-bulk-import-transactions";
import Papa from "papaparse";

// papaparse mock
jest.mock("papaparse", () => ({
  __esModule: true,
  default: { parse: jest.fn() },
  parse: jest.fn(),
}));

// sonner mock
jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

jest.mock("@/hooks/use-bulk-import-transactions", () => ({
  ...jest.requireActual("@/hooks/use-bulk-import-transactions"),
  useBulkImportTransactions: jest.fn(),
}));

const mockedPapa = jest.mocked(Papa);

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

const mockMutateAsync = jest.fn();
const mockMutation = {
  mutateAsync: mockMutateAsync,
  isPending: false,
};

(bulkHook.useBulkImportTransactions as jest.Mock).mockReturnValue(
  mockMutation as unknown as ReturnType<typeof bulkHook.useBulkImportTransactions>,
);

function renderComponent(onSuccess?: () => void) {
  const Wrapper = makeWrapper();
  return render(
    <Wrapper>
      <BulkCsvTab onSuccess={onSuccess} />
    </Wrapper>,
  );
}

// 파파파스 성공 시나리오 헬퍼
function mockPapaSuccess(
  headers: string[],
  rows: string[][],
  fileSize = 100,
) {
  mockedPapa.parse.mockImplementationOnce(
    (_file: File, opts: { complete: (r: { data: string[][] }) => void }) => {
      opts.complete({ data: [headers, ...rows] });
    },
  );
  return new File(["x".repeat(fileSize)], "test.csv", { type: "text/csv" });
}

const VALID_HEADERS = [
  "symbol",
  "exchange",
  "type",
  "quantity",
  "price",
  "traded_at",
];

describe("BulkCsvTab", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(bulkHook, "useBulkImportTransactions").mockReturnValue(
      mockMutation as unknown as ReturnType<typeof bulkHook.useBulkImportTransactions>,
    );
  });

  it("파일 input 과 저장 버튼이 렌더링된다", () => {
    renderComponent();
    expect(
      screen.getByLabelText("CSV 파일 업로드"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "저장" })).toBeDisabled();
  });

  it("1MB 초과 파일 → 인라인 에러, mutation 호출 안 됨", async () => {
    const user = userEvent.setup();
    renderComponent();

    // papaparse 가 불리지 않아야 하므로 mock 필요 없음
    const oversizedFile = new File(
      ["x".repeat(1.1 * 1024 * 1024)],
      "big.csv",
      { type: "text/csv" },
    );
    Object.defineProperty(oversizedFile, "size", { value: 1.1 * 1024 * 1024 });

    const input = screen.getByLabelText("CSV 파일 업로드");
    await user.upload(input, oversizedFile);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "파일 크기가 너무 큽니다",
      );
    });
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it("500행 초과 CSV → 인라인 에러, mutation 호출 안 됨", async () => {
    const user = userEvent.setup();
    renderComponent();

    const rows = Array.from({ length: 501 }, (_, i) => [
      `SYM${i}`,
      "UPBIT",
      "buy",
      "1",
      "1000",
      "2026-01-01T00:00:00",
    ]);
    mockedPapa.parse.mockImplementationOnce(
      (_file: File, opts: { complete: (r: { data: string[][] }) => void }) => {
        opts.complete({ data: [VALID_HEADERS, ...rows] });
      },
    );

    const file = new File(["small"], "rows.csv", { type: "text/csv" });
    const input = screen.getByLabelText("CSV 파일 업로드");
    await user.upload(input, file);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "데이터 행이 너무 많습니다",
      );
    });
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it("헤더 누락 CSV → 인라인 에러", async () => {
    const user = userEvent.setup();
    renderComponent();

    mockedPapa.parse.mockImplementationOnce(
      (_file: File, opts: { complete: (r: { data: string[][] }) => void }) => {
        // symbol 누락
        opts.complete({
          data: [
            ["exchange", "type", "quantity", "price", "traded_at"],
            ["UPBIT", "buy", "1", "1000", "2026-01-01T00:00:00"],
          ],
        });
      },
    );

    const file = new File(["x"], "noheader.csv", { type: "text/csv" });
    const input = screen.getByLabelText("CSV 파일 업로드");
    await user.upload(input, file);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("헤더가 누락");
    });
  });

  it("정상 CSV 업로드 → 미리보기 10행 표시 → 저장 버튼 활성화", async () => {
    const user = userEvent.setup();
    renderComponent();

    const rows = Array.from({ length: 12 }, (_, i) => [
      `BTC${i}`,
      "UPBIT",
      "buy",
      "0.5",
      "85000000",
      "2026-04-20T10:00:00",
    ]);
    mockedPapa.parse.mockImplementationOnce(
      (_file: File, opts: { complete: (r: { data: string[][] }) => void }) => {
        opts.complete({ data: [VALID_HEADERS, ...rows] });
      },
    );

    const file = new File(["x".repeat(500)], "valid.csv", {
      type: "text/csv",
    });
    const input = screen.getByLabelText("CSV 파일 업로드");
    await user.upload(input, file);

    await waitFor(() => {
      expect(screen.getByLabelText("CSV 미리보기")).toBeInTheDocument();
    });

    // 미리보기는 첫 10행만 표시
    const tableRows = screen
      .getByLabelText("CSV 미리보기")
      .querySelectorAll("tbody tr");
    expect(tableRows).toHaveLength(10);

    // 저장 버튼 활성화
    expect(screen.getByRole("button", { name: "저장" })).not.toBeDisabled();
  });

  it("정상 CSV 저장 버튼 클릭 → mutateAsync 호출된다", async () => {
    const user = userEvent.setup();
    const onSuccess = jest.fn();
    mockMutateAsync.mockResolvedValueOnce({ imported_count: 2, preview: [] });
    renderComponent(onSuccess);

    const file = mockPapaSuccess(
      VALID_HEADERS,
      [["BTC", "UPBIT", "buy", "0.5", "85000000", "2026-04-20T10:00:00"]],
    );

    const input = screen.getByLabelText("CSV 파일 업로드");
    await user.upload(input, file);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "저장" })).not.toBeDisabled(),
    );

    await user.click(screen.getByRole("button", { name: "저장" }));

    expect(mockMutateAsync).toHaveBeenCalledWith({
      mode: "csv",
      file: expect.any(File),
    });
  });

  it("422 응답 시 errors[] 를 미리보기 테이블에 매핑하여 행 강조", async () => {
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

    const file = mockPapaSuccess(
      VALID_HEADERS,
      [["INVALID", "UPBIT", "buy", "0.5", "85000000", "2026-04-20T10:00:00"]],
    );

    const input = screen.getByLabelText("CSV 파일 업로드");
    await user.upload(input, file);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "저장" })).not.toBeDisabled(),
    );

    await user.click(screen.getByRole("button", { name: "저장" }));

    await waitFor(() => {
      expect(screen.getByRole("alert", { name: "일괄 등록 오류 목록" })).toBeInTheDocument();
    });
  });
});
