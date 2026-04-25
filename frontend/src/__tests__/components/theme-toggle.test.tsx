import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeToggle } from "@/components/theme-toggle";
import { useThemeStore } from "@/stores/theme";

beforeEach(() => {
  localStorage.clear();
  useThemeStore.setState({ theme: "system" });
});

describe("ThemeToggle", () => {
  it("3개 버튼(라이트, 다크, 시스템)을 렌더링한다", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("button", { name: "라이트 테마" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "다크 테마" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "시스템 테마" })).toBeInTheDocument();
  });

  it("초기 theme=system 이면 시스템 버튼이 aria-pressed=true 이다", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("button", { name: "시스템 테마" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "라이트 테마" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByRole("button", { name: "다크 테마" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("라이트 버튼 클릭 시 store theme 이 'light' 로 변경된다", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);
    await user.click(screen.getByRole("button", { name: "라이트 테마" }));
    expect(useThemeStore.getState().theme).toBe("light");
  });

  it("다크 버튼 클릭 시 store theme 이 'dark' 로 변경된다", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);
    await user.click(screen.getByRole("button", { name: "다크 테마" }));
    expect(useThemeStore.getState().theme).toBe("dark");
  });

  it("시스템 버튼 클릭 시 store theme 이 'system' 으로 변경된다", async () => {
    const user = userEvent.setup();
    useThemeStore.setState({ theme: "dark" });
    render(<ThemeToggle />);
    await user.click(screen.getByRole("button", { name: "시스템 테마" }));
    expect(useThemeStore.getState().theme).toBe("system");
  });

  it("클릭 후 해당 버튼의 aria-pressed 가 true 로 바뀐다", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);
    const darkBtn = screen.getByRole("button", { name: "다크 테마" });
    await user.click(darkBtn);
    expect(darkBtn).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "시스템 테마" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("테마 선택 group 에 aria-label 이 있다", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("group", { name: "테마 선택" })).toBeInTheDocument();
  });
});
