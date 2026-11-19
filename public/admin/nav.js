/**
 * GrabLab CMS v1.5.0 — Header Navigation (Pure Grex JS v1.0.0 hygiene)
 *
 * Design contract:
 *  - Semantic <nav><ul><li><a> tree, zero wrapper <div>, zero innerHTML writes, zero dynamic eval.
 *  - Only `Posts` (WordPress dashicons-admin-post thumbtack/pushpin) and `Pages`
 *    (WordPress dashicons-admin-page stacked sheets) render 16x16 inline SVG icons (`aria-hidden="true"`).
 *    Other navigation links use text. Utility buttons have accessible names.
 *  - Dashicons license: see Dashicons-LICENSE.txt (WordPress/dashicons).
 *  - Keyboard: Tab / Shift+Tab traverse links; Enter / Space activate the "More" disclosure button;
 *    ArrowDown/ArrowUp/Home/End move within the open menu; Escape closes it and restores focus.
 */
import { setSafeText } from "../grex/grex.js";

const SVG_NS = "http://www.w3.org/2000/svg";

const HEADER_ICON_PATHS = Object.freeze({
  posts: [
    "M13.3 2.3a1 1 0 0 0-1.4 0l-1.3 1.3c-.4.4-.5 1-.3 1.5L7.6 7.8c-1.1-.4-2.4-.2-3.3.7l-.5.5 3.6 3.6-4.7 4.7-.4 1.4 1.4-.4 4.7-4.7 3.6 3.6.5-.5c.9-.9 1.1-2.2.7-3.3l2.7-2.7c.5.2 1.1.1 1.5-.3l1.3-1.3a1 1 0 0 0 0-1.4l-5.4-5.4z",
  ],
  pages: [
    "M6 15V2h10v13H6zm-1 1h8v2H3V5h2v11z",
  ],
});

const UTILITY_ICON_SPECS = Object.freeze({
  search: [
    { tag: "circle", attrs: { cx: "11", cy: "11", r: "7" } },
    { tag: "path", attrs: { d: "m20 20-3.5-3.5" } },
  ],
  fullscreen: [
    { tag: "path", attrs: { d: "M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" } },
  ],
  fullscreenExit: [
    { tag: "path", attrs: { d: "M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" } },
  ],
  bell: [
    { tag: "path", attrs: { d: "M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" } },
    { tag: "path", attrs: { d: "M13.73 21a2 2 0 0 1-3.46 0" } },
  ],
});

export function createUtilityIcon(kind) {
  const shapes = UTILITY_ICON_SPECS[kind];
  if (!shapes) return null;
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
  for (const spec of shapes) {
    const node = document.createElementNS(SVG_NS, spec.tag);
    for (const [k, v] of Object.entries(spec.attrs)) {
      node.setAttribute(k, v);
    }
    svg.appendChild(node);
  }
  return svg;
}

function replaceBtnIcon(btn, kind) {
  if (!btn) return;
  while (btn.firstChild) btn.removeChild(btn.firstChild);
  const icon = createUtilityIcon(kind);
  if (icon) btn.appendChild(icon);
}

export function createHeaderIcon(kind) {
  const paths = HEADER_ICON_PATHS[kind];
  if (!paths) return null;
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 20 20");
  svg.setAttribute("width", "16");
  svg.setAttribute("height", "16");
  svg.setAttribute("fill", "currentColor");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.setAttribute("class", "cms-nav-icon");
  for (const d of paths) {
    const pathEl = document.createElementNS(SVG_NS, "path");
    pathEl.setAttribute("d", d);
    svg.appendChild(pathEl);
  }
  return svg;
}

export function isPathMatch(path, href) {
  const cleanPath = (path || "/admin").replace(/\/+$/, "") || "/admin";
  if (href === "/admin") {
    return cleanPath === "/admin";
  }
  if (href === "/admin/entries") {
    return cleanPath === "/admin/entries";
  }
  return cleanPath === href || cleanPath.startsWith(`${href}/`);
}

