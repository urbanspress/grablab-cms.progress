/**
 * GrabLab CMS v1.1.0 Storefront Client (Pure Grex JS v1.0.0 & Semantic DOM)
 * - Zero <div> elements, zero innerHTML writes, zero dynamic eval
 * - ADR-025c exact GrabDecimal string validation ("0.00")
 * - Explicit opt-in marketing consent checkbox (defaults unchecked)
 */

import {
  setSafeText,
  isExactGrabWireString,
  createTheme,
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

function generateIdempotencyKey() {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
    return "chk-" + globalThis.crypto.randomUUID().replaceAll("-", "");
  }
  return "chk-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 14);
}

export function initShopTheme() {
  try {
    const t = createTheme({
      name: "grablab-shop",
      tokens: {
        light: { bg: "#ffffff", fg: "#0f172a", accent: "#1d4ed8" },
        dark: { bg: "#0b1120", fg: "#f8fafc", accent: "#2563eb" },
      },
    });
    const pref = globalThis.localStorage ? globalThis.localStorage.getItem("grablab_shop_theme") : null;
    if (pref === "dark" || pref === "light") {
      document.documentElement.setAttribute("data-grex-theme", pref);
    } else if (!document.documentElement.getAttribute("data-grex-theme")) {
      document.documentElement.setAttribute("data-grex-theme", "light");
    }
    return t;
  } catch {
    return null;
  }
}

async function fetchSession() {
  const res = await fetch("/api/commerce/session", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || data.error || "Unable to initialize cart session");
  }
  return data;
}

export function buildProductActionView(prodInfo, onAdd) {
  const section = node("section", { class: "cms-shop-panel", "aria-label": "Purchase options" });
  const heading = node("h2", {}, "Order " + (prodInfo.title || "Product"));
  const form = node("form", { class: "cms-form" });
  const qtyLabel = node("label", { for: "shop-qty-input" }, "Quantity");
  const qtyInput = node("input", {
    id: "shop-qty-input",
    class: "shop-input",
    type: "text",
    inputmode: "numeric",
    pattern: "[0-9]+",
    value: "1",
    required: true,
  });
  const submitBtn = node("button", { type: "submit", class: "shop-btn" }, "Add to Cart ($" + (prodInfo.price || "0.00") + ")");
  const statusEl = node("p", { role: "status", class: "cms-meta" }, "");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const rawQty = qtyInput.value.trim();
    if (!/^[1-9][0-9]{0,2}$/.test(rawQty)) {
      statusEl.className = "shop-status-err";
      setSafeText(statusEl, "Quantity must be an integer between 1 and 999 (decimals not allowed).");
      return;
    }
    submitBtn.disabled = true;
    try {
      const result = await onAdd(Number.parseInt(rawQty, 10));
      statusEl.className = "shop-status-ok";
      setSafeText(statusEl, "Added to cart. Cart total: $" + result.total + " " + result.currency);
    } catch (err) {
      statusEl.className = "shop-status-err";
      setSafeText(statusEl, err && err.message ? err.message : "Could not add item to cart.");
    } finally {
      submitBtn.disabled = false;
    }
  });

  form.appendChild(qtyLabel);
  form.appendChild(qtyInput);
  form.appendChild(submitBtn);
  section.appendChild(heading);
  section.appendChild(form);
  section.appendChild(statusEl);
  return section;
}

