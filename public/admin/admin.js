import {
  Form,
  Input,
  Select,
  Tabs,
  Modal,
  Nav,
  ForEach,
  createGrabClient,
  useQuery,
  invalidateQueries,
  createTheme,
  createClassManager,
  signal,
  effect,
  setSafeText,
} from "../grex/grex.js";

function getMeta(name) {
  const el = document.querySelector(`meta[name="${name}"]`);
  return el ? el.getAttribute("content") || "" : "";
}

function el(tag, attrs = {}, text = null) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v !== undefined && v !== null) {
      node.setAttribute(k, String(v));
    }
  }
  if (text !== null) {
    setSafeText(node, text);
  }
  return node;
}

function makeAlert(msgSignal, isOk = false) {
  const box = el("p", {
    role: isOk ? "status" : "alert",
    class: isOk ? "cms-alert cms-alert-ok" : "cms-alert cms-alert-error",
    hidden: "",
  });
  effect(() => {
    const val = msgSignal.get();
    if (val) {
      box.removeAttribute("hidden");
      setSafeText(box, val);
    } else {
      box.setAttribute("hidden", "");
      setSafeText(box, "");
    }
  });
  return box;
}

function applyAdminTheme() {
  const theme = createTheme({
    colors: {
      bg: "#0b0e13",
      surface: "#11151d",
      ink: "#f8fafc",
      muted: "#94a3b8",
      accent: "#f43f5e",
      "accent-ink": "#ffffff",
    },
    radii: { radius: "14px" },
  });
  theme.applyTo(document.documentElement);

  const cm = createClassManager({ prefix: "cms-grex-" });
  cm.registerClass("panel", {
    background: "#11151d",
    borderRadius: "14px",
  });
}

function createApiClient() {
  return createGrabClient({
    csrfToken: () => getMeta("grablab-csrf"),
    csrfHeader: "X-CSRF-Token",
  });
}

function mountLogin(api) {
  const mount = document.getElementById("login-form-mount");
  if (!mount) return;
  const errSig = signal("");
  const emailInput = Input({
    id: "login-email",
    props: { name: "email", type: "email", label: "Email Address", required: true, placeholder: "admin@example.com" },
  });
  const passInput = Input({
    id: "login-password",
    props: { name: "password", type: "password", label: "Password", required: true, minLength: 10 },
  });
  const submitBtn = el("button", { type: "submit" }, "Sign In");
  const form = Form({
    props: {
      method: "post",
      requireCsrf: false,
      onSubmit: async () => {
        errSig.set("");
        if (!emailInput.validate() || !passInput.validate()) {
          return;
        }
        try {
          const res = await fetch("/api/auth/login", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({
              email: emailInput.value.peek(),
              password: passInput.value.peek(),
            }),
          });
          const data = await res.json();
          if (!res.ok) {
            errSig.set(data.error || "Sign in failed.");
            return;
          }
          window.location.assign("/admin");
        } catch (err) {
          errSig.set(err && err.message ? err.message : "Network error during sign in.");
        }
      },
    },
    children: [makeAlert(errSig, false), emailInput.element, passInput.element, { element: submitBtn }],
  });
  mount.appendChild(form.element);
}

function mountSetup() {
  const mount = document.getElementById("setup-form-mount");
  if (!mount) return;
  const errSig = signal("");
  const nameInput = Input({
    id: "setup-name",
    props: { name: "display_name", type: "text", label: "Display Name", required: true, value: "Site Administrator" },
  });
  const emailInput = Input({
    id: "setup-email",
    props: { name: "email", type: "email", label: "Admin Email", required: true, placeholder: "admin@example.com" },
  });
  const passInput = Input({
    id: "setup-password",
    props: { name: "password", type: "password", label: "Password (min 10 characters)", required: true, minLength: 10 },
  });
  const submitBtn = el("button", { type: "submit" }, "Create Administrator");
  const form = Form({
    props: {
      method: "post",
      requireCsrf: false,
      onSubmit: async () => {
        errSig.set("");
        if (!nameInput.validate() || !emailInput.validate() || !passInput.validate()) {
          return;
        }
        try {
          const res = await fetch("/api/auth/setup", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({
              display_name: nameInput.value.peek(),
              email: emailInput.value.peek(),
              password: passInput.value.peek(),
            }),
          });
          const data = await res.json();
          if (!res.ok) {
            errSig.set(data.error || "Setup failed.");
            return;
          }
          window.location.assign("/admin");
        } catch (err) {
          errSig.set(err && err.message ? err.message : "Network error during setup.");
        }
      },
    },
    children: [makeAlert(errSig, false), nameInput.element, emailInput.element, passInput.element, { element: submitBtn }],
  });
  mount.appendChild(form.element);
}

