import { useState, useRef, useEffect } from "react";

interface LanguageSwitcherProps {
  locale: string;
  path: string;
  labels?: Record<string, string>;
}

const defaultLabels: Record<string, string> = {
  en: "English",
  nl: "Nederlands",
  fr: "Français",
  de: "Deutsch",
};

const localeFlags: Record<string, string> = {
  en: "EN",
  nl: "NL",
  fr: "FR",
  de: "DE",
};

export default function LanguageSwitcher({
  locale,
  path,
  labels = defaultLabels,
}: LanguageSwitcherProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function getLocalePath(targetLocale: string): string {
    const stripped = path.replace(/^\/(en|nl|fr|de)(\/|$)/, "/");
    return `/${targetLocale}${stripped === "/" ? "/" : stripped}`;
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label="Change language"
        className="inline-flex h-9 items-center gap-1 rounded-lg px-2 text-body-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        <span>{localeFlags[locale]}</span>
        <svg className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div
          role="listbox"
          aria-label="Select language"
          className="absolute right-0 top-full z-50 mt-1 min-w-[140px] rounded-lg border border-border bg-card py-1 shadow-lg"
        >
          {Object.entries(labels).map(([code, label]) => (
            <a
              key={code}
              href={getLocalePath(code)}
              role="option"
              aria-selected={code === locale}
              className={`flex items-center gap-2 px-3 py-2 text-body-sm transition-colors hover:bg-accent ${code === locale ? "font-medium text-foreground" : "text-muted-foreground"}`}
              onClick={() => setOpen(false)}
            >
              <span className="w-6 text-center text-body-xs font-medium">{localeFlags[code]}</span>
              {label}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
