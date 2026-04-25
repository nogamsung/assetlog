"use client";

import { useEffect } from "react";
import { useThemeStore } from "@/stores/theme";

interface ThemeProviderProps {
  children: React.ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const theme = useThemeStore((s) => s.theme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    if (theme === "light") root.classList.add("light");
    else if (theme === "dark") root.classList.add("dark");
    // system: media query handles it automatically
  }, [theme]);

  return <>{children}</>;
}
