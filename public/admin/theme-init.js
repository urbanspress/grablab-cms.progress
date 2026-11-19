/*
 * GrabLab CMS v1.5.0 — no-flash theme bootstrap (classic, CSP-safe external script, zero eval).
 * Runs in <head> before first paint so the saved Light / Dark preference never flashes the wrong theme.
 * The full controller (palette tokens, header toggle, profile preferences) lives in theme.js.
 */
(function () {
  var root = document.documentElement;
  var pref = "system";
  try {
    var saved = window.localStorage.getItem("grablab-admin-theme");
    if (saved === "light" || saved === "dark" || saved === "system") pref = saved;
    if (window.localStorage.getItem("grablab-admin-density") === "compact") root.setAttribute("data-cms-density", "compact");
    if (window.localStorage.getItem("grablab-admin-motion") === "reduce") root.setAttribute("data-cms-motion", "reduce");
  } catch (e) {
    pref = "system";
  }
  var mode = pref;
  if (pref === "system") {
    mode = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  root.setAttribute("data-cms-theme", mode);
  root.setAttribute("data-cms-theme-pref", pref);
})();
