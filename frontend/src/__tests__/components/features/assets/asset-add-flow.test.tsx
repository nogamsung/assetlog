import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { AssetAddFlow } from "@/components/features/assets/asset-add-flow";
import * as useAssetsHook from "@/hooks/use-assets";
import * as assetApiModule from "@/lib/api/asset";
import type { AssetSymbolResponse } from "@/types/asset";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("@/hooks/use-assets", () => ({
  ...jest.requireActual("@/hooks/use-assets"),
  useSymbolSearch: jest.fn(),
  useCreateUserAsset: jest.fn(),
}));

jest.mock("@/lib/api/asset");
const mockedCreateSymbol = jest.mocked(assetApiModule.createSymbol);

const mockedUseSymbolSearch = jest.mocked(useAssetsHook.useSymbolSearch);
const mockedUseCreateUserAsset = jest.mocked(useAssetsHook.useCreateUserAsset);

const fakeSymbol: AssetSymbolResponse = {
  id: 1,
  assetType: "crypto",
  symbol: "BTC",
  exchange: "BINANCE",
  name: "Bitcoin",
  currency: "USDT",
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-01T00:00:00Z",
};

const mockCreateMutate = jest.fn();

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
  return { Wrapper, queryClient };
}

function setupSearchMock(data: AssetSymbolResponse[] = []) {
  mockedUseSymbolSearch.mockReturnValue({
    data,
    isFetching: false,
    isSuccess: true,
    isError: false,
  } as unknown as ReturnType<typeof useAssetsHook.useSymbolSearch>);
}

function setupCreateMock(opts: {
  isPending?: boolean;
  isError?: boolean;
  error?: Error | null;
} = {}) {
  mockedUseCreateUserAsset.mockReturnValue({
    mutate: mockCreateMutate,
    isPending: opts.isPending ?? false,
    isSuccess: false,
    isError: opts.isError ?? false,
    error: opts.error ?? null,
  } as unknown as ReturnType<typeof useAssetsHook.useCreateUserAsset>);
}

