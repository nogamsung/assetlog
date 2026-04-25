import { render, act } from "@testing-library/react";
import { ThemeProvider } from "@/components/theme-provider";
import { useThemeStore } from "@/stores/theme";

beforeEach(() => {
  localStorage.clear();
  useThemeStore.setState({ theme: "system" });
  document.documentElement.classList.remove("light", "dark");
});

describe("ThemeProvider", () => {
  it("theme=light 시 documentElement 에 'light' 클래스를 추가하고 'dark' 를 제거한다", () => {
    document.documentElement.classList.add("dark");
    act(() => {
      useThemeStore.setState({ theme: "light" });
    });
    render(<ThemeProvider>test</ThemeProvider>);
    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("theme=dark 시 documentElement 에 'dark' 클래스를 추가하고 'light' 를 제거한다", () => {
    document.documentElement.classList.add("light");
    act(() => {
      useThemeStore.setState({ theme: "dark" });
    });
    render(<ThemeProvider>test</ThemeProvider>);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.classList.contains("light")).toBe(false);
  });

  it("theme=system 시 'light', 'dark' 클래스를 모두 제거한다", () => {
    document.documentElement.classList.add("light", "dark");
    act(() => {
      useThemeStore.setState({ theme: "system" });
    });
    render(<ThemeProvider>test</ThemeProvider>);
    expect(document.documentElement.classList.contains("light")).toBe(false);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("store theme 변경 시 클래스가 동기화된다", () => {
    render(<ThemeProvider>test</ThemeProvider>);

    act(() => {
      useThemeStore.getState().setTheme("dark");
    });
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    act(() => {
      useThemeStore.getState().setTheme("light");
    });
    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);

    act(() => {
      useThemeStore.getState().setTheme("system");
    });
    expect(document.documentElement.classList.contains("light")).toBe(false);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