/**
 * Pure data model for the header menu. Only `Posts` and `Pages` carry a `kind` icon key.
 */
export function buildNavModel(role, authorEnabled = false) {
  const profile = { href: "/admin/profile", text: "Profile" };
  if (role !== "admin" && role !== "editor" && role !== "author") {
    return { primary: [profile], more: [] };
  }
  const primary = [
    { href: "/admin", text: "Dashboard" },
    { href: "/admin/posts", text: "Posts", icon: "posts" },
    { href: "/admin/media", text: "Media" },
    { href: "/admin/pages", text: "Pages", icon: "pages" },
    { href: "/admin/entries", text: "All Entries" },
  ];
  if (role === "admin" || role === "editor") {
    primary.push({ href: "/admin/menus", text: "Menus" });
    primary.push({ href: "/admin/taxonomies", text: "Taxonomies" });
    primary.push({ href: "/admin/store", text: "Commerce" });
  }
  primary.push(profile);

  const more = [];
  if (role === "admin" || role === "editor") {
    more.push({ href: "/admin/store/shoppers", text: "Shoppers" });
  }
  if (role === "admin") {
    more.push({ href: "/admin/themes", text: "Themes & Design" });
    more.push({ href: "/admin/types", text: "Content Types" });
    more.push({ href: "/admin/settings", text: "Settings & Users" });
  }
  if (authorEnabled) {
    more.push({ href: "/admin/author", text: "Author Studio" });
  }
  return { primary, more };
}

