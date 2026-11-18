/**
 * GrabLab CMS v1.4.0 Distraction-Free Sample Web Reader (Pure Grex JS v1.0.0)
 * - Zero <div>, zero innerHTML writes, zero dynamic eval
 * - Light & Dark WCAG AA (>= 4.5:1) toggle + keyboard Enter/Space/Escape support
 */

import { signal, effect, setSafeText, Select } from "../grex/grex.js";

function node(tag, attrs = {}, textVal = null) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v === null || v === undefined) continue;
    if (v === true) {
      el.setAttribute(k, "");
    } else {
      el.setAttribute(k, String(v));
    }
  }
  if (textVal !== null && textVal !== undefined) {
    setSafeText(el, String(textVal));
  }
  return el;
}

export function buildReaderControls(initialTheme = "light", initialScale = "md") {
  const themeSig = signal(initialTheme === "dark" ? "dark" : "light");
  const scaleSig = signal(["sm", "md", "lg"].includes(initialScale) ? initialScale : "md");

  const section = node("section", { class: "reader-controls", "aria-label": "Reader display controls" });
  const themeBtn = node("button", {
    type: "button",
    id: "reader-theme-toggle",
    class: "reader-btn reader-btn-secondary",
    "aria-pressed": themeSig.peek() === "dark" ? "true" : "false",
  });

  const toggleTheme = () => {
    const next = themeSig.peek() === "dark" ? "light" : "dark";
    themeSig.set(next);
  };

  themeBtn.addEventListener("click", toggleTheme);
  themeBtn.addEventListener("keydown", (ev) => {
    if (ev && (ev.key === "Enter" || ev.key === " ")) {
      if (typeof ev.preventDefault === "function") ev.preventDefault();
      toggleTheme();
    } else if (ev && ev.key === "Escape") {
      themeSig.set("light");
    }
  });

  const sizeSel = Select({
    id: "reader-font-size",
    props: {
      name: "font_scale",
      label: "Text Size",
      value: scaleSig,
      options: [
        { value: "sm", label: "Compact" },
        { value: "md", label: "Comfortable" },
        { value: "lg", label: "Large" },
      ],
    },
  });

  effect(() => {
    const mode = themeSig.get();
    if (typeof document !== "undefined" && document.documentElement) {
      document.documentElement.setAttribute("data-grex-theme", mode);
    }
    themeBtn.setAttribute("aria-pressed", mode === "dark" ? "true" : "false");
    setSafeText(themeBtn, mode === "dark" ? "Switch to Light Theme" : "Switch to Dark Theme");
  });

  effect(() => {
    const sc = scaleSig.get();
    if (typeof document !== "undefined") {
      const prose = document.getElementById("reader-prose");
      if (prose) prose.setAttribute("data-font-scale", sc);
    }
  });

  section.appendChild(themeBtn);
  section.appendChild(sizeSel.element);
  return { element: section, theme: themeSig, scale: scaleSig };
}

function bootReader() {
  if (typeof document === "undefined") return;
  const mount = document.getElementById("reader-controls-mount");
  if (!mount) return;
  const controls = buildReaderControls("light", "md");
  mount.appendChild(controls.element);
}

bootReader();
