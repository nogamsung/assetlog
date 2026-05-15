import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ExchangeSyncSection } from "@/components/features/settings/exchange-sync-section";
import * as useUpbitSyncModule from "@/hooks/use-upbit-sync";
import type { UpbitSyncResult } from "@/lib/api/integrations";

jest.mock("@/hooks/use-upbit-sync");

const mockedUseUpbitSync = jest.mocked(useUpbitSyncModule.useUpbitSync);

function setupMutation({
  mutateFn = jest.fn(),
  isPending = false,
  data = undefined as UpbitSyncResult | undefined,
} = {}) {
  mockedUseUpbitSync.mockReturnValue({
    mutate: mutateFn,
    isPending,
    data,
    isSuccess: data !== undefined,
    isError: false,
  } as unknown as ReturnType<typeof useUpbitSyncModule.useUpbitSync>);
}

describe("ExchangeSyncSection", () => {
  beforeEach(() => jest.clearAllMocks());

  it("카드 제목과 업비트 항목이 보인다", () => {
    setupMutation();
    render(<ExchangeSyncSection />);

    expect(screen.getByText("거래소 동기화")).toBeInTheDocument();
    expect(screen.getByText(/업비트/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "업비트 동기화" })).toBeInTheDocument();
  });

  it("환경변수 안내가 노출된다", () => {
    setupMutation();
    render(<ExchangeSyncSection />);
    expect(screen.getByText(/UPBIT_ACCESS_KEY/)).toBeInTheDocument();
    expect(screen.getByText(/UPBIT_SECRET_KEY/)).toBeInTheDocument();
  });

  it("동기화 버튼 클릭 시 mutate 호출", async () => {
    const mutate = jest.fn();
    setupMutation({ mutateFn: mutate });
    render(<ExchangeSyncSection />);

    await userEvent.click(screen.getByRole("button", { name: "업비트 동기화" }));
    expect(mutate).toHaveBeenCalledTimes(1);
  });

  it("isPending 일 때 버튼 비활성·라벨 변경", () => {
    setupMutation({ isPending: true });
    render(<ExchangeSyncSection />);

    const btn = screen.getByRole("button", { name: "업비트 동기화" });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-busy", "true");
    expect(btn).toHaveTextContent("동기화 중...");
  });

  it("결과가 있으면 카운트 4개를 표시한다", () => {
    setupMutation({
      data: { fetched: 50, inserted: 12, skippedDuplicate: 38, skippedNoSymbol: 0 },
    });
    render(<ExchangeSyncSection />);

    const list = screen.getByRole("group", { name: "업비트 동기화 결과" });
    expect(list).toHaveTextContent("50건");
    expect(list).toHaveTextContent("12건");
    expect(list).toHaveTextContent("38건");
    expect(list).toHaveTextContent("0건");
  });

  it("결과가 없으면 카운트 패널을 렌더하지 않는다", () => {
    setupMutation();
    render(<ExchangeSyncSection />);
    expect(screen.queryByRole("group", { name: "업비트 동기화 결과" })).not.toBeInTheDocument();
  });
});
