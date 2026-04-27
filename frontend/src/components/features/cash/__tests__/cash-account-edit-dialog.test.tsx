import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { CashAccountEditDialog } from "@/components/features/cash/cash-account-edit-dialog";
import * as useCashAccountsHook from "@/hooks/use-cash-accounts";
import type { CashAccount } from "@/types/cash-account";

jest.mock("@/hooks/use-cash-accounts", () => ({
  ...jest.requireActual("@/hooks/use-cash-accounts"),
  useUpdateCashAccount: jest.fn(),
}));

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

const mockedUseUpdateCashAccount = jest.mocked(
  useCashAccountsHook.useUpdateCashAccount,
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

function setupUpdateMock(isPending = false) {
  mockedUseUpdateCashAccount.mockReturnValue({
    mutate: mockMutate,
    isPending,
    isError: false,
    isSuccess: false,
    error: null,
  } as unknown as ReturnType<typeof useCashAccountsHook.useUpdateCashAccount>);
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
      <CashAccountEditDialog open={open} onClose={onClose} account={account} />
    </QueryClientProvider>,
  );
}

describe("CashAccountEditDialog", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupUpdateMock();
  });

  it("open=false 이면 렌더링되지 않는다", () => {
    renderDialog(false);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("open=true 이면 다이얼로그가 렌더링된다", () => {
    renderDialog();
    expect(
      screen.getByRole("dialog", { name: "현금 계좌 수정 다이얼로그" }),
    ).toBeInTheDocument();
  });

  describe("기존 값 prefill", () => {
    it("기존 라벨이 입력 필드에 채워진다", () => {
      renderDialog();
      expect(screen.getByLabelText("계좌 라벨")).toHaveValue("토스뱅크 원화");
    });

    it("기존 잔액이 입력 필드에 채워진다", () => {
      renderDialog();
      expect(screen.getByLabelText("계좌 잔액")).toHaveValue("1500000.0000");
    });
  });

  describe("통화 readonly", () => {
    it("통화 필드가 disabled/readonly 이다", () => {
      renderDialog();
      const currencyInput = screen.getByLabelText("통화 (변경 불가)");
      expect(currencyInput).toBeDisabled();
      expect(currencyInput).toHaveValue("KRW");
    });

    it("통화 변경 불가 안내 문구가 표시된다", () => {
      renderDialog();
      expect(
        screen.getByText("통화는 생성 후 변경할 수 없습니다."),
      ).toBeInTheDocument();
    });
  });

  describe("폼 검증", () => {
    it("라벨과 잔액 모두 비우면 에러가 표시된다 (빈 라벨 에러)", async () => {
      const user = userEvent.setup();
      renderDialog();

      const labelInput = screen.getByLabelText("계좌 라벨");
      await user.clear(labelInput);
      const balanceInput = screen.getByLabelText("계좌 잔액");
      await user.clear(balanceInput);

      await user.click(screen.getByRole("button", { name: "수정" }));

      await waitFor(() => {
        // label empty → label min(1) validation fails
        const alerts = screen.getAllByRole("alert");
        expect(alerts.length).toBeGreaterThan(0);
      });
    });

    it("음수 잔액 입력 시 에러가 표시된다", async () => {
      const user = userEvent.setup();
      renderDialog();

      const balanceInput = screen.getByLabelText("계좌 잔액");
      await user.clear(balanceInput);
      await user.type(balanceInput, "-100");

      await user.click(screen.getByRole("button", { name: "수정" }));

      await waitFor(() => {
        expect(screen.getByText(/0 이상의 숫자/)).toBeInTheDocument();
      });
    });
  });

  describe("제출 동작", () => {
    it("유효한 폼 제출 시 mutation 이 호출된다", async () => {
      const user = userEvent.setup();
      renderDialog();

      const balanceInput = screen.getByLabelText("계좌 잔액");
      await user.clear(balanceInput);
      await user.type(balanceInput, "2000000");

      await user.click(screen.getByRole("button", { name: "수정" }));

      await waitFor(() => {
        expect(mockMutate).toHaveBeenCalledWith(
          expect.objectContaining({
            id: 1,
            input: expect.objectContaining({ balance: "2000000" }),
          }),
          expect.any(Object),
        );
      });
    });

    it("성공 시 다이얼로그가 닫힌다", async () => {
      const onClose = jest.fn();
      const user = userEvent.setup();

      mockMutate.mockImplementation((_data: unknown, opts: { onSuccess?: () => void }) => {
        opts?.onSuccess?.();
      });

      renderDialog(true, onClose);

      const balanceInput = screen.getByLabelText("계좌 잔액");
      await user.clear(balanceInput);
      await user.type(balanceInput, "2000000");
      await user.click(screen.getByRole("button", { name: "수정" }));

      await waitFor(() => {
        expect(onClose).toHaveBeenCalled();
      });
    });

    it("수정 중이면 버튼이 disabled 된다", () => {
      setupUpdateMock(true);
      renderDialog();
      expect(screen.getByRole("button", { name: "수정 중..." })).toBeDisabled();
    });

    it("닫기 버튼 클릭 시 onClose 가 호출된다", async () => {
      const onClose = jest.fn();
      const user = userEvent.setup();
      renderDialog(true, onClose);

      await user.click(screen.getByRole("button", { name: "취소" }));
      expect(onClose).toHaveBeenCalled();
    });
  });
});
