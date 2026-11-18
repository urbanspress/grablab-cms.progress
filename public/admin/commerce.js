/**
 * GrabLab CMS v1.1.0 Admin Commerce Module (Pure Grex JS v1.0.0)
 * Sections: overview (store), products, orders, coupons, customers, settings.
 * - Zero <div>, zero innerHTML writes, zero dynamic eval
 * - ADR-025c exact string inputs (inputmode="decimal") validated via isExactGrabWireString
 * - Orders totals strictly read-only; transitions emit order_audit rows
 * - Webhook secrets rendered strictly as Configured / Not set status badges
 */

import {
  signal,
  setSafeText,
  isExactGrabWireString,
  Tabs,
  Modal,
  Form,
  Input,
  Select,
  ForEach,
} from "../grex/grex.js";

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

function clearEl(parent) {
  while (parent.firstChild) {
    parent.removeChild(parent.firstChild);
  }
}

function makeAlert(msgSig, ok = false) {
  const p = node("p", { role: "status" });
  const render = () => {
    const val = msgSig.get();
    if (!val) {
      p.hidden = true;
      setSafeText(p, "");
      p.className = "";
    } else {
      p.hidden = false;
      setSafeText(p, val);
      p.className = ok ? "cms-alert-ok" : "cms-alert-error";
    }
  };
  msgSig.subscribe(render);
  render();
  return p;
}

export function buildStoreSubnav(activeSection, canSettings) {
  const nav = node("nav", { class: "cms-subnav", "aria-label": "Commerce sections" });
  const links = [
    { key: "store", href: "/admin/store", label: "Dashboard" },
    { key: "store_products", href: "/admin/store/products", label: "Products" },
    { key: "store_orders", href: "/admin/store/orders", label: "Orders" },
    { key: "store_coupons", href: "/admin/store/coupons", label: "Coupons" },
    { key: "store_customers", href: "/admin/store/customers", label: "Customers" },
  ];
  if (canSettings) {
    links.push({ key: "store_settings", href: "/admin/store/settings", label: "Settings" });
  }
  for (const ln of links) {
    const a = node(
      "a",
      {
        href: ln.href,
        class: activeSection === ln.key ? "cms-badge cms-badge-ok" : "cms-badge cms-badge-muted",
        "aria-current": activeSection === ln.key ? "page" : false,
      },
      ln.label
    );
    nav.appendChild(a);
  }
  return nav;
}

export function createStoreDashboardSpec(overview) {
  const counts = overview && overview.counts ? overview.counts : {};
  const section = node("section", { class: "cms-stack", "aria-label": "Store overview" });
  const stats = node("section", { class: "cms-grid", "aria-label": "Store metrics" });
  const cards = [
    ["Store Status", overview && overview.enabled ? "Enabled (USD)" : "Disabled"],
    ["Products", String(counts.products || 0)],
    ["Orders", String(counts.orders || 0)],
    ["Needs Review", String(counts.needs_review || 0)],
    ["Coupons", String(counts.coupons || 0)],
    ["Customers", String(counts.customers || 0)],
  ];
  for (const [label, val] of cards) {
    const c = node("article", { class: "cms-card" });
    c.appendChild(node("p", { class: "cms-muted" }, label));
    c.appendChild(node("p", { class: "cms-stat" }, val));
    stats.appendChild(c);
  }
  section.appendChild(stats);

  const reviewCard = node("section", { class: "cms-card", "aria-labelledby": "needs-review-h" });
  reviewCard.appendChild(node("h2", { id: "needs-review-h" }, "Orders Needing Merchant Review"));
  const revOrders = Array.isArray(overview && overview.needs_review_orders) ? overview.needs_review_orders : [];
  if (revOrders.length === 0) {
    reviewCard.appendChild(node("p", { class: "cms-muted" }, "No orders flagged for review."));
  } else {
    const ul = node("ul", { class: "cms-list", role: "list" });
    for (const o of revOrders) {
      ul.appendChild(
        node("li", { class: "cms-list-row" }, o.number + " — " + o.status + " ($" + o.total + ") — " + (o.review_note || "Review required"))
      );
    }
    reviewCard.appendChild(ul);
  }
  section.appendChild(reviewCard);
  return section;
}