function mountSidebarNav(activePath, role, api) {
  const mount = document.getElementById("admin-nav-mount");
  if (!mount) return;

  const renderNav = (authorEnabled) => {
    while (mount.firstChild) {
      mount.removeChild(mount.firstChild);
    }

    const sections = [
      {
        title: "OVERVIEW",
        items: [
          {
            href: "/admin",
            text: "Dashboard",
            icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>`,
            active: activePath === "/admin" || activePath === "/admin/",
          },
        ],
      },
      {
        title: "WORKSPACE",
        items: [
          {
            href: "/admin/entries",
            text: "Agents",
            icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>`,
            active: activePath.startsWith("/admin/entries"),
          },
          {
            href: "/admin/media",
            text: "Builder",
            icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>`,
            active: activePath.startsWith("/admin/media"),
          },
          {
            href: "/admin/author",
            text: "Executions",
            icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>`,
            active: activePath.startsWith("/admin/author"),
          },
          {
            href: "/admin/store",
            text: "Integrations",
            icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v6"/><path d="M9 2v6"/><path d="M15 2v6"/><rect x="6" y="8" width="12" height="6" rx="2"/><path d="M12 14v8"/></svg>`,
            active: activePath.startsWith("/admin/store"),
          },
        ],
      },
      {
        title: "DEVELOPER",
        items: [
          {
            href: "/admin/types",
            text: "Components",
            icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>`,
            active: activePath.startsWith("/admin/types"),
          },
          {
            href: "/admin/themes",
            text: "Documentation",
            icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`,
            active: activePath.startsWith("/admin/themes"),
          },
        ],
      },
      {
        title: "ACCOUNT",
        items: [
          {
            href: "/admin/settings",
            text: "Account",
            icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`,
            active: activePath === "/admin/settings",
          },
          {
            href: "/admin/settings",
            text: "Profile",
            icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
            active: false,
          },
        ],
      },
    ];

    const navWrap = document.createElement("nav");
    navWrap.className = "agentflow-sidebar-nav";

    for (const sec of sections) {
      const secEl = document.createElement("div");
      secEl.className = "agentflow-nav-section";

      const titleEl = document.createElement("div");
      titleEl.className = "agentflow-nav-section-title";
      titleEl.textContent = sec.title;
      secEl.appendChild(titleEl);

      const ulEl = document.createElement("ul");
      ulEl.className = "agentflow-nav-list";

      for (const item of sec.items) {
        const liEl = document.createElement("li");
        liEl.className = "agentflow-nav-item";

        const aEl = document.createElement("a");
        aEl.href = item.href;
        if (item.active) aEl.className = "active";

        const iconSpan = document.createElement("span");
        iconSpan.className = "agentflow-nav-icon";
        iconSpan.innerHTML = item.icon;

        const textSpan = document.createElement("span");
        textSpan.textContent = item.text;

        aEl.appendChild(iconSpan);
        aEl.appendChild(textSpan);
        liEl.appendChild(aEl);
        ulEl.appendChild(liEl);
      }
      secEl.appendChild(ulEl);
      navWrap.appendChild(secEl);
    }

    // Upgrade to Pro Card
    const upgradeCard = document.createElement("div");
    upgradeCard.className = "agentflow-upgrade-card";
    upgradeCard.innerHTML = `
      <div class="agentflow-upgrade-title">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 2l2.4 7.2h7.6l-6 4.8 2.4 7.2-6.4-4.8-6.4 4.8 2.4-7.2-6-4.8h7.6z"/></svg>
        <span>Upgrade to Pro</span>
      </div>
      <div class="agentflow-upgrade-desc">Unlock unlimited agents, advanced analytics & priority support.</div>
      <button type="button" class="agentflow-upgrade-btn">Upgrade</button>
    `;
    navWrap.appendChild(upgradeCard);

    // User Profile Card at Sidebar Bottom
    const userName = getMeta("grablab-user-name") || "Alex";
    const userEmail = getMeta("grablab-user-email") || "m@example.com";
    const userCard = document.createElement("div");
    userCard.className = "agentflow-user-card";
    userCard.innerHTML = `
      <div class="agentflow-user-info">
        <div class="agentflow-avatar">${userName.charAt(0).toUpperCase()}</div>
        <div class="agentflow-user-names">
          <div class="agentflow-user-name">${userName}</div>
          <div class="agentflow-user-email">${userEmail}</div>
        </div>
      </div>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2"><path d="M7 15l5 5 5-5"/><path d="M7 9l5-5 5 5"/></svg>
    `;
    navWrap.appendChild(userCard);

    mount.appendChild(navWrap);
  };

  renderNav(activePath.startsWith("/admin/author"));
  if (api && (role === "admin" || role === "editor" || role === "author")) {
    api.get("/api/admin/author/status")
      .then((res) => {
        renderNav(Boolean(res && res.enabled));
      })
      .catch(() => {});
  }
}

function mountOverview(root, api) {
  const errSig = signal("");
  const overviewQuery = useQuery(api, "/api/admin/overview", { tags: ["overview"] });
  root.appendChild(makeAlert(errSig, false));

  // 1. Top 3 KPI Cards
  const kpiGrid = document.createElement("section");
  kpiGrid.className = "agentflow-kpi-grid";
  kpiGrid.innerHTML = `
    <!-- Card 1: Active Agents -->
    <div class="agentflow-card">
      <div class="agentflow-card-head">
        <span class="agentflow-card-title">Active Agents</span>
        <button type="button" class="agentflow-card-dots" aria-label="Card options">•••</button>
      </div>
      <div class="agentflow-stat-row">
        <span class="agentflow-stat-val">12</span>
        <span class="agentflow-trend-pill">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg>
          +3 Increased vs last week
        </span>
      </div>
      <div class="agentflow-chart-wrap">
        <svg class="agentflow-sparkline-svg" viewBox="0 0 300 60" preserveAspectRatio="none">
          <defs>
            <linearGradient id="glow-grad-agents" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#f43f5e" stop-opacity="0.25"/>
              <stop offset="100%" stop-color="#f43f5e" stop-opacity="0.0"/>
            </linearGradient>
          </defs>
          <path d="M 0 42 Q 50 44 90 36 T 180 32 T 250 26 T 300 30 L 300 60 L 0 60 Z" fill="url(#glow-grad-agents)"/>
          <path class="agentflow-sparkline-path" d="M 0 42 Q 50 44 90 36 T 180 32 T 250 26 T 300 30"/>
        </svg>
        <div class="agentflow-days-row">
          <span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
        </div>
      </div>
    </div>

    <!-- Card 2: Weekly Runs -->
    <div class="agentflow-card">
      <div class="agentflow-card-head">
        <span class="agentflow-card-title">Weekly Runs</span>
        <button type="button" class="agentflow-card-dots" aria-label="Card options">•••</button>
      </div>
      <div class="agentflow-stat-row">
        <span class="agentflow-stat-val">1,284</span>
        <span class="agentflow-trend-pill">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg>
          +12% Increased vs last week
        </span>
      </div>
      <div class="agentflow-chart-wrap">
        <div class="agentflow-mini-bars">
          <div class="agentflow-mini-bar" style="height: 14px;"></div>
          <div class="agentflow-mini-bar" style="height: 24px;"></div>
          <div class="agentflow-mini-bar agentflow-mini-bar-active" style="height: 52px;"></div>
          <div class="agentflow-mini-bar" style="height: 32px;"></div>
          <div class="agentflow-mini-bar" style="height: 18px;"></div>
          <div class="agentflow-mini-bar" style="height: 20px;"></div>
        </div>
        <div class="agentflow-days-row">
          <span>Mon</span><span>Thu</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Mon</span>
        </div>
      </div>
    </div>

    <!-- Card 3: Tokens Used -->
    <div class="agentflow-card">
      <div class="agentflow-card-head">
        <span class="agentflow-card-title">Tokens Used</span>
        <button type="button" class="agentflow-card-dots" aria-label="Card options">•••</button>
      </div>
      <div class="agentflow-stat-row">
        <span class="agentflow-stat-val">26.4K</span>
        <span class="agentflow-trend-pill">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg>
          +8% Increased vs last week
        </span>
      </div>
      <div class="agentflow-chart-wrap">
        <svg class="agentflow-sparkline-svg" viewBox="0 0 300 60" preserveAspectRatio="none">
          <defs>
            <linearGradient id="glow-grad-tokens" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#f43f5e" stop-opacity="0.30"/>
              <stop offset="100%" stop-color="#f43f5e" stop-opacity="0.0"/>
            </linearGradient>
          </defs>
          <path d="M 0 36 C 45 36, 75 22, 120 25 C 165 28, 195 4, 225 6 C 255 8, 265 42, 300 36 L 300 60 L 0 60 Z" fill="url(#glow-grad-tokens)"/>
          <path class="agentflow-sparkline-path" d="M 0 36 C 45 36, 75 22, 120 25 C 165 28, 195 4, 225 6 C 255 8, 265 42, 300 36"/>
        </svg>
        <div class="agentflow-days-row">
          <span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
        </div>
      </div>
    </div>
  `;
  root.appendChild(kpiGrid);

  // 2. Middle Row: 2 Large Cards (Token Usage + Executions)
  const mainGrid = document.createElement("section");
  mainGrid.className = "agentflow-main-grid";
  mainGrid.innerHTML = `
    <!-- Card 4: Token Usage -->
    <div class="agentflow-card agentflow-usage-card">
      <div class="agentflow-usage-head">
        <span class="agentflow-card-title" style="color: #ffffff; font-size: 15px;">Token Usage</span>
        <div class="agentflow-pill-group">
          <button type="button" class="agentflow-pill-btn">Days</button>
          <button type="button" class="agentflow-pill-btn active">Week</button>
          <button type="button" class="agentflow-pill-btn">Month</button>
        </div>
      </div>
      <div class="agentflow-usage-chart-wrap">
        <div class="agentflow-y-axis">
          <span>$28K</span>
          <span>$21K</span>
          <span>$14K</span>
          <span>$7K</span>
          <span>$0K</span>
        </div>
        <div class="agentflow-chart-area">
          <div class="agentflow-grid-lines">
            <div class="agentflow-grid-line"></div>
            <div class="agentflow-grid-line"></div>
            <div class="agentflow-grid-line"></div>
            <div class="agentflow-grid-line"></div>
            <div class="agentflow-grid-line"></div>
          </div>
          <div class="agentflow-month-bars">
            <div class="agentflow-bar-col"><div class="agentflow-bar" style="height: 52%;"></div></div>
            <div class="agentflow-bar-col"><div class="agentflow-bar" style="height: 60%;"></div></div>
            <div class="agentflow-bar-col"><div class="agentflow-bar" style="height: 68%;"></div></div>
            <div class="agentflow-bar-col"><div class="agentflow-bar" style="height: 62%;"></div></div>
            <div class="agentflow-bar-col"><div class="agentflow-bar active" style="height: 98%;"></div></div>
            <div class="agentflow-bar-col"><div class="agentflow-bar" style="height: 40%;"></div></div>
            <div class="agentflow-bar-col"><div class="agentflow-bar" style="height: 48%;"></div></div>
            <div class="agentflow-bar-col"><div class="agentflow-bar" style="height: 56%;"></div></div>
            <div class="agentflow-bar-col"><div class="agentflow-bar" style="height: 64%;"></div></div>
            <div class="agentflow-bar-col"><div class="agentflow-bar" style="height: 54%;"></div></div>
            <div class="agentflow-bar-col"><div class="agentflow-bar" style="height: 58%;"></div></div>
            <div class="agentflow-bar-col"><div class="agentflow-bar" style="height: 65%;"></div></div>
          </div>
          <div class="agentflow-x-axis">
            <span>Jan</span><span>Feb</span><span>Mar</span><span>Apr</span><span style="color: #ffffff; font-weight: 700;">May</span><span>Jun</span><span>Jul</span><span>Aug</span><span>Sep</span><span>Oct</span><span>Nov</span><span>Dec</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Card 5: Executions Heatmap -->
    <div class="agentflow-card">
      <div class="agentflow-card-head agentflow-exec-head">
        <span class="agentflow-card-title" style="color: #ffffff; font-size: 15px;">Executions</span>
      </div>
      <div class="agentflow-heatmap-table">
        <div class="agentflow-heat-cols">
          <span></span>
          <span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span>
        </div>
        <div class="agentflow-heat-row">
          <span class="agentflow-week-lbl">W1</span>
          <div class="agentflow-heat-cell l2"></div>
          <div class="agentflow-heat-cell l2"></div>
          <div class="agentflow-heat-cell l3"></div>
          <div class="agentflow-heat-cell l3"></div>
          <div class="agentflow-heat-cell l4"></div>
          <div class="agentflow-heat-cell l2"></div>
          <div class="agentflow-heat-cell l1"></div>
        </div>
        <div class="agentflow-heat-row">
          <span class="agentflow-week-lbl">W2</span>
          <div class="agentflow-heat-cell l2"></div>
          <div class="agentflow-heat-cell l3"></div>
          <div class="agentflow-heat-cell l3"></div>
          <div class="agentflow-heat-cell l4"></div>
          <div class="agentflow-heat-cell l4"></div>
          <div class="agentflow-heat-cell l2"></div>
          <div class="agentflow-heat-cell l1"></div>
        </div>
        <div class="agentflow-heat-row">
          <span class="agentflow-week-lbl">W3</span>
          <div class="agentflow-heat-cell l2"></div>
          <div class="agentflow-heat-cell l2"></div>
          <div class="agentflow-heat-cell l4"></div>
          <div class="agentflow-heat-cell l5"></div>
          <div class="agentflow-heat-cell l3"></div>
          <div class="agentflow-heat-cell l2"></div>
          <div class="agentflow-heat-cell l1"></div>
        </div>
        <div class="agentflow-heat-row">
          <span class="agentflow-week-lbl">W4</span>
          <div class="agentflow-heat-cell l2"></div>
          <div class="agentflow-heat-cell l3"></div>
          <div class="agentflow-heat-cell l3"></div>
          <div class="agentflow-heat-cell l4"></div>
          <div class="agentflow-heat-cell l5"></div>
          <div class="agentflow-heat-cell l3"></div>
          <div class="agentflow-heat-cell l2"></div>
        </div>
      </div>
      <div class="agentflow-legend">
        <span>Less</span>
        <div class="agentflow-legend-dots">
          <div class="agentflow-legend-dot" style="background: #33141d;"></div>
          <div class="agentflow-legend-dot" style="background: #4a1725;"></div>
          <div class="agentflow-legend-dot" style="background: #751b34;"></div>
          <div class="agentflow-legend-dot" style="background: #ba214a;"></div>
          <div class="agentflow-legend-dot" style="background: #f43f5e;"></div>
        </div>
        <span>More</span>
      </div>
    </div>
  `;
  root.appendChild(mainGrid);

  // 3. Bottom Row: Recent Entries (CMS functionality preserved)
  const recentCard = el("section", { class: "cms-card" });
  recentCard.appendChild(el("h2", {}, "Recent Entries"));
  const listMount = el("ul", { class: "cms-list" });
  recentCard.appendChild(listMount);

  const itemsSig = signal([]);
  ForEach({
    parent: listMount,
    items: itemsSig,
    key: (item) => item.id,
    empty: () => ({ element: el("li", { class: "cms-muted" }, "No entries created yet.") }),
    render: (itemSig) => {
      const li = el("li", { class: "cms-row" });
      const left = el("section");
      const titleEl = el("strong");
      const metaEl = el("p", { class: "cms-muted" });
      left.appendChild(titleEl);
      left.appendChild(metaEl);
      const link = el("a", { class: "cms-btn-link", href: "/admin/entries" }, "Edit");
      effect(() => {
        const it = itemSig.get();
        setSafeText(titleEl, it.title);
        setSafeText(metaEl, `${it.content_type_label} · ${it.full_path} · ${it.status}`);
      });
      li.appendChild(left);
      li.appendChild(link);
      return { element: li };
    },
  });

  effect(() => {
    if (overviewQuery.error.get()) {
      errSig.set(overviewQuery.error.get().message || "Failed to load overview.");
      return;
    }
    const data = overviewQuery.data.get();
    if (!data) return;
    itemsSig.set(data.recent_entries || []);
  });

  root.appendChild(recentCard);
}

function mountEntries(root, api, role) {
  const errSig = signal("");
  const okSig = signal("");
  const statusFilter = signal("all");
  const editingId = signal(null);

  const entriesQuery = useQuery(api, "/api/entries", { tags: ["entries"] });
  const typesQuery = useQuery(api, "/api/content-types", { tags: ["types"] });
  const redirectsQuery = useQuery(api, "/api/redirects", { tags: ["redirects"] });

  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const titleInput = Input({ id: "entry-title", props: { name: "title", label: "Title", required: true } });
  const slugInput = Input({ id: "entry-slug", props: { name: "slug", label: "URL Slug", required: true, placeholder: "my-article" } });
  const typeSelect = Select({
    id: "entry-type",
    props: {
      name: "content_type",
      label: "Content Type",
      options: () =>
        (typesQuery.data.get()?.content_types || []).map((t) => ({ value: t.slug, label: `${t.label_singular} (${t.permalink_pattern})` })),
      value: signal("post"),
    },
  });
  const statusOptions =
    role === "author"
      ? [{ value: "draft", label: "Draft (Authors cannot publish)" }]
      : [
          { value: "draft", label: "Draft" },
          { value: "published", label: "Published" },
          { value: "archived", label: "Archived" },
        ];
  const statusSelect = Select({
    id: "entry-status",
    props: { name: "status", label: "Status", options: statusOptions, value: signal(role === "author" ? "draft" : "published") },
  });
  const bodyInput = Input({ id: "entry-body", props: { name: "body_html", type: "textarea", label: "Body Content" } });
  const metaTitleInput = Input({ id: "entry-meta-title", props: { name: "meta_title", label: "SEO Meta Title (optional)" } });
  const cfJsonInput = Input({
    id: "entry-custom-fields",
    props: { name: "custom_fields_json", type: "textarea", label: "Custom Fields JSON", value: "{}" },
  });
  const termIdsInput = Input({
    id: "entry-term-ids",
    props: { name: "term_ids", label: "Term IDs (comma-separated, optional)", placeholder: "e.g. 1, 2" },
  });

  const submitLabel = signal("Create Entry");
  const submitBtn = el("button", { type: "submit" }, "Create Entry");
  effect(() => setSafeText(submitBtn, submitLabel.get()));

  const cancelBtn = el("button", { type: "button", class: "cms-btn-secondary" }, "Reset Form");
  cancelBtn.addEventListener("click", () => {
    editingId.set(null);
    submitLabel.set("Create Entry");
    titleInput.value.set("");
    slugInput.value.set("");
    bodyInput.value.set("");
    metaTitleInput.value.set("");
    cfJsonInput.value.set("{}");
    termIdsInput.value.set("");
  });

  const parseTermIdsCsv = (rawCsv) => {
    const clean = (rawCsv || "").trim();
    if (!clean) return [];
    return clean
      .split(",")
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => Number.isInteger(n) && n > 0);
  };

  const editorForm = Form({
    props: {
      csrfToken: () => getMeta("grablab-csrf"),
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        if (!titleInput.validate() || !slugInput.validate()) return;
        let cfObj = {};
        const rawCf = cfJsonInput.value.peek().trim();
        if (rawCf) {
          try {
            cfObj = JSON.parse(rawCf);
          } catch {
            errSig.set("Custom Fields must be valid JSON.");
            return;
          }
        }
        const termIds = parseTermIdsCsv(termIdsInput.value.peek());
        try {
          const id = editingId.peek();
          if (id) {
            await api.put(`/api/entries/${id}`, {
              title: titleInput.value.peek(),
              slug: slugInput.value.peek(),
              status: statusSelect.value.peek(),
              body_html: bodyInput.value.peek(),
              meta_title: metaTitleInput.value.peek(),
              custom_fields: cfObj,
              ...(termIdsInput.value.peek().trim() ? { term_ids: termIds } : {}),
            });
            okSig.set("Entry updated (301 redirect recorded if published slug changed).");
          } else {
            await api.post("/api/entries", {
              content_type: typeSelect.value.peek(),
              title: titleInput.value.peek(),
              slug: slugInput.value.peek(),
              status: statusSelect.value.peek(),
              body_html: bodyInput.value.peek(),
              meta_title: metaTitleInput.value.peek(),
              custom_fields: cfObj,
              term_ids: termIds,
            });
            okSig.set("Entry created.");
          }
          editingId.set(null);
          submitLabel.set("Create Entry");
          termIdsInput.value.set("");
          invalidateQueries(["entries", "redirects", "overview"]);
        } catch (err) {
          errSig.set(err.message || "Failed to save entry.");
        }
      },
    },
    children: [
      typeSelect.element,
      titleInput.element,
      slugInput.element,
      statusSelect.element,
      bodyInput.element,
      metaTitleInput.element,
      cfJsonInput.element,
      termIdsInput.element,
      el("section", { class: "cms-row" }),
    ],
  });
  editorForm.element.lastChild.appendChild(submitBtn);
  editorForm.element.lastChild.appendChild(cancelBtn);

  const editorCard = el("section", { class: "cms-card" });
  editorCard.appendChild(el("h2", {}, "Entry Editor"));
  editorCard.appendChild(editorForm.element);

  const filterSelect = Select({
    id: "entries-filter-status",
    props: {
      name: "filter_status",
      label: "Filter by Status",
      value: statusFilter,
      options: [
        { value: "all", label: "All Statuses" },
        { value: "published", label: "Published" },
        { value: "draft", label: "Draft" },
        { value: "archived", label: "Archived" },
      ],
    },
  });

  const listCard = el("section", { class: "cms-card" });
  listCard.appendChild(el("h2", {}, "Entries"));
  listCard.appendChild(filterSelect.element);
  const ul = el("ul", { class: "cms-list" });
  listCard.appendChild(ul);

  const filteredItems = signal([]);
  effect(() => {
    const all = entriesQuery.data.get()?.entries || [];
    const st = statusFilter.get();
    filteredItems.set(st === "all" ? all : all.filter((e) => e.status === st));
  });

  ForEach({
    parent: ul,
    items: filteredItems,
    key: (item) => item.id,
    empty: () => ({ element: el("li", { class: "cms-muted" }, "No matching entries.") }),
    render: (itemSig) => {
      const li = el("li", { class: "cms-card" });
      const row = el("section", { class: "cms-row" });
      const info = el("section");
      const h3 = el("h3");
      const meta = el("p", { class: "cms-muted" });
      info.appendChild(h3);
      info.appendChild(meta);

      const actions = el("section", { class: "cms-topbar-right" });
      const editBtn = el("button", { type: "button", class: "cms-btn-secondary" }, "Edit");
      const delBtn = el("button", { type: "button", class: "cms-btn-danger" }, "Delete");
      actions.appendChild(editBtn);
      actions.appendChild(delBtn);

      editBtn.addEventListener("click", () => {
        const it = itemSig.peek();
        editingId.set(it.id);
        submitLabel.set(`Update Entry #${it.id}`);
        typeSelect.value.set(it.content_type_slug);
        titleInput.value.set(it.title);
        slugInput.value.set(it.slug);
        statusSelect.value.set(it.status);
        bodyInput.value.set(it.body_html || "");
        metaTitleInput.value.set(it.meta_title || "");
        cfJsonInput.value.set(it.custom_fields_json || "{}");
      });

      delBtn.addEventListener("click", async () => {
        const it = itemSig.peek();
        errSig.set("");
        okSig.set("");
        try {
          await api.delete(`/api/entries/${it.id}`);
          okSig.set(`Deleted entry "${it.title}".`);
          invalidateQueries(["entries", "redirects", "overview"]);
        } catch (err) {
          errSig.set(err.message || "Delete failed.");
        }
      });

      effect(() => {
        const it = itemSig.get();
        setSafeText(h3, it.title);
        setSafeText(meta, `${it.content_type_label} · ${it.full_path} · ${it.status}`);
      });

      row.appendChild(info);
      row.appendChild(actions);
      li.appendChild(row);
      return { element: li };
    },
  });

  const redirectCard = el("section", { class: "cms-card" });
  redirectCard.appendChild(el("h2", {}, "Automatic 301 Redirect History"));
  const redirUl = el("ul", { class: "cms-list" });
  redirectCard.appendChild(redirUl);
  const redirItems = signal([]);
  effect(() => redirItems.set(redirectsQuery.data.get()?.redirects || []));
  ForEach({
    parent: redirUl,
    items: redirItems,
    key: (r) => r.id,
    empty: () => ({ element: el("li", { class: "cms-muted" }, "No 301 redirects recorded yet.") }),
    render: (rSig) => {
      const li = el("li");
      effect(() => {
        const r = rSig.get();
        setSafeText(li, `${r.old_path} -> ${r.target_path} (301)`);
      });
      return { element: li };
    },
  });

  const stack = el("section", { class: "cms-stack" });
  stack.appendChild(editorCard);
  stack.appendChild(listCard);
  stack.appendChild(redirectCard);
  root.appendChild(stack);
}

