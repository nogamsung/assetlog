import { render, screen } from "@testing-library/react";
import { TagBreakdownTable } from "@/components/features/portfolio/tag-breakdown-table";
import * as useTagBreakdownModule from "@/hooks/use-tag-breakdown";
import type { TagBreakdownResponse } from "@/types/tag-breakdown";

jest.mock("@/hooks/use-tag-breakdown");

const mockedUseTagBreakdown = jest.mocked(useTagBreakdownModule.useTagBreakdown);

function setupMock(
  overrides: Partial<ReturnType<typeof useTagBreakdownModule.useTagBreakdown>>,
) {
  mockedUseTagBreakdown.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: false,
    ...overrides,
  } as ReturnType<typeof useTagBreakdownModule.useTagBreakdown>);
}

const fakeData: TagBreakdownResponse = {
  entries: [
    {
      tag: "DCA",
      transactionCount: 12,
      buyCount: 10,
      sellCount: 2,
      totalBoughtValueByCurrency: { USD: "1500.00", KRW: "5000000.00" },
      totalSoldValueByCurrency: { USD: "100.00" },
    },
    {
      tag: "LUMP",
      transactionCount: 5,
      buyCount: 4,
      sellCount: 1,
      totalBoughtValueByCurrency: { USD: "3000.00" },
      totalSoldValueByCurrency: { USD: "500.00" },
    },
    {
      tag: null,
      transactionCount: 3,
      buyCount: 3,
      sellCount: 0,
      totalBoughtValueByCurrency: { KRW: "900000.00" },
      totalSoldValueByCurrency: {},
    },
  ],
};

describe("TagBreakdownTable", () => {
  beforeEach(() => jest.clearAllMocks());

  describe("로딩 상태", () => {
    it("isLoading 이면 스켈레톤 3개를 렌더링한다", () => {
      setupMock({ isLoading: true });
      render(<TagBreakdownTable />);
      expect(
        screen.getByRole("status", { name: "태그별 거래 집계 로딩 중" }),
      ).toBeInTheDocument();
    });
  });

  describe("에러 상태", () => {
    it("isError 이면 role=alert 메시지를 렌더링한다", () => {
      setupMock({
        isError: true,
        error: new Error("서버 오류"),
      });
      render(<TagBreakdownTable />);
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("에러 메시지를 표시한다", () => {
      setupMock({
        isError: true,
        error: new Error("서버 오류"),
      });
      render(<TagBreakdownTable />);
      expect(screen.getByRole("alert")).toHaveTextContent("서버 오류");
    });

    it("에러 객체가 Error 가 아니면 기본 메시지를 표시한다", () => {
      setupMock({
        isError: true,
        error: undefined,
      } as unknown as Partial<ReturnType<typeof useTagBreakdownModule.useTagBreakdown>>);
      render(<TagBreakdownTable />);
      expect(screen.getByRole("alert")).toHaveTextContent(
        "태그별 거래 집계를 불러오지 못했습니다.",
      );
    });
  });

  describe("빈 상태", () => {
    it("entries 가 빈 배열이면 empty state 를 렌더링한다", () => {
      setupMock({ data: { entries: [] }, isSuccess: true });
      render(<TagBreakdownTable />);
      expect(screen.getByText("거래 내역이 없습니다.")).toBeInTheDocument();
    });

    it("data 가 undefined 이면 empty state 를 렌더링한다", () => {
      setupMock({ data: undefined });
      render(<TagBreakdownTable />);
      expect(screen.getByText("거래 내역이 없습니다.")).toBeInTheDocument();
    });
  });

  describe("정상 렌더", () => {
    beforeEach(() => {
      setupMock({ data: fakeData, isSuccess: true });
    });

    it("테이블 헤더를 렌더링한다", () => {
      render(<TagBreakdownTable />);
      expect(screen.getByRole("columnheader", { name: "태그" })).toBeInTheDocument();
      expect(screen.getByRole("columnheader", { name: "거래수" })).toBeInTheDocument();
      expect(screen.getByRole("columnheader", { name: "매수 합계" })).toBeInTheDocument();
      expect(screen.getByRole("columnheader", { name: "매도 합계" })).toBeInTheDocument();
    });

    it("DCA 태그 행을 렌더링한다", () => {
      render(<TagBreakdownTable />);
      expect(screen.getByText("DCA")).toBeInTheDocument();
    });

    it("LUMP 태그 행을 렌더링한다", () => {
      render(<TagBreakdownTable />);
      expect(screen.getByText("LUMP")).toBeInTheDocument();
    });

    it("거래수 셀에 매수·매도 상세를 표시한다", () => {
      render(<TagBreakdownTable />);
      expect(screen.getByText("(매수 10 · 매도 2)")).toBeInTheDocument();
    });
  });

  describe("null 태그 표시", () => {
    it("tag = null 인 행에 '(태그 없음)' 회색 텍스트를 표시한다", () => {
      setupMock({ data: fakeData, isSuccess: true });
      render(<TagBreakdownTable />);
      expect(screen.getByText("(태그 없음)")).toBeInTheDocument();
    });
  });

  describe("다중 통화 셀 표시", () => {
    it("여러 통화가 있을 때 셀에 모두 표시한다", () => {
      setupMock({ data: fakeData, isSuccess: true });
      render(<TagBreakdownTable />);
      // DCA 매수 합계: USD + KRW
      const boughtCell = screen.getByLabelText("DCA 매수 합계");
      expect(boughtCell).toBeInTheDocument();
      expect(boughtCell.textContent).toContain("$");
      expect(boughtCell.textContent).toContain("₩");
    });

    it("매도 내역이 없으면 '—' 를 표시한다", () => {
      setupMock({ data: fakeData, isSuccess: true });
      render(<TagBreakdownTable />);
      // null 태그 행의 매도 합계는 빈 객체 → "—" (aria-label: "태그 없음 매도 합계")
      const untaggedRow = screen.getByText("(태그 없음)").closest("tr");
      expect(untaggedRow).not.toBeNull();
      // 해당 행의 마지막 td(매도 합계)가 "—" 를 포함하는지 확인
      const cells = untaggedRow!.querySelectorAll("td");
      const soldCell = cells[cells.length - 1];
      expect(soldCell).toHaveTextContent("—");
    });
  });

  describe("카드 헤딩", () => {
    it("'태그별 거래 집계' 제목이 렌더링된다", () => {
      setupMock({ data: fakeData, isSuccess: true });
      render(<TagBreakdownTable />);
      expect(screen.getByRole("heading", { name: "태그별 거래 집계" })).toBeInTheDocument();
    });
  });
});
