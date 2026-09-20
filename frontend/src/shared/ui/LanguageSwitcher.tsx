"use client";

import { useEffect, useRef, useState } from "react";
import { APP_LANGUAGES, type AppLanguageCode } from "@/shared/lib/languages";
import { GlobeIcon } from "@/shared/ui/icons";

type LanguageSwitcherProps = {
  readonly language: AppLanguageCode;
  readonly onSelect: (code: AppLanguageCode) => void;
};

export function LanguageSwitcher({
  language,
  onSelect,
}: LanguageSwitcherProps): React.JSX.Element {
  const [open, setOpen] = useState<boolean>(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect((): (() => void) | undefined => {
    if (!open) return undefined;
    function handleOutsideClick(event: MouseEvent): void {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleOutsideClick);
    return (): void =>
      document.removeEventListener("mousedown", handleOutsideClick);
  }, [open]);

  return (
    <div className="language-switcher" ref={containerRef}>
      <button
        type="button"
        className="chrome-globe"
        onClick={(): void => setOpen((current: boolean): boolean => !current)}
        aria-label="Choose app language"
        aria-expanded={open}
      >
        <GlobeIcon className="icon-sm" />
      </button>
      {open ? (
        <div className="language-menu">
          {APP_LANGUAGES.map(
            (option): React.JSX.Element => (
              <button
                key={option.code}
                type="button"
                className={`language-menu-item ${option.code === language ? "active" : ""}`}
                onClick={(): void => {
                  onSelect(option.code);
                  setOpen(false);
                }}
              >
                <span>{option.native}</span>
                <span className="language-menu-gloss">{option.gloss}</span>
              </button>
            ),
          )}
        </div>
      ) : null}
    </div>
  );
}
