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
      bg: "#f8fafc",
      surface: "#ffffff",
      ink: "#0f172a",
      muted: "#475569",
      accent: "#0d9488",
      "accent-ink": "#ffffff",
    },
    radii: { radius: "12px" },
  });
  theme.applyTo(document.documentElement);

  const cm = createClassManager({ prefix: "cms-grex-" });
  cm.registerClass("panel", {
    background: "#ffffff",
    borderRadius: "12px",
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
    children: [makeAlert(errSig, false), emailInput.element, passInput.element, submitBtn],
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
    children: [makeAlert(errSig, false), nameInput.element, emailInput.element, passInput.element, submitBtn],
  });
  mount.appendChild(form.element);
}

function mountSidebarNav(activePath, role) {
  const mount = document.getElementById("admin-nav-mount");
  if (!mount) return;
  const items = [
    { href: "/admin", text: "Overview" },
    { href: "/admin/entries", text: "Entries & Redirects" },
  ];
  if (role === "admin") {
    items.push({ href: "/admin/types", text: "Content Types" });
    items.push({ href: "/admin/themes", text: "Themes & Grex" });
    items.push({ href: "/admin/settings", text: "Settings & Users" });
  }
  const nav = Nav({
    id: "grablab-admin-nav",
    props: {
      label: "GrabLab Admin Sections",
      activePath,
      items,
    },
  });
  mount.appendChild(nav.element);
}

function mountOverview(root, api) {
  const errSig = signal("");
  const overviewQuery = useQuery(api, "/api/admin/overview", { tags: ["overview"] });
  root.appendChild(makeAlert(errSig, false));

  const statsGrid = el("section", { class: "cms-grid", "aria-label": "Site summary" });
  const recentCard = el("section", { class: "cms-card" });
  recentCard.appendChild(el("h2", {}, "Recent Entries"));
  const listMount = el("ul", { class: "cms-list" });
  recentCard.appendChild(listMount);

  const itemsSig = signal([]);
  ForEach({
    parent: listMount,
    items: itemsSig,
    key: (item) => item.id,
    empty: () => el("li", { class: "cms-muted" }, "No entries created yet."),
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
      return li;
    },
  });

  effect(() => {
    if (overviewQuery.error.get()) {
      errSig.set(overviewQuery.error.get().message || "Failed to load overview.");
      return;
    }
    const data = overviewQuery.data.get();
    if (!data) return;
    while (statsGrid.firstChild) statsGrid.removeChild(statsGrid.firstChild);
    const cards = [
      { label: "Total Entries", value: String(data.entry_count ?? 0) },
      { label: "Content Types", value: String(data.type_count ?? 0) },
      { label: "Active Theme", value: `${data.active_theme_slug} (${data.active_theme_mode})` },
      { label: "301 Redirects", value: String(data.redirect_count ?? 0) },
    ];
    for (const c of cards) {
      const art = el("article", { class: "cms-card" });
      art.appendChild(el("span", { class: "cms-muted" }, c.label));
      art.appendChild(el("p", { class: "cms-stat-num" }, c.value));
      statsGrid.appendChild(art);
    }
    itemsSig.set(data.recent_entries || []);
  });

  root.appendChild(statsGrid);
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
  });

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
            });
            okSig.set("Entry created.");
          }
          editingId.set(null);
          submitLabel.set("Create Entry");
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
    empty: () => el("li", { class: "cms-muted" }, "No matching entries."),
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
      return li;
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
    empty: () => el("li", { class: "cms-muted" }, "No 301 redirects recorded yet."),
    render: (rSig) => {
      const li = el("li");
      effect(() => {
        const r = rSig.get();
        setSafeText(li, `${r.old_path} -> ${r.target_path} (301)`);
      });
      return li;
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
    children: [slugIn.element, singIn.element, plurIn.element, patIn.element, archIn.element, el("button", { type: "submit" }, "Create Type"), closeBtn],
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
      return li;
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
    children: [targetTypeSel.element, fkIn.element, flIn.element, ftSel.element, el("button", { type: "submit" }, "Add Field")],
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
    children: [regSlug.element, el("button", { type: "submit" }, "Validate & Register Theme")],
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
      return li;
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
    children: [siteTitleIn.element, siteTaglineIn.element, homeEntryIn.element, el("button", { type: "submit" }, "Save General Settings")],
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
  oauthChildren.push(el("button", { type: "submit" }, "Save Social Login Settings"));

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
    children: [uEmail.element, uName.element, uRole.element, uPass.element, el("button", { type: "submit" }, "Create User"), uCancel],
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
      return li;
    },
  });

  const usersTabContent = el("section", { class: "cms-stack" });
  const usersHead = el("section", { class: "cms-row" });
  usersHead.appendChild(el("h2", {}, "Users & Capabilities"));
  usersHead.appendChild(newUserBtn);
  usersTabContent.appendChild(usersHead);
  usersTabContent.appendChild(usersUl);
  usersTabContent.appendChild(userModal.element);

  const tabs = Tabs({
    id: "settings-tabs",
    props: {
      label: "Admin Settings Sections",
      tabs: [
        { id: "general", label: "General", content: generalForm.element },
        { id: "oauth", label: "Social Login (OAuth2/PKCE)", content: oauthForm.element },
        { id: "users", label: "Users & Roles", content: usersTabContent },
      ],
    },
  });
  root.appendChild(tabs.element);
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
  mountSidebarNav(activePath, role);
  wireLogout(api);

  const root = document.getElementById("admin-app");
  if (!root) return;

  if (page === "overview") {
    mountOverview(root, api);
  } else if (page === "entries") {
    mountEntries(root, api, role);
  } else if (page === "types") {
    mountTypes(root, api);
  } else if (page === "themes") {
    mountThemes(root, api);
  } else if (page === "settings") {
    mountSettings(root, api);
  }
}

boot();