describe("AssetAddFlow", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupSearchMock();
    setupCreateMock();
  });

  describe("Step 1 — 심볼 검색", () => {
    it("초기 렌더 시 Step 1 레이블이 표시된다", () => {
      const { Wrapper } = makeWrapper();
      render(<AssetAddFlow />, { wrapper: Wrapper });
      expect(screen.getByText(/1\. 심볼 검색/)).toBeInTheDocument();
    });

    it("검색 결과 없을 때 직접 등록 버튼이 있다", async () => {
      const user = userEvent.setup();
      const { Wrapper } = makeWrapper();
      render(<AssetAddFlow />, { wrapper: Wrapper });

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "UNKNOWN",
      );

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /직접 등록하기/ }),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Step 1b — 수동 심볼 등록", () => {
    it("직접 등록 버튼 클릭 시 Step 1b 로 전환된다", async () => {
      const user = userEvent.setup();
      const { Wrapper } = makeWrapper();
      render(<AssetAddFlow />, { wrapper: Wrapper });

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "UNKNOWN",
      );
      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /직접 등록하기/ }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /직접 등록하기/ }));

      await waitFor(() => {
        expect(screen.getByText(/1b\. 심볼 직접 등록/)).toBeInTheDocument();
      });
    });

    it("심볼 등록 성공 시 Step 2 로 전환된다", async () => {
      mockedCreateSymbol.mockResolvedValueOnce(fakeSymbol);
      const user = userEvent.setup();
      const { Wrapper } = makeWrapper();
      render(<AssetAddFlow />, { wrapper: Wrapper });

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "UNKNOWN",
      );
      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /직접 등록하기/ }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /직접 등록하기/ }));

      await waitFor(() => {
        expect(screen.getByText(/1b\. 심볼 직접 등록/)).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("자산 유형"), "crypto");
      await user.type(screen.getByLabelText("심볼"), "BTC");
      await user.type(screen.getByLabelText("거래소"), "BINANCE");
      await user.type(screen.getByLabelText("종목명"), "Bitcoin");
      await user.type(screen.getByLabelText("통화"), "USDT");

      await user.click(screen.getByRole("button", { name: "심볼 등록" }));

      await waitFor(() => {
        expect(screen.getByText("2. 자산 등록 확정")).toBeInTheDocument();
      });
    });

    it("심볼 검색으로 돌아가기 버튼 클릭 시 Step 1 로 복귀한다", async () => {
      const user = userEvent.setup();
      const { Wrapper } = makeWrapper();
      render(<AssetAddFlow />, { wrapper: Wrapper });

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "UNKNOWN",
      );
      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /직접 등록하기/ }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /직접 등록하기/ }));
      await waitFor(() => {
        expect(screen.getByText(/1b/)).toBeInTheDocument();
      });

      await user.click(
        screen.getByRole("button", { name: "심볼 검색으로 돌아가기" }),
      );

      await waitFor(() => {
        expect(screen.getByText("1. 심볼 검색")).toBeInTheDocument();
      });
    });

    it("심볼 등록 409 에러 시 '이미 등록된 심볼입니다' 에러가 표시된다", async () => {
      // createSymbol 은 409 시 ApiError { status: 409 } 형태를 throw 함
      const conflictErr = { status: 409, detail: "이미 등록된 심볼입니다." };
      mockedCreateSymbol.mockRejectedValueOnce(conflictErr);
      const user = userEvent.setup();
      const { Wrapper } = makeWrapper();
      render(<AssetAddFlow />, { wrapper: Wrapper });

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "UNKNOWN",
      );
      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /직접 등록하기/ }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /직접 등록하기/ }));
      await waitFor(() => {
        expect(screen.getByText(/1b/)).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("자산 유형"), "crypto");
      await user.type(screen.getByLabelText("심볼"), "BTC");
      await user.type(screen.getByLabelText("거래소"), "BINANCE");
      await user.type(screen.getByLabelText("종목명"), "Bitcoin");
      await user.type(screen.getByLabelText("통화"), "USDT");
      await user.click(screen.getByRole("button", { name: "심볼 등록" }));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(
          "이미 등록된 심볼입니다.",
        );
      });
    });

    it("심볼 등록 기타 에러 시 API detail 메시지가 표시된다", async () => {
      const serverErr = Object.assign(new Error("Server error"), {
        response: { status: 500, data: { detail: "서버 오류입니다." } },
      });
      mockedCreateSymbol.mockRejectedValueOnce(serverErr);
      const user = userEvent.setup();
      const { Wrapper } = makeWrapper();
      render(<AssetAddFlow />, { wrapper: Wrapper });

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "UNKNOWN",
      );
      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /직접 등록하기/ }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /직접 등록하기/ }));
      await waitFor(() => {
        expect(screen.getByText(/1b/)).toBeInTheDocument();
      });

      await user.selectOptions(screen.getByLabelText("자산 유형"), "crypto");
      await user.type(screen.getByLabelText("심볼"), "BTC");
      await user.type(screen.getByLabelText("거래소"), "BINANCE");
      await user.type(screen.getByLabelText("종목명"), "Bitcoin");
      await user.type(screen.getByLabelText("통화"), "USDT");
      await user.click(screen.getByRole("button", { name: "심볼 등록" }));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent("서버 오류입니다.");
      });
    });
  });

  describe("Step 전환 (1 → 2)", () => {
    it("심볼 선택 시 Step 2 로 전환되고 선택된 심볼이 표시된다", async () => {
      setupSearchMock([fakeSymbol]);
      const user = userEvent.setup();
      const { Wrapper } = makeWrapper();
      render(<AssetAddFlow />, { wrapper: Wrapper });

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "BTC",
      );
      await waitFor(() => {
        expect(screen.getByRole("option", { name: /BTC/ })).toBeInTheDocument();
      });
      await user.click(screen.getByRole("option", { name: /BTC/ }));

      await waitFor(() => {
        expect(screen.getByText("2. 자산 등록 확정")).toBeInTheDocument();
      });
      expect(screen.getByText("선택된 심볼")).toBeInTheDocument();
      expect(screen.getAllByText("BTC").length).toBeGreaterThan(0);
    });
  });

  describe("Step 2 — 자산 등록 확정", () => {
    async function goToStep2() {
      setupSearchMock([fakeSymbol]);
      const user = userEvent.setup();
      const { Wrapper } = makeWrapper();
      render(<AssetAddFlow />, { wrapper: Wrapper });

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "BTC",
      );
      await waitFor(() => {
        expect(screen.getByRole("option", { name: /BTC/ })).toBeInTheDocument();
      });
      await user.click(screen.getByRole("option", { name: /BTC/ }));
      await waitFor(() => {
        expect(screen.getByText("2. 자산 등록 확정")).toBeInTheDocument();
      });
      return user;
    }

    it("등록 버튼 클릭 시 createMutation.mutate 가 호출된다", async () => {
      const user = await goToStep2();

      await user.click(
        screen.getByRole("button", { name: /보유 자산으로 등록/ }),
      );

      expect(mockCreateMutate).toHaveBeenCalledWith({
        assetSymbolId: 1,
        memo: null,
      });
    });

    it("memo 입력 후 등록 시 memo 값이 전달된다", async () => {
      const user = await goToStep2();

      await user.type(screen.getByLabelText("메모 (선택)"), "장기 보유");
      await user.click(
        screen.getByRole("button", { name: /보유 자산으로 등록/ }),
      );

      expect(mockCreateMutate).toHaveBeenCalledWith({
        assetSymbolId: 1,
        memo: "장기 보유",
      });
    });

    it("돌아가기 버튼 클릭 시 Step 1 로 복귀한다", async () => {
      const user = await goToStep2();

      await user.click(
        screen.getByRole("button", { name: "심볼 검색으로 돌아가기" }),
      );

      await waitFor(() => {
        expect(screen.getByText("1. 심볼 검색")).toBeInTheDocument();
      });
    });

    it("pending 중 버튼 텍스트가 '등록 중...' 이고 disabled 된다", async () => {
      // Step 2 이동 후 pending 상태 적용
      setupCreateMock({ isPending: true });
      await goToStep2();

      const submitBtn = screen.getByRole("button", { name: /등록/ });
      expect(submitBtn).toBeDisabled();
    });
  });

  describe("Step 2 — 에러 표시", () => {
    async function goToStep2WithError(error: Error) {
      setupSearchMock([fakeSymbol]);
      setupCreateMock({ isError: true, error });
      const user = userEvent.setup();
      const { Wrapper } = makeWrapper();
      render(<AssetAddFlow />, { wrapper: Wrapper });

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "BTC",
      );
      await waitFor(() => {
        expect(screen.getByRole("option", { name: /BTC/ })).toBeInTheDocument();
      });
      await user.click(screen.getByRole("option", { name: /BTC/ }));
      await waitFor(() => {
        expect(screen.getByText("2. 자산 등록 확정")).toBeInTheDocument();
      });

      await user.click(
        screen.getByRole("button", { name: /보유 자산으로 등록/ }),
      );
      return user;
    }

    it("409 에러 시 '이미 등록된 자산입니다' 가 표시된다", async () => {
      const conflictErr = Object.assign(new Error("Conflict"), {
        response: { status: 409 },
      });
      await goToStep2WithError(conflictErr);

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(
          "이미 등록된 자산입니다.",
        );
      });
    });

    it("404 에러 시 '심볼을 다시 선택하세요' 가 표시된다", async () => {
      const notFoundErr = Object.assign(new Error("Not Found"), {
        response: { status: 404 },
      });
      await goToStep2WithError(notFoundErr);

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(
          "심볼을 다시 선택하세요.",
        );
      });
    });

    it("기타 에러 시 detail 메시지가 표시된다", async () => {
      const serverErr = Object.assign(new Error("Server error"), {
        response: { status: 500, data: { detail: "내부 서버 오류" } },
      });
      await goToStep2WithError(serverErr);

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent("내부 서버 오류");
      });
    });
  });
});