async function mountOverviewSection(root, api) {
  const errSig = signal("");
  root.appendChild(makeAlert(errSig, false));
  const mount = node("section", { class: "cms-stack" });
  root.appendChild(mount);
  try {
    const data = await api.get("/api/admin/commerce/overview");
    clearEl(mount);
    mount.appendChild(createStoreDashboardSpec(data));
  } catch (err) {
    errSig.set(err && err.message ? err.message : "Failed to load commerce overview.");
  }
}

async function mountProductsSection(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const listCard = node("section", { class: "cms-card" });
  listCard.appendChild(node("h2", {}, "Catalog Products"));
  const listMount = node("ul", { class: "cms-list", role: "list" });
  listCard.appendChild(listMount);

  const productsSig = signal([]);
  ForEach({
    parent: listMount,
    items: productsSig,
    key: (p) => p.id,
    empty: () => node("li", { class: "cms-muted" }, "No products created yet."),
    render: (pSig) => {
      const p = pSig.peek();
      const li = node("li", { class: "cms-list-row" });
      const info = p.title + " [" + p.sku + "] — $" + p.price + " " + p.currency + " (" + p.kind + (p.carrier ? " / " + p.carrier : "") + ", stock: " + (p.stock_qty === null || p.stock_qty === undefined ? "unlimited" : String(p.stock_qty)) + ")";
      li.appendChild(node("span", {}, info));
      const toggleBtn = node("button", { type: "button", class: "cms-btn-secondary" }, p.active ? "Deactivate" : "Activate");
      toggleBtn.addEventListener("click", async () => {
        try {
          await api.put("/api/admin/commerce/products/" + String(p.id), { active: p.active ? 0 : 1 });
          okSig.set("Updated product " + p.sku);
          await loadProducts();
        } catch (err) {
          errSig.set(err.message);
        }
      });
      li.appendChild(toggleBtn);
      return li;
    },
  });

  async function loadProducts() {
    const data = await api.get("/api/admin/commerce/products");
    productsSig.set(Array.isArray(data.products) ? data.products : []);
  }

  const titleIn = Input({ id: "prod-title", props: { name: "title", type: "text", label: "Title", required: true } });
  const slugIn = Input({ id: "prod-slug", props: { name: "slug", type: "text", label: "URL Slug (/shop/...)", required: true } });
  const skuIn = Input({ id: "prod-sku", props: { name: "sku", type: "text", label: "SKU", required: true } });
  const priceIn = Input({ id: "prod-price", props: { name: "price", type: "text", label: "Price (USD exact string e.g. 19.99)", value: "19.99", required: true } });
  priceIn.inputElement.setAttribute("inputmode", "decimal");
  const kindSel = Select({
    id: "prod-kind",
    props: {
      name: "kind",
      label: "Product Kind",
      value: "physical",
      options: [
        { value: "physical", label: "Physical (USPS / Lulu Direct)" },
        { value: "digital", label: "Digital Download" },
      ],
    },
  });
  const carrierSel = Select({
    id: "prod-carrier",
    props: {
      name: "carrier",
      label: "Physical Carrier",
      value: "usps",
      options: [
        { value: "usps", label: "USPS Only" },
        { value: "lulu_direct", label: "Lulu Direct (Book Print Fulfillment)" },
      ],
    },
  });
  const stockIn = Input({ id: "prod-stock", props: { name: "stock_qty", type: "text", label: "Stock Quantity", value: "25" } });
  stockIn.inputElement.setAttribute("inputmode", "numeric");
  const weightIn = Input({ id: "prod-weight", props: { name: "weight_g", type: "text", label: "Weight (grams, <= 31751)", value: "350" } });
  weightIn.inputElement.setAttribute("inputmode", "numeric");
  const luluIn = Input({ id: "prod-lulu", props: { name: "lulu_sku", type: "text", label: "Lulu SKU (required for lulu_direct)" } });
  const isbnIn = Input({ id: "prod-isbn", props: { name: "isbn_13", type: "text", label: "ISBN-13 (optional)" } });

  const createBtn = node("button", { type: "submit" }, "Create Published Product");
  const form = Form({
    props: {
      method: "post",
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        const pVal = priceIn.value.peek().trim();
        if (!isExactGrabWireString(pVal)) {
          errSig.set("Price must be an exact USD GrabDecimal string (e.g. 19.99).");
          return;
        }
        try {
          const cf = {};
          const isbn = isbnIn.value.peek().trim();
          if (isbn) cf.isbn_13 = isbn;
          await api.post("/api/admin/commerce/products", {
            title: titleIn.value.peek().trim(),
            slug: slugIn.value.peek().trim(),
            sku: skuIn.value.peek().trim(),
            price: pVal,
            kind: kindSel.value.peek(),
            carrier: carrierSel.value.peek(),
            stock_qty: Number.parseInt(stockIn.value.peek().trim() || "0", 10),
            weight_g: Number.parseInt(weightIn.value.peek().trim() || "250", 10),
            lulu_sku: luluIn.value.peek().trim(),
            custom_fields: cf,
            status: "published",
          });
          okSig.set("Product created and published.");
          await loadProducts();
        } catch (err) {
          errSig.set(err && err.message ? err.message : "Failed to create product.");
        }
      },
    },
    children: [titleIn.element, slugIn.element, skuIn.element, priceIn.element, kindSel.element, carrierSel.element, stockIn.element, weightIn.element, luluIn.element, isbnIn.element, createBtn],
  });

  const formCard = node("section", { class: "cms-card" });
  formCard.appendChild(node("h2", {}, "Add Product"));
  formCard.appendChild(form.element);

  root.appendChild(listCard);
  root.appendChild(formCard);
  await loadProducts().catch((e) => errSig.set(e.message));
}

