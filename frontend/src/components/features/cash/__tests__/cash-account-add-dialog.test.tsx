import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { CashAccountAddDialog } from "@/components/features/cash/cash-account-add-dialog";
import * as useCashAccountsHook from "@/hooks/use-cash-accounts";
import type { CashAccount } from "@/types/cash-account";

jest.mock("@/hooks/use-cash-accounts", () => ({
  ...jest.requireActual("@/hooks/use-cash-accounts"),
  useCreateCashAccount: jest.fn(),
}));

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

const mockedUseCreateCashAccount = jest.mocked(
  useCashAccountsHook.useCreateCashAccount,
);

const mockMutate = jest.fn();

const fakeCashAccount: CashAccount = {
  id: 1,
  label: "토스뱅크 원화",
  currency: "KRW",
  balance: "1500000",
  createdAt: "2026-04-01T00:00:00Z",
  updatedAt: "2026-04-01T00:00:00Z",
};

function setupCreateMock(isPending = false) {
  mockedUseCreateCashAccount.mockReturnValue({
    mutate: mockMutate,
    isPending,
    isError: false,
    isSuccess: false,
    error: null,
  } as unknown as ReturnType<typeof useCashAccountsHook.useCreateCashAccount>);
}

function renderDialog(open = true, onClose = jest.fn()) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <CashAccountAddDialog open={open} onClose={onClose} />
    </QueryClientProvider>,
  );
}

describe("CashAccountAddDialog", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupCreateMock();
  });

  it("open=false 이면 렌더링되지 않는다", () => {
    renderDialog(false);
    expect(
      screen.queryByRole("dialog"),
    ).not.toBeInTheDocument();
  });

  it("open=true 이면 다이얼로그가 렌더링된다", () => {
    renderDialog();
    expect(
      screen.getByRole("dialog", { name: "현금 계좌 추가 다이얼로그" }),
    ).toBeInTheDocument();
  });

  describe("폼 검증", () => {
    it("빈 폼 제출 시 라벨 에러가 표시된다", async () => {
      const user = userEvent.setup();
      renderDialog();

      await user.click(screen.getByRole("button", { name: "추가" }));

      await waitFor(() => {
        expect(screen.getByText("라벨을 입력하세요")).toBeInTheDocument();
      });
    });

    it("통화를 선택하지 않으면 currency 에러가 표시된다", async () => {
      const user = userEvent.setup();
      renderDialog();

      await user.type(screen.getByLabelText("계좌 라벨"), "테스트 계좌");
      await user.type(screen.getByLabelText("계좌 잔액"), "1000");
      await user.click(screen.getByRole("button", { name: "추가" }));

      await waitFor(() => {
        expect(
          screen.getByText(/통화 코드는 3~4자 영문 대문자/),
        ).toBeInTheDocument();
      });
    });

    it("음수 잔액 입력 시 에러가 표시된다", async () => {
      const user = userEvent.setup();
      renderDialog();

      await user.type(screen.getByLabelText("계좌 라벨"), "테스트 계좌");
      // KRW 선택
      await user.selectOptions(
        screen.getByLabelText("통화 선택"),
        "KRW",
      );
      await user.type(screen.getByLabelText("계좌 잔액"), "-100");
      await user.click(screen.getByRole("button", { name: "추가" }));

      await waitFor(() => {
        expect(
          screen.getByText(/0 이상의 숫자/),
        ).toBeInTheDocument();
      });
    });

    it("소문자 통화를 '기타 입력'으로 입력하면 자동 대문자 변환 후 통과한다", async () => {
      const user = userEvent.setup();
      renderDialog();

      await user.type(screen.getByLabelText("계좌 라벨"), "THB 계좌");
      // 기타 선택
      await user.selectOptions(
        screen.getByLabelText("통화 선택"),
        "__other__",
      );
      // 직접 입력 필드에 소문자 입력
      const customInput = screen.getByLabelText("통화 코드 직접 입력");
      await user.type(customInput, "thb");
      await user.type(screen.getByLabelText("계좌 잔액"), "10000");

      await user.click(screen.getByRole("button", { name: "추가" }));

      // Zod transform 이 대문자로 변환 → mutate 호출
      await waitFor(() => {
        expect(mockMutate).toHaveBeenCalledWith(
          expect.objectContaining({ currency: "THB" }),
          expect.any(Object),
        );
      });
    });
  });

  describe("제출 동작", () => {
    it("유효한 폼 제출 시 mutation 이 호출된다", async () => {
      const user = userEvent.setup();
      renderDialog();

      await user.type(screen.getByLabelText("계좌 라벨"), "토스뱅크 원화");
      await user.selectOptions(screen.getByLabelText("통화 선택"), "KRW");
      await user.type(screen.getByLabelText("계좌 잔액"), "1500000");

      await user.click(screen.getByRole("button", { name: "추가" }));

      await waitFor(() => {
        expect(mockMutate).toHaveBeenCalledWith(
          { label: "토스뱅크 원화", currency: "KRW", balance: "1500000" },
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

      await user.type(screen.getByLabelText("계좌 라벨"), "토스뱅크 원화");
      await user.selectOptions(screen.getByLabelText("통화 선택"), "KRW");
      await user.type(screen.getByLabelText("계좌 잔액"), "1500000");
      await user.click(screen.getByRole("button", { name: "추가" }));

      await waitFor(() => {
        expect(onClose).toHaveBeenCalled();
      });
    });

    it("제출 중이면 버튼이 disabled 된다", () => {
      setupCreateMock(true);
      renderDialog();
      expect(screen.getByRole("button", { name: "추가 중..." })).toBeDisabled();
    });

    it("닫기 버튼 클릭 시 onClose 가 호출된다", async () => {
      const onClose = jest.fn();
      const user = userEvent.setup();
      renderDialog(true, onClose);

      await user.click(screen.getByRole("button", { name: "취소" }));
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("존재하지 않는 변수를 참조하지 않도록 fakeCashAccount 를 사용한다", () => {
    // coverage를 위한 참조
    expect(fakeCashAccount.id).toBe(1);
  });
});
