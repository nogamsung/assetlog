import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { AssetList } from "@/components/features/assets/asset-list";
import * as useAssetsHook from "@/hooks/use-assets";
import type { UserAssetResponse } from "@/types/asset";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("@/hooks/use-assets");
const mockedUseUserAssets = jest.mocked(useAssetsHook.useUserAssets);
const mockedUseDeleteUserAsset = jest.mocked(useAssetsHook.useDeleteUserAsset);

const fakeAsset: UserAssetResponse = {
  id: 10,
  userId: 1,
  assetSymbol: {
    id: 1,
    assetType: "crypto",
    symbol: "BTC",
    exchange: "BINANCE",
    name: "Bitcoin",
    currency: "USDT",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
  memo: null,
  createdAt: "2024-01-01T00:00:00Z",
};

const fakeKrAsset: UserAssetResponse = {
  id: 11,
  userId: 1,
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
  memo: "장기보유",
  createdAt: "2024-01-01T00:00:00Z",
};

const mockDeleteMutate = jest.fn();

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

describe("AssetList", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupDeleteMock();
  });

  describe("로딩 상태", () => {
    it("isLoading 일 때 스켈레톤을 표시한다", () => {
      mockedUseUserAssets.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      } as unknown as ReturnType<typeof useAssetsHook.useUserAssets>);

      renderAssetList();
      expect(screen.getByLabelText("자산 목록 로딩 중")).toBeInTheDocument();
    });
  });

  describe("에러 상태", () => {
    it("isError 일 때 에러 메시지를 표시한다", () => {
      const err = Object.assign(new Error("Fetch failed"), {
        response: { data: { detail: "서버 오류" } },
      });
      mockedUseUserAssets.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: err,
      } as unknown as ReturnType<typeof useAssetsHook.useUserAssets>);

      renderAssetList();
      expect(screen.getByRole("alert")).toHaveTextContent("서버 오류");
    });

    it("에러 detail 없을 때 기본 메시지를 표시한다", () => {
      mockedUseUserAssets.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error("Network"),
      } as unknown as ReturnType<typeof useAssetsHook.useUserAssets>);

      renderAssetList();
      expect(screen.getByRole("alert")).toHaveTextContent(
        "자산 목록을 불러오지 못했습니다.",
      );
    });
  });

  describe("빈 상태", () => {
    it("자산이 없을 때 빈 상태 UI 와 추가 링크를 표시한다", () => {
      mockedUseUserAssets.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      } as unknown as ReturnType<typeof useAssetsHook.useUserAssets>);

      renderAssetList();
      expect(screen.getByText("보유 자산이 없습니다.")).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: /자산 추가하기/ }),
      ).toHaveAttribute("href", "/assets/new");
    });
  });

  describe("자산 렌더링", () => {
    it("자산 목록을 심볼, 이름, 배지와 함께 표시한다", () => {
      mockedUseUserAssets.mockReturnValue({
        data: [fakeAsset, fakeKrAsset],
        isLoading: false,
        isError: false,
        error: null,
      } as unknown as ReturnType<typeof useAssetsHook.useUserAssets>);

      renderAssetList();
      expect(screen.getByText("BTC")).toBeInTheDocument();
      expect(screen.getByText("Bitcoin")).toBeInTheDocument();
      expect(screen.getByText("암호화폐")).toBeInTheDocument();
      expect(screen.getByText("005930")).toBeInTheDocument();
      expect(screen.getByText("삼성전자")).toBeInTheDocument();
      expect(screen.getByText("국내주식")).toBeInTheDocument();
    });

    it("각 자산마다 삭제 버튼이 있다", () => {
      mockedUseUserAssets.mockReturnValue({
        data: [fakeAsset, fakeKrAsset],
        isLoading: false,
        isError: false,
        error: null,
      } as unknown as ReturnType<typeof useAssetsHook.useUserAssets>);

      renderAssetList();
      expect(screen.getByLabelText("BTC 삭제")).toBeInTheDocument();
      expect(screen.getByLabelText("005930 삭제")).toBeInTheDocument();
    });
  });

  describe("삭제 동작", () => {
    beforeEach(() => {
      mockedUseUserAssets.mockReturnValue({
        data: [fakeAsset],
        isLoading: false,
        isError: false,
        error: null,
      } as unknown as ReturnType<typeof useAssetsHook.useUserAssets>);
    });

    it("confirm 승인 시 deleteMutation.mutate 가 호출된다", async () => {
      jest.spyOn(window, "confirm").mockReturnValueOnce(true);
      const user = userEvent.setup();
      renderAssetList();

      await user.click(screen.getByLabelText("BTC 삭제"));
      expect(window.confirm).toHaveBeenCalledWith(
        expect.stringContaining("BTC"),
      );
      expect(mockDeleteMutate).toHaveBeenCalledWith(10);
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

  describe("data undefined 상태", () => {
    it("data 가 undefined 일 때 빈 상태 UI 를 표시한다", () => {
      mockedUseUserAssets.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: false,
        error: null,
      } as unknown as ReturnType<typeof useAssetsHook.useUserAssets>);

      renderAssetList();
      expect(screen.getByText("보유 자산이 없습니다.")).toBeInTheDocument();
    });
  });
});
