/**
 * GrabLab CMS v1.5.0 Admin UI Polish & Universal User Profile Studio Audit
 * Verifies:
 *  - Pure Grex JS v1.0.0 DOM hygiene (divCount === 0, innerHTMLWriteCount === 0, zero eval)
 *  - Header navigation for all four roles, with WordPress icons only on Posts and Pages
 *  - Keyboard navigation (Tab, Enter, Space, ArrowUp/Down, Home/End, Escape + focus restoration)
 *  - Dynamic Light & Dark WCAG AA (>= 4.5:1) contrast check parsed directly from admin-ui.css
 *
 * Usage: node tests/profile_dom_audit.mjs
 */

import fs from "node:fs";
import assert from "node:assert/strict";

let divCount = 0;
let innerHTMLWriteCount = 0;
const createdElements = [];
let activeEl = null;

function makeFakeElement(tag) {
  const tagLower = String(tag).toLowerCase();
  if (tagLower === "div") divCount += 1;
  const attrs = new Map();
  const children = [];
  const listeners = new Map();
  const classes = new Set();
  let textVal = "";

  const syncClassSet = (val) => {
    classes.clear();
    for (const part of String(val || "").split(/\s+/).filter(Boolean)) {
      classes.add(part);
    }
  };

  const el = {
    tagName: tagLower.toUpperCase(),
    localName: tagLower,
    nodeName: tagLower.toUpperCase(),
    nodeType: 1,
    hidden: false,
    disabled: false,
    checked: false,
    open: false,
    value: "",
    children,
    childNodes: children,
    parentNode: null,
    style: {},
    dataset: {},
    classList: {
      add: (...names) => {
        for (const n of names) classes.add(n);
        attrs.set("class", Array.from(classes).join(" "));
      },
      remove: (...names) => {
        for (const n of names) classes.delete(n);
        attrs.set("class", Array.from(classes).join(" "));
      },
      toggle: (name, force) => {
        const shouldAdd = force !== undefined ? Boolean(force) : !classes.has(name);
        if (shouldAdd) classes.add(name);
        else classes.delete(name);
        attrs.set("class", Array.from(classes).join(" "));
        return shouldAdd;
      },
      contains: (name) => classes.has(name),
    },
    get firstChild() {
      return children[0] || null;
    },
    get textContent() {
      if (textVal) return textVal;
      return children.map((c) => c.textContent || "").join("");
    },
    set textContent(v) {
      textVal = String(v);
      children.length = 0;
    },
    get innerHTML() {
      return "";
    },
    set innerHTML(_v) {
      innerHTMLWriteCount += 1;
      throw new Error("innerHTML writes are strictly forbidden");
    },
    get className() {
      return attrs.get("class") || "";
    },
    set className(v) {
      attrs.set("class", String(v));
      syncClassSet(v);
    },
    get href() {
      return attrs.get("href") || "";
    },
    set href(v) {
      attrs.set("href", String(v));
    },
    ...(tagLower === "input" || tagLower === "button" || tagLower === "select" || tagLower === "textarea"
      ? {
          get type() {
            return attrs.get("type") || "";
          },
          set type(v) {
            attrs.set("type", String(v));
          },
        }
      : {}),
    setAttribute(k, v) {
      attrs.set(k, String(v));
      if (k === "class") syncClassSet(v);
      if (k === "hidden") el.hidden = true;
      if (k === "disabled") el.disabled = true;
    },
    getAttribute(k) {
      return attrs.has(k) ? attrs.get(k) : null;
    },
    hasAttribute(k) {
      return attrs.has(k);
    },
    removeAttribute(k) {
      attrs.delete(k);
      if (k === "hidden") el.hidden = false;
      if (k === "disabled") el.disabled = false;
    },
    appendChild(ch) {
      ch.parentNode = el;
      children.push(ch);
      return ch;
    },
    removeChild(ch) {
      const idx = children.indexOf(ch);
      if (idx >= 0) {
        children.splice(idx, 1);
        ch.parentNode = null;
      }
      return ch;
    },
    insertBefore(ch, ref) {
      ch.parentNode = el;
      const idx = children.indexOf(ref);
      if (idx >= 0) children.splice(idx, 0, ch);
      else children.push(ch);
      return ch;
    },
    contains(target) {
      if (target === el) return true;
      return children.some((c) => typeof c.contains === "function" && c.contains(target));
    },
    focus() {
      activeEl = el;
    },
    showModal() {
      el.open = true;
    },
    close() {
      el.open = false;
    },
    click() {
      const fns = listeners.get("click") || [];
      for (const fn of fns) fn({ type: "click", target: el, preventDefault() {}, stopPropagation() {} });
    },
    addEventListener(evName, fn) {
      if (!listeners.has(evName)) listeners.set(evName, []);
      listeners.get(evName).push(fn);
    },
    removeEventListener(evName, fn) {
      const arr = listeners.get(evName) || [];
      const i = arr.indexOf(fn);
      if (i >= 0) arr.splice(i, 1);
    },
    dispatchEvent(ev) {
      const fns = listeners.get(ev.type) || [];
      for (const fn of fns) fn(ev);
    },
    querySelectorAll(sel) {
      const out = [];
      const walk = (n) => {
        if (!n || typeof n !== "object" || n.nodeType !== 1) return;
        const match =
          sel === "*" ||
          (sel === "div" && n.tagName === "DIV") ||
          (sel === "a[data-nav-href]" && n.tagName === "A" && n.hasAttribute("data-nav-href")) ||
          (sel === "svg, img" && (n.tagName === "SVG" || n.tagName === "IMG")) ||
          (sel.includes("button") && ["BUTTON", "A", "INPUT", "SELECT", "TEXTAREA"].includes(n.tagName) && !n.disabled);
        if (match) out.push(n);
        for (const c of n.children || []) walk(c);
      };
      for (const c of children) walk(c);
      return out;
    },
    querySelector(sel) {
      const walk = (n) => {
        if (!n || typeof n !== "object" || n.nodeType !== 1) return null;
        if (sel.startsWith("#") && n.getAttribute("id") === sel.slice(1)) return n;
        if (/^[a-z0-9]+$/i.test(sel) && n.tagName === sel.toUpperCase()) return n;
        for (const c of n.children || []) {
          const hit = walk(c);
          if (hit) return hit;
        }
        return null;
      };
      return walk(el);
    },
  };
  createdElements.push(el);
  return el;
}