async function mountOrdersSection(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const ordersCard = node("section", { class: "cms-card" });
  ordersCard.appendChild(node("h2", {}, "Orders (Read-Only Totals + Audited Transitions)"));
  const listMount = node("ul", { class: "cms-list", role: "list" });
  ordersCard.appendChild(listMount);

  const detailCard = node("section", { class: "cms-card", "aria-live": "polite" });
  detailCard.appendChild(node("h2", {}, "Order Detail & Audit Trail"));
  const detailBody = node("section", { class: "cms-stack" });
  detailBody.appendChild(node("p", { class: "cms-muted" }, "Select an order to inspect line items, audit entries, and transition actions."));
  detailCard.appendChild(detailBody);

  const ordersSig = signal([]);
  async function loadDetail(orderId) {
    try {
      const data = await api.get("/api/admin/commerce/orders/" + String(orderId));
      clearEl(detailBody);
      const o = data.order;
      detailBody.appendChild(node("p", {}, o.number + " — Status: " + o.status + " — Total: $" + o.total + " " + o.currency));
      if (o.needs_review) {
        detailBody.appendChild(node("p", { class: "cms-alert-error" }, "Flagged for review: " + o.review_note));
        const resBtn = node("button", { type: "button" }, "Mark Review Resolved");
        resBtn.addEventListener("click", async () => {
          await api.post("/api/admin/commerce/orders/" + String(orderId) + "/resolve-review", { note: "Verified in Admin UI" });
          okSig.set("Resolved review flag on " + o.number);
          await loadOrders();
          await loadDetail(orderId);
        });
        detailBody.appendChild(resBtn);
      }
      const nextTransitions = {
        pending_payment: ["paid", "cancelled"],
        paid: ["fulfilling", "cancelled"],
        fulfilling: ["shipped", "cancelled"],
        shipped: ["delivered"],
      }[o.status] || [];
      const btnRow = node("section", { class: "cms-actions-row" });
      for (const nextSt of nextTransitions) {
        const b = node("button", { type: "button", class: "cms-btn-secondary" }, "Move to " + nextSt);
        b.addEventListener("click", async () => {
          try {
            await api.post("/api/admin/commerce/orders/" + String(orderId) + "/transition", { status: nextSt, reason: "admin_ui_action" });
            okSig.set("Order " + o.number + " moved to " + nextSt);
            await loadOrders();
            await loadDetail(orderId);
          } catch (err) {
            errSig.set(err.message);
          }
        });
        btnRow.appendChild(b);
      }
      detailBody.appendChild(btnRow);

      detailBody.appendChild(node("h3", {}, "Audit Trail"));
      const aUl = node("ul", { class: "cms-list", role: "list" });
      for (const au of data.audit || []) {
        aUl.appendChild(node("li", { class: "cms-list-row" }, au.created_at + " | " + au.actor + ": " + (au.from_status || "(new)") + " -> " + au.to_status + " (" + au.reason + ")"));
      }
      detailBody.appendChild(aUl);
    } catch (err) {
      errSig.set(err.message);
    }
  }

  ForEach({
    parent: listMount,
    items: ordersSig,
    key: (o) => o.id,
    empty: () => node("li", { class: "cms-muted" }, "No orders placed yet."),
    render: (oSig) => {
      const o = oSig.peek();
      const li = node("li", { class: "cms-list-row" });
      li.appendChild(node("span", {}, o.number + " — " + o.customer_email + " — $" + o.total + " — " + o.status + (o.needs_review ? " [NEEDS REVIEW]" : "")));
      const viewBtn = node("button", { type: "button", class: "cms-btn-secondary" }, "Inspect");
      viewBtn.addEventListener("click", () => loadDetail(o.id));
      li.appendChild(viewBtn);
      return li;
    },
  });

  async function loadOrders() {
    const data = await api.get("/api/admin/commerce/orders");
    ordersSig.set(Array.isArray(data.orders) ? data.orders : []);
  }

  root.appendChild(ordersCard);
  root.appendChild(detailCard);
  await loadOrders().catch((e) => errSig.set(e.message));
}

