/**
 * GrabLab CMS v1.5.0 — Light / Dark theme controller for the Admin UI (Grex JS v1.0.0 createTheme).
 *
 * - Preference is stored per-browser (localStorage key `grablab-admin-theme`: "light" | "dark" | "system").
 * - The resolved mode is mirrored to <html data-cms-theme="light|dark"> so the token layer in
 *   admin-ui.css can restyle every admin, commerce, author and profile surface.
 * - All palettes below are verified at >= 4.5:1 (WCAG AA) by tests/profile_dom_audit.mjs.
 */
import { createTheme, effect, signal } from "../grex/grex.js";

export const THEME_STORAGE_KEY = "grablab-admin-theme";
export const DENSITY_STORAGE_KEY = "grablab-admin-density";
export const MOTION_STORAGE_KEY = "grablab-admin-motion";

export const ADMIN_PALETTES = Object.freeze({
  dark: Object.freeze({
    bg: "#2f1321",
    surface: "#2f1622",
    ink: "#ffffff",
    muted: "#c5b2bb",
    accent: "#e3ae5f",
    "accent-ink": "#ffffff",
  }),
  light: Object.freeze({
    bg: "#f3f7f6",
    surface: "#ffffff",
    ink: "#12201d",
    muted: "#4a5a57",
    accent: "#1c6b5f",
    "accent-ink": "#ffffff",
  }),
});

export function readStoredPreference(storage = globalThis.localStorage) {
  try {
    const v = storage && storage.getItem(THEME_STORAGE_KEY);
    return v === "light" || v === "dark" || v === "system" ? v : "system";
  } catch {
    return "system";
  }
}

export function readStoredFlag(key, onValue, storage = globalThis.localStorage) {
  try {
    return Boolean(storage && storage.getItem(key) === onValue);
  } catch {
    return false;
  }
}

export function persistFlag(key, onValue, on, storage = globalThis.localStorage) {
  try {
    if (!storage) return;
    if (on) storage.setItem(key, onValue);
    else storage.removeItem(key);
  } catch {
    // Storage may be unavailable; the flag still applies for this page view.
  }
}

export function applyDensity(compact) {
  const root = globalThis.document && globalThis.document.documentElement;
  if (!root) return;
  if (compact) root.setAttribute("data-cms-density", "compact");
  else root.removeAttribute("data-cms-density");
}

export function applyMotion(reduce) {
  const root = globalThis.document && globalThis.document.documentElement;
  if (!root) return;
  if (reduce) root.setAttribute("data-cms-motion", "reduce");
  else root.removeAttribute("data-cms-motion");
}

export function resolveMode(preference, matchMediaFn = globalThis.matchMedia) {
  if (preference === "light" || preference === "dark") return preference;
  try {
    if (typeof matchMediaFn === "function" && matchMediaFn("(prefers-color-scheme: light)").matches) {
      return "light";
    }
  } catch {
    // fall through to dark default
  }
  return "dark";
}

export const themePreference = signal("system");
export const themeMode = signal("dark");

export function applyAdminTheme(preference) {
  const pref = preference === "light" || preference === "dark" ? preference : "system";
  const mode = resolveMode(pref);
  const root = document.documentElement;
  const prev = root.getAttribute("data-cms-theme");
  if (prev && prev !== mode && typeof root.offsetHeight === "number") {
    root.setAttribute("data-cms-theme-switching", "true");
  }
  root.setAttribute("data-cms-theme", mode);
  root.setAttribute("data-cms-theme-pref", pref);
  const theme = createTheme({
    colors: ADMIN_PALETTES[mode],
    radii: { radius: "12px" },
  });
  theme.applyTo(root);
  if (root.getAttribute("data-cms-theme-switching")) {
    void root.offsetHeight;
    root.removeAttribute("data-cms-theme-switching");
  }
  themePreference.set(pref);
  themeMode.set(mode);
  return mode;
}

export function persistThemePreference(preference, storage = globalThis.localStorage) {
  const pref = preference === "light" || preference === "dark" ? preference : "system";
  try {
    if (storage) storage.setItem(THEME_STORAGE_KEY, pref);
  } catch {
    // Storage may be unavailable (private mode); preference still applies for this page view.
  }
  return applyAdminTheme(pref);
}

export function initAdminTheme() {
  const pref = readStoredPreference();
  const mode = applyAdminTheme(pref);
  applyDensity(readStoredFlag(DENSITY_STORAGE_KEY, "compact"));
  applyMotion(readStoredFlag(MOTION_STORAGE_KEY, "reduce"));
  try {
    const mq = globalThis.matchMedia && globalThis.matchMedia("(prefers-color-scheme: light)");
    if (mq && typeof mq.addEventListener === "function") {
      mq.addEventListener("change", () => {
        if (themePreference.peek() === "system") applyAdminTheme("system");
      });
    }
  } catch {
    // matchMedia listeners are best-effort
  }
  return mode;
}

const SVG_NS = "http://www.w3.org/2000/svg";

function buildThemeIconSvg(dark) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", "18");
  svg.setAttribute("height", "18");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.setAttribute("class", "cms-utility-icon");
  if (dark) {
    const circle = document.createElementNS(SVG_NS, "circle");
    circle.setAttribute("cx", "12");
    circle.setAttribute("cy", "12");
    circle.setAttribute("r", "4");
    svg.appendChild(circle);
    for (const d of [
      "M12 2v2",
      "M12 20v2",
      "m4.93 4.93 1.41 1.41",
      "m17.66 17.66 1.41 1.41",
      "M2 12h2",
      "M20 12h2",
      "m6.34 17.66-1.41 1.41",
      "m19.07 4.93-1.41 1.41",
    ]) {
      const ray = document.createElementNS(SVG_NS, "path");
      ray.setAttribute("d", d);
      svg.appendChild(ray);
    }
  } else {
    const moon = document.createElementNS(SVG_NS, "path");
    moon.setAttribute("d", "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z");
    svg.appendChild(moon);
  }
  return svg;
}

/**
 * Header theme icon button (Fleetyu-inspired sun/moon icon).
 * `aria-pressed` reflects "dark mode is currently on".
 */
export function wireThemeToggle(buttonEl) {
  if (!buttonEl) return;
  effect(() => {
    const dark = themeMode.get() === "dark";
    buttonEl.setAttribute("aria-pressed", dark ? "true" : "false");
    const nextLabel = dark ? "Switch to Light mode" : "Switch to Dark mode";
    buttonEl.setAttribute("aria-label", `Color theme: ${dark ? "dark" : "light"}. ${nextLabel}.`);
    buttonEl.setAttribute("title", nextLabel);
    while (buttonEl.firstChild) buttonEl.removeChild(buttonEl.firstChild);
    buttonEl.appendChild(buildThemeIconSvg(dark));
  });
  buttonEl.addEventListener("click", () => {
    persistThemePreference(themeMode.peek() === "dark" ? "light" : "dark");
  });
}