function mountTypes(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  const typesQuery = useQuery(api, "/api/content-types", { tags: ["types"] });
  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const modalOpen = signal(false);
  const openBtn = el("button", { type: "button", class: "cms-btn" }, "New Content Type");
  openBtn.addEventListener("click", () => modalOpen.set(true));

  const slugIn = Input({ id: "ct-slug", props: { name: "slug", label: "Type Slug", required: true, placeholder: "product" } });
  const singIn = Input({ id: "ct-sing", props: { name: "label_singular", label: "Singular Label", required: true, placeholder: "Product" } });
  const plurIn = Input({ id: "ct-plur", props: { name: "label_plural", label: "Plural Label", required: true, placeholder: "Products" } });
  const patIn = Input({ id: "ct-pat", props: { name: "permalink_pattern", label: "Permalink Pattern", required: true, value: "/items/:slug" } });
  const archIn = Input({ id: "ct-arch", props: { name: "archive_slug", label: "Archive Slug", placeholder: "items" } });
  const closeBtn = el("button", { type: "button", class: "cms-btn-secondary" }, "Cancel");
  closeBtn.addEventListener("click", () => modalOpen.set(false));

  const ctForm = Form({
    props: {
      csrfToken: () => getMeta("grablab-csrf"),
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        if (!slugIn.validate() || !singIn.validate() || !plurIn.validate() || !patIn.validate()) return;
        try {
          await api.post("/api/content-types", {
            slug: slugIn.value.peek(),
            label_singular: singIn.value.peek(),
            label_plural: plurIn.value.peek(),
            permalink_pattern: patIn.value.peek(),
            has_archive: Boolean(archIn.value.peek().trim()),
            archive_slug: archIn.value.peek().trim() || undefined,
          });
          modalOpen.set(false);
          okSig.set("Content type registered.");
          invalidateQueries(["types", "overview"]);
        } catch (err) {
          errSig.set(err.message || "Failed to create content type.");
        }
      },
    },
    children: [slugIn.element, singIn.element, plurIn.element, patIn.element, archIn.element, { element: el("button", { type: "submit" }, "Create Type") }, { element: closeBtn }],
  });

  const modal = Modal({
    id: "new-type-modal",
    props: { open: modalOpen, title: "Create Content Type" },
    children: [ctForm.element],
  });

  const listCard = el("section", { class: "cms-card" });
  const headerRow = el("section", { class: "cms-row" });
  headerRow.appendChild(el("h2", {}, "Registered Content Types"));
  headerRow.appendChild(openBtn);
  listCard.appendChild(headerRow);

  const ul = el("ul", { class: "cms-list" });
  listCard.appendChild(ul);
  const typeItems = signal([]);
  effect(() => typeItems.set(typesQuery.data.get()?.content_types || []));

  ForEach({
    parent: ul,
    items: typeItems,
    key: (ct) => ct.slug,
    render: (ctSig) => {
      const li = el("li", { class: "cms-card" });
      const title = el("h3");
      const meta = el("p", { class: "cms-muted" });
      effect(() => {
        const ct = ctSig.get();
        setSafeText(title, `${ct.label_plural} (${ct.slug})`);
        const fieldNames = (ct.fields || []).map((f) => `${f.field_key}:${f.field_type}`).join(", ") || "none";
        setSafeText(meta, `Pattern: ${ct.permalink_pattern} · Fields: ${fieldNames}`);
      });
      li.appendChild(title);
      li.appendChild(meta);
      return { element: li };
    },
  });

  const fieldCard = el("section", { class: "cms-card" });
  fieldCard.appendChild(el("h2", {}, "Attach Custom Field"));
  const targetTypeSel = Select({
    id: "field-target-type",
    props: {
      name: "content_type",
      label: "Target Content Type",
      options: () => (typesQuery.data.get()?.content_types || []).map((t) => ({ value: t.slug, label: t.label_plural })),
      value: signal("post"),
    },
  });
  const fkIn = Input({ id: "field-key", props: { name: "field_key", label: "Field Key", required: true, placeholder: "price" } });
  const flIn = Input({ id: "field-label", props: { name: "label", label: "Label", required: true, placeholder: "Price" } });
  const ftSel = Select({
    id: "field-type",
    props: {
      name: "field_type",
      label: "Field Type",
      value: signal("text"),
      options: [
        { value: "text", label: "Text" },
        { value: "rich_text", label: "Rich Text" },
        { value: "integer", label: "Exact Integer (GrabInteger)" },
        { value: "decimal", label: "Exact Decimal (GrabDecimal)" },
        { value: "boolean", label: "Boolean" },
        { value: "date", label: "Date (YYYY-MM-DD)" },
        { value: "url", label: "Safe URL" },
        { value: "json", label: "Grex JSON Layout" },
      ],
    },
  });
  const fieldForm = Form({
    props: {
      csrfToken: () => getMeta("grablab-csrf"),
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        if (!fkIn.validate() || !flIn.validate()) return;
        try {
          await api.post(`/api/content-types/${targetTypeSel.value.peek()}/fields`, {
            field_key: fkIn.value.peek(),
            label: flIn.value.peek(),
            field_type: ftSel.value.peek(),
          });
          okSig.set("Custom field added.");
          fkIn.value.set("");
          flIn.value.set("");
          invalidateQueries(["types"]);
        } catch (err) {
          errSig.set(err.message || "Failed to add field.");
        }
      },
    },
    children: [targetTypeSel.element, fkIn.element, flIn.element, ftSel.element, { element: el("button", { type: "submit" }, "Add Field") }],
  });
  fieldCard.appendChild(fieldForm.element);

  const stack = el("section", { class: "cms-stack" });
  stack.appendChild(listCard);
  stack.appendChild(fieldCard);
  stack.appendChild(modal.element);
  root.appendChild(stack);
}

