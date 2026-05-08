import { render, screen } from "@testing-library/react";
import { FxWarningInfo } from "@/components/features/portfolio/fx-warning-info";

describe("FxWarningInfo", () => {
  it("warning이 null이면 아무것도 렌더하지 않는다", () => {
    const { container } = render(<FxWarningInfo warning={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("warning이 undefined여도 렌더하지 않는다", () => {
    const { container } = render(<FxWarningInfo warning={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("warning이 same_currency이면 렌더하지 않는다", () => {
    const { container } = render(<FxWarningInfo warning="same_currency" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("missing_historical_rate일 때 인포 아이콘과 tooltip을 표시한다", () => {
    render(<FxWarningInfo warning="missing_historical_rate" />);
    const icon = screen.getByLabelText("환율 데이터 누적 중");
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveAttribute("title", expect.stringContaining("거래일 환율"));
  });

  it("missing_current_rate일 때 인포 아이콘을 표시한다", () => {
    render(<FxWarningInfo warning="missing_current_rate" />);
    const icon = screen.getByLabelText("환율 데이터 누적 중");
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveAttribute("title", expect.stringContaining("현재 환율"));
  });
});
