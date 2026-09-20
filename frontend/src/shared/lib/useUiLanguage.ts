"use client";

import { useEffect, useState } from "react";
import {
  type AppLanguageCode,
  DEFAULT_APP_LANGUAGE,
} from "@/shared/lib/languages";
import { UI_STRINGS } from "@/shared/lib/uiStrings";

const storageKey: string = "legalfriend-ui-language";

export function useUiLanguage() {
  const [language, setLanguageState] =
    useState<AppLanguageCode>(DEFAULT_APP_LANGUAGE);

  useEffect((): void => {
    const stored: string | null = localStorage.getItem(storageKey);
    if (stored && stored in UI_STRINGS) {
      setLanguageState(stored as AppLanguageCode);
    }
  }, []);

  function setLanguage(code: AppLanguageCode): void {
    setLanguageState(code);
    localStorage.setItem(storageKey, code);
  }

  return { language, setLanguage, strings: UI_STRINGS[language] };
}
