import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { SymbolSearch } from "@/components/features/assets/symbol-search";
import * as useAssetsHook from "@/hooks/use-assets";
import type { AssetSymbolResponse } from "@/types/asset";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("@/hooks/use-assets");
const mockedUseSymbolSearch = jest.mocked(useAssetsHook.useSymbolSearch);

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

const onSelect = jest.fn();
const onRequestManualAdd = jest.fn();

function renderSymbolSearch() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <SymbolSearch onSelect={onSelect} onRequestManualAdd={onRequestManualAdd} />
    </QueryClientProvider>,
  );
}

function setupSearchMock(
  opts: Partial<{
    data: AssetSymbolResponse[];
    isFetching: boolean;
  }> = {},
) {
  mockedUseSymbolSearch.mockReturnValue({
    data: opts.data ?? undefined,
    isFetching: opts.isFetching ?? false,
    isSuccess: true,
    isError: false,
  } as unknown as ReturnType<typeof useAssetsHook.useSymbolSearch>);
}

describe("SymbolSearch", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // 초기 상태: 쿼리 없음
    setupSearchMock();
  });

  it("검색 Input 과 자산 유형 select 가 렌더된다", () => {
    renderSymbolSearch();
    expect(screen.getByLabelText("심볼 또는 종목명을 입력하세요")).toBeInTheDocument();
    expect(screen.getByLabelText("자산 유형 필터")).toBeInTheDocument();
  });

  it("검색어 입력 전에는 결과 영역이 표시되지 않는다", () => {
    renderSymbolSearch();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  describe("검색 결과 있을 때", () => {
    beforeEach(() => {
      setupSearchMock({ data: [fakeSymbol] });
    });

    it("검색어 입력 시 결과 리스트가 나타난다", async () => {
      const user = userEvent.setup();
      renderSymbolSearch();

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "BTC",
      );

      await waitFor(() => {
        expect(screen.getByRole("listbox")).toBeInTheDocument();
      });
      expect(screen.getByText("BTC")).toBeInTheDocument();
      expect(screen.getByText("Bitcoin")).toBeInTheDocument();
    });

    it("결과 클릭 시 onSelect 가 해당 심볼과 함께 호출된다", async () => {
      const user = userEvent.setup();
      renderSymbolSearch();

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "BTC",
      );

      await waitFor(() => {
        expect(screen.getByRole("listbox")).toBeInTheDocument();
      });

      await user.click(screen.getByRole("option", { name: /BTC/ }));
      expect(onSelect).toHaveBeenCalledWith(fakeSymbol);
    });
  });

  describe("검색 결과 없을 때", () => {
    beforeEach(() => {
      setupSearchMock({ data: [] });
    });

    it("결과 없음 메시지와 직접 등록 버튼을 표시한다", async () => {
      const user = userEvent.setup();
      renderSymbolSearch();

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "UNKNOWNSYMBOL",
      );

      await waitFor(() => {
        expect(
          screen.getByText("검색 결과가 없습니다."),
        ).toBeInTheDocument();
      });
      expect(screen.getByRole("button", { name: /직접 등록하기/ })).toBeInTheDocument();
    });

    it("직접 등록 버튼 클릭 시 onRequestManualAdd 가 호출된다", async () => {
      const user = userEvent.setup();
      renderSymbolSearch();

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "UNKNOWNSYMBOL",
      );

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /직접 등록하기/ }),
        ).toBeInTheDocument();
      });

      await user.click(screen.getByRole("button", { name: /직접 등록하기/ }));
      expect(onRequestManualAdd).toHaveBeenCalledTimes(1);
    });
  });

  describe("검색 중 (isFetching)", () => {
    it("isFetching 이 true 이면 검색 중 메시지를 표시한다", async () => {
      setupSearchMock({ isFetching: true });
      const user = userEvent.setup();
      renderSymbolSearch();

      await user.type(
        screen.getByLabelText("심볼 또는 종목명을 입력하세요"),
        "BTC",
      );

      await waitFor(() => {
        expect(screen.getByRole("status")).toHaveTextContent("검색 중...");
      });
    });
  });

  describe("자산 유형 필터", () => {
    it("자산 유형 변경 시 쿼리가 해당 필터로 호출된다", async () => {
      setupSearchMock({ data: [fakeSymbol] });
      const user = userEvent.setup();
      renderSymbolSearch();

      await user.selectOptions(
        screen.getByLabelText("자산 유형 필터"),
        "crypto",
      );

      // useSymbolSearch 가 "crypto" assetType 으로 호출됨을 확인
      await waitFor(() => {
        expect(mockedUseSymbolSearch).toHaveBeenCalledWith(
          expect.any(String),
          "crypto",
        );
      });
    });
  });
});
