import en from "./en.json";
import nl from "./nl.json";
import fr from "./fr.json";
import de from "./de.json";

export type Locale = "en" | "nl" | "fr" | "de";

export const locales: Locale[] = ["en", "nl", "fr", "de"];
export const defaultLocale: Locale = "en";

const translations: Record<Locale, Record<string, unknown>> = { en, nl, fr, de };

/**
 * Get a translation string by dot-separated key path.
 * Supports {count} interpolation.
 */
export function t(
  key: string,
  locale: Locale,
  params?: Record<string, string | number>
): string {
  const keys = key.split(".");
  let value: unknown = translations[locale];

  for (const k of keys) {
    if (value && typeof value === "object" && k in value) {
      value = (value as Record<string, unknown>)[k];
    } else {
      // Fallback to English
      value = translations.en;
      for (const fk of keys) {
        if (value && typeof value === "object" && fk in value) {
          value = (value as Record<string, unknown>)[fk];
        } else {
          return key; // Return key if not found
        }
      }
      break;
    }
  }

  if (typeof value !== "string") return key;

  if (params) {
    return Object.entries(params).reduce(
      (str, [k, v]) => str.replace(`{${k}}`, String(v)),
      value
    );
  }

  return value;
}

/** Extract locale from URL pathname (first segment after /) */
export function getLocaleFromUrl(url: URL): Locale {
  const segment = url.pathname.split("/")[1];
  if (locales.includes(segment as Locale)) {
    return segment as Locale;
  }
  return defaultLocale;
}

/** Build a localized path: /en/pricing → /fr/pricing */
export function getLocalePath(path: string, locale: Locale): string {
  // Remove leading locale prefix if present
  const stripped = path.replace(/^\/(en|nl|fr|de)(\/|$)/, "/");
  return `/${locale}${stripped === "/" ? "/" : stripped}`;
}
