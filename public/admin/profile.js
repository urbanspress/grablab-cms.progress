/**
 * GrabLab CMS v1.5.0 — Universal User Profile Studio (Pure Grex JS v1.0.0)
 *
 * One Fleetyu-inspired profile template for EVERY role (admin, editor, author, viewer):
 *   page header  ->  [ vertical tablist card | tabpanel card stack ]  ->  identity summary card,
 *   2-column expandable information cards (scrollbar-free), security, notifications, billing,
 *   data export, and account deletion panels.
 *
 * Hygiene contract (asserted by tests/profile_dom_audit.mjs):
 *   divCount === 0, innerHTMLWriteCount === 0, zero dynamic eval, zero wrapper <div>,
 *   every element is created through Grex JS v1.0.0 (`renderElement`, `Card`, `Heading`, `Text`,
 *   `Button`, `Form`, `Input`, `Select`, `Tabs`, `Modal`, `ForEach`) with text routed through
 *   `setSafeText` — user-controlled strings (display name, user-agent) can never become markup.
 */
import {
  Button,
  Card,
  Form,
  ForEach,
  Heading,
  Input,
  Modal,
  Select,
  Tabs,
  effect,
  invalidateQueries,
  renderElement,
  setSafeText,
  signal,
  useQuery,
} from "../grex/grex.js";
import { persistFlag } from "./theme.js";

/* ------------------------------------------------------------------ pure helpers (unit-audited) */

export function initialsOf(name) {
  const parts = String(name || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0][0] || "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] || "" : "";
  return (first + last).toUpperCase();
}

export function formatDate(iso) {
  if (!iso) return "Not yet";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Not yet";
  return d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
}