function mountThemes(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  const themesQuery = useQuery(api, "/api/themes", { tags: ["themes"] });
  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const regSlug = Input({ id: "reg-theme-slug", props: { name: "slug", label: "Register Theme Directory (themes/<slug>)", required: true, placeholder: "grex-builder" } });
  const regForm = Form({
    props: {
      csrfToken: () => getMeta("grablab-csrf"),
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        if (!regSlug.validate()) return;
        try {
          await api.post("/api/themes/register", { slug: regSlug.value.peek() });
          okSig.set(`Validated and registered theme "${regSlug.value.peek()}".`);
          regSlug.value.set("");
          invalidateQueries(["themes"]);
        } catch (err) {
          errSig.set(err.message || "Failed to register theme.");
        }
      },
    },
    children: [regSlug.element, { element: el("button", { type: "submit" }, "Validate & Register Theme") }],
  });
  const regCard = el("section", { class: "cms-card" });
  regCard.appendChild(el("h2", {}, "Install / Register Validated Theme"));
  regCard.appendChild(regForm.element);

  const listCard = el("section", { class: "cms-card" });
  listCard.appendChild(el("h2", {}, "1-Click Exclusive Theme & Grex Theme Builder Switcher"));
  listCard.appendChild(el("p", { class: "cms-muted" }, "Only one theme may be active at a time. Activating a theme atomically deactivates the previous theme and transfers 100% template ownership."));
  const ul = el("ul", { class: "cms-list" });
  listCard.appendChild(ul);

  const themeItems = signal([]);
  effect(() => themeItems.set(themesQuery.data.get()?.themes || []));

  ForEach({
    parent: ul,
    items: themeItems,
    key: (t) => t.slug,
    render: (tSig) => {
      const li = el("li", { class: "cms-card" });
      const row = el("section", { class: "cms-row" });
      const info = el("section");
      const title = el("h3");
      const badges = el("p", { class: "cms-row" });
      const modeBadge = el("span", { class: "cms-badge" });
      const statusBadge = el("span", { class: "cms-badge" });
      badges.appendChild(modeBadge);
      badges.appendChild(statusBadge);
      info.appendChild(title);
      info.appendChild(badges);

      const activateBtn = el("button", { type: "button", class: "cms-btn" }, "Activate");
      activateBtn.addEventListener("click", async () => {
        const t = tSig.peek();
        errSig.set("");
        okSig.set("");
        try {
          const res = await api.post("/api/admin/themes/activate", { slug: t.slug });
          okSig.set(`Theme "${t.name}" is now exclusively active (${res.mode} mode).`);
          const topBadge = document.querySelector(".cms-admin-topbar .cms-badge");
          if (topBadge) setSafeText(topBadge, `Active Theme: ${t.slug}`);
          invalidateQueries(["themes", "overview"]);
        } catch (err) {
          errSig.set(err.message || "Theme activation failed.");
        }
      });

      effect(() => {
        const t = tSig.get();
        setSafeText(title, `${t.name} (${t.slug}) v${t.version}`);
        const isVisual = t.engine === "grex-visual";
        setSafeText(modeBadge, isVisual ? "Grex Theme Builder (Visual)" : "Coded Theme");
        if (t.is_active === 1) {
          setSafeText(statusBadge, "Active (Exclusive Owner)");
          statusBadge.setAttribute("class", "cms-badge cms-badge-ok");
          activateBtn.setAttribute("disabled", "");
          setSafeText(activateBtn, "Active");
        } else {
          setSafeText(statusBadge, "Inactive");
          statusBadge.setAttribute("class", "cms-badge cms-badge-muted");
          activateBtn.removeAttribute("disabled");
          setSafeText(activateBtn, "Activate");
        }
      });

      row.appendChild(info);
      row.appendChild(activateBtn);
      li.appendChild(row);
      return { element: li };
    },
  });

  const stack = el("section", { class: "cms-stack" });
  stack.appendChild(listCard);
  stack.appendChild(regCard);
  root.appendChild(stack);
}