async function mountCouponsSection(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const listCard = node("section", { class: "cms-card" });
  listCard.appendChild(node("h2", {}, "Coupons (AI / MCP Drafts Highlighted)"));
  const listMount = node("ul", { class: "cms-list", role: "list" });
  listCard.appendChild(listMount);

  const couponsSig = signal([]);
  ForEach({
    parent: listMount,
    items: couponsSig,
    key: (c) => c.id,
    empty: () => node("li", { class: "cms-muted" }, "No coupons created yet."),
    render: (cSig) => {
      const c = cSig.peek();
      const li = node("li", { class: "cms-list-row" });
      const isAi = String(c.created_by || "").startsWith("mcp:");
      const label = c.code + " (" + c.type + ": " + String(c.value) + ", min $" + c.min_subtotal + ", used " + String(c.redeemed_count) + "/" + String(c.max_redemptions) + ")" + (isAi ? " [AI Draft — Human Activation Required]" : "") + (c.active ? " [ACTIVE]" : " [INACTIVE]");
      li.appendChild(node("span", {}, label));
      const toggle = node("button", { type: "button", class: "cms-btn-secondary" }, c.active ? "Disable" : "Activate");
      toggle.addEventListener("click", async () => {
        try {
          await api.put("/api/admin/commerce/coupons/" + String(c.id), { active: c.active ? 0 : 1 });
          okSig.set("Updated coupon " + c.code);
          await loadCoupons();
        } catch (err) {
          errSig.set(err.message);
        }
      });
      li.appendChild(toggle);
      return li;
    },
  });

  async function loadCoupons() {
    const data = await api.get("/api/admin/commerce/coupons");
    couponsSig.set(Array.isArray(data.coupons) ? data.coupons : []);
  }

  const codeIn = Input({ id: "cpn-code", props: { name: "code", type: "text", label: "Code", required: true } });
  const typeSel = Select({
    id: "cpn-type",
    props: {
      name: "type",
      label: "Discount Type",
      value: "percent_bp",
      options: [
        { value: "percent_bp", label: "Percentage (basis points, e.g. 1500 = 15%)" },
        { value: "fixed_cents", label: "Fixed Amount (cents, e.g. 500 = $5.00)" },
      ],
    },
  });
  const valIn = Input({ id: "cpn-val", props: { name: "value", type: "text", label: "Value (integer bp or cents)", value: "1500", required: true } });
  const minIn = Input({ id: "cpn-min", props: { name: "min_subtotal", type: "text", label: "Min Subtotal (USD exact string)", value: "0.00", required: true } });
  minIn.inputElement.setAttribute("inputmode", "decimal");
  const maxIn = Input({ id: "cpn-max", props: { name: "max_redemptions", type: "text", label: "Max Redemptions", value: "100", required: true } });

  const createBtn = node("button", { type: "submit" }, "Create Coupon");
  const form = Form({
    props: {
      method: "post",
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        const mStr = minIn.value.peek().trim();
        if (!isExactGrabWireString(mStr)) {
          errSig.set("min_subtotal must be an exact GrabDecimal string (e.g. 0.00).");
          return;
        }
        try {
          await api.post("/api/admin/commerce/coupons", {
            code: codeIn.value.peek().trim(),
            type: typeSel.value.peek(),
            value: Number.parseInt(valIn.value.peek().trim(), 10),
            min_subtotal: mStr,
            max_redemptions: Number.parseInt(maxIn.value.peek().trim(), 10),
            active: 1,
          });
          okSig.set("Coupon created.");
          await loadCoupons();
        } catch (err) {
          errSig.set(err.message);
        }
      },
    },
    children: [codeIn.element, typeSel.element, valIn.element, minIn.element, maxIn.element, createBtn],
  });

  const formCard = node("section", { class: "cms-card" });
  formCard.appendChild(node("h2", {}, "Create Coupon"));
  formCard.appendChild(form.element);
  root.appendChild(listCard);
  root.appendChild(formCard);
  await loadCoupons().catch((e) => errSig.set(e.message));
}

