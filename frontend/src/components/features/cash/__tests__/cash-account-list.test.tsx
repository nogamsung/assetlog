import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { CashAccountList } from "@/components/features/cash/cash-account-list";
import * as useCashAccountsHook from "@/hooks/use-cash-accounts";
import type { CashAccount } from "@/types/cash-account";

jest.mock("@/hooks/use-cash-accounts", () => ({
  ...jest.requireActual("@/hooks/use-cash-accounts"),
  useCashAccounts: jest.fn(),
  useDeleteCashAccount: jest.fn(),
  useCreateCashAccount: jest.fn(),
  useUpdateCashAccount: jest.fn(),
}));

// Sonner toast mock
jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

const mockedUseCashAccounts = jest.mocked(useCashAccountsHook.useCashAccounts);
const mockedUseDeleteCashAccount = jest.mocked(
  useCashAccountsHook.useDeleteCashAccount,
);
const mockedUseCreateCashAccount = jest.mocked(
  useCashAccountsHook.useCreateCashAccount,
);
const mockedUseUpdateCashAccount = jest.mocked(
  useCashAccountsHook.useUpdateCashAccount,
);

const mockDeleteMutate = jest.fn();
const mockCreateMutate = jest.fn();
const mockUpdateMutate = jest.fn();

const fakeAccount: CashAccount = {
  id: 1,
  label: "토스뱅크 원화",
  currency: "KRW",
  balance: "1500000.0000",
  createdAt: "2026-04-01T00:00:00Z",
  updatedAt: "2026-04-01T00:00:00Z",
};

const fakeAccount2: CashAccount = {
  id: 2,
  label: "바이낸스 테더",
  currency: "USDT",
  balance: "200.5000",
  createdAt: "2026-04-01T00:00:00Z",
  updatedAt: "2026-04-01T00:00:00Z",
};

function setupMutationMocks() {
  mockedUseDeleteCashAccount.mockReturnValue({
    mutate: mockDeleteMutate,
    isPending: false,
    isError: false,
    isSuccess: false,
    error: null,
  } as unknown as ReturnType<typeof useCashAccountsHook.useDeleteCashAccount>);

  mockedUseCreateCashAccount.mockReturnValue({
    mutate: mockCreateMutate,
    isPending: false,
    isError: false,
    isSuccess: false,
    error: null,
  } as unknown as ReturnType<typeof useCashAccountsHook.useCreateCashAccount>);

  mockedUseUpdateCashAccount.mockReturnValue({
    mutate: mockUpdateMutate,
    isPending: false,
    isError: false,
    isSuccess: false,
    error: null,
  } as unknown as ReturnType<typeof useCashAccountsHook.useUpdateCashAccount>);
}

function renderCashAccountList() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <CashAccountList />
    </QueryClientProvider>,
  );
}