function mountSettings(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  const settingsQuery = useQuery(api, "/api/admin/settings", { tags: ["settings"] });
  const usersQuery = useQuery(api, "/api/admin/users", { tags: ["users"] });

  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  // Tab 1: General Settings
  const siteTitleIn = Input({ id: "set-site-title", props: { name: "site_title", label: "Site Title", required: true } });
  const siteTaglineIn = Input({ id: "set-site-tagline", props: { name: "site_tagline", label: "Site Tagline" } });
  const homeEntryIn = Input({ id: "set-home-entry", props: { name: "home_entry_id", label: "Static Home Entry ID (blank for feed)" } });
  const generalForm = Form({
    props: {
      csrfToken: () => getMeta("grablab-csrf"),
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        if (!siteTitleIn.validate()) return;
        try {
          await api.put("/api/admin/settings/general", {
            site_title: siteTitleIn.value.peek(),
            site_tagline: siteTaglineIn.value.peek(),
            home_entry_id: homeEntryIn.value.peek().trim(),
          });
          okSig.set("General site settings saved.");
          invalidateQueries(["settings", "overview"]);
        } catch (err) {
          errSig.set(err.message || "Failed to save general settings.");
        }
      },
    },
    children: [siteTitleIn.element, siteTaglineIn.element, homeEntryIn.element, { element: el("button", { type: "submit" }, "Save General Settings") }],
  });

  // Tab 2: Social Login (OAuth2/PKCE)
  const allowSignupSel = Select({
    id: "oauth-allow-signup",
    props: {
      name: "oauth_allow_signup",
      label: "Auto-Create Viewer Account on First OAuth Login",
      value: signal("false"),
      options: [
        { value: "false", label: "Disabled (Only link existing GrabLab users)" },
        { value: "true", label: "Enabled (New signups receive lowest 'viewer' role)" },
      ],
    },
  });

  const providerControls = {};
  const providerList = [
    { key: "google", label: "Google", hosts: "accounts.google.com,oauth2.googleapis.com,openidconnect.googleapis.com" },
    { key: "github", label: "GitHub", hosts: "github.com,api.github.com" },
    { key: "discord", label: "Discord", hosts: "discord.com" },
    { key: "apple", label: "Apple", hosts: "appleid.apple.com" },
  ];
  const oauthChildren = [
    el("p", { class: "cms-muted" }, "All social providers are disabled by default. Secrets are encrypted at rest via AES-256-GCM (GRABLAB_MASTER_KEY) and never exposed to browsers or templates."),
    allowSignupSel.element,
  ];
  for (const p of providerList) {
    const enabledSel = Select({
      id: `oauth-${p.key}-enabled`,
      props: {
        name: `${p.key}_enabled`,
        label: `${p.label} Login`,
        value: signal("false"),
        options: [
          { value: "false", label: "Disabled" },
          { value: "true", label: "Enabled" },
        ],
      },
    });
    const cidIn = Input({ id: `oauth-${p.key}-cid`, props: { name: `${p.key}_client_id`, label: `${p.label} Client ID` } });
    const secIn = Input({
      id: `oauth-${p.key}-secret`,
      props: { name: `${p.key}_client_secret`, type: "password", label: `${p.label} Client Secret (leave blank to keep existing)` },
    });
    const domIn = Input({ id: `oauth-${p.key}-domains`, props: { name: `${p.key}_allowed_domains`, label: `${p.label} Allowed Email Domains (optional comma-separated)` } });
    const hintP = el("p", { class: "cms-muted" }, `--allow-net hosts: ${p.hosts}`);
    const card = el("section", { class: "cms-card" });
    card.appendChild(el("h3", {}, p.label));
    card.appendChild(enabledSel.element);
    card.appendChild(cidIn.element);
    card.appendChild(secIn.element);
    card.appendChild(domIn.element);
    card.appendChild(hintP);
    providerControls[p.key] = { enabledSel, cidIn, secIn, domIn, hintP, hosts: p.hosts };
    oauthChildren.push(card);
  }
  oauthChildren.push({ element: el("button", { type: "submit" }, "Save Social Login Settings") });

  const oauthForm = Form({
    props: {
      csrfToken: () => getMeta("grablab-csrf"),
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        const providersPayload = {};
        for (const p of providerList) {
          const ctrl = providerControls[p.key];
          providersPayload[p.key] = {
            enabled: ctrl.enabledSel.value.peek() === "true",
            client_id: ctrl.cidIn.value.peek().trim(),
            client_secret: ctrl.secIn.value.peek(),
            allowed_domains: ctrl.domIn.value.peek().trim(),
          };
        }
        try {
          await api.put("/api/admin/settings/oauth", {
            oauth_allow_signup: allowSignupSel.value.peek() === "true",
            providers: providersPayload,
          });
          for (const p of providerList) {
            providerControls[p.key].secIn.value.set("");
          }
          okSig.set("OAuth2/PKCE settings saved with encrypted secrets.");
          invalidateQueries(["settings"]);
        } catch (err) {
          errSig.set(err.message || "Failed to save OAuth settings.");
        }
      },
    },
    children: oauthChildren,
  });

  effect(() => {
    const s = settingsQuery.data.get();
    if (!s) return;
    siteTitleIn.value.set(s.general?.site_title || "");
    siteTaglineIn.value.set(s.general?.site_tagline || "");
    homeEntryIn.value.set(s.general?.home_entry_id || "");
    allowSignupSel.value.set(s.oauth_allow_signup ? "true" : "false");
    const provs = s.oauth_providers || {};
    for (const p of providerList) {
      const info = provs[p.key] || {};
      const ctrl = providerControls[p.key];
      ctrl.enabledSel.value.set(info.enabled ? "true" : "false");
      ctrl.cidIn.value.set(info.client_id || "");
      ctrl.domIn.value.set(info.allowed_domains || "");
      const secState = info.has_secret ? `Secret stored (${info.secret_hint || "••••"})` : "No secret stored";
      setSafeText(ctrl.hintP, `${secState} · --allow-net ${ctrl.hosts}`);
    }
  });

  // Tab 3: Users & Roles
  const userModalOpen = signal(false);
  const newUserBtn = el("button", { type: "button", class: "cms-btn" }, "Create User");
  newUserBtn.addEventListener("click", () => userModalOpen.set(true));

  const uEmail = Input({ id: "new-user-email", props: { name: "email", type: "email", label: "Email", required: true } });
  const uName = Input({ id: "new-user-name", props: { name: "display_name", label: "Display Name", required: true } });
  const uRole = Select({
    id: "new-user-role",
    props: {
      name: "role",
      label: "Role",
      value: signal("author"),
      options: [
        { value: "admin", label: "Administrator" },
        { value: "editor", label: "Editor" },
        { value: "author", label: "Author" },
        { value: "viewer", label: "Viewer" },
      ],
    },
  });
  const uPass = Input({ id: "new-user-pass", props: { name: "password", type: "password", label: "Password (min 10 chars)", required: true, minLength: 10 } });
  const uCancel = el("button", { type: "button", class: "cms-btn-secondary" }, "Cancel");
  uCancel.addEventListener("click", () => userModalOpen.set(false));

  const userForm = Form({
    props: {
      csrfToken: () => getMeta("grablab-csrf"),
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        if (!uEmail.validate() || !uName.validate() || !uPass.validate()) return;
        try {
          await api.post("/api/admin/users", {
            email: uEmail.value.peek(),
            display_name: uName.value.peek(),
            role: uRole.value.peek(),
            password: uPass.value.peek(),
          });
          userModalOpen.set(false);
          uEmail.value.set("");
          uName.value.set("");
          uPass.value.set("");
          okSig.set("User account created.");
          invalidateQueries(["users"]);
        } catch (err) {
          errSig.set(err.message || "Failed to create user.");
        }
      },
    },
    children: [uEmail.element, uName.element, uRole.element, uPass.element, { element: el("button", { type: "submit" }, "Create User") }, { element: uCancel }],
  });

  const userModal = Modal({
    id: "create-user-modal",
    props: { open: userModalOpen, title: "Create User Account" },
    children: [userForm.element],
  });

  const usersUl = el("ul", { class: "cms-list" });
  const userItems = signal([]);
  effect(() => userItems.set(usersQuery.data.get()?.users || []));
  ForEach({
    parent: usersUl,
    items: userItems,
    key: (u) => u.id,
    render: (uSig) => {
      const li = el("li", { class: "cms-card" });
      const row = el("section", { class: "cms-row" });
      const info = el("section");
      const nameEl = el("strong");
      const metaEl = el("p", { class: "cms-muted" });
      info.appendChild(nameEl);
      info.appendChild(metaEl);

      const toggleBtn = el("button", { type: "button", class: "cms-btn-secondary" }, "Toggle Active");
      toggleBtn.addEventListener("click", async () => {
        const u = uSig.peek();
        errSig.set("");
        okSig.set("");
        try {
          await api.patch(`/api/admin/users/${u.id}`, {
            is_active: u.is_active === 1 ? false : true,
          });
          okSig.set(`Updated account status for ${u.email}.`);
          invalidateQueries(["users"]);
        } catch (err) {
          errSig.set(err.message || "Failed to update user.");
        }
      });

      effect(() => {
        const u = uSig.get();
        setSafeText(nameEl, `${u.display_name} (${u.email})`);
        setSafeText(metaEl, `Role: ${u.role} · Status: ${u.is_active === 1 ? "Active" : "Suspended"}`);
        setSafeText(toggleBtn, u.is_active === 1 ? "Suspend" : "Reactivate");
      });

      row.appendChild(info);
      row.appendChild(toggleBtn);
      li.appendChild(row);
      return { element: li };
    },
  });

  const usersTabContent = el("section", { class: "cms-stack" });
  const usersHead = el("section", { class: "cms-row" });
  usersHead.appendChild(el("h2", {}, "Users & Capabilities"));
  usersHead.appendChild(newUserBtn);
  usersTabContent.appendChild(usersHead);
  usersTabContent.appendChild(usersUl);
  usersTabContent.appendChild(userModal.element);

  // Tab 4: Author Mode & Groxy AI Bridge
  const authorEnSel = Select({
    id: "set-author-enabled",
    props: {
      name: "author_mode_enabled",
      label: "Author Mode & Embedded Bestseller Radar",
      value: signal("0"),
      options: [
        { value: "0", label: "Disabled (404 on /books, /series, /admin/author*)" },
        { value: "1", label: "Enabled" },
      ],
    },
  });
  const groxyOriginIn = Input({
    id: "set-groxy-origin",
    props: {
      name: "groxy_ai_origin",
      label: "Groxy AI Origin (GRAB-E402: https://... or http://127.0.0.1:<port>)",
      placeholder: "http://127.0.0.1:8090",
    },
  });
  const authorForm = Form({
    props: {
      csrfToken: () => getMeta("grablab-csrf"),
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        try {
          await api.post("/api/admin/author/settings", {
            author_mode_enabled: authorEnSel.value.peek() === "1",
            groxy_ai_origin: groxyOriginIn.value.peek().trim(),
          });
          okSig.set("Author Mode settings saved.");
          invalidateQueries(["settings"]);
        } catch (err) {
          errSig.set(err.message || "Failed to save Author Mode settings.");
        }
      },
    },
    children: [authorEnSel.element, groxyOriginIn.element, { element: el("button", { type: "submit" }, "Save Author Mode Settings") }],
  });
  api.get("/api/admin/author/settings")
    .then((as) => {
      authorEnSel.value.set(as && as.author_mode_enabled ? "1" : "0");
      groxyOriginIn.value.set((as && as.groxy_ai_origin) || "");
    })
    .catch(() => {});

  const tabs = Tabs({
    id: "settings-tabs",
    props: {
      label: "Admin Settings Sections",
      tabs: [
        { id: "general", label: "General", content: generalForm.element },
        { id: "oauth", label: "Social Login (OAuth2/PKCE)", content: oauthForm.element },
        { id: "users", label: "Users & Roles", content: usersTabContent },
        { id: "author", label: "Author Mode", content: authorForm.element },
      ],
    },
  });
  root.appendChild(tabs.element);
}

