import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { DividendList } from "@/components/features/assets/dividend-list";
import * as dividendApi from "@/lib/api/dividend";

jest.mock("@/lib/api/dividend");
const mockedListDividends = jest.mocked(dividendApi.listDividends);

function renderWith(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("DividendList", () => {
  beforeEach(() => jest.clearAllMocks());

  it("배당 내역과 누적 배당 요약을 렌더링한다", async () => {
    mockedListDividends.mockResolvedValueOnce({
      dividends: [
        {
          id: 1,
          assetSymbolId: 9,
          exDate: "2026-02-07",
          payDate: "2026-03-01",
          amount: "0.50",
          currency: "USD",
        },
      ],
      summary: [{ assetSymbolId: 9, totalAmount: "1.20", currency: "USD" }],
    });

    renderWith(<DividendList assetSymbolId={9} />);
    expect(await screen.findByText("2026-02-07")).toBeInTheDocument();
    expect(screen.getByText("2026-03-01")).toBeInTheDocument();
    expect(screen.getByText(/누적 배당/)).toBeInTheDocument();
  });

  it("배당이 없으면 안내 문구를 보여준다", async () => {
    mockedListDividends.mockResolvedValueOnce({ dividends: [], summary: [] });
    renderWith(<DividendList assetSymbolId={9} />);
    expect(
      await screen.findByText("아직 받은 배당이 없습니다."),
    ).toBeInTheDocument();
  });
});
