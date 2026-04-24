import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { AssetList } from "@/components/features/assets/asset-list";
import * as portfolioHook from "@/hooks/use-portfolio";
import * as useAssetsHook from "@/hooks/use-assets";
import type { HoldingResponse } from "@/types/portfolio";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("@/hooks/use-portfolio", () => ({
  ...jest.requireActual("@/hooks/use-portfolio"),
  usePortfolioHoldings: jest.fn(),
}));

jest.mock("@/hooks/use-assets", () => ({
  ...jest.requireActual("@/hooks/use-assets"),
  useDeleteUserAsset: jest.fn(),
}));

const mockedUsePortfolioHoldings = jest.mocked(portfolioHook.usePortfolioHoldings);
const mockedUseDeleteUserAsset = jest.mocked(useAssetsHook.useDeleteUserAsset);

const mockDeleteMutate = jest.fn();

const fakeHolding: HoldingResponse = {
  userAssetId: 10,
  assetSymbol: {
    id: 1,
    assetType: "crypto",
    symbol: "BTC",
    exchange: "BINANCE",
    name: "Bitcoin",
    currency: "USD",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
  quantity: "1.5000000000",
  avgCost: "50000.000000",
  costBasis: "75000.00",
  latestPrice: "55000.000000",
  latestValue: "82500.00",
  pnlAbs: "7500.00",
  pnlPct: 10.0,
  weightPct: 100,
  lastPriceRefreshedAt: "2026-04-24T09:00:00Z",
  isStale: false,
  isPending: false,
};

const fakeHolding2: HoldingResponse = {
  userAssetId: 11,
  assetSymbol: {
    id: 2,
    assetType: "kr_stock",
    symbol: "005930",
    exchange: "KRX",
    name: "삼성전자",
    currency: "KRW",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
  quantity: "10.0000",
  avgCost: "70000.0000",
  costBasis: "700000.00",
  latestPrice: "75000.0000",
  latestValue: "750000.00",
  pnlAbs: "50000.00",
  pnlPct: 7.14,
  weightPct: 50,
  lastPriceRefreshedAt: "2026-04-24T09:00:00Z",
  isStale: false,
  isPending: false,
};

function renderAssetList() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AssetList />
    </QueryClientProvider>,
  );
}

function setupDeleteMock(isPending = false) {
  mockedUseDeleteUserAsset.mockReturnValue({
    mutate: mockDeleteMutate,
    isPending,
    isError: false,
    isSuccess: false,
    error: null,
  } as unknown as ReturnType<typeof useAssetsHook.useDeleteUserAsset>);
}

function setupHoldingsMock(
  data: HoldingResponse[] | undefined,
  isLoading = false,
  isError = false,
  error: Error | null = null,
) {
  mockedUsePortfolioHoldings.mockReturnValue({
    data,
    isLoading,
    isError,
    error,
    isSuccess: !isLoading && !isError,
  } as unknown as ReturnType<typeof portfolioHook.usePortfolioHoldings>);
}

describe("AssetList", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupDeleteMock();
    setupHoldingsMock([fakeHolding]);
  });

  describe("로딩 상태", () => {
    it("isLoading 일 때 스켈레톤을 표시한다", () => {
      setupHoldingsMock(undefined, true);
      renderAssetList();
      expect(screen.getByLabelText("자산 목록 로딩 중")).toBeInTheDocument();
    });
  });

  describe("에러 상태", () => {
    it("isError 일 때 에러 메시지를 표시한다", () => {
      const err = Object.assign(new Error("Fetch failed"), {
        response: { data: { detail: "서버 오류" } },
      });
      setupHoldingsMock(undefined, false, true, err);
      renderAssetList();
      expect(screen.getByRole("alert")).toHaveTextContent("서버 오류");
    });

    it("에러 detail 없을 때 기본 메시지를 표시한다", () => {
      setupHoldingsMock(undefined, false, true, new Error("Network"));
      renderAssetList();
      expect(screen.getByRole("alert")).toHaveTextContent(
        "자산 목록을 불러오지 못했습니다.",
      );
    });
  });

  describe("빈 상태", () => {
    it("자산이 없을 때 빈 상태 UI 와 추가 링크를 표시한다", () => {
      setupHoldingsMock([]);
      renderAssetList();
      expect(screen.getByText("보유 자산이 없습니다.")).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: /자산 추가하기/ }),
      ).toHaveAttribute("href", "/assets/new");
    });

    it("data 가 undefined 일 때 빈 상태 UI 를 표시한다", () => {
      setupHoldingsMock(undefined);
      renderAssetList();
      expect(screen.getByText("보유 자산이 없습니다.")).toBeInTheDocument();
    });
  });

  describe("자산 렌더링", () => {
    it("자산 목록을 심볼, 이름, 배지와 함께 표시한다", () => {
      setupHoldingsMock([fakeHolding, fakeHolding2]);
      renderAssetList();
      expect(screen.getByText("BTC")).toBeInTheDocument();
      expect(screen.getByText("Bitcoin")).toBeInTheDocument();
      expect(screen.getByText("암호화폐")).toBeInTheDocument();
      expect(screen.getByText("005930")).toBeInTheDocument();
      expect(screen.getByText("삼성전자")).toBeInTheDocument();
      expect(screen.getByText("국내주식")).toBeInTheDocument();
    });

    it("각 자산마다 삭제 버튼이 있다", () => {
      setupHoldingsMock([fakeHolding, fakeHolding2]);
      renderAssetList();
      expect(screen.getByLabelText("BTC 삭제")).toBeInTheDocument();
      expect(screen.getByLabelText("005930 삭제")).toBeInTheDocument();
    });

    it("상세 페이지 링크가 올바른 href 를 가진다", () => {
      renderAssetList();
      expect(
        screen.getByRole("link", { name: "BTC 상세 보기" }),
      ).toHaveAttribute("href", "/assets/10");
    });
  });

  describe("삭제 동작", () => {
    it("confirm 승인 시 deleteMutation.mutate 가 호출된다", async () => {
      jest.spyOn(window, "confirm").mockReturnValueOnce(true);
      const user = userEvent.setup();
      renderAssetList();

      await user.click(screen.getByLabelText("BTC 삭제"));
      expect(window.confirm).toHaveBeenCalledWith(
        expect.stringContaining("BTC"),
      );
      await waitFor(() => {
        expect(mockDeleteMutate).toHaveBeenCalledWith(10);
      });
    });

    it("confirm 취소 시 mutation 이 호출되지 않는다", async () => {
      jest.spyOn(window, "confirm").mockReturnValueOnce(false);
      const user = userEvent.setup();
      renderAssetList();

      await user.click(screen.getByLabelText("BTC 삭제"));
      expect(mockDeleteMutate).not.toHaveBeenCalled();
    });

    it("삭제 pending 중 버튼이 disabled 된다", () => {
      setupDeleteMock(true);
      renderAssetList();
      expect(screen.getByLabelText("BTC 삭제")).toBeDisabled();
    });
  });
});