export function mountHorizontalNav(initialPath, role, api) {
  const mount = document.getElementById("admin-nav-mount");
  if (!mount) {
    return { setActivePath: () => {}, closeMenus: () => {} };
  }

  let currentPath = initialPath;
  let authorEnabledState = initialPath.startsWith("/admin/author");
  let moreDropdownEl = null;
  let moreBtnEl = null;

  const setMoreOpen = (open, restoreFocus = false) => {
    if (!moreDropdownEl || !moreBtnEl) return;
    moreDropdownEl.classList.toggle("open", open);
    moreDropdownEl.setAttribute("aria-hidden", open ? "false" : "true");
    moreBtnEl.setAttribute("aria-expanded", open ? "true" : "false");
    if (!open && restoreFocus) {
      moreBtnEl.focus();
    }
  };

  const closeMenus = () => {
    setMoreOpen(false);
    const mobileBtn = document.getElementById("cms-mobile-nav-toggle");
    if (mobileBtn) {
      mount.classList.remove("mobile-open");
      mobileBtn.setAttribute("aria-expanded", "false");
    }
  };

  const updateActiveStates = () => {
    const links = mount.querySelectorAll("a[data-nav-href]");
    let moreHasActive = false;
    for (const a of links) {
      const href = a.getAttribute("data-nav-href") || "";
      const active = isPathMatch(currentPath, href);
      a.classList.toggle("active", active);
      if (active) {
        a.setAttribute("aria-current", "page");
        if (a.classList.contains("cms-topnav-dropdown-link")) {
          moreHasActive = true;
        }
      } else {
        a.removeAttribute("aria-current");
      }
    }
    if (moreBtnEl) {
      moreBtnEl.classList.toggle("active", moreHasActive);
    }
  };

  const makeLink = (item, className) => {
    const a = document.createElement("a");
    a.href = item.href;
    a.className = className;
    a.setAttribute("data-nav-href", item.href);
    if (item.icon) {
      const svg = createHeaderIcon(item.icon);
      if (svg) a.appendChild(svg);
    }
    const label = document.createElement("span");
    setSafeText(label, item.text);
    a.appendChild(label);
    return a;
  };

  const renderNav = () => {
    while (mount.firstChild) {
      mount.removeChild(mount.firstChild);
    }
    moreDropdownEl = null;
    moreBtnEl = null;

    const model = buildNavModel(role, authorEnabledState);

    const navWrap = document.createElement("nav");
    navWrap.className = "cms-topnav-nav";
    navWrap.setAttribute("aria-label", "Admin horizontal navigation");

    const ulEl = document.createElement("ul");
    ulEl.className = "cms-topnav-list";

    for (const item of model.primary) {
      const liEl = document.createElement("li");
      liEl.className = "cms-topnav-item";
      liEl.appendChild(makeLink(item, "cms-topnav-link"));
      ulEl.appendChild(liEl);
    }

    if (model.more.length > 0) {
      const moreLi = document.createElement("li");
      moreLi.className = "cms-topnav-item";

      const moreBtn = document.createElement("button");
      moreBtn.type = "button";
      moreBtn.className = "cms-topnav-more-btn";
      moreBtn.setAttribute("aria-haspopup", "true");
      moreBtn.setAttribute("aria-expanded", "false");
      setSafeText(moreBtn, "More");

      const dropUl = document.createElement("ul");
      dropUl.className = "cms-topnav-dropdown";
      dropUl.setAttribute("aria-hidden", "true");
      dropUl.setAttribute("aria-label", "More admin sections");

      const dropLinks = [];
      for (const mItem of model.more) {
        const subLi = document.createElement("li");
        const subA = makeLink(mItem, "cms-topnav-dropdown-link");
        dropLinks.push(subA);
        subLi.appendChild(subA);
        dropUl.appendChild(subLi);
      }

      moreBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        setMoreOpen(!dropUl.classList.contains("open"));
      });

      moreBtn.addEventListener("keydown", (e) => {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setMoreOpen(true);
          if (dropLinks[0]) dropLinks[0].focus();
        }
      });

      dropUl.addEventListener("keydown", (e) => {
        const idx = dropLinks.indexOf(document.activeElement);
        if (e.key === "ArrowDown") {
          e.preventDefault();
          dropLinks[(idx + 1) % dropLinks.length].focus();
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          dropLinks[(idx - 1 + dropLinks.length) % dropLinks.length].focus();
        } else if (e.key === "Home") {
          e.preventDefault();
          dropLinks[0].focus();
        } else if (e.key === "End") {
          e.preventDefault();
          dropLinks[dropLinks.length - 1].focus();
        } else if (e.key === "Escape") {
          e.preventDefault();
          e.stopPropagation();
          setMoreOpen(false, true);
        } else if (e.key === "Tab") {
          const leavingForward = !e.shiftKey && idx === dropLinks.length - 1;
          const leavingBack = e.shiftKey && idx === 0;
          if (leavingForward || leavingBack) {
            setMoreOpen(false);
          }
        }
      });

      moreLi.appendChild(moreBtn);
      moreLi.appendChild(dropUl);
      ulEl.appendChild(moreLi);

      moreDropdownEl = dropUl;
      moreBtnEl = moreBtn;
    }

    navWrap.appendChild(ulEl);
    mount.appendChild(navWrap);
    updateActiveStates();
  };

  renderNav();

  const mobileBtn = document.getElementById("cms-mobile-nav-toggle");
  if (mobileBtn) {
    mobileBtn.addEventListener("click", () => {
      const open = mount.classList.toggle("mobile-open");
      mobileBtn.setAttribute("aria-expanded", String(open));
    });
  }

  document.addEventListener("click", (e) => {
    if (moreDropdownEl && moreBtnEl && !moreDropdownEl.contains(e.target) && !moreBtnEl.contains(e.target)) {
      setMoreOpen(false);
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const wasOpen = moreDropdownEl && moreDropdownEl.classList.contains("open");
    const mobileOpen = mount.classList.contains("mobile-open");
    closeMenus();
    if (mobileOpen && mobileBtn) {
      mobileBtn.focus();
    } else if (wasOpen && moreBtnEl) {
      moreBtnEl.focus();
    }
  });

  if (api && (role === "admin" || role === "editor" || role === "author")) {
    api
      .get("/api/admin/author/status")
      .then((res) => {
        const enabled = Boolean(res && res.enabled);
        if (enabled !== authorEnabledState) {
          authorEnabledState = enabled;
          renderNav();
        }
      })
      .catch(() => {});
  }

  return {
    setActivePath(nextPath) {
      currentPath = nextPath;
      updateActiveStates();
    },
    closeMenus,
  };
}