async function mountCustomersSection(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const card = node("section", { class: "cms-card" });
  card.appendChild(node("h2", {}, "Customers & GDPR Privacy Tools"));
  const listMount = node("ul", { class: "cms-list", role: "list" });
  card.appendChild(listMount);

  const targetAnonIdSig = signal(null);
  const modalOpenSig = signal(false);
  const anonModal = Modal({
    id: "gdpr-anonymize-modal",
    props: {
      title: "Confirm GDPR Customer Anonymization",
      open: modalOpenSig,
      onClose: () => modalOpenSig.set(false),
    },
    children: [
      node("p", {}, "This permanently removes customer email, display name, and shipping addresses while preserving financial ledger totals."),
      (() => {
        const confirmBtn = node("button", { type: "button", class: "cms-btn-danger" }, "Confirm Anonymize");
        confirmBtn.addEventListener("click", async () => {
          const cid = targetAnonIdSig.peek();
          if (!cid) return;
          try {
            await api.delete("/api/admin/commerce/customers/" + String(cid));
            okSig.set("Customer #" + String(cid) + " anonymized.");
            modalOpenSig.set(false);
            await loadCustomers();
          } catch (err) {
            errSig.set(err.message);
          }
        });
        return confirmBtn;
      })(),
    ],
  });

  const custSig = signal([]);
  ForEach({
    parent: listMount,
    items: custSig,
    key: (c) => c.id,
    empty: () => node("li", { class: "cms-muted" }, "No customer records yet."),
    render: (cSig) => {
      const c = cSig.peek();
      const li = node("li", { class: "cms-list-row" });
      li.appendChild(node("span", {}, "#" + String(c.id) + " " + c.email_masked + " | Marketing opt-in: " + (c.marketing_consent ? "Yes" : "No")));
      const expBtn = node("button", { type: "button", class: "cms-btn-secondary" }, "Export JSON");
      expBtn.addEventListener("click", async () => {
        try {
          const exp = await api.get("/api/admin/commerce/customers/" + String(c.id) + "/export");
          okSig.set("Exported GDPR package for customer #" + String(c.id) + " (" + String((exp.orders || []).length) + " orders).");
        } catch (err) {
          errSig.set(err.message);
        }
      });
      const delBtn = node("button", { type: "button", class: "cms-btn-danger" }, "Anonymize");
      delBtn.addEventListener("click", () => {
        targetAnonIdSig.set(c.id);
        modalOpenSig.set(true);
      });
      const actions = node("section", { class: "cms-actions-row" });
      actions.appendChild(expBtn);
      actions.appendChild(delBtn);
      li.appendChild(actions);
      return li;
    },
  });

  async function loadCustomers() {
    const data = await api.get("/api/admin/commerce/customers");
    custSig.set(Array.isArray(data.customers) ? data.customers : []);
  }

  root.appendChild(card);
  root.appendChild(anonModal.element);
  await loadCustomers().catch((e) => errSig.set(e.message));
}

