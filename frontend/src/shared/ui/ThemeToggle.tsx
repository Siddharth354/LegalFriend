"use client";

import { useEffect, useState } from "react";
import { MoonIcon, SunIcon } from "@/shared/ui/icons";

type Theme = "light" | "dark";

const themeStorageKey: string = "legalfriend-theme";

export function ThemeToggle(): React.JSX.Element {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect((): void => {
    const stored: string | null = localStorage.getItem(themeStorageKey);
    if (stored === "light" || stored === "dark") {
      setTheme(stored);
      return;
    }
    const prefersLight: boolean = window.matchMedia(
      "(prefers-color-scheme: light)",
    ).matches;
    setTheme(prefersLight ? "light" : "dark");
  }, []);

  useEffect((): void => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(themeStorageKey, theme);
  }, [theme]);

  return (
    <div className="theme-toggle">
      <button
        type="button"
        aria-pressed={theme === "light"}
        onClick={(): void => setTheme("light")}
        title="Light"
        className={`theme-toggle-option ${theme === "light" ? "active" : ""}`}
      >
        <SunIcon className="icon-sm" />
      </button>
      <button
        type="button"
        aria-pressed={theme === "dark"}
        onClick={(): void => setTheme("dark")}
        title="Dark"
        className={`theme-toggle-option ${theme === "dark" ? "active" : ""}`}
      >
        <MoonIcon className="icon-sm" />
      </button>
    </div>
  );
}
