import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CurrencySwitcher } from "@/components/features/portfolio/currency-switcher";

describe("CurrencySwitcher", () => {
  const defaultProps = {
    value: null,
    onChange: jest.fn(),
    availableCurrencies: ["KRW", "USD"],
  };

  beforeEach(() => jest.clearAllMocks());

  it("'환산 안 함' 옵션을 항상 렌더링한다", () => {
    render(<CurrencySwitcher {...defaultProps} />);
    expect(screen.getByRole("button", { name: "환산 안 함" })).toBeInTheDocument();
  });

  it("availableCurrencies 에 따라 환산 버튼을 렌더링한다", () => {
    render(<CurrencySwitcher {...defaultProps} />);
    expect(screen.getByRole("button", { name: "KRW 환산" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "USD 환산" })).toBeInTheDocument();
  });

  it("value=null 이면 '환산 안 함' 이 active 상태다", () => {
    render(<CurrencySwitcher {...defaultProps} value={null} />);
    const btn = screen.getByRole("button", { name: "환산 안 함" });
    expect(btn).toHaveAttribute("aria-pressed", "true");
  });

  it("value='KRW' 이면 'KRW 환산' 이 active 상태다", () => {
    render(<CurrencySwitcher {...defaultProps} value="KRW" />);
    const btn = screen.getByRole("button", { name: "KRW 환산" });
    expect(btn).toHaveAttribute("aria-pressed", "true");
    const noneBtn = screen.getByRole("button", { name: "환산 안 함" });
    expect(noneBtn).toHaveAttribute("aria-pressed", "false");
  });

  it("'환산 안 함' 클릭 시 onChange(null) 를 호출한다", async () => {
    const onChange = jest.fn();
    render(<CurrencySwitcher {...defaultProps} value="KRW" onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "환산 안 함" }));
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("'KRW 환산' 클릭 시 onChange('KRW') 를 호출한다", async () => {
    const onChange = jest.fn();
    render(<CurrencySwitcher {...defaultProps} onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "KRW 환산" }));
    expect(onChange).toHaveBeenCalledWith("KRW");
  });

  it("availableCurrencies 가 비면 '환산 안 함' 만 렌더링한다", () => {
    render(
      <CurrencySwitcher value={null} onChange={jest.fn()} availableCurrencies={[]} />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(1);
    expect(buttons[0]).toHaveAttribute("aria-label", "환산 안 함");
  });

  it("role=group 과 aria-label 이 있다", () => {
    render(<CurrencySwitcher {...defaultProps} />);
    expect(
      screen.getByRole("group", { name: "통화 환산 선택" }),
    ).toBeInTheDocument();
  });
});