export function buildCartCheckoutView(cartData, handlers) {
  const wrap = node("section", { class: "cms-shop-stack", "aria-label": "Shopping cart and checkout" });
  const itemsSection = node("section", { class: "cms-shop-panel", "aria-labelledby": "cart-items-heading" });
  itemsSection.appendChild(node("h2", { id: "cart-items-heading" }, "Your Cart"));

  const items = Array.isArray(cartData.items) ? cartData.items : [];
  if (items.length === 0) {
    itemsSection.appendChild(node("p", { class: "cms-muted" }, "Your cart is currently empty."));
  } else {
    const ul = node("ul", { class: "cms-list", role: "list" });
    for (const it of items) {
      const li = node("li", { class: "cms-card" });
      const titleP = node("p", {}, it.title + " (" + it.sku + ") — $" + it.unit_price + " × " + String(it.qty) + " = $" + it.line_total);
      const rmBtn = node("button", { type: "button", class: "shop-btn shop-btn-secondary" }, "Remove");
      rmBtn.addEventListener("click", () => handlers.onRemove(it.product_id));
      li.appendChild(titleP);
      li.appendChild(rmBtn);
      ul.appendChild(li);
    }
    itemsSection.appendChild(ul);
  }

  const dl = node("dl", { class: "cms-order-totals" });
  const pairs = [
    ["Subtotal", "$" + (cartData.subtotal || "0.00")],
    ["Discount", "-$" + (cartData.discount_total || "0.00")],
    ["Tax", "$" + (cartData.tax_total || "0.00")],
    ["Shipping", "$" + (cartData.shipping_total || "0.00")],
    ["Total", "$" + (cartData.total || "0.00") + " " + (cartData.currency || "USD")],
  ];
  for (const [k, v] of pairs) {
    dl.appendChild(node("dt", {}, k));
    dl.appendChild(node("dd", {}, v));
  }
  itemsSection.appendChild(dl);
  wrap.appendChild(itemsSection);

  // Coupon panel
  const cpnSection = node("section", { class: "cms-shop-panel", "aria-labelledby": "coupon-heading" });
  cpnSection.appendChild(node("h2", { id: "coupon-heading" }, "Promo Code"));
  const cpnForm = node("form", { class: "cms-form" });
  const cpnLabel = node("label", { for: "shop-coupon-input" }, "Coupon Code");
  const cpnInput = node("input", {
    id: "shop-coupon-input",
    class: "shop-input",
    type: "text",
    value: cartData.coupon_code || "",
    placeholder: "Enter code (optional)",
  });
  const cpnBtn = node("button", { type: "submit", class: "shop-btn shop-btn-secondary" }, "Apply Coupon");
  const cpnStatus = node("p", { role: "status", class: "cms-meta" }, "");
  cpnForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await handlers.onCoupon(cpnInput.value.trim());
    } catch (err) {
      cpnStatus.className = "shop-status-err";
      setSafeText(cpnStatus, err && err.message ? err.message : "Coupon rejected.");
    }
  });
  cpnForm.appendChild(cpnLabel);
  cpnForm.appendChild(cpnInput);
  cpnForm.appendChild(cpnBtn);
  cpnSection.appendChild(cpnForm);
  cpnSection.appendChild(cpnStatus);
  wrap.appendChild(cpnSection);

  // Guest-first checkout form
  const chkSection = node("section", { class: "cms-shop-panel", "aria-labelledby": "checkout-heading" });
  chkSection.appendChild(node("h2", { id: "checkout-heading" }, "Guest Checkout"));
  const chkForm = node("form", { class: "cms-form" });

  const emailLbl = node("label", { for: "chk-email" }, "Email Address (for receipt and order updates)");
  const emailIn = node("input", { id: "chk-email", class: "shop-input", type: "email", required: true, autocomplete: "email" });
  const nameLbl = node("label", { for: "chk-name" }, "Full Name");
  const nameIn = node("input", { id: "chk-name", class: "shop-input", type: "text", autocomplete: "name" });

  chkForm.appendChild(emailLbl);
  chkForm.appendChild(emailIn);
  chkForm.appendChild(nameLbl);
  chkForm.appendChild(nameIn);

  let addrInputs = null;
  if (cartData.has_physical) {
    const l1Lbl = node("label", { for: "chk-line1" }, "Street Address");
    const l1In = node("input", { id: "chk-line1", class: "shop-input", type: "text", required: true });
    const cityLbl = node("label", { for: "chk-city" }, "City");
    const cityIn = node("input", { id: "chk-city", class: "shop-input", type: "text", required: true });
    const stLbl = node("label", { for: "chk-state" }, "State");
    const stIn = node("input", { id: "chk-state", class: "shop-input", type: "text", required: true });
    const zipLbl = node("label", { for: "chk-zip" }, "Postal Code");
    const zipIn = node("input", { id: "chk-zip", class: "shop-input", type: "text", required: true });
    chkForm.appendChild(l1Lbl);
    chkForm.appendChild(l1In);
    chkForm.appendChild(cityLbl);
    chkForm.appendChild(cityIn);
    chkForm.appendChild(stLbl);
    chkForm.appendChild(stIn);
    chkForm.appendChild(zipLbl);
    chkForm.appendChild(zipIn);
    addrInputs = { l1In, cityIn, stIn, zipIn };
  }

  // Explicit opt-in checkbox (MUST default unchecked!)
  const mktLabel = node("label", { for: "chk-marketing" });
  const mktBox = node("input", { id: "chk-marketing", type: "checkbox" });
  mktBox.checked = false;
  mktLabel.appendChild(mktBox);
  mktLabel.appendChild(document.createTextNode(" Email me occasional cart reminders and offers (optional)"));
  chkForm.appendChild(mktLabel);

  const chkBtn = node("button", { type: "submit", class: "shop-btn" }, "Complete Order ($" + (cartData.total || "0.00") + " USD)");
  const chkStatus = node("p", { role: "status", class: "cms-meta" }, "");

  chkForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    chkBtn.disabled = true;
    try {
      const payload = {
        email: emailIn.value.trim(),
        display_name: nameIn.value.trim(),
        marketing_opt_in: Boolean(mktBox.checked),
        marketing_consent: mktBox.checked ? 1 : 0,
      };
      if (addrInputs) {
        payload.shipping_address = {
          name: nameIn.value.trim(),
          line1: addrInputs.l1In.value.trim(),
          city: addrInputs.cityIn.value.trim(),
          state: addrInputs.stIn.value.trim(),
          postal_code: addrInputs.zipIn.value.trim(),
          country: "US",
        };
      }
      const res = await handlers.onCheckout(payload);
      chkStatus.className = "shop-status-ok";
      setSafeText(chkStatus, "Order " + res.order_number + " created! Redirecting to payment...");
      if (typeof res.redirect_url === "string" && res.redirect_url.startsWith("https://")) {
        window.location.assign(res.redirect_url);
      }
    } catch (err) {
      chkStatus.className = "shop-status-err";
      setSafeText(chkStatus, err && err.message ? err.message : "Checkout failed.");
    } finally {
      chkBtn.disabled = false;
    }
  });

  chkForm.appendChild(chkBtn);
  chkSection.appendChild(chkForm);
  chkSection.appendChild(chkStatus);
  wrap.appendChild(chkSection);

  return wrap;
}

