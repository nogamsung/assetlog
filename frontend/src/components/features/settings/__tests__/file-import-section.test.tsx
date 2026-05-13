import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FileImportSection } from "@/components/features/settings/file-import-section";
import * as useImportFileModule from "@/hooks/use-import-file";
import type { ImportFileResult } from "@/lib/api/integrations";

jest.mock("@/hooks/use-import-file");
jest.mock("@/hooks/use-portfolio-history", () => ({
  useBackfillPortfolioHistory: () => ({
    mutate: jest.fn(),
    isPending: false,
  }),
}));
jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));
jest.mock("@/lib/datetime", () => ({
  formatDateTimeKST: (v: string) => `KST:${v}`,
}));

const mockedUseImportFile = jest.mocked(useImportFileModule.useImportFile);

const fakeDryRunResult: ImportFileResult = {
  insertedTrades: 10,
  insertedDividends: 3,
  insertedCashTxs: 2,
  skippedDuplicate: 1,
  skippedUnsupported: 5,
  dryRun: true,
  preview: [
    { type: "ParsedTrade", externalId: "EXT-001", tradedAt: "2025-05-14T06:00:00Z" },
    { type: "ParsedDividend", externalId: "EXT-002", tradedAt: "2025-04-10T06:00:00Z" },
  ],
};

const fakeImportResult: ImportFileResult = {
  insertedTrades: 10,
  insertedDividends: 3,
  insertedCashTxs: 2,
  skippedDuplicate: 1,
  skippedUnsupported: 5,
  dryRun: false,
  preview: [],
};

function setupMutation({
  mutateFn = jest.fn(),
  isPending = false,
  variables = undefined as { dryRun: boolean } | undefined,
} = {}) {
  mockedUseImportFile.mockReturnValue({
    mutate: mutateFn,
    isPending,
    variables,
    isSuccess: false,
    isError: false,
    error: null,
    data: undefined,
  } as unknown as ReturnType<typeof useImportFileModule.useImportFile>);
  return mutateFn;
}

function makePdfFile(name = "report.pdf") {
  return new File(["pdf-content"], name, { type: "application/pdf" });
}

