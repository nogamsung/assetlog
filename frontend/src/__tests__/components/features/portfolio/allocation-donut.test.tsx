import { render, screen } from "@testing-library/react";
import { AllocationDonut } from "@/components/features/portfolio/allocation-donut";
import type { AllocationEntry } from "@/types/portfolio";

const sampleAllocation: AllocationEntry[] = [
  { assetType: "kr_stock", pct: 42.1 },
  { assetType: "us_stock", pct: 37.9 },
  { assetType: "crypto", pct: 20.0 },
];

describe("AllocationDonut", () => {
  it("빈 배열이면 데이터 없음 placeholder 를 렌더링한다", () => {
    render(<AllocationDonut allocation={[]} />);
    expect(screen.getByText("데이터 없음")).toBeInTheDocument();
  });

  it("빈 배열이어도 aria-label 이 존재한다", () => {
    render(<AllocationDonut allocation={[]} />);
    const el = screen.getByLabelText("자산 클래스별 비중 도넛 차트");
    expect(el).toBeInTheDocument();
  });

  it("데이터가 있으면 SVG 차트를 렌더링한다", () => {
    const { container } = render(<AllocationDonut allocation={sampleAllocation} />);
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("aria-label 이 SVG 에 설정된다", () => {
    render(<AllocationDonut allocation={sampleAllocation} />);
    const svg = screen.getByRole("img", { name: "자산 클래스별 비중 도넛 차트" });
    expect(svg).toBeInTheDocument();
  });

  it("각 자산 클래스명이 범례에 표시된다", () => {
    render(<AllocationDonut allocation={sampleAllocation} />);
    expect(screen.getByText(/국내주식/)).toBeInTheDocument();
    expect(screen.getByText(/미국주식/)).toBeInTheDocument();
    expect(screen.getByText(/암호화폐/)).toBeInTheDocument();
  });

  it("스크린리더용 목록이 aria-label 을 가진다", () => {
    render(<AllocationDonut allocation={sampleAllocation} />);
    const list = screen.getByRole("list", { name: "자산 클래스 비중 목록" });
    expect(list).toBeInTheDocument();
  });

  it("퍼센트 값이 표시된다 (MODIFIED: trailing zero trimmed by formatPercent)", () => {
    render(<AllocationDonut allocation={sampleAllocation} />);
    // 42.10 → 42.1% (trailing zero removed)
    expect(screen.getByText(/42\.1%/)).toBeInTheDocument();
  });
});
