import { act, renderHook } from "@testing-library/react";
import { useThemeStore } from "@/stores/theme";
import type { Theme } from "@/stores/theme";

// zustand persist 는 localStorage 를 사용하므로 jsdom 환경에서는 동작
// but reset store between tests
beforeEach(() => {
  localStorage.clear();
  useThemeStore.setState({ theme: "system" });
});

describe("useThemeStore", () => {
  it("초기 theme 은 'system' 이다", () => {
    const { result } = renderHook(() => useThemeStore());
    expect(result.current.theme).toBe("system");
  });

  it("setTheme('light') 호출 후 theme 이 'light' 로 변경된다", () => {
    const { result } = renderHook(() => useThemeStore());
    act(() => {
      result.current.setTheme("light");
    });
    expect(result.current.theme).toBe("light");
  });

  it("setTheme('dark') 호출 후 theme 이 'dark' 로 변경된다", () => {
    const { result } = renderHook(() => useThemeStore());
    act(() => {
      result.current.setTheme("dark");
    });
    expect(result.current.theme).toBe("dark");
  });

  it("setTheme('system') 호출 후 theme 이 'system' 으로 변경된다", () => {
    const { result } = renderHook(() => useThemeStore());
    act(() => {
      result.current.setTheme("dark");
    });
    act(() => {
      result.current.setTheme("system");
    });
    expect(result.current.theme).toBe("system");
  });

  it("persist: localStorage 에 'assetlog-theme' key 로 저장된다", () => {
    const { result } = renderHook(() => useThemeStore());
    act(() => {
      result.current.setTheme("dark");
    });
    const stored = localStorage.getItem("assetlog-theme");
    expect(stored).not.toBeNull();
    const parsed = JSON.parse(stored!) as { state: { theme: Theme } };
    expect(parsed.state.theme).toBe("dark");
  });

  it("모든 유효한 theme 값을 허용한다", () => {
    const { result } = renderHook(() => useThemeStore());
    const themes: Theme[] = ["light", "dark", "system"];
    themes.forEach((t) => {
      act(() => {
        result.current.setTheme(t);
      });
      expect(result.current.theme).toBe(t);
    });
  });
});