describe("FileImportSection", () => {
  beforeEach(() => jest.clearAllMocks());

  it("제목 '파일에서 거래내역 가져오기' 를 렌더링한다", () => {
    setupMutation();
    render(<FileImportSection />);
    expect(screen.getByText("파일에서 거래내역 가져오기")).toBeInTheDocument();
  });

  it("드롭존이 렌더링된다", () => {
    setupMutation();
    render(<FileImportSection />);
    expect(
      screen.getByRole("button", { name: "PDF 파일 선택 또는 드래그 앤 드롭" }),
    ).toBeInTheDocument();
  });

  it("미리보기 버튼과 가져오기 버튼이 렌더링된다", () => {
    setupMutation();
    render(<FileImportSection />);
    expect(screen.getByRole("button", { name: "미리보기" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "가져오기" })).toBeInTheDocument();
  });

  it("파일 미선택 시 버튼이 비활성화된다", () => {
    setupMutation();
    render(<FileImportSection />);
    expect(screen.getByRole("button", { name: "미리보기" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "가져오기" })).toBeDisabled();
  });

  it("파일 선택 후 파일명이 표시된다", async () => {
    setupMutation();
    render(<FileImportSection />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = makePdfFile("toss-2025.pdf");
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("toss-2025.pdf")).toBeInTheDocument();
    });
  });

  it("파일 선택 후 버튼이 활성화된다", async () => {
    setupMutation();
    render(<FileImportSection />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [makePdfFile()] } });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "미리보기" })).not.toBeDisabled();
      expect(screen.getByRole("button", { name: "가져오기" })).not.toBeDisabled();
    });
  });

  it("'미리보기' 클릭 시 dryRun=true 로 mutate 를 호출한다", async () => {
    const user = userEvent.setup();
    const mutateFn = setupMutation();
    render(<FileImportSection />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [makePdfFile()] } });

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "미리보기" })).not.toBeDisabled(),
    );

    await user.click(screen.getByRole("button", { name: "미리보기" }));
    expect(mutateFn).toHaveBeenCalledWith(
      expect.objectContaining({ dryRun: true }),
      expect.any(Object),
    );
  });

  it("'미리보기' 성공 후 결과 카운트가 표시된다", async () => {
    const user = userEvent.setup();
    let capturedOptions: { onSuccess?: (r: ImportFileResult) => void } = {};
    const mutateFn = jest.fn((_args, options) => {
      capturedOptions = options as typeof capturedOptions;
    });
    setupMutation({ mutateFn });
    render(<FileImportSection />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [makePdfFile()] } });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "미리보기" })).not.toBeDisabled(),
    );

    await user.click(screen.getByRole("button", { name: "미리보기" }));
    capturedOptions.onSuccess?.(fakeDryRunResult);

    await waitFor(() => {
      expect(screen.getByRole("region", { name: "미리보기 결과" })).toBeInTheDocument();
      expect(screen.getByText("10건")).toBeInTheDocument();
    });
  });

  it("'미리보기' 후 preview 테이블에 KST 시간이 표시된다", async () => {
    const user = userEvent.setup();
    let capturedOptions: { onSuccess?: (r: ImportFileResult) => void } = {};
    const mutateFn = jest.fn((_args, options) => {
      capturedOptions = options as typeof capturedOptions;
    });
    setupMutation({ mutateFn });
    render(<FileImportSection />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [makePdfFile()] } });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "미리보기" })).not.toBeDisabled(),
    );

    await user.click(screen.getByRole("button", { name: "미리보기" }));
    capturedOptions.onSuccess?.(fakeDryRunResult);

    await waitFor(() => {
      expect(screen.getByText("KST:2025-05-14T06:00:00Z")).toBeInTheDocument();
    });
  });

  it("'가져오기' 클릭 시 dryRun=false 로 mutate 를 호출한다", async () => {
    const user = userEvent.setup();
    const mutateFn = setupMutation();
    render(<FileImportSection />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [makePdfFile()] } });

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "가져오기" })).not.toBeDisabled(),
    );

    await user.click(screen.getByRole("button", { name: "가져오기" }));
    expect(mutateFn).toHaveBeenCalledWith(
      expect.objectContaining({ dryRun: false }),
      expect.any(Object),
    );
  });

  it("'가져오기' 성공 후 파일 상태가 초기화된다", async () => {
    const user = userEvent.setup();
    let capturedOptions: { onSuccess?: (r: ImportFileResult) => void } = {};
    const mutateFn = jest.fn((_args, options) => {
      capturedOptions = options as typeof capturedOptions;
    });
    setupMutation({ mutateFn });
    render(<FileImportSection />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [makePdfFile("toss.pdf")] } });
    await waitFor(() => expect(screen.getByText("toss.pdf")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "가져오기" }));
    await act(async () => {
      capturedOptions.onSuccess?.(fakeImportResult);
    });

    await waitFor(() => {
      expect(screen.queryByText("toss.pdf")).not.toBeInTheDocument();
    });
  });

  it("password 필드 입력 후 mutate 호출 시 password 가 포함된다", async () => {
    const user = userEvent.setup();
    const mutateFn = setupMutation();
    render(<FileImportSection />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [makePdfFile()] } });

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "가져오기" })).not.toBeDisabled(),
    );

    const pwField = document.getElementById("import-password") as HTMLInputElement;
    await user.type(pwField, "secret123");

    await user.click(screen.getByRole("button", { name: "가져오기" }));
    expect(mutateFn).toHaveBeenCalledWith(
      expect.objectContaining({ password: "secret123" }),
      expect.any(Object),
    );
  });

  it("isPending=true 시 버튼이 비활성화된다", () => {
    setupMutation({ isPending: true, variables: { dryRun: true } });
    render(<FileImportSection />);
    expect(screen.getByRole("button", { name: "미리보기" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "가져오기" })).toBeDisabled();
  });

  it("'가져오기' 성공 후 결과 패널이 유지되고 '✅ 가져오기 완료' 가 표시된다", async () => {
    let onSuccessFn: ((result: ImportFileResult) => void) | undefined;
    const mutate = jest.fn((_args, opts: { onSuccess: (r: ImportFileResult) => void }) => {
      onSuccessFn = opts.onSuccess;
    });
    setupMutation({ mutateFn: mutate });
    render(<FileImportSection />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [makePdfFile("statement.pdf")] } });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "가져오기" })).not.toBeDisabled(),
    );
    await userEvent.click(screen.getByRole("button", { name: "가져오기" }));

    onSuccessFn?.(fakeImportResult);

    await waitFor(() => {
      expect(screen.getByText(/가져오기 완료/)).toBeInTheDocument();
    });
    expect(screen.getByText(`${fakeImportResult.insertedTrades}건`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "결과 닫기" })).toBeInTheDocument();
  });

  it("'가져오기 완료' 패널의 '결과 닫기' 클릭 시 패널이 사라진다", async () => {
    let onSuccessFn: ((result: ImportFileResult) => void) | undefined;
    const mutate = jest.fn((_args, opts: { onSuccess: (r: ImportFileResult) => void }) => {
      onSuccessFn = opts.onSuccess;
    });
    setupMutation({ mutateFn: mutate });
    render(<FileImportSection />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [makePdfFile("statement.pdf")] } });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "가져오기" })).not.toBeDisabled(),
    );
    await userEvent.click(screen.getByRole("button", { name: "가져오기" }));
    onSuccessFn?.(fakeImportResult);

    await waitFor(() => {
      expect(screen.getByText(/가져오기 완료/)).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: "결과 닫기" }));
    expect(screen.queryByText(/가져오기 완료/)).not.toBeInTheDocument();
  });

  it("drag-and-drop 으로 파일을 선택할 수 있다", async () => {
    setupMutation();
    render(<FileImportSection />);

    const dropzone = screen.getByRole("button", { name: "PDF 파일 선택 또는 드래그 앤 드롭" });
    const file = makePdfFile("dropped.pdf");
    const dt = { files: [file], types: ["Files"] };
    fireEvent.dragOver(dropzone, { dataTransfer: dt });
    fireEvent.drop(dropzone, { dataTransfer: dt });

    await waitFor(() => {
      expect(screen.getByText("dropped.pdf")).toBeInTheDocument();
    });
  });
});