function getSearchRoutes(role) {
  const routes = [
    { label: "Dashboard", keys: ["dashboard", "overview", "home"], path: "/admin" },
    { label: "Posts", keys: ["post", "posts", "blog"], path: "/admin/posts" },
    { label: "Media Library", keys: ["media", "image", "upload", "files"], path: "/admin/media" },
    { label: "Pages", keys: ["page", "pages"], path: "/admin/pages" },
    { label: "All Entries", keys: ["entry", "entries", "all"], path: "/admin/entries" },
    { label: "My Profile", keys: ["profile", "account", "password", "security", "preferences"], path: "/admin/profile" },
  ];
  if (role === "admin" || role === "editor") {
    routes.push(
      { label: "Navigation Menus", keys: ["menu", "menus", "nav"], path: "/admin/menus" },
      { label: "Taxonomies & Terms", keys: ["taxonomy", "taxonomies", "category", "tag"], path: "/admin/taxonomies" },
      { label: "Commerce", keys: ["commerce", "store", "shop", "product", "order", "coupon"], path: "/admin/store" },
      { label: "Shoppers Directory", keys: ["shopper", "shoppers", "directory", "customers"], path: "/admin/store/shoppers" }
    );
  }
  if (role === "admin") {
    routes.push(
      { label: "Themes & Design", keys: ["theme", "themes", "design"], path: "/admin/themes" },
      { label: "Content Types", keys: ["type", "types", "field", "fields"], path: "/admin/types" },
      { label: "Settings & Users", keys: ["setting", "settings", "user", "users", "oauth"], path: "/admin/settings" }
    );
  }
  if (role === "admin" || role === "editor" || role === "author") {
    routes.push({ label: "Author Studio", keys: ["author", "book", "books", "series", "radar"], path: "/admin/author" });
  }
  return routes;
}

/**
 * Mount search, fullscreen, and notification utility icons + interactions next to the header avatar.
 */