function mountMedia(root, api, role) {
  const errSig = signal("");
  const okSig = signal("");
  const mimeFilter = signal("");
  const mediaQuery = useQuery(api, "/api/admin/media", { tags: ["media"] });

  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const uploadOpen = signal(false);
  const openUploadBtn = el("button", { type: "button", class: "cms-btn" }, "Upload Media Asset");
  openUploadBtn.addEventListener("click", () => uploadOpen.set(true));

  const fileInput = el("input", {
    id: "media-file-input",
    type: "file",
    accept: "image/png,image/jpeg,image/webp,image/gif,application/pdf",
    required: "required",
  });
  const fileLabel = el("label", { for: "media-file-input", class: "cms-label-block" }, "Select File (PNG, JPEG, WebP, GIF, or PDF — SVG/Executables Blocked)");
  const fileSection = el("section", { class: "grex-input" });
  fileSection.appendChild(fileLabel);
  fileSection.appendChild(fileInput);

  const altIn = Input({ id: "media-alt", props: { name: "alt_text", label: "Alternative Text (WCAG AA Required for Images)", placeholder: "Describe image meaning for screen readers" } });
  const decCheck = el("input", { id: "media-decorative", type: "checkbox" });
  const decLabel = el("label", { for: "media-decorative", class: "cms-row" });
  decLabel.appendChild(decCheck);
  decLabel.appendChild(el("span", {}, "Purely decorative image (sets alt=\"\" and aria-hidden=\"true\")"));
  const capIn = Input({ id: "media-caption", props: { name: "caption", label: "Caption (Optional)" } });
  const closeUploadBtn = el("button", { type: "button", class: "cms-btn-secondary" }, "Cancel");
  closeUploadBtn.addEventListener("click", () => uploadOpen.set(false));

  const uploadForm = Form({
    props: {
      csrfToken: () => getMeta("grablab-csrf"),
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        const f = fileInput.files && fileInput.files[0];
        if (!f) {
          errSig.set("Please choose a PNG, JPEG, WebP, GIF, or PDF file.");
          return;
        }
        const isImg = (f.type || "").startsWith("image/");
        const altVal = altIn.value.peek().trim();
        const isDec = Boolean(decCheck.checked);
        if (isImg && !altVal && !isDec) {
          errSig.set("WCAG AA requires non-empty Alt Text or checking Purely Decorative before uploading an image.");
          return;
        }
        try {
          const dataUrl = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result || ""));
            reader.onerror = () => reject(new Error("Failed to read file."));
            reader.readAsDataURL(f);
          });
          await api.post("/api/admin/media/upload", {
            original_name: f.name,
            mime_type: f.type || "application/octet-stream",
            data_base64: dataUrl,
            alt_text: altVal,
            is_decorative: isDec,
            caption: capIn.value.peek().trim(),
          });
          uploadOpen.set(false);
          fileInput.value = "";
          altIn.value.set("");
          capIn.value.set("");
          decCheck.checked = false;
          okSig.set(`Uploaded "${f.name}" securely.`);
          invalidateQueries(["media"]);
        } catch (err) {
          errSig.set(err.message || "Upload failed.");
        }
      },
    },
    children: [fileSection, altIn.element, decLabel, capIn.element, el("section", { class: "cms-row" }, undefined)],
  });
  uploadForm.element.lastChild.appendChild(el("button", { type: "submit" }, "Verify & Upload"));
  uploadForm.element.lastChild.appendChild(closeUploadBtn);

  const uploadModal = Modal({
    id: "upload-media-modal",
    props: { open: uploadOpen, title: "Upload Media Asset" },
    children: [uploadForm.element],
  });

  const editOpen = signal(false);
  const editTargetId = signal(null);
  const editAltIn = Input({ id: "edit-media-alt", props: { name: "alt_text", label: "Alternative Text" } });
  const editDecChk = el("input", { id: "edit-media-dec", type: "checkbox" });
  const editDecLbl = el("label", { for: "edit-media-dec", class: "cms-row" });
  editDecLbl.appendChild(editDecChk);
  editDecLbl.appendChild(el("span", {}, "Decorative image"));
  const editCapIn = Input({ id: "edit-media-cap", props: { name: "caption", label: "Caption" } });
  const editCloseBtn = el("button", { type: "button", class: "cms-btn-secondary" }, "Cancel");
  editCloseBtn.addEventListener("click", () => editOpen.set(false));

  const editForm = Form({
    props: {
      csrfToken: () => getMeta("grablab-csrf"),
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        try {
          await api.patch(`/api/admin/media/${editTargetId.peek()}`, {
            alt_text: editAltIn.value.peek().trim(),
            is_decorative: Boolean(editDecChk.checked),
            caption: editCapIn.value.peek().trim(),
          });
          editOpen.set(false);
          okSig.set("Updated media accessibility metadata.");
          invalidateQueries(["media"]);
        } catch (err) {
          errSig.set(err.message || "Update failed.");
        }
      },
    },
    children: [editAltIn.element, editDecLbl, editCapIn.element, el("section", { class: "cms-row" })],
  });
  editForm.element.lastChild.appendChild(el("button", { type: "submit" }, "Save Metadata"));
  editForm.element.lastChild.appendChild(editCloseBtn);

  const editModal = Modal({
    id: "edit-media-modal",
    props: { open: editOpen, title: "Edit Media Metadata" },
    children: [editForm.element],
  });

  const filterSel = Select({
    id: "media-mime-filter",
    props: {
      name: "mime_filter",
      label: "Filter Asset Type",
      value: mimeFilter,
      options: [
        { value: "", label: "All Media" },
        { value: "image/", label: "Images Only" },
        { value: "application/pdf", label: "PDF Documents" },
      ],
    },
  });

  const listCard = el("section", { class: "cms-card" });
  const headRow = el("section", { class: "cms-row" });
  headRow.appendChild(el("h2", {}, "Uploaded Media Assets"));
  headRow.appendChild(openUploadBtn);
  listCard.appendChild(headRow);
  listCard.appendChild(filterSel.element);

  const gridUl = el("ul", { class: "cms-media-grid" });
  listCard.appendChild(gridUl);

  const filteredItems = signal([]);
  effect(() => {
    const all = mediaQuery.data.get()?.media || [];
    const pref = mimeFilter.get();
    filteredItems.set(pref ? all.filter((m) => (m.mime_type || "").startsWith(pref)) : all);
  });

  ForEach({
    parent: gridUl,
    items: filteredItems,
    key: (m) => m.id,
    empty: () => ({ element: el("li", { class: "cms-muted" }, "No media assets uploaded yet.") }),
    render: (mSig) => {
      const li = el("li", { class: "cms-card" });
      const titleEl = el("h3");
      const metaEl = el("p", { class: "cms-muted" });
      const altBadge = el("span", { class: "cms-badge" });
      const urlCode = el("p", { class: "cms-code-line" });
      const actRow = el("section", { class: "cms-row" });
      const editBtn = el("button", { type: "button", class: "cms-btn-secondary" }, "Edit Alt / Caption");
      const delBtn = el("button", { type: "button", class: "cms-btn-danger" }, "Delete");
      actRow.appendChild(editBtn);
      actRow.appendChild(delBtn);

      editBtn.addEventListener("click", () => {
        const m = mSig.peek();
        editTargetId.set(m.id);
        editAltIn.value.set(m.alt_text || "");
        editDecChk.checked = Boolean(m.is_decorative);
        editCapIn.value.set(m.caption || "");
        editOpen.set(true);
      });

      delBtn.addEventListener("click", async () => {
        const m = mSig.peek();
        errSig.set("");
        okSig.set("");
        try {
          await api.delete(`/api/admin/media/${m.id}`);
          okSig.set(`Deleted "${m.original_name}".`);
          invalidateQueries(["media"]);
        } catch (err) {
          errSig.set(err.message || "Delete failed.");
        }
      });

      effect(() => {
        const m = mSig.get();
        setSafeText(titleEl, m.original_name);
        const dims = m.width && m.height ? `${m.width}x${m.height} px · ` : "";
        setSafeText(metaEl, `${m.mime_type} · ${dims}${m.byte_size} bytes`);
        setSafeText(urlCode, m.url);
        if (m.is_decorative) {
          setSafeText(altBadge, "Decorative (aria-hidden)");
          altBadge.setAttribute("class", "cms-badge cms-badge-muted");
        } else if (m.alt_text) {
          setSafeText(altBadge, `Alt: ${m.alt_text}`);
          altBadge.setAttribute("class", "cms-badge cms-badge-ok");
        } else {
          setSafeText(altBadge, m.mime_type === "application/pdf" ? "Document (PDF)" : "Missing Alt");
          altBadge.setAttribute("class", "cms-badge cms-badge-muted");
        }
      });

      li.appendChild(titleEl);
      li.appendChild(metaEl);
      li.appendChild(altBadge);
      li.appendChild(urlCode);
      li.appendChild(actRow);
      return { element: li };
    },
  });

  const stack = el("section", { class: "cms-stack" });
  stack.appendChild(listCard);
  stack.appendChild(uploadModal.element);
  stack.appendChild(editModal.element);
  root.appendChild(stack);
}

