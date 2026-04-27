import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BulkImportButton } from "../bulk-import-button";

jest.mock("../bulk-import-dialog", () => ({
  BulkImportDialog: ({ open, onClose }: { open: boolean; onClose: () => void }) =>
    open ? (
      <div role="dialog" aria-label="일괄 등록 다이얼로그">
        <button onClick={onClose}>닫기</button>
      </div>
    ) : null,
}));

function renderButton() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BulkImportButton />
    </QueryClientProvider>,
  );
}

describe("BulkImportButton", () => {
  it("렌더 시 다이얼로그는 닫혀 있고 버튼만 노출된다", () => {
    renderButton();
    expect(screen.getByRole("button", { name: "여러 종목 일괄 등록" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("버튼 클릭 시 다이얼로그가 열린다", async () => {
    const user = userEvent.setup();
    renderButton();

    await user.click(screen.getByRole("button", { name: "여러 종목 일괄 등록" }));

    expect(screen.getByRole("dialog", { name: "일괄 등록 다이얼로그" })).toBeInTheDocument();
  });

  it("다이얼로그 닫기 콜백이 동작한다", async () => {
    const user = userEvent.setup();
    renderButton();

    await user.click(screen.getByRole("button", { name: "여러 종목 일괄 등록" }));
    await user.click(screen.getByRole("button", { name: "닫기" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