export function formatDateTime(iso) {
  if (!iso) return "Not yet";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Not yet";
  return d.toLocaleString("en-US", { year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export function describeUserAgent(ua) {
  const s = String(ua || "");
  if (!s) return "Unknown device";
  let browser = "Browser";
  if (/Edg\//.test(s)) browser = "Edge";
  else if (/OPR\/|Opera/.test(s)) browser = "Opera";
  else if (/Firefox\//.test(s)) browser = "Firefox";
  else if (/Chrome\//.test(s)) browser = "Chrome";
  else if (/Safari\//.test(s)) browser = "Safari";
  else if (/curl|python|node|axios|fetch|Go-http/i.test(s)) browser = "API client";
  let os = "";
  if (/Windows/.test(s)) os = "Windows";
  else if (/iPhone|iPad|iOS/.test(s)) os = "iOS";
  else if (/Android/.test(s)) os = "Android";
  else if (/Mac OS X|Macintosh/.test(s)) os = "macOS";
  else if (/Linux|X11/.test(s)) os = "Linux";
  return os ? `${browser} on ${os}` : browser;
}

export const PASSWORD_RULES = Object.freeze([
  { id: "length", label: "At least 10 characters", test: (p) => p.length >= 10 },
  { id: "case", label: "Upper & lower case letters", test: (p) => /[a-z]/.test(p) && /[A-Z]/.test(p) },
  { id: "number", label: "Includes a number", test: (p) => /\d/.test(p) },
  { id: "special", label: "Includes a special character", test: (p) => /[^A-Za-z0-9]/.test(p) },
]);

export function scorePassword(pw) {
  const value = String(pw || "");
  const checks = PASSWORD_RULES.map((r) => ({ id: r.id, label: r.label, ok: r.test(value) }));
  const score = value.length === 0 ? 0 : checks.filter((c) => c.ok).length;
  const labels = ["Not set", "Weak", "Fair", "Good", "Strong"];
  return { score, label: labels[score], checks };
}

/* ------------------------------------------------------------------ Grex element helpers */

function rootNode(child) {
  if (child == null || child === false) return null;
  if (typeof child === "object" && child.element && child.element.nodeType) return child.element;
  return child;
}

/**
 * h(tag, attrs, children, on) — thin, safe wrapper over Grex `renderElement`.
 * Children may be Grex component results ({element}), DOM nodes, strings, or reactive () => text.
 */
export function h(tag, attrs = {}, children = [], on = undefined) {
  const kids = (Array.isArray(children) ? children : [children]).map(rootNode).filter((c) => c != null);
  return renderElement({ tag, attrs, children: kids, on });
}

function text(tag, className, value, extraAttrs = {}) {
  return renderElement({ tag, attrs: { class: className, ...extraAttrs }, text: value });
}

function setHidden(node, hidden) {
  if (hidden) node.setAttribute("hidden", "");
  else node.removeAttribute("hidden");
}

/* ------------------------------------------------------------------ reusable profile components */

/** Status / error live region — role="alert" for errors, role="status" for success. */
export function StatusMessage(messageSignal, kind = "error") {
  const ok = kind === "ok";
  const node = renderElement({
    tag: "p",
    attrs: { role: ok ? "status" : "alert", class: ok ? "cms-alert cms-alert-ok" : "cms-alert cms-alert-error", hidden: "" },
  }).element;
  effect(() => {
    const v = messageSignal.get();
    setSafeText(node, v || "");
    setHidden(node, !v);
  });
  return { element: node };
}

export const AVATAR_STORAGE_KEY = "grablab-admin-avatar";
export const AVATAR_CHOICES = Object.freeze([
  { value: "/static/admin/avatars/avatar-01.png", label: "Avatar 01 (Maya Chen)" },
  { value: "/static/admin/avatars/avatar-02.png", label: "Avatar 02 (Sofia Alvarez)" },
  { value: "/static/admin/avatars/avatar-03.png", label: "Avatar 03 (Claire Brooks)" },
  { value: "/static/admin/avatars/avatar-04.png", label: "Avatar 04 (Hannah Kim)" },
  { value: "/static/admin/avatars/avatar-05.png", label: "Avatar 05 (Marcus Rivera)" },
  { value: "/static/admin/avatars/avatar-06.png", label: "Avatar 06 (Daniel Grant)" },
]);
export const DEFAULT_AVATAR_URL = AVATAR_CHOICES[5].value;

export function readStoredAvatar(storage = globalThis.localStorage) {
  try {
    const v = storage && storage.getItem(AVATAR_STORAGE_KEY);
    return AVATAR_CHOICES.some((c) => c.value === v) ? v : DEFAULT_AVATAR_URL;
  } catch {
    return DEFAULT_AVATAR_URL;
  }
}

export const selectedAvatar = signal(readStoredAvatar());

export function syncHeaderAvatar(url) {
  const safeUrl = AVATAR_CHOICES.some((c) => c.value === url) ? url : DEFAULT_AVATAR_URL;
  selectedAvatar.set(safeUrl);
  try {
    if (globalThis.localStorage) globalThis.localStorage.setItem(AVATAR_STORAGE_KEY, safeUrl);
  } catch {
    // storage may be unavailable
  }
  const hdrImg = document.getElementById("cms-header-avatar-img");
  if (hdrImg) hdrImg.setAttribute("src", safeUrl);
}

/** Circular profile avatar using local PNG portrait asset (user-selectable avatar-01..06, default avatar-06.png). */
export function Avatar(nameSource, sizeClass = "") {
  const img = renderElement({
    tag: "img",
    attrs: {
      src: selectedAvatar.peek(),
      alt: "",
      "aria-hidden": "true",
      width: "48",
      height: "48",
      class: "cms-avatar-img",
    },
  }).element;
  effect(() => {
    img.setAttribute("src", selectedAvatar.get());
  });
  const node = renderElement({
    tag: "span",
    attrs: { class: `cms-avatar ${sizeClass}`.trim(), "aria-hidden": "true" },
    children: [img],
  }).element;
  return node;
}

const SVG_NS = "http://www.w3.org/2000/svg";

function createSvgIcon({ className, width, height, viewBox, fill = "none", stroke = "none", strokeWidth = "2", shapes = [] }) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", viewBox);
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("fill", fill);
  if (stroke !== "none") {
    svg.setAttribute("stroke", stroke);
    svg.setAttribute("stroke-width", strokeWidth);
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
  }
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  if (className) svg.setAttribute("class", className);
  for (const spec of shapes) {
    const node = document.createElementNS(SVG_NS, spec.tag);
    for (const [k, v] of Object.entries(spec.attrs)) node.setAttribute(k, v);
    svg.appendChild(node);
  }
  return svg;
}

const PROFILE_TAB_ICON_SPECS = Object.freeze({
  overview: [
    { tag: "circle", attrs: { cx: "12", cy: "8", r: "4" } },
    { tag: "path", attrs: { d: "M20 21a8 8 0 0 0-16 0" } },
  ],
  security: [
    { tag: "path", attrs: { d: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" } },
  ],
  notifications: [
    { tag: "path", attrs: { d: "M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" } },
    { tag: "path", attrs: { d: "M13.73 21a2 2 0 0 1-3.46 0" } },
  ],
  billing: [
    { tag: "rect", attrs: { width: "20", height: "14", x: "2", y: "5", rx: "2" } },
    { tag: "path", attrs: { d: "M2 10h20" } },
  ],
  export: [
    { tag: "ellipse", attrs: { cx: "12", cy: "5", rx: "9", ry: "3" } },
    { tag: "path", attrs: { d: "M3 5v14a9 3 0 0 0 18 0V5" } },
    { tag: "path", attrs: { d: "M3 12a9 3 0 0 0 18 0" } },
  ],
  delete: [
    { tag: "path", attrs: { d: "M3 6h18" } },
    { tag: "path", attrs: { d: "M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" } },
    { tag: "path", attrs: { d: "M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" } },
  ],
});

export function createProfileTabIcon(tabId) {
  return createSvgIcon({
    className: "cms-tab-icon",
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "1.8",
    shapes: PROFILE_TAB_ICON_SPECS[tabId] || [],
  });
}

export function createPencilIcon() {
  return createSvgIcon({
    className: "cms-btn-icon",
    width: 15,
    height: 15,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    shapes: [
      { tag: "path", attrs: { d: "M12 20h9" } },
      { tag: "path", attrs: { d: "M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" } },
    ],
  });
}

export function createVerifiedCheckIcon() {
  return createSvgIcon({
    className: "cms-verified-check",
    width: 16,
    height: 16,
    viewBox: "0 0 20 20",
    fill: "currentColor",
    stroke: "none",
    shapes: [
      { tag: "path", attrs: { d: "M10 1.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17Zm-1.1 11.9L5.7 10.2l1.15-1.15 2.05 2.05 4.25-4.25 1.15 1.15-5.4 5.4Z" } },
    ],
  });
}

function createCardActionButton(label, onClick, ariaLabel = label) {
  const isEdit = String(label || "").trim().toLowerCase() === "edit";
  if (!isEdit) {
    return Button({ props: { text: label, onClick, label: ariaLabel }, className: "cms-btn-secondary cms-profile-card-action" });
  }
  const btn = Button({ props: { onClick, label: ariaLabel }, className: "cms-btn-secondary cms-profile-card-action" });
  btn.element.appendChild(createPencilIcon());
  btn.element.appendChild(renderElement({ tag: "span", text: label }).element);
  return btn;
}

function isInteractiveCardChild(target, cardEl) {
  let cur = target;
  while (cur && cur !== cardEl) {
    const tag = String(cur.tagName || "").toUpperCase();
    if (tag === "BUTTON" || tag === "A" || tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA" || tag === "LABEL") {
      return true;
    }
    if (typeof cur.getAttribute === "function") {
      const role = cur.getAttribute("role");
      if (role === "button" || role === "switch" || role === "link") return true;
    }
    const cls = typeof cur.className === "string" ? cur.className : "";
    if (cls.includes("cms-profile-card-action")) return true;
    cur = cur.parentNode || null;
  }
  return false;
}

function measureCardExpandHeight(cardEl) {
  const sh = Number(cardEl && cardEl.scrollHeight) || 0;
  return Math.max(312, sh + 24);
}

export function syncCardOverflow(cardEl) {
  if (!cardEl || typeof cardEl.setAttribute !== "function") return false;
  const sh = Number(cardEl.scrollHeight) || 0;
  const overflows = sh > 316;
  cardEl.setAttribute("data-overflows", overflows ? "true" : "false");
  if (cardEl.style && typeof cardEl.style.setProperty === "function") {
    cardEl.style.setProperty("--cms-card-expanded-max", `${Math.max(312, sh + 24)}px`);
  }
  return overflows;
}

/** Card with Fleetyu header row: title on the left, optional action button on the right, and click-to-expand height. */
export function InfoCard({
  id,
  title,
  actionText,
  onAction,
  className = "",
  expandable = true,
  expandedSignal = null,
  headingLevel = 2,
  children = [],
}) {
  const headingId = `${id}-title`;
  const headKids = [Heading({ props: { level: headingLevel, text: title }, attrs: { id: headingId }, className: "cms-profile-card-title" })];
  let actionBtn = null;
  if (actionText) {
    actionBtn = createCardActionButton(actionText, onAction);
    headKids.push(actionBtn);
  }
  const expanded = expandedSignal || signal(false);
  const cue = expandable
    ? renderElement({
        tag: "span",
        attrs: { class: "cms-card-expand-cue", "aria-hidden": "true" },
        text: "Expand",
      }).element
    : null;
  if (cue) headKids.push(cue);
  const header = h("header", { class: "cms-profile-card-head" }, headKids);
  const cardChildren = [header, ...children];
  const card = Card({
    tag: "section",
    props: { labelledBy: headingId },
    attrs: expandable
      ? {
          id,
          tabindex: "0",
          "aria-expanded": "false",
          "data-expanded": "false",
          "data-overflows": "false",
        }
      : { id },
    className: `cms-card cms-profile-card ${expandable ? "cms-profile-card-expandable" : ""} ${className}`.trim(),
    children: cardChildren,
  });

  if (expandable) {
    const toggleExpanded = () => {
      syncCardOverflow(card.element);
      expanded.set(!expanded.peek());
    };
    card.element.addEventListener("click", (ev) => {
      if (isInteractiveCardChild(ev && ev.target, card.element)) return;
      if (typeof globalThis.getSelection === "function") {
        const sel = String(globalThis.getSelection() || "").trim();
        if (sel.length > 0) return;
      }
      toggleExpanded();
    });
    card.element.addEventListener("keydown", (ev) => {
      if (!ev || (ev.key !== "Enter" && ev.key !== " ")) return;
      if (isInteractiveCardChild(ev.target, card.element)) return;
      if (typeof ev.preventDefault === "function") ev.preventDefault();
      toggleExpanded();
    });
    effect(() => {
      const isOpen = Boolean(expanded.get());
      card.element.setAttribute("aria-expanded", isOpen ? "true" : "false");
      card.element.setAttribute("data-expanded", isOpen ? "true" : "false");
      if (card.element.style && typeof card.element.style.setProperty === "function") {
        card.element.style.setProperty("--cms-card-expanded-max", `${measureCardExpandHeight(card.element)}px`);
      }
      if (cue) setSafeText(cue, isOpen ? "Collapse" : "Expand");
    });
  }

  return { element: card.element, action: actionBtn, header: header.element, expanded };
}

/** Label/value field list — semantic <ul><li>, no wrapper divs. Values may be reactive functions. */
export function FieldList(items, className = "") {
  const kids = items.map((it) =>
    h("li", { class: "cms-field" }, [
      text("span", "cms-field-label", it.label),
      text("strong", "cms-field-value", it.value),
    ])
  );
  return h("ul", { class: `cms-field-grid ${className}`.trim(), role: "list" }, kids);
}

/** Rounded pill tags (Fleetyu "Skills & Expertise" treatment). */
export function PillList(items, label) {
  const kids = items.map((it) => h("li", { class: "cms-pill" }, [it]));
  return h("ul", { class: "cms-pill-list", role: "list", "aria-label": label }, kids);
}

/** Accessible switch row (role="switch", Space/Enter toggle natively via <button>). */
export function SwitchRow({ id, label, description, checked, onToggle }) {
  const labelId = `${id}-label`;
  const descId = `${id}-desc`;
  const btn = renderElement({
    tag: "button",
    attrs: {
      type: "button",
      role: "switch",
      id,
      class: "cms-switch",
      "aria-checked": "false",
      "aria-labelledby": labelId,
      "aria-describedby": descId,
    },
    on: {
      click: () => {
        const next = !checked.peek();
        checked.set(next);
        if (onToggle) onToggle(next);
      },
    },
  }).element;
  btn.appendChild(renderElement({ tag: "span", attrs: { class: "cms-switch-knob", "aria-hidden": "true" } }).element);
  effect(() => btn.setAttribute("aria-checked", checked.get() ? "true" : "false"));
  const li = h("li", { class: "cms-switch-row" }, [
    h("span", { class: "cms-switch-copy" }, [
      text("strong", "cms-switch-label", label, { id: labelId }),
      text("small", "cms-switch-desc", description, { id: descId }),
    ]),
    btn,
  ]);
  return { element: li.element, button: btn };
}

/** Password strength meter: native <progress> + rule checklist (conveys state with text, not color alone). */
export function StrengthMeter(passwordSignal) {
  const bar = renderElement({
    tag: "progress",
    attrs: { class: "cms-strength-bar", max: "4", value: "0", "aria-label": "Password strength" },
  }).element;
  const labelNode = text("strong", "cms-strength-label", "Not set");
  const items = PASSWORD_RULES.map((r) => ({ rule: r, node: text("li", "cms-rule", r.label, { "data-ok": "false" }).element }));
  const list = h("ul", { class: "cms-rule-list", role: "list", "aria-label": "Password requirements" }, items.map((i) => i.node));
  effect(() => {
    const res = scorePassword(passwordSignal.get());
    bar.setAttribute("value", String(res.score));
    bar.setAttribute("data-level", String(res.score));
    setSafeText(labelNode.element, res.label);
    for (const it of items) {
      const ok = res.checks.find((c) => c.id === it.rule.id).ok;
      it.node.setAttribute("data-ok", ok ? "true" : "false");
      setSafeText(it.node, `${ok ? "Met: " : "Not met: "}${it.rule.label}`);
    }
  });
  const meta = h("p", { class: "cms-strength-meta" }, [text("span", "cms-field-label", "Strength"), labelNode]);
  return h("section", { class: "cms-strength", "aria-live": "polite" }, [meta, bar, list]);
}

/** Identity summary card — avatar, name, role line, verified email checkmark, and "Edit" action. */
export function IdentitySummary({ profile, onEdit }) {
  const nameOf = () => (profile.get() && profile.get().user ? profile.get().user.display_name : "");
  const roleLabel = () => {
    const r = profile.get() && profile.get().user ? String(profile.get().user.role || "") : "";
    return r ? r.charAt(0).toUpperCase() + r.slice(1) : "";
  };
  const emailOf = () => (profile.get() && profile.get().user ? profile.get().user.email : "");
  const avatar = Avatar(() => initialsOf(nameOf()), "cms-avatar-lg");
  const nameHeading = Heading({ props: { level: 2, text: () => nameOf() || "Loading profile" }, attrs: { id: "profile-identity-name" }, className: "cms-identity-name" });
  const roleLine = text("p", "cms-identity-role", roleLabel);
  const emailSpan = renderElement({ tag: "span" }).element;
  const verifiedCheck = createVerifiedCheckIcon();
  verifiedCheck.setAttribute("title", "Email verified");
  setHidden(verifiedCheck, true);
  const verifiedSr = renderElement({ tag: "span", attrs: { class: "cms-sr-only" } }).element;
  effect(() => {
    const p = profile.get();
    setSafeText(emailSpan, emailOf());
    const ok = Boolean(p && p.user && p.user.email_verified);
    setHidden(verifiedCheck, !ok);
    setSafeText(verifiedSr, p && p.user ? (ok ? " (Email verified)" : " (Email not verified)") : "");
  });
  const emailRow = h("p", { class: "cms-identity-email" }, [emailSpan, verifiedCheck, verifiedSr]);
  const editBtn = createCardActionButton("Edit", onEdit, "Edit personal information");
  const copy = h("section", { class: "cms-identity-copy" }, [
    h("header", { class: "cms-identity-line" }, [nameHeading]),
    roleLine,
    emailRow,
  ]);
  const card = Card({
    tag: "section",
    props: { labelledBy: "profile-identity-name" },
    className: "cms-card cms-profile-card cms-identity-card",
    children: [avatar, copy, editBtn],
  });
  return { element: card.element, editButton: editBtn };
}

/* ------------------------------------------------------------------ panels */

function buildOverviewPanel(profile, openEdit) {
  const get = (fn, fallback = "—") => () => {
    const p = profile.get();
    if (!p) return fallback;
    const v = fn(p);
    return v === undefined || v === null || v === "" ? fallback : String(v);
  };
  const identity = IdentitySummary({ profile, onEdit: openEdit });

  const personal = InfoCard({
    id: "profile-personal",
    title: "Personal Information",
    actionText: "Edit",
    onAction: openEdit,
    children: [
      FieldList([
        { label: "Display name", value: get((p) => p.user.display_name) },
        { label: "Email address", value: get((p) => p.user.email) },
        { label: "Member since", value: get((p) => formatDate(p.user.created_at)) },
        { label: "Role", value: get((p) => (p.user.role ? p.user.role.charAt(0).toUpperCase() + p.user.role.slice(1) : "")) },
      ]),
    ],
  });

  const activity = InfoCard({
    id: "profile-activity",
    title: "Account Activity",
    children: [
      FieldList([
        { label: "Last sign-in", value: get((p) => formatDateTime(p.user.last_login_at)) },
        { label: "Signed-in devices", value: get((p) => p.stats.session_count) },
        { label: "Published entries", value: get((p) => p.stats.entries_published) },
        { label: "Drafts", value: get((p) => p.stats.entries_draft) },
        { label: "Current session expires", value: get((p) => formatDateTime(p.sessions.find((s) => s.current)?.expires_at)) },
      ]),
    ],
  });

  const capsSig = signal([]);
  effect(() => {
    const p = profile.get();
    capsSig.set(p && p.capabilities ? p.capabilities : []);
  });
  const capsList = renderElement({ tag: "ul", attrs: { class: "cms-cap-list", role: "list", "aria-label": "Role permissions" } });
  ForEach({
    parent: capsList.element,
    items: capsSig,
    key: (c) => c.key,
    render: (itemSig) => {
      const li = renderElement({ tag: "li", attrs: { class: "cms-cap" } }).element;
      const label = renderElement({ tag: "span", attrs: { class: "cms-cap-label" } }).element;
      const state = renderElement({ tag: "strong", attrs: { class: "cms-cap-state" } }).element;
      li.appendChild(label);
      li.appendChild(state);
      effect(() => {
        const c = itemSig.get();
        setSafeText(label, c.label);
        setSafeText(state, c.granted ? "Allowed" : "Not allowed");
        state.setAttribute("data-granted", c.granted ? "true" : "false");
      });
      return { element: li };
    },
  });
  const perms = InfoCard({ id: "profile-permissions", title: "Role & Permissions", children: [capsList] });

  const methodsSig = signal([]);
  effect(() => {
    const p = profile.get();
    if (!p) return methodsSig.set([]);
    const out = [];
    if (p.has_password) out.push({ key: "password", label: "Password" });
    for (const o of p.oauth_accounts || []) {
      out.push({ key: `oauth:${o.provider}`, label: o.provider.charAt(0).toUpperCase() + o.provider.slice(1) });
    }
    methodsSig.set(out);
  });
  const methodsList = renderElement({ tag: "ul", attrs: { class: "cms-pill-list", role: "list", "aria-label": "Sign-in methods" } });
  ForEach({
    parent: methodsList.element,
    items: methodsSig,
    key: (m) => m.key,
    empty: () => ({ element: renderElement({ tag: "li", attrs: { class: "cms-muted" }, text: "No sign-in methods configured." }).element }),
    render: (itemSig) => {
      const li = renderElement({ tag: "li", attrs: { class: "cms-pill" } }).element;
      effect(() => setSafeText(li, itemSig.get().label));
      return { element: li };
    },
  });
  const methods = InfoCard({
    id: "profile-methods",
    title: "Sign-in Methods",
    children: [methodsList, text("p", "cms-muted", "Manage your password on the Security tab.")],
  });

  const grid = h("section", { class: "cms-profile-grid" }, [personal, activity, methods, perms]);
  return { nodes: [identity, grid], identity, grid, cards: [personal, activity, methods, perms] };
}

function buildSecurityPanel(profile, api, flash) {
  /* --- Password card (disclosure form) --- */
  const formOpen = signal(false);
  const curPw = Input({ id: "profile-current-password", props: { name: "current_password", type: "password", label: "Current password", required: true } });
  const newPw = Input({ id: "profile-new-password", props: { name: "new_password", type: "password", label: "New password", required: true, minLength: 10, maxLength: 1024 } });
  const confPw = Input({ id: "profile-confirm-password", props: { name: "confirm_password", type: "password", label: "Confirm new password", required: true } });
  curPw.input.setAttribute("autocomplete", "current-password");
  newPw.input.setAttribute("autocomplete", "new-password");
  confPw.input.setAttribute("autocomplete", "new-password");
  const pwErr = signal("");
  const submitBtn = renderElement({ tag: "button", attrs: { type: "submit", class: "cms-btn" }, text: "Update password" }).element;
  const cancelBtn = Button({ props: { text: "Cancel", onClick: () => formOpen.set(false) }, className: "cms-btn-secondary" });
  const pwForm = Form({
    id: "profile-password-form",
    props: {
      method: "post",
      requireCsrf: false,
      onSubmit: async () => {
        pwErr.set("");
        const okCur = curPw.validate();
        const okNew = newPw.validate();
        const okConf = confPw.validate();
        if (!okCur || !okNew || !okConf) return;
        if (newPw.value.peek() !== confPw.value.peek()) {
          pwErr.set("New password and confirmation do not match.");
          return;
        }
        try {
          await api.post("/api/auth/password", { current_password: curPw.value.peek(), new_password: newPw.value.peek() });
          curPw.value.set("");
          newPw.value.set("");
          confPw.value.set("");
          formOpen.set(false);
          flash("Password updated. Every other signed-in device was signed out.");
          invalidateQueries(["profile"]);
        } catch (err) {
          pwErr.set(err && err.message ? err.message : "Password update failed.");
        }
      },
    },
    children: [
      StatusMessage(pwErr, "error"),
      curPw.element,
      newPw.element,
      confPw.element,
      StrengthMeter(newPw.value),
      h("footer", { class: "cms-actions-row" }, [{ element: submitBtn }, cancelBtn]),
    ],
  });
  const formRegion = h("section", { id: "profile-password-region", class: "cms-disclosure", hidden: "" }, [pwForm]);
  const passwordExpanded = signal(false);
  const changeBtn = Button({
    props: {
      text: "Change",
      onClick: () => {
        const next = !formOpen.peek();
        formOpen.set(next);
        if (next) passwordExpanded.set(true);
      },
      expanded: "false",
      label: "Change password",
    },
    className: "cms-btn-secondary cms-profile-card-action",
    attrs: { "aria-controls": "profile-password-region" },
  });
  effect(() => {
    const open = formOpen.get();
    setHidden(formRegion.element, !open);
    changeBtn.element.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      passwordExpanded.set(true);
      curPw.input.focus();
    }
  });
  const passwordSummary = h("p", { class: "cms-muted" }, [
    () => {
      const p = profile.get();
      if (!p) return "Loading…";
      if (!p.has_password) return "Password sign-in is not enabled for this account. You sign in with a linked provider.";
      return "Use a long, unique password. Changing it signs out every other device.";
    },
  ]);
  const passwordCard = InfoCard({
    id: "profile-password",
    title: "Password",
    expandedSignal: passwordExpanded,
    children: [passwordSummary, formRegion],
  });
  passwordCard.header.appendChild(changeBtn.element);
  effect(() => {
    const p = profile.get();
    setHidden(changeBtn.element, !!p && !p.has_password);
  });
  effect(() => {
    formOpen.get();
    syncCardOverflow(passwordCard.element);
  });

  /* --- Active sessions card --- */
  const sessionsSig = signal([]);
  effect(() => {
    const p = profile.get();
    sessionsSig.set(p && p.sessions ? p.sessions : []);
  });
  const sessionList = renderElement({ tag: "ul", attrs: { class: "cms-session-list", role: "list", "aria-label": "Signed-in devices" } });
  ForEach({
    parent: sessionList.element,
    items: sessionsSig,
    key: (s) => s.id,
    empty: () => ({ element: renderElement({ tag: "li", attrs: { class: "cms-muted" }, text: "No active sessions." }).element }),
    render: (itemSig) => {
      const li = renderElement({ tag: "li", attrs: { class: "cms-session" } }).element;
      const copy = renderElement({ tag: "span", attrs: { class: "cms-session-copy" } }).element;
      const title = renderElement({ tag: "strong", attrs: { class: "cms-session-title" } }).element;
      const meta = renderElement({ tag: "small", attrs: { class: "cms-session-meta" } }).element;
      const badge = renderElement({ tag: "span", attrs: { class: "cms-badge cms-badge-ok" }, text: "This device" }).element;
      copy.appendChild(title);
      copy.appendChild(meta);
      li.appendChild(copy);
      li.appendChild(badge);
      effect(() => {
        const s = itemSig.get();
        setSafeText(title, describeUserAgent(s.user_agent));
        setSafeText(meta, `Last active ${formatDateTime(s.last_seen_at)} · Expires ${formatDate(s.expires_at)}`);
        setHidden(badge, !s.current);
      });
      return { element: li };
    },
  });
  const revokeErr = signal("");
  const revokeBtn = Button({
    props: {
      text: "Sign out other devices",
      onClick: async () => {
        revokeErr.set("");
        try {
          await api.post("/api/auth/sessions/revoke-others", {});
          flash("Signed out every other device.");
          invalidateQueries(["profile"]);
        } catch (err) {
          revokeErr.set(err && err.message ? err.message : "Could not sign out other devices.");
        }
      },
    },
    className: "cms-btn-danger",
  });
  effect(() => {
    const list = sessionsSig.get();
    if (list.length <= 1) revokeBtn.element.setAttribute("disabled", "");
    else revokeBtn.element.removeAttribute("disabled");
  });
  const sessionsCard = InfoCard({
    id: "profile-sessions",
    title: "Trusted Devices",
    children: [StatusMessage(revokeErr, "error"), sessionList, h("footer", { class: "cms-actions-row" }, [revokeBtn])],
  });

  return { nodes: [passwordCard, sessionsCard], cards: [passwordCard, sessionsCard] };
}

function buildNotificationsPanel(flash) {
  const secKey = "grablab-notif-security";
  const editKey = "grablab-notif-editorial";
  const digestKey = "grablab-notif-digest";
  const readDefault = (k, def) => {
    try {
      const v = globalThis.localStorage && globalThis.localStorage.getItem(k);
      if (v === null) return def;
      return v === "1";
    } catch {
      return def;
    }
  };
  const secAlerts = signal(readDefault(secKey, true));
  const editAlerts = signal(readDefault(editKey, true));
  const digestAlerts = signal(readDefault(digestKey, false));

  const alertsCard = InfoCard({
    id: "profile-notif-alerts",
    title: "Alert Channels",
    className: "cms-span-2",
    children: [
      text("p", "cms-muted", "Choose which workspace and security updates appear in your header notification center."),
      h("ul", { class: "cms-switch-list", role: "list" }, [
        SwitchRow({
          id: "profile-switch-notif-security",
          label: "Security & sign-in alerts",
          description: "Highlight password updates, active devices, and session revocations.",
          checked: secAlerts,
          onToggle: (on) => {
            persistFlag(secKey, "1", on);
            flash(`Security alerts ${on ? "enabled" : "paused"}.`);
          },
        }),
        SwitchRow({
          id: "profile-switch-notif-editorial",
          label: "Editorial & content updates",
          description: "Show status notices when posts, pages, or media change state.",
          checked: editAlerts,
          onToggle: (on) => {
            persistFlag(editKey, "1", on);
            flash(`Editorial updates ${on ? "enabled" : "paused"}.`);
          },
        }),
        SwitchRow({
          id: "profile-switch-notif-digest",
          label: "Workspace summary digest",
          description: "Include weekly publishing and store status highlights.",
          checked: digestAlerts,
          onToggle: (on) => {
            persistFlag(digestKey, "1", on);
            flash(`Workspace digest ${on ? "enabled" : "paused"}.`);
          },
        }),
      ]),
    ],
  });
  return { nodes: [alertsCard], cards: [alertsCard] };
}

function buildBillingPanel(profile) {
  const get = (fn, fallback = "—") => () => {
    const p = profile.get();
    if (!p) return fallback;
    const v = fn(p);
    return v === undefined || v === null || v === "" ? fallback : String(v);
  };
  const planCard = InfoCard({
    id: "profile-billing-plan",
    title: "Plan & Subscription",
    children: [
      FieldList([
        { label: "Edition", value: "GrabLab CMS Self-Hosted" },
        { label: "Architecture", value: "Zero-Plugin Core (Open Core)" },
        { label: "Billing Contact", value: get((p) => p.user.email) },
        { label: "Subscription Status", value: "Active · Self-Managed" },
      ]),
    ],
  });

  const storeLink = renderElement({
    tag: "a",
    attrs: { href: "/admin/store", class: "grex-button cms-btn-secondary cms-profile-card-action" },
    text: "Open Commerce Store",
  }).element;
  effect(() => {
    const p = profile.get();
    const role = p && p.user ? p.user.role : "";
    setHidden(storeLink, role !== "admin" && role !== "editor");
  });

  const invoicesCard = InfoCard({
    id: "profile-billing-invoices",
    title: "Billing & Store Integration",
    children: [
      text(
        "p",
        "cms-muted",
        "Self-hosted GrabLab CMS instances carry zero platform subscription fees. Customer orders, coupons, and payment gateways are managed directly in Commerce."
      ),
      h("footer", { class: "cms-actions-row" }, [{ element: storeLink }]),
    ],
  });
  return { nodes: [planCard, invoicesCard], cards: [planCard, invoicesCard] };
}

function buildDataExportPanel(profile, flash) {
  const exportBtn = Button({
    props: {
      text: "Download Account Data (JSON)",
      label: "Download your account profile data as JSON",
      onClick: () => {
        const p = profile.peek();
        if (!p || !p.user) {
          flash("Profile data is still loading.");
          return;
        }
        const payload = {
          exported_at: new Date().toISOString(),
          user: {
            id: p.user.id,
            display_name: p.user.display_name,
            email: p.user.email,
            role: p.user.role,
            email_verified: Boolean(p.user.email_verified),
            created_at: p.user.created_at,
            last_login_at: p.user.last_login_at,
          },
          stats: p.stats || {},
          capabilities: p.capabilities || [],
          sessions: (p.sessions || []).map((s) => ({
            id: s.id,
            user_agent: s.user_agent,
            last_seen_at: s.last_seen_at,
            expires_at: s.expires_at,
            current: Boolean(s.current),
          })),
        };
        if (typeof Blob === "function" && globalThis.URL && typeof globalThis.URL.createObjectURL === "function") {
          const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
          const url = globalThis.URL.createObjectURL(blob);
          const link = renderElement({
            tag: "a",
            attrs: { href: url, download: `grablab-account-${p.user.id || "profile"}.json` },
          }).element;
          document.body.appendChild(link);
          if (typeof link.click === "function") link.click();
          document.body.removeChild(link);
          if (typeof globalThis.URL.revokeObjectURL === "function") globalThis.URL.revokeObjectURL(url);
        }
        flash("Account data export downloaded.");
      },
    },
    className: "cms-btn",
  });

  const exportCard = InfoCard({
    id: "profile-data-export",
    title: "Export Personal Data",
    className: "cms-span-2",
    children: [
      text(
        "p",
        "cms-muted",
        "Download a portable JSON archive of your account details, granted capabilities, authoring totals, and active device metadata. Password hashes and session tokens are never included."
      ),
      FieldList(
        [
          { label: "Format", value: "JSON (UTF-8)" },
          { label: "Includes", value: "Identity, role permissions, entry counts, trusted devices" },
        ],
        "cms-field-grid-wide"
      ),
      h("footer", { class: "cms-actions-row" }, [exportBtn]),
    ],
  });
  return { nodes: [exportCard], cards: [exportCard] };
}

function buildDeleteAccountPanel(profile) {
  const ack = signal(false);
  const statusMsg = signal("");
  const confirmIn = Input({
    id: "profile-delete-confirm-email",
    props: { name: "confirm_email", type: "email", label: "Type your account email to confirm" },
  });
  const delBtn = Button({
    props: {
      text: "Show deletion instructions",
      label: "Show account deletion instructions",
      onClick: () => {
        const p = profile.peek();
        const expected = p && p.user ? String(p.user.email || "").trim().toLowerCase() : "";
        const typed = String(confirmIn.value.peek() || "").trim().toLowerCase();
        if (!ack.peek() || !expected || typed !== expected) {
          statusMsg.set("Confirm the acknowledgement switch and enter your exact account email first.");
          return;
        }
        confirmIn.value.set("");
        ack.set(false);
        statusMsg.set("Contact a site administrator to submit your deletion request.");
      },
    },
    className: "cms-btn-danger",
  });

  effect(() => {
    const p = profile.get();
    const expected = p && p.user ? String(p.user.email || "").trim().toLowerCase() : "";
    const typed = String(confirmIn.value.get() || "").trim().toLowerCase();
    const ready = Boolean(ack.get() && expected && typed === expected);
    if (!ready) delBtn.element.setAttribute("disabled", "");
    else delBtn.element.removeAttribute("disabled");
  });

  const deleteCard = InfoCard({
    id: "profile-delete-account",
    title: "Delete Account",
    className: "cms-span-2",
    children: [
      text(
        "p",
        "cms-alert cms-alert-error",
        "Deleting an account removes access to this GrabLab workspace and revokes active sessions. Admin safeguards prevent unintended removal while signed in."
      ),
      StatusMessage(statusMsg, "ok"),
      h("ul", { class: "cms-switch-list", role: "list" }, [
        SwitchRow({
          id: "profile-switch-delete-ack",
          label: "Acknowledge permanent removal",
          description: "Confirm you want to begin closing your account access.",
          checked: ack,
        }),
      ]),
      confirmIn.element,
      h("footer", { class: "cms-actions-row" }, [delBtn]),
    ],
  });
  return { nodes: [deleteCard], cards: [deleteCard] };
}

/* ------------------------------------------------------------------ edit dialog */

function buildEditDialog(profile, api, flash, openSig) {
  const nameIn = Input({
    id: "profile-edit-name",
    props: { name: "display_name", type: "text", label: "Display name", required: true, maxLength: 80 },
  });
  const avatarSel = Select({
    id: "profile-edit-avatar",
    props: {
      name: "avatar",
      label: "Profile avatar",
      value: selectedAvatar.peek(),
      options: AVATAR_CHOICES,
    },
  });
  const err = signal("");
  const submit = renderElement({ tag: "button", attrs: { type: "submit", class: "cms-btn" }, text: "Save changes" }).element;
  const cancel = Button({ props: { text: "Cancel", onClick: () => openSig.set(false) }, className: "cms-btn-secondary" });
  effect(() => {
    if (openSig.get()) {
      const p = profile.peek();
      nameIn.value.set(p && p.user ? p.user.display_name : "");
      avatarSel.value.set(selectedAvatar.peek());
      err.set("");
    }
  });
  const form = Form({
    id: "profile-edit-form",
    props: {
      method: "post",
      requireCsrf: false,
      onSubmit: async () => {
        err.set("");
        if (!nameIn.validate()) return;
        try {
          const res = await api.patch("/api/auth/profile", { display_name: nameIn.value.peek().trim() });
          syncHeaderIdentity(res.user.display_name);
          syncHeaderAvatar(avatarSel.value.peek());
          openSig.set(false);
          flash("Profile updated.");
          invalidateQueries(["profile"]);
        } catch (e) {
          err.set(e && e.message ? e.message : "Could not save profile.");
        }
      },
    },
    children: [StatusMessage(err, "error"), nameIn.element, avatarSel.element, h("footer", { class: "cms-actions-row" }, [{ element: submit }, cancel])],
  });
  return Modal({ id: "profile-edit-dialog", props: { open: openSig, title: "Edit Personal Information" }, children: [form] });
}

/** Keep the sticky header identity controls in step with a saved display name (text only, never markup). */
export function syncHeaderIdentity(displayName) {
  const meta = document.querySelector('meta[name="grablab-user-name"]');
  if (meta) meta.setAttribute("content", displayName);
  const role = (document.querySelector('meta[name="grablab-role"]') || { getAttribute: () => "" }).getAttribute("content");
  const chip = document.getElementById("cms-user-chip");
  if (chip) {
    setSafeText(chip, `${displayName} (${role})`);
  }
  const menuName = document.getElementById("cms-avatar-menu-name");
  if (menuName) {
    setSafeText(menuName, displayName);
  }
  const avatarBtn = document.getElementById("cms-avatar-btn");
  if (avatarBtn) {
    avatarBtn.setAttribute("aria-label", `${displayName} (${role}) account menu`);
  }
}

/* ------------------------------------------------------------------ top-level specs / mount */

export const PROFILE_TABS = Object.freeze([
  { id: "overview", label: "My Profile" },
  { id: "security", label: "Security" },
  { id: "notifications", label: "Notifications" },
  { id: "billing", label: "Billing & Subscriptions" },
  { id: "export", label: "Data Export" },
  { id: "delete", label: "Delete Account" },
]);

export function resolveProfileTabId(raw) {
  const clean = String(raw || "")
    .trim()
    .replace(/^#/, "")
    .replace(/^profile-/, "");
  if (clean === "my-profile") return "overview";
  if (clean === "data-export") return "export";
  if (clean === "delete-account") return "delete";
  const match = PROFILE_TABS.find((t) => t.id === clean);
  return match ? match.id : "overview";
}

export function createProfileView(api, { profile = signal(null), initialTab = "overview", onTabChange } = {}) {
  const flashSig = signal("");
  let flashTimer = null;
  const flash = (msg) => {
    flashSig.set(msg);
    if (flashTimer) clearTimeout(flashTimer);
    flashTimer = setTimeout(() => flashSig.set(""), 6000);
  };
  const loadErr = signal("");
  const editOpen = signal(false);
  const openEdit = () => editOpen.set(true);

  const overview = buildOverviewPanel(profile, openEdit);
  const security = buildSecurityPanel(profile, api, flash);
  const notifications = buildNotificationsPanel(flash);
  const billing = buildBillingPanel(profile);
  const dataExport = buildDataExportPanel(profile, flash);
  const deleteAccount = buildDeleteAccountPanel(profile);

  const expandableCards = [
    ...overview.cards,
    ...security.cards,
    ...notifications.cards,
    ...billing.cards,
    ...dataExport.cards,
    ...deleteAccount.cards,
  ];
  const syncAllOverflow = () => {
    for (const c of expandableCards) syncCardOverflow(c.element);
  };

  const wanted = resolveProfileTabId(initialTab);
  const activeId = signal(wanted);
  const tabs = Tabs({
    id: "profile-tabs",
    className: "cms-profile-tabs",
    props: {
      label: "Profile sections",
      activeId,
      tabs: [
        { id: "overview", label: "My Profile", content: [h("section", { class: "cms-profile-stack" }, overview.nodes)] },
        { id: "security", label: "Security", content: [h("section", { class: "cms-profile-grid" }, security.nodes)] },
        { id: "notifications", label: "Notifications", content: [h("section", { class: "cms-profile-grid" }, notifications.nodes)] },
        { id: "billing", label: "Billing & Subscriptions", content: [h("section", { class: "cms-profile-grid" }, billing.nodes)] },
        { id: "export", label: "Data Export", content: [h("section", { class: "cms-profile-grid" }, dataExport.nodes)] },
        { id: "delete", label: "Delete Account", content: [h("section", { class: "cms-profile-grid" }, deleteAccount.nodes)] },
      ],
    },
  });

  // Vertical tablist: add accessible icons per section + Up/Down orientation keyboard navigation.
  const tablist = tabs.element.children[0];
  PROFILE_TABS.forEach((tabDef, i) => {
    const btn = tablist.children[i];
    if (!btn) return;
    btn.textContent = "";
    btn.appendChild(createProfileTabIcon(tabDef.id));
    btn.appendChild(renderElement({ tag: "span", text: tabDef.label }).element);
  });
  tablist.setAttribute("aria-orientation", "vertical");
  const onTablistKeyDown = (ev) => {
    if (!ev || (ev.key !== "ArrowDown" && ev.key !== "ArrowUp")) return;
    if (typeof ev.preventDefault === "function") ev.preventDefault();
    const ids = PROFILE_TABS.map((t) => t.id);
    const idx = Math.max(0, ids.indexOf(activeId.peek()));
    const next = ids[(idx + (ev.key === "ArrowDown" ? 1 : ids.length - 1)) % ids.length];
    activeId.set(next);
    const btn = tabs.element.querySelector ? tabs.element.querySelector(`#profile-tabs-tab-${next}`) : null;
    if (btn && typeof btn.focus === "function") btn.focus();
  };
  tablist.addEventListener("keydown", onTablistKeyDown);

  let resizeObs = null;
  if (typeof globalThis.ResizeObserver === "function") {
    resizeObs = new globalThis.ResizeObserver(() => syncAllOverflow());
    for (const c of expandableCards) resizeObs.observe(c.element);
  }

  let didInitSync = false;
  effect(() => {
    const id = activeId.get();
    if (typeof globalThis.requestAnimationFrame === "function") {
      globalThis.requestAnimationFrame(() => syncAllOverflow());
    } else {
      syncAllOverflow();
    }
    if (didInitSync && onTabChange) onTabChange(id);
    didInitSync = true;
  });

  effect(() => {
    profile.get();
    if (typeof globalThis.requestAnimationFrame === "function") {
      globalThis.requestAnimationFrame(() => syncAllOverflow());
    } else {
      syncAllOverflow();
    }
  });

  const rawTabsDispose = tabs.dispose;
  const dispose = () => {
    if (flashTimer) clearTimeout(flashTimer);
    tablist.removeEventListener("keydown", onTablistKeyDown);
    if (resizeObs) resizeObs.disconnect();
    if (typeof rawTabsDispose === "function") rawTabsDispose();
  };
  tabs.dispose = dispose;

  const dialog = buildEditDialog(profile, api, flash, editOpen);
  const view = h("section", { class: "cms-profile-layout", "aria-label": "User profile" }, [
    StatusMessage(loadErr, "error"),
    StatusMessage(flashSig, "ok"),
    tabs,
    dialog,
  ]);
  return {
    element: view.element,
    tabs,
    cards: expandableCards,
    activeId,
    profile,
    loadErr,
    editOpen,
    dialog,
    syncAllOverflow,
    dispose,
  };
}

export function mountProfile(root, api) {
  const profile = signal(null);
  const query = useQuery(api, "/api/auth/profile", { tags: ["profile"] });
  const searchParams =
    globalThis.location && globalThis.location.search ? new URLSearchParams(globalThis.location.search) : null;
  const rawQueryTab = searchParams ? searchParams.get("section") || searchParams.get("tab") || "" : "";
  const rawHash = globalThis.location && globalThis.location.hash ? globalThis.location.hash.slice(1) : "";
  const initialTab = resolveProfileTabId(rawQueryTab || rawHash);
  const view = createProfileView(api, {
    profile,
    initialTab,
    onTabChange: (id) => {
      if (globalThis.history && globalThis.location) {
        const nextUrl =
          id === "overview"
            ? globalThis.location.pathname
            : `${globalThis.location.pathname}?section=${encodeURIComponent(id)}`;
        const curUrl = `${globalThis.location.pathname}${globalThis.location.search || ""}`;
        if (nextUrl !== curUrl) {
          globalThis.history.replaceState(globalThis.history.state, "", nextUrl);
        }
      }
    },
  });
  effect(() => {
    const err = query.error.get();
    if (err) {
      view.loadErr.set(err);
      return;
    }
    const data = query.data.get();
    if (data) {
      view.loadErr.set("");
      profile.set(data);
    }
  });
  root.appendChild(view.element);
  if (typeof globalThis.requestAnimationFrame === "function") {
    globalThis.requestAnimationFrame(() => view.syncAllOverflow());
  }
  return view;
}
