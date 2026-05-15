import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { InterestView } from "@/components/features/interest/interest-view";
import * as cashApi from "@/lib/api/cash-account";

jest.mock("@/lib/api/cash-account");
const mockedList = jest.mocked(cashApi.listCashTransactions);

function renderWith(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("InterestView", () => {
  beforeEach(() => jest.clearAllMocks());

  it("이자 내역을 통화별 합계와 함께 렌더링한다", async () => {
    mockedList.mockResolvedValueOnce([
      {
        id: 1,
        cashAccountId: null,
        kind: "interest",
        amount: "290",
        currency: "KRW",
        tradedAt: "2025-05-30T15:00:00Z",
        externalSource: "toss_investment",
      },
      {
        id: 2,
        cashAccountId: null,
        kind: "interest",
        amount: "0.63",
        currency: "USD",
        tradedAt: "2026-01-30T15:00:00Z",
        externalSource: "toss_investment",
      },
    ]);

    renderWith(<InterestView />);
    expect(await screen.findByText("2025-05-30")).toBeInTheDocument();
    expect(screen.getByText("2026-01-30")).toBeInTheDocument();
    expect(screen.getByText(/누적 이자 \(KRW\)/)).toBeInTheDocument();
    expect(screen.getByText(/누적 이자 \(USD\)/)).toBeInTheDocument();
    expect(mockedList).toHaveBeenCalledWith({ kind: "interest" });
  });

  it("이자가 없으면 안내 문구를 표시한다", async () => {
    mockedList.mockResolvedValueOnce([]);
    renderWith(<InterestView />);
    expect(
      await screen.findByText("아직 받은 이자가 없습니다."),
    ).toBeInTheDocument();
  });
});
