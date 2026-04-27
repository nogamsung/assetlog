import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { CashAccountDeleteDialog } from "@/components/features/cash/cash-account-delete-dialog";
import * as useCashAccountsHook from "@/hooks/use-cash-accounts";
import type { CashAccount } from "@/types/cash-account";

jest.mock("@/hooks/use-cash-accounts", () => ({
  ...jest.requireActual("@/hooks/use-cash-accounts"),
  useDeleteCashAccount: jest.fn(),
}));

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

const mockedUseDeleteCashAccount = jest.mocked(
  useCashAccountsHook.useDeleteCashAccount,
);

const mockMutate = jest.fn();

const fakeAccount: CashAccount = {
  id: 1,
  label: "토스뱅크 원화",
  currency: "KRW",
  balance: "1500000.0000",
  createdAt: "2026-04-01T00:00:00Z",
  updatedAt: "2026-04-01T00:00:00Z",
};

function setupDeleteMock(
  opts: { isPending?: boolean; isError?: boolean } = {},
) {
  mockedUseDeleteCashAccount.mockReturnValue({
    mutate: mockMutate,
    isPending: opts.isPending ?? false,
    isError: opts.isError ?? false,
    isSuccess: false,
    error: null,
  } as unknown as ReturnType<typeof useCashAccountsHook.useDeleteCashAccount>);
}

function renderDialog(
  open = true,
  onClose = jest.fn(),
  account = fakeAccount,
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <CashAccountDeleteDialog open={open} onClose={onClose} account={account} />
    </QueryClientProvider>,
  );
}

describe("CashAccountDeleteDialog", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupDeleteMock();
  });

  it("open=false 이면 렌더링되지 않는다", () => {
    renderDialog(false);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("open=true 이면 다이얼로그가 렌더링된다", () => {
    renderDialog();
    expect(
      screen.getByRole("dialog", { name: "현금 계좌 삭제 확인 다이얼로그" }),
    ).toBeInTheDocument();
  });

  it("계좌 라벨과 통화가 표시된다", () => {
    renderDialog();
    expect(screen.getByText("토스뱅크 원화")).toBeInTheDocument();
    expect(screen.getByText(/KRW/)).toBeInTheDocument();
  });

  it("삭제하면 복구할 수 없다는 경고가 표시된다", () => {
    renderDialog();
    expect(
      screen.getByText("삭제하면 복구할 수 없습니다."),
    ).toBeInTheDocument();
  });

  describe("확인 흐름", () => {
    it("삭제 버튼 클릭 시 mutation 이 호출된다", async () => {
      const user = userEvent.setup();
      renderDialog();

      await user.click(screen.getByRole("button", { name: "삭제" }));

      await waitFor(() => {
        expect(mockMutate).toHaveBeenCalledWith(1, expect.any(Object));
      });
    });

    it("성공 시 onClose 가 호출된다", async () => {
      const onClose = jest.fn();
      const user = userEvent.setup();

      mockMutate.mockImplementation((_id: number, opts: { onSuccess?: () => void }) => {
        opts?.onSuccess?.();
      });

      renderDialog(true, onClose);

      await user.click(screen.getByRole("button", { name: "삭제" }));

      await waitFor(() => {
        expect(onClose).toHaveBeenCalled();
      });
    });

    it("취소 버튼 클릭 시 onClose 가 호출된다", async () => {
      const onClose = jest.fn();
      const user = userEvent.setup();
      renderDialog(true, onClose);

      await user.click(screen.getByRole("button", { name: "취소" }));
      expect(onClose).toHaveBeenCalled();
    });

    it("X 버튼 클릭 시 onClose 가 호출된다", async () => {
      const onClose = jest.fn();
      const user = userEvent.setup();
      renderDialog(true, onClose);

      await user.click(screen.getByRole("button", { name: "다이얼로그 닫기" }));
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("상태 표시", () => {
    it("삭제 중이면 버튼들이 disabled 된다", () => {
      setupDeleteMock({ isPending: true });
      renderDialog();
      expect(screen.getByRole("button", { name: "삭제 중..." })).toBeDisabled();
      expect(screen.getByRole("button", { name: "취소" })).toBeDisabled();
    });

    it("에러 시 에러 메시지가 표시된다", () => {
      setupDeleteMock({ isError: true });
      renderDialog();
      expect(
        screen.getByText("삭제에 실패했습니다. 다시 시도해 주세요."),
      ).toBeInTheDocument();
    });
  });
});