function mountMenus(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  const menusQuery = useQuery(api, "/api/admin/menus", { tags: ["menus"] });
  const entriesQuery = useQuery(api, "/api/entries", { tags: ["entries"] });

  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const selectedMenuId = signal(null);
  const workingItems = signal([]);
  const dragFromIdx = signal(null);

  const flattenTree = (nodes, depth = 1, parentKey = "") => {
    const out = [];
    for (const n of nodes || []) {
      const ck = `item_${n.id}`;
      out.push({
        client_id: ck,
        parent_key: parentKey,
        depth,
        label: n.label,
        link_type: n.link_type,
        entry_id: n.entry_id || null,
        external_url: n.external_url || "",
        target_blank: Boolean(n.target_blank),
        css_class: n.css_class || "",
      });
      if (n.children && n.children.length > 0) {
        out.push(...flattenTree(n.children, depth + 1, ck));
      }
    }
    return out;
  };

  effect(() => {
    const menus = menusQuery.data.get()?.menus || [];
    if (menus.length > 0 && !selectedMenuId.peek()) {
      selectedMenuId.set(menus[0].id);
      workingItems.set(flattenTree(menus[0].items || []));
    } else if (selectedMenuId.peek()) {
      const cur = menus.find((m) => m.id === selectedMenuId.peek());
      if (cur && workingItems.peek().length === 0) {
        workingItems.set(flattenTree(cur.items || []));
      }
    }
  });

  const newSlugIn = Input({ id: "menu-new-slug", props: { name: "slug", label: "Menu Slug", required: true, placeholder: "footer-nav" } });
  const newNameIn = Input({ id: "menu-new-name", props: { name: "name", label: "Menu Name", required: true, placeholder: "Footer Links" } });
  const newLocSel = Select({
    id: "menu-new-loc",
    props: {
      name: "location",
      label: "Theme Location",
      value: signal(""),
      options: [
        { value: "", label: "Unassigned" },
        { value: "primary", label: "Primary Navigation (primary)" },
        { value: "footer", label: "Footer Links (footer)" },
        { value: "mobile", label: "Mobile Drawer (mobile)" },
      ],
    },
  });
  const createMenuForm = Form({
    props: {
      csrfToken: () => getMeta("grablab-csrf"),
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        if (!newSlugIn.validate() || !newNameIn.validate()) return;
        try {
          const res = await api.post("/api/admin/menus", {
            slug: newSlugIn.value.peek(),
            name: newNameIn.value.peek(),
            location: newLocSel.value.peek() || null,
          });
          newSlugIn.value.set("");
          newNameIn.value.set("");
          okSig.set(`Created menu "${res.menu.name}".`);
          selectedMenuId.set(res.menu.id);
          workingItems.set([]);
          invalidateQueries(["menus"]);
        } catch (err) {
          errSig.set(err.message || "Failed to create menu.");
        }
      },
    },
    children: [newSlugIn.element, newNameIn.element, newLocSel.element, { element: el("button", { type: "submit" }, "Create Menu") }],
  });

  const createCard = el("section", { class: "cms-card" });
  createCard.appendChild(el("h2", {}, "Create Menu"));
  createCard.appendChild(createMenuForm.element);

  const menuSel = Select({
    id: "menu-active-select",
    props: {
      name: "menu_id",
      label: "Select Menu to Edit",
      value: signal(""),
      options: () => (menusQuery.data.get()?.menus || []).map((m) => ({ value: String(m.id), label: `${m.name} (${m.location || "unassigned"})` })),
    },
  });
  effect(() => {
    const mid = selectedMenuId.get();
    if (mid) menuSel.value.set(String(mid));
  });
  menuSel.element.querySelector("select").addEventListener("change", (ev) => {
    const idNum = parseInt(ev.target.value, 10);
    const menus = menusQuery.data.get()?.menus || [];
    const found = menus.find((m) => m.id === idNum);
    selectedMenuId.set(idNum);
    workingItems.set(found ? flattenTree(found.items || []) : []);
  });

  const slotSel = Select({
    id: "menu-slot-select",
    props: {
      name: "slot_location",
      label: "Assign Theme Location",
      value: signal(""),
      options: [
        { value: "", label: "Unassigned" },
        { value: "primary", label: "primary (Header)" },
        { value: "footer", label: "footer (Footer)" },
        { value: "mobile", label: "mobile (Drawer)" },
      ],
    },
  });
  const assignSlotBtn = el("button", { type: "button", class: "cms-btn-secondary" }, "Assign Location Atomically");
  assignSlotBtn.addEventListener("click", async () => {
    const mid = selectedMenuId.peek();
    if (!mid) return;
    errSig.set("");
    okSig.set("");
    try {
      await api.put(`/api/admin/menus/${mid}`, { location: slotSel.value.peek() || null });
      okSig.set("Updated exclusive theme menu location.");
      invalidateQueries(["menus"]);
    } catch (err) {
      errSig.set(err.message || "Failed to assign location.");
    }
  });

  const addLblIn = Input({ id: "mi-label", props: { name: "label", label: "Link Label", required: true, placeholder: "Docs" } });
  const linkTypeSel = Select({
    id: "mi-type",
    props: {
      name: "link_type",
      label: "Link Type",
      value: signal("entry"),
      options: [
        { value: "entry", label: "Dynamic Published Entry" },
        { value: "external", label: "External URL (https:// or http://)" },
      ],
    },
  });
  const entryPickSel = Select({
    id: "mi-entry",
    props: {
      name: "entry_id",
      label: "Target Entry (Permalink Auto-Resolved)",
      value: signal(""),
      options: () => (entriesQuery.data.get()?.entries || []).map((e) => ({ value: String(e.id), label: `${e.title} (${e.full_path})` })),
    },
  });
  const extUrlIn = Input({ id: "mi-ext-url", props: { name: "external_url", label: "External URL", placeholder: "https://grab-lang.org" } });

  const addItemBtn = el("button", { type: "button" }, "Add Item to Builder");
  addItemBtn.addEventListener("click", () => {
    errSig.set("");
    if (!addLblIn.validate()) return;
    const lt = linkTypeSel.value.peek();
    const cur = [...workingItems.peek()];
    const cid = `new_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    if (lt === "entry") {
      const eid = parseInt(entryPickSel.value.peek(), 10);
      if (!Number.isInteger(eid) || eid < 1) {
        errSig.set("Please select an entry.");
        return;
      }
      cur.push({ client_id: cid, parent_key: "", depth: 1, label: addLblIn.value.peek().trim(), link_type: "entry", entry_id: eid, external_url: "", target_blank: false, css_class: "" });
    } else {
      const u = extUrlIn.value.peek().trim();
      if (!u.toLowerCase().startsWith("https://") && !u.toLowerCase().startsWith("http://")) {
        errSig.set("External URL must start with https:// or http://.");
        return;
      }
      cur.push({ client_id: cid, parent_key: "", depth: 1, label: addLblIn.value.peek().trim(), link_type: "external", entry_id: null, external_url: u, target_blank: true, css_class: "" });
    }
    addLblIn.value.set("");
    extUrlIn.value.set("");
    workingItems.set(cur);
  });

  const recomputeParentsFromDepth = (list) => {
    const stackAtDepth = {};
    return list.map((it) => {
      const d = Math.max(1, Math.min(4, it.depth || 1));
      const pKey = d > 1 ? stackAtDepth[d - 1] || "" : "";
      const effDepth = pKey ? d : 1;
      stackAtDepth[effDepth] = it.client_id;
      return { ...it, depth: effDepth, parent_key: pKey };
    });
  };

  const reorderItem = (idx, dir) => {
    const arr = [...workingItems.peek()];
    const nextIdx = idx + dir;
    if (nextIdx < 0 || nextIdx >= arr.length) return;
    const [moved] = arr.splice(idx, 1);
    arr.splice(nextIdx, 0, moved);
    workingItems.set(recomputeParentsFromDepth(arr));
  };

  const changeDepth = (idx, delta) => {
    const arr = [...workingItems.peek()];
    if (idx === 0 && delta > 0) return;
    const target = { ...arr[idx] };
    const nextD = Math.max(1, Math.min(4, (target.depth || 1) + delta));
    if (idx > 0 && nextD > (arr[idx - 1].depth || 1) + 1) return;
    target.depth = nextD;
    arr[idx] = target;
    workingItems.set(recomputeParentsFromDepth(arr));
  };

  const itemsUl = el("ul", { class: "cms-list", "aria-label": "Menu Items Order and Nesting Builder" });
  effect(() => {
    const arr = workingItems.get();
    itemsUl.replaceChildren();
    if (arr.length === 0) {
      itemsUl.appendChild(el("li", { class: "cms-muted" }, "No items yet. Add items above and reorder with drag-and-drop or keyboard controls."));
      return;
    }
    arr.forEach((it, idx) => {
      const li = el("li", {
        class: `cms-card cms-menu-item cms-menu-depth-${it.depth || 1}`,
        draggable: "true",
      });
      li.addEventListener("dragstart", () => dragFromIdx.set(idx));
      li.addEventListener("dragover", (ev) => {
        ev.preventDefault();
        li.classList.add("cms-drop-target");
      });
      li.addEventListener("dragleave", () => li.classList.remove("cms-drop-target"));
      li.addEventListener("drop", (ev) => {
        ev.preventDefault();
        li.classList.remove("cms-drop-target");
        const from = dragFromIdx.peek();
        if (from !== null && from !== idx) {
          const next = [...workingItems.peek()];
          const [moved] = next.splice(from, 1);
          next.splice(idx, 0, moved);
          workingItems.set(recomputeParentsFromDepth(next));
        }
        dragFromIdx.set(null);
      });

      const row = el("section", { class: "cms-row" });
      const info = el("section");
      const ttl = el("strong");
      setSafeText(ttl, `${it.label}`);
      const sub = el("p", { class: "cms-muted" });
      setSafeText(sub, `Depth ${it.depth || 1}/4 · ${it.link_type === "entry" ? `Entry #${it.entry_id}` : it.external_url}`);
      info.appendChild(ttl);
      info.appendChild(sub);

      const ctrls = el("section", { class: "cms-topbar-right" });
      const upBtn = el("button", { type: "button", class: "cms-btn-secondary", "aria-label": `Move ${it.label} up` }, "Up");
      const dnBtn = el("button", { type: "button", class: "cms-btn-secondary", "aria-label": `Move ${it.label} down` }, "Down");
      const inBtn = el("button", { type: "button", class: "cms-btn-secondary", "aria-label": `Indent ${it.label}` }, "Indent");
      const outBtn = el("button", { type: "button", class: "cms-btn-secondary", "aria-label": `Outdent ${it.label}` }, "Outdent");
      const rmBtn = el("button", { type: "button", class: "cms-btn-danger", "aria-label": `Remove ${it.label}` }, "Remove");

      upBtn.addEventListener("click", () => reorderItem(idx, -1));
      dnBtn.addEventListener("click", () => reorderItem(idx, 1));
      inBtn.addEventListener("click", () => changeDepth(idx, 1));
      outBtn.addEventListener("click", () => changeDepth(idx, -1));
      rmBtn.addEventListener("click", () => {
        const next = [...workingItems.peek()];
        next.splice(idx, 1);
        workingItems.set(recomputeParentsFromDepth(next));
      });

      ctrls.appendChild(upBtn);
      ctrls.appendChild(dnBtn);
      ctrls.appendChild(inBtn);
      ctrls.appendChild(outBtn);
      ctrls.appendChild(rmBtn);
      row.appendChild(info);
      row.appendChild(ctrls);
      li.appendChild(row);
      itemsUl.appendChild(li);
    });
  });

  const saveTreeBtn = el("button", { type: "button" }, "Save Menu Hierarchy");
  saveTreeBtn.addEventListener("click", async () => {
    const mid = selectedMenuId.peek();
    if (!mid) return;
    errSig.set("");
    okSig.set("");
    try {
      const normalized = recomputeParentsFromDepth(workingItems.peek());
      await api.put(`/api/admin/menus/${mid}/items`, { items: normalized });
      okSig.set("Saved menu order and nested hierarchy (max depth 4 validated).");
      invalidateQueries(["menus"]);
    } catch (err) {
      errSig.set(err.message || "Failed to save menu items.");
    }
  });

  const builderCard = el("section", { class: "cms-card" });
  builderCard.appendChild(el("h2", {}, "Menu Order & Nesting Builder"));
  builderCard.appendChild(menuSel.element);
  builderCard.appendChild(slotSel.element);
  builderCard.appendChild(assignSlotBtn);
  builderCard.appendChild(addLblIn.element);
  builderCard.appendChild(linkTypeSel.element);
  builderCard.appendChild(entryPickSel.element);
  builderCard.appendChild(extUrlIn.element);
  builderCard.appendChild(addItemBtn);
  builderCard.appendChild(itemsUl);
  builderCard.appendChild(saveTreeBtn);

  const stack = el("section", { class: "cms-stack" });
  stack.appendChild(builderCard);
  stack.appendChild(createCard);
  root.appendChild(stack);
}

function mountTaxonomies(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  const taxQuery = useQuery(api, "/api/admin/taxonomies", { tags: ["taxonomies"] });

  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const tSlugIn = Input({ id: "tax-slug", props: { name: "slug", label: "Taxonomy Slug", required: true, placeholder: "topic" } });
  const tSingIn = Input({ id: "tax-sing", props: { name: "label_singular", label: "Singular Label", required: true, placeholder: "Topic" } });
  const tPlurIn = Input({ id: "tax-plur", props: { name: "label_plural", label: "Plural Label", required: true, placeholder: "Topics" } });
  const tArchIn = Input({ id: "tax-arch", props: { name: "archive_slug", label: "Archive URL Prefix", required: true, placeholder: "topic" } });
  const tHierChk = el("input", { id: "tax-hier", type: "checkbox" });
  const tHierLbl = el("label", { for: "tax-hier", class: "cms-row" });
  tHierLbl.appendChild(tHierChk);
  tHierLbl.appendChild(el("span", {}, "Hierarchical taxonomy (supports parent/child terms)"));
  const tCtsIn = Input({ id: "tax-cts", props: { name: "content_types", label: "Attached Content Types (CSV)", value: "post" } });

  const createTaxForm = Form({
    props: {
      csrfToken: () => getMeta("grablab-csrf"),
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        if (!tSlugIn.validate() || !tSingIn.validate() || !tPlurIn.validate() || !tArchIn.validate()) return;
        const cts = tCtsIn.value.peek().split(",").map((s) => s.trim()).filter(Boolean);
        try {
          await api.post("/api/admin/taxonomies", {
            slug: tSlugIn.value.peek(),
            label_singular: tSingIn.value.peek(),
            label_plural: tPlurIn.value.peek(),
            archive_slug: tArchIn.value.peek(),
            is_hierarchical: Boolean(tHierChk.checked),
            content_type_slugs: cts,
          });
          tSlugIn.value.set("");
          tSingIn.value.set("");
          tPlurIn.value.set("");
          tArchIn.value.set("");
          okSig.set("Custom taxonomy created.");
          invalidateQueries(["taxonomies"]);
        } catch (err) {
          errSig.set(err.message || "Failed to create taxonomy.");
        }
      },
    },
    children: [tSlugIn.element, tSingIn.element, tPlurIn.element, tArchIn.element, tHierLbl, tCtsIn.element, { element: el("button", { type: "submit" }, "Create Taxonomy") }],
  });

  const taxSelect = Select({
    id: "term-tax-select",
    props: {
      name: "taxonomy_slug",
      label: "Target Taxonomy",
      value: signal("category"),
      options: () => (taxQuery.data.get()?.taxonomies || []).map((t) => ({ value: t.slug, label: `${t.label_plural} (/${t.archive_slug}/:slug)` })),
    },
  });
  const termSlugIn = Input({ id: "term-slug", props: { name: "slug", label: "Term Slug", required: true, placeholder: "tutorials" } });
  const termNameIn = Input({ id: "term-name", props: { name: "name", label: "Term Name", required: true, placeholder: "Tutorials" } });
  const termParentSel = Select({
    id: "term-parent",
    props: {
      name: "parent_id",
      label: "Parent Term (Hierarchical Only)",
      value: signal(""),
      options: () => {
        const all = taxQuery.data.get()?.taxonomies || [];
        const cur = all.find((t) => t.slug === taxSelect.value.get());
        const opts = [{ value: "", label: "None (Top Level)" }];
        if (cur && cur.is_hierarchical) {
          for (const tm of cur.terms || []) {
            opts.push({ value: String(tm.id), label: tm.name });
          }
        }
        return opts;
      },
    },
  });
  const termDescIn = Input({ id: "term-desc", props: { name: "description", label: "Archive Description" } });

  const createTermForm = Form({
    props: {
      csrfToken: () => getMeta("grablab-csrf"),
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        if (!termSlugIn.validate() || !termNameIn.validate()) return;
        const pid = termParentSel.value.peek();
        try {
          await api.post(`/api/admin/taxonomies/${taxSelect.value.peek()}/terms`, {
            slug: termSlugIn.value.peek(),
            name: termNameIn.value.peek(),
            parent_id: pid ? parseInt(pid, 10) : null,
            description: termDescIn.value.peek(),
          });
          termSlugIn.value.set("");
          termNameIn.value.set("");
          termDescIn.value.set("");
          okSig.set("Term added.");
          invalidateQueries(["taxonomies"]);
        } catch (err) {
          errSig.set(err.message || "Failed to add term.");
        }
      },
    },
    children: [taxSelect.element, termSlugIn.element, termNameIn.element, termParentSel.element, termDescIn.element, { element: el("button", { type: "submit" }, "Add Term") }],
  });

  const taxUl = el("ul", { class: "cms-list" });
  const taxItems = signal([]);
  effect(() => taxItems.set(taxQuery.data.get()?.taxonomies || []));
  ForEach({
    parent: taxUl,
    items: taxItems,
    key: (t) => t.slug,
    render: (tSig) => {
      const li = el("li", { class: "cms-card" });
      const title = el("h3");
      const meta = el("p", { class: "cms-muted" });
      const termList = el("p");
      effect(() => {
        const t = tSig.get();
        setSafeText(title, `${t.label_plural} (${t.slug})`);
        setSafeText(meta, `Archive: /${t.archive_slug}/:slug · ${t.is_hierarchical ? "Hierarchical" : "Flat"} · Types: ${(t.content_type_slugs || []).join(", ")}`);
        const tSummary = (t.terms || []).map((tm) => `#${tm.id} ${tm.name} (/${t.archive_slug}/${tm.slug})`).join(" · ") || "No terms yet";
        setSafeText(termList, tSummary);
      });
      li.appendChild(title);
      li.appendChild(meta);
      li.appendChild(termList);
      return { element: li };
    },
  });

  const listCard = el("section", { class: "cms-card" });
  listCard.appendChild(el("h2", {}, "Registered Taxonomies & Terms"));
  listCard.appendChild(taxUl);

  const termCard = el("section", { class: "cms-card" });
  termCard.appendChild(el("h2", {}, "Add Term"));
  termCard.appendChild(createTermForm.element);

  const taxCard = el("section", { class: "cms-card" });
  taxCard.appendChild(el("h2", {}, "Create Custom Taxonomy"));
  taxCard.appendChild(createTaxForm.element);

  const stack = el("section", { class: "cms-stack" });
  stack.appendChild(listCard);
  stack.appendChild(termCard);
  stack.appendChild(taxCard);
  root.appendChild(stack);
}