export async function mountStorefront() {
  initShopTheme();

  const prodMount = document.getElementById("shop-product-mount");
  if (prodMount) {
    const pid = Number.parseInt(prodMount.getAttribute("data-product-id") || "0", 10);
    const title = prodMount.getAttribute("data-product-title") || "Product";
    const price = prodMount.getAttribute("data-product-price") || "0.00";
    if (!isExactGrabWireString(price)) return;

    const view = buildProductActionView({ id: pid, title, price }, async (qty) => {
      const sess = await fetchSession();
      const res = await fetch("/api/commerce/cart", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": sess.csrf_token,
        },
        body: JSON.stringify({ action: "add", product_id: pid, qty }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || data.error || "Failed to add item");
      return data;
    });
    clearEl(prodMount);
    prodMount.appendChild(view);
  }

  const cartMount = document.getElementById("shop-cart-mount");
  if (cartMount) {
    let csrfToken = "";
    const refreshCart = async () => {
      const sess = await fetchSession();
      csrfToken = sess.csrf_token;
      clearEl(cartMount);
      cartMount.appendChild(
        buildCartCheckoutView(sess, {
          onRemove: async (productId) => {
            await fetch("/api/commerce/cart", {
              method: "POST",
              credentials: "same-origin",
              headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
              body: JSON.stringify({ action: "remove", product_id: productId }),
            });
            await refreshCart();
          },
          onCoupon: async (code) => {
            const res = await fetch("/api/commerce/coupon/apply", {
              method: "POST",
              credentials: "same-origin",
              headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
              body: JSON.stringify({ code }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.message || data.error || "Invalid coupon");
            await refreshCart();
          },
          onCheckout: async (payload) => {
            const res = await fetch("/api/commerce/checkout", {
              method: "POST",
              credentials: "same-origin",
              headers: {
                "Content-Type": "application/json",
                "X-CSRF-Token": csrfToken,
                "Idempotency-Key": generateIdempotencyKey(),
              },
              body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.message || data.error || "Checkout failed");
            return data;
          },
        })
      );
    };
    try {
      await refreshCart();
    } catch (err) {
      clearEl(cartMount);
      cartMount.appendChild(node("p", { class: "shop-status-err" }, err && err.message ? err.message : "Unable to load cart."));
    }
  }
}

if (typeof document !== "undefined" && typeof window !== "undefined") {
  mountStorefront();
}