export function mountUtilityActions(role, navigateSmoothly) {
  const searchBtn = document.getElementById("cms-search-toggle");
  const fullscreenBtn = document.getElementById("cms-fullscreen-toggle");
  const notifBtn = document.getElementById("cms-notif-btn");
  const notifDrop = document.getElementById("cms-notif-dropdown");
  const backdrop = document.getElementById("cms-search-backdrop");
  const searchDialog = document.getElementById("cms-search-dialog");
  const searchClose = document.getElementById("cms-search-close");
  const searchInput = document.getElementById("cms-admin-search");
  const searchResults = document.getElementById("cms-search-results");

  replaceBtnIcon(searchBtn, "search");
  replaceBtnIcon(fullscreenBtn, "fullscreen");
  replaceBtnIcon(notifBtn, "bell");

  if (role === "viewer") {
    if (searchBtn) searchBtn.setAttribute("hidden", "");
    const brand = document.querySelector(".cms-brand");
    if (brand) brand.setAttribute("href", "/admin/profile");
  }

  const routes = getSearchRoutes(role);
  const renderSearchResults = (query) => {
    if (!searchResults) return;
    while (searchResults.firstChild) searchResults.removeChild(searchResults.firstChild);
    const q = String(query || "").trim().toLowerCase();
    const matches = q
      ? routes.filter((r) => r.label.toLowerCase().includes(q) || r.keys.some((k) => k.includes(q) || q.includes(k)))
      : routes.slice(0, 6);
    if (matches.length === 0) {
      const li = document.createElement("li");
      li.className = "cms-search-empty";
      setSafeText(li, "No matching admin sections.");
      searchResults.appendChild(li);
      return;
    }
    for (const r of matches) {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = r.path;
      a.className = "cms-search-result-link";
      setSafeText(a, r.label);
      li.appendChild(a);
      searchResults.appendChild(li);
    }
  };

  const setSearchOpen = (open, restoreFocus = false) => {
    if (!backdrop || !searchBtn || role === "viewer") return;
    if (open) {
      backdrop.removeAttribute("hidden");
      searchBtn.setAttribute("aria-expanded", "true");
      renderSearchResults(searchInput ? searchInput.value : "");
      if (searchInput) {
        if (typeof searchInput.focus === "function") searchInput.focus();
        if (typeof searchInput.select === "function") searchInput.select();
      }
    } else {
      backdrop.setAttribute("hidden", "");
      searchBtn.setAttribute("aria-expanded", "false");
      if (restoreFocus) searchBtn.focus();
    }
  };

  if (searchBtn && role !== "viewer") {
    searchBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      setNotifOpen(false);
      setSearchOpen(backdrop ? backdrop.hasAttribute("hidden") : false);
    });
  }
  if (searchClose) {
    searchClose.addEventListener("click", () => setSearchOpen(false, true));
  }
  if (backdrop && searchDialog) {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) setSearchOpen(false, true);
    });
  }
  if (searchInput) {
    searchInput.addEventListener("input", () => renderSearchResults(searchInput.value));
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        searchInput.value = "";
        setSearchOpen(false, true);
        return;
      }
      if (e.key === "Enter") {
        const q = searchInput.value.trim().toLowerCase();
        const match = routes.find((r) => r.label.toLowerCase().includes(q) || r.keys.some((k) => k.includes(q) || q.includes(k)));
        if (match) {
          e.preventDefault();
          searchInput.value = "";
          setSearchOpen(false);
          navigateSmoothly(match.path, true);
        }
      }
    });
  }

  const setNotifOpen = (open, restoreFocus = false) => {
    if (!notifDrop || !notifBtn) return;
    notifDrop.classList.toggle("open", open);
    notifDrop.setAttribute("aria-hidden", open ? "false" : "true");
    notifBtn.setAttribute("aria-expanded", open ? "true" : "false");
    if (!open && restoreFocus) notifBtn.focus();
  };

  if (notifBtn && notifDrop) {
    notifBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      setSearchOpen(false);
      setNotifOpen(!notifDrop.classList.contains("open"));
    });
    document.addEventListener("click", (e) => {
      if (!notifDrop.contains(e.target) && !notifBtn.contains(e.target)) setNotifOpen(false);
    });
  }

  if (fullscreenBtn) {
    const syncFullscreen = () => {
      const active = Boolean(document.fullscreenElement);
      fullscreenBtn.setAttribute("aria-pressed", active ? "true" : "false");
      fullscreenBtn.setAttribute("aria-label", active ? "Exit fullscreen" : "Enter fullscreen");
      replaceBtnIcon(fullscreenBtn, active ? "fullscreenExit" : "fullscreen");
    };
    fullscreenBtn.addEventListener("click", () => {
      if (document.fullscreenElement) {
        if (document.exitFullscreen) Promise.resolve(document.exitFullscreen()).catch(() => {});
      } else if (document.documentElement && document.documentElement.requestFullscreen) {
        Promise.resolve(document.documentElement.requestFullscreen()).catch(() => {});
      }
    });
    document.addEventListener("fullscreenchange", syncFullscreen);
  }

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && String(e.key).toLowerCase() === "k" && role !== "viewer") {
      e.preventDefault();
      setNotifOpen(false);
      setSearchOpen(true);
    } else if (e.key === "Escape") {
      if (backdrop && !backdrop.hasAttribute("hidden")) {
        e.preventDefault();
        setSearchOpen(false, true);
      } else if (notifDrop && notifDrop.classList.contains("open")) {
        setNotifOpen(false, true);
      }
    }
  });

  return {
    close() {
      setSearchOpen(false);
      setNotifOpen(false);
    },
  };
}