describe("CashAccountList", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupMutationMocks();
  });

  describe("로딩 상태", () => {
    it("isLoading 일 때 스켈레톤을 표시한다", () => {
      mockedUseCashAccounts.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
        isSuccess: false,
      } as unknown as ReturnType<typeof useCashAccountsHook.useCashAccounts>);

      renderCashAccountList();
      expect(
        screen.getByLabelText("현금 계좌 목록 로딩 중"),
      ).toBeInTheDocument();
    });
  });

  describe("에러 상태", () => {
    it("isError 일 때 에러 메시지를 표시한다", () => {
      const err = Object.assign(new Error("Fetch failed"), {
        response: { data: { detail: "서버 오류" } },
      });
      mockedUseCashAccounts.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: err,
        isSuccess: false,
      } as unknown as ReturnType<typeof useCashAccountsHook.useCashAccounts>);

      renderCashAccountList();
      expect(screen.getByRole("alert")).toHaveTextContent("서버 오류");
    });

    it("에러 detail 없을 때 기본 메시지를 표시한다", () => {
      mockedUseCashAccounts.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error("Network"),
        isSuccess: false,
      } as unknown as ReturnType<typeof useCashAccountsHook.useCashAccounts>);

      renderCashAccountList();
      expect(screen.getByRole("alert")).toHaveTextContent(
        "현금 계좌를 불러오지 못했습니다.",
      );
    });
  });

  describe("빈 상태", () => {
    it("계좌가 없을 때 빈 상태 UI를 표시한다", () => {
      mockedUseCashAccounts.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
      } as unknown as ReturnType<typeof useCashAccountsHook.useCashAccounts>);

      renderCashAccountList();
      expect(
        screen.getByText("등록된 현금 계좌가 없습니다."),
      ).toBeInTheDocument();
    });

    it("빈 상태 '현금 추가' 버튼 클릭 시 다이얼로그가 열린다", async () => {
      mockedUseCashAccounts.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
      } as unknown as ReturnType<typeof useCashAccountsHook.useCashAccounts>);

      const user = userEvent.setup();
      renderCashAccountList();

      // 빈 상태 버튼 클릭
      const emptyAddBtn = screen.getAllByRole("button", { name: "현금 추가" })[0];
      await user.click(emptyAddBtn);

      // 다이얼로그가 열림
      await waitFor(() => {
        expect(
          screen.getByRole("dialog", { name: "현금 계좌 추가 다이얼로그" }),
        ).toBeInTheDocument();
      });
    });
  });

  describe("데이터 렌더링", () => {
    beforeEach(() => {
      mockedUseCashAccounts.mockReturnValue({
        data: [fakeAccount, fakeAccount2],
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
      } as unknown as ReturnType<typeof useCashAccountsHook.useCashAccounts>);
    });

    it("헤더에 '현금' 제목이 표시된다", () => {
      renderCashAccountList();
      expect(screen.getByText("현금")).toBeInTheDocument();
    });

    it("계좌 라벨이 표시된다", () => {
      renderCashAccountList();
      expect(screen.getByText("토스뱅크 원화")).toBeInTheDocument();
      expect(screen.getByText("바이낸스 테더")).toBeInTheDocument();
    });

    it("통화 배지가 표시된다", () => {
      renderCashAccountList();
      expect(screen.getByText("KRW")).toBeInTheDocument();
      expect(screen.getByText("USDT")).toBeInTheDocument();
    });

    it("각 계좌마다 수정/삭제 버튼이 있다", () => {
      renderCashAccountList();
      expect(screen.getByLabelText("토스뱅크 원화 수정")).toBeInTheDocument();
      expect(screen.getByLabelText("토스뱅크 원화 삭제")).toBeInTheDocument();
      expect(screen.getByLabelText("바이낸스 테더 수정")).toBeInTheDocument();
      expect(screen.getByLabelText("바이낸스 테더 삭제")).toBeInTheDocument();
    });
  });

  describe("다이얼로그 열기", () => {
    beforeEach(() => {
      mockedUseCashAccounts.mockReturnValue({
        data: [fakeAccount],
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
      } as unknown as ReturnType<typeof useCashAccountsHook.useCashAccounts>);
    });

    it("헤더의 '현금 추가' 버튼 클릭 시 추가 다이얼로그가 열린다", async () => {
      const user = userEvent.setup();
      renderCashAccountList();

      const headerAddBtn = screen.getByRole("button", { name: "현금 추가" });
      await user.click(headerAddBtn);

      await waitFor(() => {
        expect(
          screen.getByRole("dialog", { name: "현금 계좌 추가 다이얼로그" }),
        ).toBeInTheDocument();
      });
    });

    it("수정 버튼 클릭 시 수정 다이얼로그가 열린다", async () => {
      const user = userEvent.setup();
      renderCashAccountList();

      await user.click(screen.getByLabelText("토스뱅크 원화 수정"));

      await waitFor(() => {
        expect(
          screen.getByRole("dialog", { name: "현금 계좌 수정 다이얼로그" }),
        ).toBeInTheDocument();
      });
    });

    it("삭제 버튼 클릭 시 삭제 다이얼로그가 열린다", async () => {
      const user = userEvent.setup();
      renderCashAccountList();

      await user.click(screen.getByLabelText("토스뱅크 원화 삭제"));

      await waitFor(() => {
        expect(
          screen.getByRole("dialog", { name: "현금 계좌 삭제 확인 다이얼로그" }),
        ).toBeInTheDocument();
      });
    });
  });
});