const docAttrs = new Map();
const docListeners = new Map();
const byId = new Map();

const docRoot = {
  style: {
    setProperty: () => {},
  },
  setAttribute: (k, v) => docAttrs.set(k, String(v)),
  getAttribute: (k) => (docAttrs.has(k) ? docAttrs.get(k) : null),
  removeAttribute: (k) => docAttrs.delete(k),
};

globalThis.document = {
  documentElement: docRoot,
  get activeElement() {
    return activeEl;
  },
  head: makeFakeElement("head"),
  body: makeFakeElement("body"),
  createElement: (tag) => makeFakeElement(tag),
  createElementNS: (_ns, tag) => makeFakeElement(tag),
  createTextNode: (t) => ({ nodeType: 3, textContent: String(t), children: [] }),
  createComment: (t) => ({ nodeType: 8, textContent: String(t), children: [] }),
  getElementById: (id) => byId.get(id) || null,
  querySelector: (sel) => {
    if (sel.startsWith("#")) return byId.get(sel.slice(1)) || null;
    return null;
  },
  querySelectorAll: (sel) => (sel === "div" ? createdElements.filter((e) => e.tagName === "DIV") : []),
  addEventListener: (ev, fn) => {
    if (!docListeners.has(ev)) docListeners.set(ev, []);
    docListeners.get(ev).push(fn);
  },
  dispatchEvent: (ev) => {
    for (const fn of docListeners.get(ev.type) || []) fn(ev);
  },
};

const { auditAccessibility, computeContrastRatio, signal } = await import("../public/grex/grex.js");
const navMod = await import("../public/admin/nav.js");
const themeMod = await import("../public/admin/theme.js");
const profileMod = await import("../public/admin/profile.js");

function countDivsInTree(root) {
  let count = root.tagName === "DIV" ? 1 : 0;
  for (const ch of root.children || []) {
    if (ch.nodeType === 1) count += countDivsInTree(ch);
  }
  return count;
}