async function mountSettingsSection(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const card = node("section", { class: "cms-card" });
  card.appendChild(node("h2", {}, "Storefront & Payment Redirect Settings (Admin Only)"));
  const formMount = node("section", { class: "cms-stack" });
  card.appendChild(formMount);
  root.appendChild(card);

  try {
    const s = await api.get("/api/admin/commerce/settings");
    const statusLine = node(
      "p",
      { class: "cms-muted" },
      "Webhook Keys (env-only): Primary = " + (s.webhook_primary_configured ? "Configured" : "Not set") + ", Rotating Next = " + (s.webhook_next_configured ? "Configured" : "Not set")
    );
    const enabledSel = Select({
      id: "set-enabled",
      props: {
        name: "commerce_enabled",
        label: "Storefront Status",
        value: s.commerce_enabled ? "1" : "0",
        options: [
          { value: "0", label: "Disabled (404 storefront)" },
          { value: "1", label: "Enabled (USD)" },
        ],
      },
    });
    const allowIn = Input({ id: "set-allowlist", props: { name: "payment_redirect_allowlist", type: "text", label: "Allowed HTTPS Payment Hosts (comma-separated, no wildcards)", value: s.payment_redirect_allowlist || "" } });
    const tmplIn = Input({ id: "set-tmpl", props: { name: "payment_redirect_template", type: "text", label: "Payment Redirect URL Template ({order_number}, {amount}, {currency}, {return_url})", value: s.payment_redirect_template || "" } });
    const taxStdIn = Input({ id: "set-tax-std", props: { name: "standard_bp", type: "text", label: "Standard Tax (basis points, e.g. 825 = 8.25%)", value: String(s.tax_rates ? s.tax_rates.standard_bp : 0) } });
    const shipUspsIn = Input({ id: "set-ship-usps", props: { name: "usps_ground_advantage", type: "text", label: "USPS Ground Advantage Flat Rate (USD)", value: (s.shipping_rates && s.shipping_rates.usps_ground_advantage) || "0.00" } });
    shipUspsIn.inputElement.setAttribute("inputmode", "decimal");
    const shipLuluIn = Input({ id: "set-ship-lulu", props: { name: "lulu_direct", type: "text", label: "Lulu Direct Flat Rate (USD)", value: (s.shipping_rates && s.shipping_rates.lulu_direct) || "0.00" } });
    shipLuluIn.inputElement.setAttribute("inputmode", "decimal");
    const saveBtn = node("button", { type: "submit" }, "Save Store Settings");

    const form = Form({
      props: {
        method: "post",
        onSubmit: async () => {
          errSig.set("");
          okSig.set("");
          const uRate = shipUspsIn.value.peek().trim();
          const lRate = shipLuluIn.value.peek().trim();
          if (!isExactGrabWireString(uRate) || !isExactGrabWireString(lRate)) {
            errSig.set("Shipping rates must be exact GrabDecimal USD strings (e.g. 5.99).");
            return;
          }
          try {
            await api.put("/api/admin/commerce/settings", {
              commerce_enabled: enabledSel.value.peek() === "1",
              currency: "USD",
              payment_redirect_allowlist: allowIn.value.peek().trim(),
              payment_redirect_template: tmplIn.value.peek().trim(),
              tax_rates: {
                standard_bp: Number.parseInt(taxStdIn.value.peek().trim() || "0", 10),
                reduced_bp: 0,
                digital_bp: 0,
              },
              shipping_rates: {
                usps_ground_advantage: uRate,
                usps_priority: uRate,
                usps_media_mail: uRate,
                lulu_direct: lRate,
              },
            });
            okSig.set("Commerce settings updated cleanly.");
          } catch (err) {
            errSig.set(err && err.message ? err.message : "Failed to save settings.");
          }
        },
      },
      children: [enabledSel.element, allowIn.element, tmplIn.element, taxStdIn.element, shipUspsIn.element, shipLuluIn.element, saveBtn],
    });
    formMount.appendChild(statusLine);
    formMount.appendChild(form.element);
  } catch (err) {
    errSig.set(err && err.message ? err.message : "Failed to load settings.");
  }
}

export async function mountCommerce(root, api, page, role) {
  const canSettings = role === "admin";
  root.appendChild(buildStoreSubnav(page, canSettings));
  const tabsDemo = Tabs({
    id: "store-mode-note",
    props: {
      tabs: [
        { id: "usps", label: "Fulfillment Policy", content: node("p", { class: "cms-muted" }, "Physical book shipments enforce USPS-only / lulu_direct fulfillment (LULU-USPS-001) and USD integer-cent wire precision.") },
      ],
    },
  });
  root.appendChild(tabsDemo.element);

  if (page === "store") {
    await mountOverviewSection(root, api);
  } else if (page === "store_products") {
    await mountProductsSection(root, api);
  } else if (page === "store_orders") {
    await mountOrdersSection(root, api);
  } else if (page === "store_coupons") {
    await mountCouponsSection(root, api);
  } else if (page === "store_customers") {
    await mountCustomersSection(root, api);
  } else if (page === "store_settings") {
    await mountSettingsSection(root, api);
  }
}