function wireLogout(api) {
  const btn = document.getElementById("admin-logout-btn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    try {
      await api.post("/api/auth/logout", {});
    } catch {
      // Ignore and redirect to login
    }
    window.location.assign("/login");
  });
}

function boot() {
  applyAdminTheme();
  const page = getMeta("grablab-page");
  const api = createApiClient();

  if (page === "login") {
    mountLogin(api);
    return;
  }
  if (page === "setup") {
    mountSetup();
    return;
  }

  const role = getMeta("grablab-role");
  const activePath = window.location.pathname;
  mountSidebarNav(activePath, role, api);
  wireLogout(api);

  const root = document.getElementById("admin-app");
  if (!root) return;

  if (page === "overview") {
    mountOverview(root, api);
  } else if (page === "entries") {
    mountEntries(root, api, role);
  } else if (page === "media") {
    mountMedia(root, api, role);
  } else if (page === "menus") {
    mountMenus(root, api);
  } else if (page === "taxonomies") {
    mountTaxonomies(root, api);
  } else if (page === "types") {
    mountTypes(root, api);
  } else if (page === "themes") {
    mountThemes(root, api);
  } else if (page === "settings") {
    mountSettings(root, api);
  } else if (page === "store" || page.startsWith("store_")) {
    import("./commerce.js").then((mod) => mod.mountCommerce(root, api, page, role));
  } else if (page === "author" || page.startsWith("author_")) {
    import("./author.js").then((mod) => mod.mountAuthor(root, api, page, role));
  }
}

boot();