// 1. Static JS hygiene audit
const jsFiles = [
  "public/admin/profile.js",
  "public/admin/nav.js",
  "public/admin/theme.js",
  "public/admin/theme-init.js",
  "public/admin/admin.js",
  "public/admin/commerce.js",
  "public/admin/author.js",
];
for (const rel of jsFiles) {
  const src = fs.readFileSync(rel, "utf8");
  assert.equal(/\.innerHTML\s*=/.test(src), false, `${rel} contains forbidden .innerHTML assignment`);
  assert.equal(/\beval\s*\(|new\s+Function\s*\(/.test(src), false, `${rel} contains eval/new Function`);
  assert.equal(/createElement\(\s*["']div["']\s*\)/.test(src), false, `${rel} creates forbidden <div>`);
  assert.equal(/type:\s*["']number["']/.test(src), false, `${rel} uses forbidden float-prone type="number"`);
}

// Admin main script must not inject raw SVG strings outside nav.js Posts/Pages icons
const adminJsSrc = fs.readFileSync("public/admin/admin.js", "utf8");
assert.equal(/createElementNS\s*\(|<svg|makeSvg/.test(adminJsSrc), false, "public/admin/admin.js must not inject SVG icons");

// 2. Static .grab.html template zero-<div>, zero-inline-handler, zero-header-SVG audit
const htmlTargets = [
  "src/views/admin/dashboard.grab.html",
  "src/views/admin/login.grab.html",
  "src/views/admin/setup.grab.html",
];
for (const rel of htmlTargets) {
  const html = fs.readFileSync(rel, "utf8").toLowerCase();
  assert.equal(html.includes("<div"), false, `Found <div> in ${rel}`);
  assert.equal(/\bon[a-z]+\s*=/.test(html), false, `Found inline handler in ${rel}`);
  assert.equal(html.includes("<svg"), false, `Found <svg> icon in ${rel}`);
  assert.equal(html.includes("<aside"), false, `Found removed <aside> sidebar in ${rel}`);
}

// 3. Header navigation: text links + WordPress 16x16 aria-hidden icons on Posts & Pages ONLY + keyboard disclosure/Escape
for (const role of ["admin", "editor", "author", "viewer"]) {
  const model = navMod.buildNavModel(role, role !== "viewer");
  for (const item of [...model.primary, ...model.more]) {
    assert.ok(item.text && item.href, "Nav item requires text and href");
    if (item.href === "/admin/posts") {
      assert.equal(item.icon, "posts", "Posts link must carry posts icon");
    } else if (item.href === "/admin/pages") {
      assert.equal(item.icon, "pages", "Pages link must carry pages icon");
    } else {
      assert.equal("icon" in item || "iconSvg" in item, false, `Nav item ${item.text} must not carry icon property`);
    }
  }
  assert.ok(model.primary.some((i) => i.href === "/admin/profile"), `Role ${role} must include Profile link`);
  if (role === "viewer") {
    assert.equal(model.primary.length, 1, "Viewer header nav must show only Profile");
    assert.equal(model.more.length, 0, "Viewer header nav must have no More menu");
  }
}

const navMount = makeFakeElement("section");
navMount.setAttribute("id", "admin-nav-mount");
byId.set("admin-nav-mount", navMount);
const mobileBtn = makeFakeElement("button");
mobileBtn.setAttribute("id", "cms-mobile-nav-toggle");
byId.set("cms-mobile-nav-toggle", mobileBtn);

navMod.mountHorizontalNav("/admin/profile", "admin", null);
assert.equal(countDivsInTree(navMount), 0, "Header navigation must contain 0 <div> tags");
const headerIcons = navMount.querySelectorAll("svg, img");
assert.equal(headerIcons.length, 2, "Header navigation must contain WordPress icons ONLY on Posts and Pages");
for (const svg of headerIcons) {
  assert.equal(svg.tagName, "SVG");
  assert.equal(svg.getAttribute("width"), "16");
  assert.equal(svg.getAttribute("height"), "16");
  assert.equal(svg.getAttribute("aria-hidden"), "true");
  assert.equal(svg.parentNode.tagName, "A");
  const href = svg.parentNode.getAttribute("data-nav-href");
  assert.ok(href === "/admin/posts" || href === "/admin/pages", `Unexpected header icon on ${href}`);
}
// Check WordPress official admin-page SVG path on Pages
const pagesSvg = headerIcons.find((s) => s.parentNode.getAttribute("data-nav-href") === "/admin/pages");
assert.ok(pagesSvg, "Expected WordPress Pages icon");
assert.equal(pagesSvg.children.length, 1);
assert.equal(pagesSvg.children[0].getAttribute("d"), "M6 15V2h10v13H6zm-1 1h8v2H3V5h2v11z");

const navLinks = navMount.querySelectorAll("a[data-nav-href]");
assert.ok(navLinks.length >= 8, "Expected rendered admin navigation links");
for (const link of navLinks) {
  assert.ok(link.textContent.trim().length > 0, "Nav link must have visible text");
  assert.equal(link.classList.contains("cms-topnav-icon"), false);
}

// 3b. Right header utility actions: search, fullscreen, and bell icons next to avatar
const searchBtn = makeFakeElement("button");
searchBtn.setAttribute("id", "cms-search-toggle");
byId.set("cms-search-toggle", searchBtn);
const fullBtn = makeFakeElement("button");
fullBtn.setAttribute("id", "cms-fullscreen-toggle");
byId.set("cms-fullscreen-toggle", fullBtn);
const notifBtn = makeFakeElement("button");
notifBtn.setAttribute("id", "cms-notif-btn");
byId.set("cms-notif-btn", notifBtn);
const notifDrop = makeFakeElement("ul");
notifDrop.setAttribute("id", "cms-notif-dropdown");
byId.set("cms-notif-dropdown", notifDrop);
const searchBackdrop = makeFakeElement("section");
searchBackdrop.setAttribute("id", "cms-search-backdrop");
searchBackdrop.setAttribute("hidden", "");
byId.set("cms-search-backdrop", searchBackdrop);
const searchDialog = makeFakeElement("section");
searchDialog.setAttribute("id", "cms-search-dialog");
byId.set("cms-search-dialog", searchDialog);
const searchInput = makeFakeElement("input");
searchInput.setAttribute("id", "cms-admin-search");
byId.set("cms-admin-search", searchInput);
const searchResults = makeFakeElement("ul");
searchResults.setAttribute("id", "cms-search-results");
byId.set("cms-search-results", searchResults);

navMod.mountUtilityActions("admin", () => {});
for (const [label, btn] of [["search", searchBtn], ["fullscreen", fullBtn], ["bell", notifBtn]]) {
  const icons = btn.querySelectorAll("svg, img");
  assert.equal(icons.length, 1, `Expected 1 SVG icon inside ${label} utility button`);
  assert.equal(icons[0].getAttribute("aria-hidden"), "true");
}
assert.equal(countDivsInTree(searchBackdrop), 0);
searchBtn.click();
assert.equal(searchBackdrop.hasAttribute("hidden"), false, "Search button must open search dialog");
globalThis.document.dispatchEvent({ type: "keydown", key: "Escape", preventDefault() {} });
assert.equal(searchBackdrop.hasAttribute("hidden"), true, "Escape must close search dialog");
assert.equal(activeEl, searchBtn, "Escape must restore focus to search button");

// Viewer header nav must show 0 icons
navMod.mountHorizontalNav("/admin/profile", "viewer", null);
assert.equal(navMount.querySelectorAll("svg, img").length, 0, "Viewer header nav must have 0 icons");
navMod.mountHorizontalNav("/admin/profile", "admin", null);

// Test "More" dropdown keyboard behavior (ArrowDown opens + focuses first, Escape closes + restores focus)
const moreBtn = navMount.children[0].children[0].children.find((li) => li.children.some((c) => c.tagName === "BUTTON")).children[0];
const dropUl = moreBtn.parentNode.children[1];
moreBtn.focus();
moreBtn.dispatchEvent({ type: "keydown", key: "ArrowDown", preventDefault() {} });
assert.equal(dropUl.classList.contains("open"), true, "ArrowDown on More button must open dropdown");
assert.equal(dropUl.getAttribute("aria-hidden"), "false");
assert.equal(activeEl, dropUl.children[0].children[0], "ArrowDown must focus first dropdown link");

dropUl.dispatchEvent({ type: "keydown", key: "Escape", preventDefault() {}, stopPropagation() {} });
assert.equal(dropUl.classList.contains("open"), false, "Escape must close More dropdown");
assert.equal(dropUl.getAttribute("aria-hidden"), "true");
assert.equal(activeEl, moreBtn, "Escape must restore focus to More button");

// Urbanist font tokens check in tokens.css & admin-ui.css
const tokensCss = fs.readFileSync("public/grex/tokens.css", "utf8");
assert.ok(/--grex-font-sans:\s*"Urbanist"/.test(tokensCss), "tokens.css must define --grex-font-sans with Urbanist");
assert.ok(/--grex-font-display:\s*"Urbanist"/.test(tokensCss), "tokens.css must define --grex-font-display with Urbanist");
const adminUiCssCheck = fs.readFileSync("public/admin/admin-ui.css", "utf8");
assert.ok(/--grex-font-sans:\s*"Urbanist"/.test(adminUiCssCheck), "admin-ui.css must define --grex-font-sans with Urbanist");
assert.ok(/--grex-font-display:\s*"Urbanist"/.test(adminUiCssCheck), "admin-ui.css must define --grex-font-display with Urbanist");

// 4. Universal Profile Studio DOM, XSS-safety & keyboard audit
const profileSig = signal({
  user: {
    id: 42,
    email: "reader@example.com",
    display_name: '<img src=x onerror="alert(1)"> Jane',
    role: "viewer",
    email_verified: 1,
    created_at: "2026-11-01T12:00:00Z",
    updated_at: "2026-11-18T12:00:00Z",
    last_login_at: "2026-11-19T08:30:00Z",
  },
  has_password: true,
  sessions: [
    { id: "s1", user_agent: "Mozilla/5.0 Chrome/120.0", created_at: "2026-11-18T08:00:00Z", last_seen_at: "2026-11-19T08:30:00Z", expires_at: "2026-11-26T08:30:00Z", current: true },
    { id: "s2", user_agent: "Mozilla/5.0 (iPhone) Safari/605.1", created_at: "2026-11-17T08:00:00Z", last_seen_at: "2026-11-17T09:00:00Z", expires_at: "2026-11-24T08:30:00Z", current: false },
  ],
  oauth_accounts: [],
  capabilities: [
    { key: "admin:access", label: "Open the admin area", granted: false },
    { key: "entries:read", label: "Read entries", granted: false },
  ],
  stats: { entries_total: 0, entries_published: 0, entries_draft: 0, session_count: 2 },
});

const mockApi = {
  patch: async (_p, body) => ({ user: { id: 42, email: "reader@example.com", display_name: body.display_name, role: "viewer" } }),
  post: async () => ({ ok: true }),
};
const view = profileMod.createProfileView(mockApi, { profile: profileSig });
assert.equal(countDivsInTree(view.element), 0, "Profile view must contain 0 <div> tags");
assert.equal(divCount, 0, "Expected global divCount === 0");
assert.equal(innerHTMLWriteCount, 0, "Expected innerHTMLWriteCount === 0");

// Verify removed cms-role-badge / cms-identity-meta, role line above email, verified checkmark, and Edit pencil icons
const profileSrc = fs.readFileSync("public/admin/profile.js", "utf8");
assert.equal(profileSrc.includes("cms-role-badge"), false, "cms-role-badge must be removed from profile.js");
assert.equal(profileSrc.includes("cms-identity-meta"), false, "cms-identity-meta must be removed from profile.js");
assert.ok(profileSrc.includes("cms-identity-role"), "profile.js must render .cms-identity-role above email");
const profileSvgs = view.element.querySelectorAll("svg, img");
const checkSvgs = profileSvgs.filter((s) => (s.getAttribute("class") || "").includes("cms-verified-check"));
assert.equal(checkSvgs.length, 1, "Expected 1 verified checkmark SVG next to email");
assert.equal(checkSvgs[0].hasAttribute("hidden"), false, "Verified checkmark must be visible for email_verified=1");
const pencilSvgs = profileSvgs.filter((s) => (s.getAttribute("class") || "").includes("cms-btn-icon"));
assert.equal(pencilSvgs.length, 2, "Expected pencil SVG icons inside both Edit action buttons");
for (const svg of pencilSvgs) {
  assert.equal(svg.parentNode.tagName, "BUTTON");
  assert.ok((svg.parentNode.getAttribute("class") || "").includes("cms-profile-card-action"));
  assert.equal(svg.parentNode.textContent, "Edit");
}

// Vertical tablist keyboard ArrowDown / ArrowUp + click switching across all 6 dedicated tabpanels
const expectedTabs = ["overview", "security", "notifications", "billing", "export", "delete"];
const tablist = view.tabs.element.children[0];
assert.equal(tablist.tagName, "NAV", "Vertical tablist must use semantic <nav>");
assert.equal(tablist.getAttribute("role"), "tablist");
assert.equal(tablist.getAttribute("aria-orientation"), "vertical");
assert.equal(tablist.children.length, 6, "Expected 6 profile tabs");
for (let i = 0; i < expectedTabs.length; i += 1) {
  const btn = tablist.children[i];
  assert.equal(btn.tagName, "BUTTON", "Sidebar tab item must be a <button role='tab'>");
  assert.equal(btn.getAttribute("role"), "tab");
  assert.equal(btn.getAttribute("id"), `profile-tabs-tab-${expectedTabs[i]}`);
  assert.equal(btn.querySelectorAll("svg, img").length, 1, `Tab ${btn.textContent} must include 1 SVG icon`);
}
assert.equal(profileSrc.includes("IntersectionObserver"), false, "Single-page IntersectionObserver must be removed");
assert.equal(profileSrc.includes('href: `#${sec.id}`'), false, "Single-page anchor links must be removed");

const panelsById = new Map(
  expectedTabs.map((id) => [id, view.tabs.element.querySelector(`#profile-tabs-panel-${id}`)])
);
const assertOnlyPanelVisible = (visibleId, contextMsg) => {
  for (const id of expectedTabs) {
    const p = panelsById.get(id);
    assert.ok(p, `Missing tabpanel #profile-tabs-panel-${id}`);
    if (id === visibleId) {
      assert.equal(p.hasAttribute("hidden"), false, `${contextMsg}: ${id} panel must be visible`);
    } else {
      assert.equal(p.hasAttribute("hidden"), true, `${contextMsg}: ${id} panel must be hidden`);
    }
  }
};

assert.equal(view.activeId.peek(), "overview");
assertOnlyPanelVisible("overview", "Initial load");

tablist.dispatchEvent({ type: "keydown", key: "ArrowDown", preventDefault() {} });
assert.equal(view.activeId.peek(), "security", "ArrowDown must switch to Security tab");
assertOnlyPanelVisible("security", "After ArrowDown");
tablist.dispatchEvent({ type: "keydown", key: "ArrowUp", preventDefault() {} });
assert.equal(view.activeId.peek(), "overview", "ArrowUp must switch back to My Profile tab");
assertOnlyPanelVisible("overview", "After ArrowUp");

for (const [idx, expectedId] of [[2, "notifications"], [3, "billing"], [4, "export"], [5, "delete"]]) {
  tablist.children[idx].click();
  assert.equal(view.activeId.peek(), expectedId, `Clicking tab ${idx} must activate ${expectedId}`);
  assertOnlyPanelVisible(expectedId, `Clicking tab ${expectedId}`);
}
tablist.children[0].click();
assert.equal(view.activeId.peek(), "overview", "Clicking My Profile tab must reactivate My Profile");
assertOnlyPanelVisible("overview", "Returning to My Profile");

// Verify Security tab keeps 2-column layout (Password + Trusted Devices side-by-side in .cms-profile-grid, no cms-span-2)
const securityPanel = panelsById.get("security");
const securityGrid = securityPanel.children[0];
assert.ok(securityGrid && (securityGrid.getAttribute("class") || "").includes("cms-profile-grid"), "Security tabpanel must use .cms-profile-grid");
const passwordCard = securityPanel.querySelector("#profile-password");
const sessionsCard = securityPanel.querySelector("#profile-sessions");
assert.ok(passwordCard, "Security tabpanel must contain #profile-password");
assert.ok(sessionsCard, "Security tabpanel must contain #profile-sessions");
assert.equal((passwordCard.getAttribute("class") || "").includes("cms-span-2"), false, "Security #profile-password must stay 1-column (no cms-span-2)");
assert.equal((sessionsCard.getAttribute("class") || "").includes("cms-span-2"), false, "Security #profile-sessions must stay 1-column (no cms-span-2)");

// Verify all expected cards exist in their dedicated tabpanels
const overviewPanel = panelsById.get("overview");
for (const [panel, cardId] of [
  [overviewPanel, "profile-personal"],
  [overviewPanel, "profile-activity"],
  [overviewPanel, "profile-methods"],
  [overviewPanel, "profile-permissions"],
  [securityPanel, "profile-password"],
  [securityPanel, "profile-sessions"],
  [panelsById.get("notifications"), "profile-notif-alerts"],
  [panelsById.get("billing"), "profile-billing-plan"],
  [panelsById.get("billing"), "profile-billing-invoices"],
  [panelsById.get("export"), "profile-data-export"],
  [panelsById.get("delete"), "profile-delete-account"],
]) {
  assert.ok(panel.querySelector(`#${cardId}`), `Expected card #${cardId} inside its dedicated tabpanel`);
}

// Verify click-to-expand + Enter/Space keyboard expand + ignoring clicks on interactive children
assert.ok(Array.isArray(view.cards) && view.cards.length >= 11, "Expected expandable profile cards");
const personalCard = overviewPanel.querySelector("#profile-personal");
assert.equal(personalCard.getAttribute("aria-expanded"), "false");
assert.equal(personalCard.getAttribute("data-expanded"), "false");
assert.equal(personalCard.getAttribute("tabindex"), "0");
personalCard.click();
assert.equal(personalCard.getAttribute("aria-expanded"), "true", "Clicking card must expand height (aria-expanded=true)");
assert.equal(personalCard.getAttribute("data-expanded"), "true");
personalCard.dispatchEvent({ type: "keydown", key: "Enter", target: personalCard, preventDefault() {} });
assert.equal(personalCard.getAttribute("aria-expanded"), "false", "Pressing Enter on card must collapse it");
personalCard.dispatchEvent({ type: "keydown", key: " ", target: personalCard, preventDefault() {} });
assert.equal(personalCard.getAttribute("aria-expanded"), "true", "Pressing Space on card must expand it");

const personalEditBtn = personalCard.querySelector("button");
assert.ok(personalEditBtn, "Expected Edit button inside Personal Information card");
personalCard.dispatchEvent({ type: "click", target: personalEditBtn, preventDefault() {} });
assert.equal(personalCard.getAttribute("aria-expanded"), "true", "Clicking interactive Edit button must NOT toggle card expansion");
personalCard.click();
assert.equal(personalCard.getAttribute("aria-expanded"), "false");

// Verify Change button on Password card opens form & expands the card automatically
tablist.children[1].click();
const passwordChangeBtn = passwordCard.querySelector("button");
assert.ok(passwordChangeBtn, "Expected Change button inside Password card");
assert.equal(passwordCard.getAttribute("aria-expanded"), "false");
passwordChangeBtn.click();
assert.equal(passwordCard.getAttribute("aria-expanded"), "true", "Opening Password form must automatically expand Password card");
tablist.children[0].click();

// Verify dispose() compatibility with admin.js
assert.equal(typeof view.tabs.dispose, "function", "view.tabs.dispose must remain callable for admin.js cleanup");
view.tabs.dispose();

// Modal open + Escape focus restoration
const editBtn = view.element.querySelector(".cms-identity-card button") || profileMod.IdentitySummary({ profile: profileSig, onEdit: () => view.editOpen.set(true) }).editButton.element;
editBtn.focus();
view.editOpen.set(true);
assert.equal(view.dialog.element.open, true, "Edit Personal Information modal must open");
view.dialog.element.dispatchEvent({ type: "keydown", key: "Escape", preventDefault() {} });
assert.equal(view.dialog.element.open, false, "Escape must close Edit modal");
assert.equal(activeEl, editBtn, "Escape must restore focus to triggering button");

// Password strength scoring check
assert.equal(profileMod.scorePassword("").label, "Not set");
assert.equal(profileMod.scorePassword("abcdefghij").label, "Weak");
assert.equal(profileMod.scorePassword("StrongPass!123").label, "Strong");

// Theme Light/Dark controller + sun/moon icon toggle check
const themeToggleBtn = makeFakeElement("button");
themeToggleBtn.setAttribute("id", "cms-theme-toggle");
themeMod.wireThemeToggle(themeToggleBtn);
assert.equal(themeMod.applyAdminTheme("light"), "light");
assert.equal(docRoot.getAttribute("data-cms-theme"), "light");
assert.equal(themeToggleBtn.querySelectorAll("svg, img").length, 1, "Theme toggle must render moon icon SVG");
assert.equal(themeToggleBtn.textContent, "", "Theme toggle must be icon-only");
assert.equal(themeMod.applyAdminTheme("dark"), "dark");
assert.equal(docRoot.getAttribute("data-cms-theme"), "dark");
assert.equal(themeToggleBtn.querySelectorAll("svg, img").length, 1, "Theme toggle must render sun icon SVG");
assert.equal(themeToggleBtn.textContent, "", "Theme toggle must be icon-only");

// CSS polish rules check (.cms-icon-btn rgb(0 0 0 / 8%), 80px border-radius, glow removed, vertical tablist, scrollbar-free expandable cards, 1.825rem brand)
assert.ok(/background:\s*rgb\(0 0 0 \/ 8%\)/.test(adminUiCssCheck), ".cms-icon-btn must use background: rgb(0 0 0 / 8%)");
assert.ok(/\.cms-fleetyu-header\s+:focus-visible[\s\S]*border-radius:\s*80px/.test(adminUiCssCheck), ".cms-fleetyu-header :focus-visible must set border-radius: 80px");
assert.equal(/\.cms-profile-card\s*\{[^}]*--ui-panel-glow/.test(adminUiCssCheck), false, "Glow must be removed from .cms-profile-card");
assert.equal(/\.cms-profile-grid[^{]*\.cms-profile-card[^{]*\{[^}]*overflow-y:\s*(auto|scroll)/s.test(adminUiCssCheck), false, "Profile cards must NOT use overflow-y: auto or scroll");
assert.ok(/\.cms-profile-card-expandable\s*\{[^}]*max-height:\s*312px;[^}]*overflow:\s*hidden;/s.test(adminUiCssCheck), ".cms-profile-card-expandable must use max-height: 312px and overflow: hidden");
assert.ok(/\.cms-profile-card-expandable\[data-overflows="true"\]\[data-expanded="false"\]::after/.test(adminUiCssCheck), "Expandable overflowing collapsed cards must render bottom fade indicator");
assert.ok(/\.cms-profile-tabs\s*>\s*\[role="tablist"\]/.test(adminUiCssCheck), "admin-ui.css must style .cms-profile-tabs > [role=\"tablist\"]");
assert.ok(/\.cms-profile-tabs\s+\[role="tab"\]\[aria-selected="true"\]\s*\{[^}]*linear-gradient\(90deg,\s*#d18700\s+0%,\s*#61022e\s+100%\)/s.test(adminUiCssCheck), "Active vertical tab must use gold-to-plum gradient");
assert.equal(adminUiCssCheck.includes(".cms-profile-sidebar"), false, "Sticky anchor .cms-profile-sidebar rules must be removed");
assert.equal(adminUiCssCheck.includes(".cms-profile-section"), false, "Single-page .cms-profile-section rules must be removed");
assert.ok(adminUiCssCheck.includes("linear-gradient(180deg, #d18700 0%, #61022e 100%)"), "Header gradient must match exact stop values");
assert.ok(adminUiCssCheck.includes("rgba(85, 244, 218, 0.14)"), "Header border-bottom must match exact color");
assert.ok(adminUiCssCheck.includes("0 8px 28px rgba(0, 0, 0, 0.35)"), "Header box-shadow must match exact value");

// Account cards must reflect the current user's profile, including zero counts.
const fields = new Map(view.element.querySelectorAll("*")
  .filter((li) => li.classList.contains("cms-field"))
  .map((li) => [li.children[0].textContent, li.children[1].textContent]));
assert.equal(fields.get("Email address"), profileSig.peek().user.email);
assert.equal(fields.get("Published entries"), String(profileSig.peek().stats.entries_published));
assert.equal(fields.get("Signed-in devices"), String(profileSig.peek().stats.session_count));
assert.ok(adminUiCssCheck.includes("background: #2b1a24;"), "Secondary / Edit buttons must use #2b1a24 dark plum fill");
assert.ok(/\.cms-brand[\s\S]*?font-size:\s*1\.825rem;/.test(adminUiCssCheck), ".cms-brand must use 1.825rem font-size");
assert.ok(/\.cms-page-head h1[\s\S]*?font-size:\s*1\.5rem;/.test(adminUiCssCheck), ".cms-page-head h1 must use 1.5rem font-size");
for (const av of ["avatar-01.png", "avatar-02.png", "avatar-03.png", "avatar-04.png", "avatar-05.png", "avatar-06.png"]) {
  assert.ok(fs.existsSync(`public/admin/avatars/${av}`), `Missing local avatar asset public/admin/avatars/${av}`);
}

// 5. Grex auditAccessibility check
const treeAudit = auditAccessibility({
  type: "Section",
  children: [
    { type: "Heading", props: { level: 1, text: "My Profile" }, styles: { color: "#12201d", backgroundColor: "#f3f7f6" } },
    { type: "Text", props: { text: "Manage your account identity, security, and preferences." }, styles: { color: "#4a5a57", backgroundColor: "#ffffff" } },
    { type: "Button", props: { text: "Save changes" }, styles: { color: "#ffffff", backgroundColor: "#1c6b5f" } },
    { type: "Link", props: { href: "/admin/profile", text: "Profile" }, styles: { color: "#12201d", backgroundColor: "#ffffff" } },
  ],
});
assert.equal(treeAudit.ok, true, `Grex auditAccessibility failed: ${JSON.stringify(treeAudit.issues)}`);

// 6. Dynamic Light & Dark WCAG AA >= 4.5:1 Contrast Verification parsed directly from admin-ui.css
const uiCss = fs.readFileSync("public/admin/admin-ui.css", "utf8");
function extractCssTokens(selectorPattern) {
  const m = uiCss.match(selectorPattern);
  assert.ok(m, `Missing token block for ${selectorPattern}`);
  const tokens = {};
  for (const line of m[1].split("\n")) {
    const kv = line.match(/^\s*(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;/);
    if (kv) tokens[kv[1]] = kv[2];
  }
  return tokens;
}

const darkTokens = extractCssTokens(/:root,\s*:root\[data-cms-theme="dark"\]\s*\{([\s\S]*?)\n\}/);
const lightTokens = extractCssTokens(/:root\[data-cms-theme="light"\]\s*\{([\s\S]*?)\n\}/);

let contrastPairsVerified = 0;
for (const [modeName, t] of [["dark", darkTokens], ["light", lightTokens]]) {
  const pairs = [
    [`${modeName}:ink-on-bg`, t["--ui-ink"], t["--ui-bg"]],
    [`${modeName}:ink-on-surface`, t["--ui-ink"], t["--ui-surface"]],
    [`${modeName}:ink-on-surface-2`, t["--ui-ink"], t["--ui-surface-2"]],
    [`${modeName}:muted-on-bg`, t["--ui-muted"], t["--ui-bg"]],
    [`${modeName}:muted-on-surface`, t["--ui-muted"], t["--ui-surface"]],
    [`${modeName}:muted-on-surface-2`, t["--ui-muted"], t["--ui-surface-2"]],
    [`${modeName}:btn-ink-on-btn-bg`, t["--ui-btn-ink"], t["--ui-btn-bg"]],
    [`${modeName}:btn-ink-on-btn-hover`, t["--ui-btn-ink"], t["--ui-btn-bg-hover"]],
    [`${modeName}:badge-ink-on-badge-bg`, t["--ui-badge-ink"], t["--ui-badge-bg"]],
    [`${modeName}:pill-ink-on-pill-bg`, t["--ui-pill-ink"], t["--ui-pill-bg"]],
    [`${modeName}:avatar-ink-on-avatar-bg`, t["--ui-avatar-ink"], t["--ui-avatar-bg"]],
    [`${modeName}:danger-on-surface`, t["--ui-danger"], t["--ui-surface"]],
    [`${modeName}:ok-on-surface`, t["--ui-ok"], t["--ui-surface"]],
    [`${modeName}:warn-on-surface`, t["--ui-warn"], t["--ui-surface"]],
    [`${modeName}:hdr-ink-on-hdr-solid`, t["--hdr-ink"], t["--hdr-solid"]],
    [`${modeName}:hdr-soft-on-hdr-solid`, t["--hdr-ink-soft"], t["--hdr-solid"]],
    [`${modeName}:hdr-menu-ink-on-hdr-menu-bg`, t["--hdr-menu-ink"], t["--hdr-menu-bg"]],
    [`${modeName}:accent-on-surface`, t["--ui-accent"], t["--ui-surface"]],
    [`${modeName}:focus-on-bg`, t["--ui-focus"], t["--ui-bg"]],
  ];
  if (modeName === "dark") {
    pairs.push(["header text on gradient halo", t["--hdr-ink-soft"], t["--ui-text-halo"]],
      ["button text on gradient halo", t["--ui-btn-ink"], t["--ui-text-halo"]]);
  }
  for (const [label, fg, bg] of pairs) {
    assert.ok(fg && bg, `Missing token color for ${label}`);
    const ratio = computeContrastRatio(fg, bg);
    assert.ok(ratio >= 4.5, `WCAG AA contrast failed for ${label} (${fg} on ${bg}): ${ratio.toFixed(2)} < 4.50`);
    contrastPairsVerified += 1;
  }
}

console.log(
  JSON.stringify({
    ok: true,
    divCount,
    innerHTMLWriteCount,
    headerIcons: headerIcons.length,
    rolesVerified: ["admin", "editor", "author", "viewer"],
    contrastPairsVerified,
    auditAccessibilityPassed: treeAudit.ok,
    templatesChecked: htmlTargets.length,
    keyboardFocusRestored: true,
  })
);
