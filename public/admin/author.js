/**
 * GrabLab CMS v1.4.0 Admin Author Mode & Embedded Bestseller Radar (Pure Grex JS v1.0.0)
 * Sections: author (overview), author_books, author_series, author_chapters, author_authors, author_radar.
 * - Zero <div>, zero innerHTML writes, zero dynamic eval
 * - ADR-025c exact string inputs (inputmode="decimal") validated via isExactGrabWireString
 * - Radar 1-click import confirmation Modal with Escape + focus restoration
 * - Draft-only import enforcement (status_enforced: "draft")
 */

import {
  signal,
  setSafeText,
  isExactGrabWireString,
  Modal,
  Form,
  Input,
  Select,
  Tabs,
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
  const p = node("p", { role: ok ? "status" : "alert" });
  const render = () => {
    const val = msgSig.get();
    if (!val) {
      p.hidden = true;
      setSafeText(p, "");
      p.className = "";
    } else {
      p.hidden = false;
      setSafeText(p, val);
      p.className = ok ? "cms-alert cms-alert-ok" : "cms-alert cms-alert-error";
    }
  };
  msgSig.subscribe(render);
  render();
  return p;
}

export function buildAuthorSubnav(activeSection) {
  const nav = node("nav", { class: "cms-subnav", "aria-label": "Author studio sections" });
  const links = [
    { key: "author", href: "/admin/author", label: "Author Overview" },
    { key: "author_authors", href: "/admin/author/authors", label: "Authors" },
    { key: "author_series", href: "/admin/author/series", label: "Series" },
    { key: "author_books", href: "/admin/author/books", label: "Books" },
    { key: "author_chapters", href: "/admin/author/chapters", label: "Chapters & Readability" },
    { key: "author_radar", href: "/admin/author/radar", label: "Bestseller Radar" },
  ];
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

export function createAuthorDashboardSpec(overview) {
  const counts = overview && overview.counts ? overview.counts : {};
  const section = node("section", { class: "cms-stack", "aria-label": "Author Mode overview" });
  const stats = node("section", { class: "cms-grid", "aria-label": "Publishing metrics" });
  const cards = [
    ["Author Mode", overview && overview.enabled ? "Enabled" : "Disabled"],
    ["Authors", String(counts.authors || 0)],
    ["Series", String(counts.series || 0)],
    ["Books", String(counts.books || 0)],
    ["Chapters", String(counts.chapters || 0)],
    ["Radar Imports", String(counts.radar_imports || 0)],
  ];
  for (const [label, val] of cards) {
    const c = node("article", { class: "cms-card" });
    c.appendChild(node("p", { class: "cms-muted" }, label));
    c.appendChild(node("p", { class: "cms-stat-num" }, val));
    stats.appendChild(c);
  }
  section.appendChild(stats);

  const booksCard = node("section", { class: "cms-card", "aria-labelledby": "recent-books-h" });
  booksCard.appendChild(node("h2", { id: "recent-books-h" }, "Catalog Books"));
  const recent = Array.isArray(overview && overview.recent_books) ? overview.recent_books : [];
  if (recent.length === 0) {
    booksCard.appendChild(node("p", { class: "cms-muted" }, "No books created yet. Create a book or import a draft from Bestseller Radar."));
  } else {
    const ul = node("ul", { class: "cms-list", role: "list" });
    for (const b of recent) {
      const isbnNote = b.isbn_13 ? " · ISBN-13: " + b.isbn_13 : "";
      const prodNote = b.product_id ? " · Linked Product #" + String(b.product_id) : " · Unlinked";
      ul.appendChild(
        node("li", { class: "cms-list-row" }, b.title + " ($" + b.list_price + " " + b.currency + ", " + b.edition_format + isbnNote + prodNote + ")")
      );
    }
    booksCard.appendChild(ul);
  }
  section.appendChild(booksCard);
  return section;
}

export function createRadarConfirmationDialog(proposalSig, onConfirm) {
  const openSig = signal(false);
  const body = node("section", { class: "cms-stack" });
  const summaryP = node("p", {}, "");
  const noteP = node("p", { class: "cms-muted" }, "Imported outlines always land as status: draft and never overwrite live copy.");
  const btnRow = node("section", { class: "cms-actions-row" });
  const confirmBtn = node("button", { type: "button", id: "radar-confirm-import-btn", class: "cms-btn" }, "Confirm Draft Import");
  const cancelBtn = node("button", { type: "button", id: "radar-cancel-import-btn", class: "cms-btn-secondary" }, "Cancel");

  confirmBtn.addEventListener("click", async () => {
    const prop = proposalSig.peek();
    if (prop) {
      await onConfirm(prop);
    }
    openSig.set(false);
  });
  confirmBtn.addEventListener("keydown", (ev) => {
    if (ev && (ev.key === "Enter" || ev.key === " ")) {
      if (typeof ev.preventDefault === "function") ev.preventDefault();
      confirmBtn.click();
    }
  });
  cancelBtn.addEventListener("click", () => openSig.set(false));

  btnRow.appendChild(confirmBtn);
  btnRow.appendChild(cancelBtn);
  body.appendChild(summaryP);
  body.appendChild(noteP);
  body.appendChild(btnRow);

  const modal = Modal({
    id: "radar-import-modal",
    props: {
      open: openSig,
      title: "Confirm Draft Import from Bestseller Radar",
    },
    children: [body],
  });

  const openForProposal = (prop) => {
    proposalSig.set(prop);
    const tier = prop.selected_price_tier_usd || "14.99";
    setSafeText(
      summaryP,
      "Plan " + String(prop.radar_plan_id || "") + " (" + String(prop.genre_slug || "") + ", $" + String(tier) + " USD) will be imported as a draft."
    );
    openSig.set(true);
  };

  return { modal, open: openSig, openForProposal, confirmBtn, cancelBtn };
}

async function mountOverviewSection(root, api) {
  const errSig = signal("");
  root.appendChild(makeAlert(errSig, false));
  const mount = node("section", { class: "cms-stack" });
  root.appendChild(mount);
  try {
    const data = await api.get("/api/admin/author/overview");
    clearEl(mount);
    mount.appendChild(createAuthorDashboardSpec(data));
  } catch (err) {
    errSig.set(err && err.message ? err.message : "Failed to load Author overview.");
  }
}

async function mountAuthorsSection(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const listCard = node("section", { class: "cms-card" });
  listCard.appendChild(node("h2", {}, "Registered Authors"));
  const listUl = node("ul", { class: "cms-list", role: "list" });
  listCard.appendChild(listUl);
  const authorsSig = signal([]);

  ForEach({
    parent: listUl,
    items: authorsSig,
    key: (a) => a.id,
    empty: () => node("li", { class: "cms-muted" }, "No author profiles yet."),
    render: (aSig) => {
      const a = aSig.peek();
      return node("li", { class: "cms-list-row" }, "#" + String(a.id) + " " + a.pen_name + " (" + a.full_path + " · " + a.status + ")");
    },
  });

  async function loadAuthors() {
    const res = await api.get("/api/admin/author/authors");
    authorsSig.set(Array.isArray(res.authors) ? res.authors : []);
  }

  const penIn = Input({ id: "author-pen-name", props: { name: "pen_name", type: "text", label: "Pen Name", required: true } });
  const slugIn = Input({ id: "author-slug", props: { name: "slug", type: "text", label: "Slug (/authors/...)", required: true } });
  const bioIn = Input({ id: "author-bio", props: { name: "bio_summary", type: "text", label: "Bio Summary" } });
  const urlIn = Input({ id: "author-url", props: { name: "website_url", type: "url", label: "Website URL (https://...)" } });
  const submitBtn = node("button", { type: "submit" }, "Save Author Profile");

  const form = Form({
    props: {
      method: "post",
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        try {
          await api.post("/api/admin/author/authors", {
            pen_name: penIn.value.peek().trim(),
            slug: slugIn.value.peek().trim(),
            bio_summary: bioIn.value.peek().trim(),
            website_url: urlIn.value.peek().trim(),
            status: "published",
          });
          okSig.set("Author profile saved.");
          await loadAuthors();
        } catch (err) {
          errSig.set(err && err.message ? err.message : "Failed to save author.");
        }
      },
    },
    children: [penIn.element, slugIn.element, bioIn.element, urlIn.element, submitBtn],
  });

  const formCard = node("section", { class: "cms-card" });
  formCard.appendChild(node("h2", {}, "Create Author Profile"));
  formCard.appendChild(form.element);
  root.appendChild(listCard);
  root.appendChild(formCard);
  await loadAuthors().catch((e) => errSig.set(e.message));
}

async function mountSeriesSection(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const listCard = node("section", { class: "cms-card" });
  listCard.appendChild(node("h2", {}, "Book Series & Reading Order"));
  const listUl = node("ul", { class: "cms-list", role: "list" });
  listCard.appendChild(listUl);
  const seriesSig = signal([]);

  ForEach({
    parent: listUl,
    items: seriesSig,
    key: (s) => s.id,
    empty: () => node("li", { class: "cms-muted" }, "No series created yet."),
    render: (sSig) => {
      const s = sSig.peek();
      return node("li", { class: "cms-list-row" }, "#" + String(s.id) + " " + s.title + " (" + s.full_path + " · " + s.genre_slug + " · " + s.reading_order_mode + ")");
    },
  });

  async function loadSeries() {
    const res = await api.get("/api/admin/author/series");
    seriesSig.set(Array.isArray(res.series) ? res.series : []);
  }

  const titleIn = Input({ id: "series-title", props: { name: "title", type: "text", label: "Series Title", required: true } });
  const slugIn = Input({ id: "series-slug", props: { name: "slug", type: "text", label: "Series Slug (/series/...)", required: true } });
  const authorIdIn = Input({ id: "series-author-id", props: { name: "author_id", type: "text", label: "Author ID", value: "1", required: true } });
  authorIdIn.inputElement.setAttribute("inputmode", "numeric");
  const genreIn = Input({ id: "series-genre", props: { name: "genre_slug", type: "text", label: "Genre Slug", value: "urban-fiction" } });
  const orderSel = Select({
    id: "series-order-mode",
    props: {
      name: "reading_order_mode",
      label: "Reading Order Mode",
      value: "chronological",
      options: [
        { value: "chronological", label: "Chronological" },
        { value: "publication", label: "Publication Order" },
      ],
    },
  });
  const submitBtn = node("button", { type: "submit" }, "Create Series");

  const form = Form({
    props: {
      method: "post",
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        try {
          await api.post("/api/admin/author/series", {
            title: titleIn.value.peek().trim(),
            slug: slugIn.value.peek().trim(),
            author_id: Number.parseInt(authorIdIn.value.peek().trim() || "1", 10),
            genre_slug: genreIn.value.peek().trim(),
            reading_order_mode: orderSel.value.peek(),
            status: "draft",
          });
          okSig.set("Series created as draft.");
          await loadSeries();
        } catch (err) {
          errSig.set(err && err.message ? err.message : "Failed to create series.");
        }
      },
    },
    children: [titleIn.element, slugIn.element, authorIdIn.element, genreIn.element, orderSel.element, submitBtn],
  });

  const formCard = node("section", { class: "cms-card" });
  formCard.appendChild(node("h2", {}, "Create Series"));
  formCard.appendChild(form.element);
  root.appendChild(listCard);
  root.appendChild(formCard);
  await loadSeries().catch((e) => errSig.set(e.message));
}

async function mountBooksSection(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const listCard = node("section", { class: "cms-card" });
  listCard.appendChild(node("h2", {}, "Books Catalog & Store Linkage"));
  const listUl = node("ul", { class: "cms-list", role: "list" });
  listCard.appendChild(listUl);
  const booksSig = signal([]);

  async function loadBooks() {
    const res = await api.get("/api/admin/author/books");
    booksSig.set(Array.isArray(res.books) ? res.books : []);
  }

  ForEach({
    parent: listUl,
    items: booksSig,
    key: (b) => b.id,
    empty: () => node("li", { class: "cms-muted" }, "No books created yet."),
    render: (bSig) => {
      const b = bSig.peek();
      const li = node("li", { class: "cms-list-row" });
      const info = "#" + String(b.id) + " " + b.title + " — $" + b.list_price + " " + b.currency + " (" + b.edition_format + ", royalty: " + b.royalty_rate + "%, status: " + b.status + ")";
      li.appendChild(node("span", {}, info));
      const syncBtn = node("button", { type: "button", class: "cms-btn-secondary" }, "Sync to Store Product");
      syncBtn.addEventListener("click", async () => {
        errSig.set("");
        okSig.set("");
        try {
          await api.post("/api/admin/author/books/" + String(b.id) + "/sync-product", {});
          okSig.set("Synced book #" + String(b.id) + " to v1.1.0 store product.");
          await loadBooks();
        } catch (err) {
          errSig.set(err && err.message ? err.message : "Failed to sync book product.");
        }
      });
      li.appendChild(syncBtn);
      return li;
    },
  });

  const titleIn = Input({ id: "book-title", props: { name: "title", type: "text", label: "Book Title", required: true } });
  const slugIn = Input({ id: "book-slug", props: { name: "slug", type: "text", label: "Slug (/books/...)", required: true } });
  const authorIdIn = Input({ id: "book-author-id", props: { name: "author_id", type: "text", label: "Author ID", value: "1", required: true } });
  authorIdIn.inputElement.setAttribute("inputmode", "numeric");
  const isbnIn = Input({ id: "book-isbn", props: { name: "isbn_13", type: "text", label: "ISBN-13 (optional)" } });
  const asinIn = Input({ id: "book-asin", props: { name: "asin", type: "text", label: "ASIN (optional, 10 uppercase chars)" } });
  const priceIn = Input({ id: "book-price", props: { name: "list_price", type: "text", label: "List Price (USD exact string e.g. 14.99)", value: "14.99", required: true } });
  priceIn.inputElement.setAttribute("inputmode", "decimal");
  const royaltyIn = Input({ id: "book-royalty", props: { name: "royalty_rate", type: "text", label: "Royalty Rate % (0.00-100.00)", value: "70.00", required: true } });
  royaltyIn.inputElement.setAttribute("inputmode", "decimal");
  const fmtSel = Select({
    id: "book-format",
    props: {
      name: "edition_format",
      label: "Edition Format",
      value: "paperback",
      options: [
        { value: "paperback", label: "Paperback (Lulu / USPS)" },
        { value: "hardcover", label: "Hardcover (USPS)" },
        { value: "ebook", label: "eBook (Digital Grant)" },
        { value: "bundle", label: "Bundle" },
      ],
    },
  });
  const submitBtn = node("button", { type: "submit" }, "Save Book Draft");

  const form = Form({
    props: {
      method: "post",
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        const lp = priceIn.value.peek().trim();
        const rr = royaltyIn.value.peek().trim();
        if (!isExactGrabWireString(lp) || !isExactGrabWireString(rr)) {
          errSig.set("List price and royalty rate must be exact GrabDecimal strings (e.g. 14.99 and 70.00).");
          return;
        }
        try {
          await api.post("/api/admin/author/books", {
            title: titleIn.value.peek().trim(),
            slug: slugIn.value.peek().trim(),
            author_id: Number.parseInt(authorIdIn.value.peek().trim() || "1", 10),
            isbn_13: isbnIn.value.peek().trim(),
            asin: asinIn.value.peek().trim(),
            list_price: lp,
            royalty_rate: rr,
            edition_format: fmtSel.value.peek(),
            status: "draft",
          });
          okSig.set("Book draft created.");
          await loadBooks();
        } catch (err) {
          errSig.set(err && err.message ? err.message : "Failed to save book.");
        }
      },
    },
    children: [titleIn.element, slugIn.element, authorIdIn.element, isbnIn.element, asinIn.element, priceIn.element, royaltyIn.element, fmtSel.element, submitBtn],
  });

  const formCard = node("section", { class: "cms-card" });
  formCard.appendChild(node("h2", {}, "Add Book"));
  formCard.appendChild(form.element);
  root.appendChild(listCard);
  root.appendChild(formCard);
  await loadBooks().catch((e) => errSig.set(e.message));
}

async function mountChaptersSection(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const listCard = node("section", { class: "cms-card" });
  listCard.appendChild(node("h2", {}, "Manuscript Chapters & Sample Previews"));
  const listUl = node("ul", { class: "cms-list", role: "list" });
  listCard.appendChild(listUl);
  const chaptersSig = signal([]);

  async function loadChapters() {
    const res = await api.get("/api/admin/author/chapters");
    chaptersSig.set(Array.isArray(res.chapters) ? res.chapters : []);
  }

  ForEach({
    parent: listUl,
    items: chaptersSig,
    key: (c) => c.id,
    empty: () => node("li", { class: "cms-muted" }, "No chapters created yet."),
    render: (cSig) => {
      const c = cSig.peek();
      const li = node("li", { class: "cms-list-row" });
      li.appendChild(
        node("span", {}, "Book #" + String(c.book_id) + " Ch." + String(c.chapter_number) + " — " + c.title + (c.is_sample ? " [Sample]" : ""))
      );
      return li;
    },
  });

  const bookIdIn = Input({ id: "chap-book-id", props: { name: "book_id", type: "text", label: "Book ID", value: "1", required: true } });
  bookIdIn.inputElement.setAttribute("inputmode", "numeric");
  const titleIn = Input({ id: "chap-title", props: { name: "title", type: "text", label: "Chapter Title", required: true } });
  const slugIn = Input({ id: "chap-slug", props: { name: "slug", type: "text", label: "Chapter Slug", required: true } });
  const numIn = Input({ id: "chap-num", props: { name: "chapter_number", type: "text", label: "Chapter Number", value: "1", required: true } });
  numIn.inputElement.setAttribute("inputmode", "numeric");
  const sampleSel = Select({
    id: "chap-sample",
    props: {
      name: "is_sample",
      label: "Public Sample Reader",
      value: "1",
      options: [
        { value: "1", label: "Yes — Expose as free sample" },
        { value: "0", label: "No — Manuscript only" },
      ],
    },
  });
  const bodyIn = Input({ id: "chap-body", props: { name: "body_html", type: "text", label: "Chapter Prose / Excerpt" } });
  const saveBtn = node("button", { type: "submit" }, "Save Chapter Draft");

  const form = Form({
    props: {
      method: "post",
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        try {
          await api.post("/api/admin/author/chapters", {
            book_id: Number.parseInt(bookIdIn.value.peek().trim() || "1", 10),
            title: titleIn.value.peek().trim(),
            slug: slugIn.value.peek().trim(),
            chapter_number: Number.parseInt(numIn.value.peek().trim() || "1", 10),
            is_sample: sampleSel.value.peek() === "1",
            body_html: bodyIn.value.peek(),
            status: "draft",
          });
          okSig.set("Chapter draft saved.");
          await loadChapters();
        } catch (err) {
          errSig.set(err && err.message ? err.message : "Failed to save chapter.");
        }
      },
    },
    children: [bookIdIn.element, titleIn.element, slugIn.element, numIn.element, sampleSel.element, bodyIn.element, saveBtn],
  });

  const auditProseIn = Input({ id: "audit-prose", props: { name: "prose", type: "text", label: "Prose to Audit (Hemingway Readability)" } });
  const auditBtn = node("button", { type: "button", class: "cms-btn-secondary" }, "Run Readability Audit");
  const auditOut = node("p", { class: "cms-muted" }, "Connect Groxy AI in Settings to run live Hemingway readability audits.");
  auditBtn.addEventListener("click", async () => {
    errSig.set("");
    okSig.set("");
    try {
      const res = await api.post("/api/admin/author/readability-audit", { prose: auditProseIn.value.peek() });
      setSafeText(auditOut, JSON.stringify(res));
      okSig.set("Readability audit completed.");
    } catch (err) {
      errSig.set(err && err.message ? err.message : "Readability audit failed.");
    }
  });

  const formCard = node("section", { class: "cms-card" });
  formCard.appendChild(node("h2", {}, "Add Chapter"));
  formCard.appendChild(form.element);

  const auditCard = node("section", { class: "cms-card" });
  auditCard.appendChild(node("h2", {}, "Hemingway Readability Auditor (Groxy AI v1.7.0)"));
  auditCard.appendChild(auditProseIn.element);
  auditCard.appendChild(auditBtn);
  auditCard.appendChild(auditOut);

  root.appendChild(listCard);
  root.appendChild(formCard);
  root.appendChild(auditCard);
  await loadChapters().catch((e) => errSig.set(e.message));
}

async function mountRadarSection(root, api) {
  const errSig = signal("");
  const okSig = signal("");
  root.appendChild(makeAlert(errSig, false));
  root.appendChild(makeAlert(okSig, true));

  const proposalSig = signal(null);
  const dialogCtrl = createRadarConfirmationDialog(proposalSig, async (prop) => {
    errSig.set("");
    okSig.set("");
    try {
      const res = await api.post("/api/admin/author/radar/import", {
        radar_plan_id: prop.radar_plan_id,
        approval_token: prop.approval_token,
        payload_sha256: prop.payload_sha256,
        genre_slug: prop.genre_slug,
        target_type: "book",
        title: (prop.brief && prop.brief.display_name ? prop.brief.display_name : prop.genre_slug) + " Draft Concept",
        slug: String(prop.genre_slug || "radar") + "-" + String(prop.radar_plan_id || "draft").slice(-8),
        list_price: prop.selected_price_tier_usd || "14.99",
        brief: prop.brief || {},
      });
      okSig.set("Imported draft entry #" + String(res.entry ? res.entry.id : "") + " (status_enforced: " + String(res.status_enforced) + ").");
    } catch (err) {
      errSig.set(err && err.message ? err.message : "Failed to import radar draft.");
    }
  });

  const genreSel = Select({
    id: "radar-genre-slug",
    props: {
      name: "genre_slug",
      label: "Target Genre Playbook",
      value: "urban-fiction",
      options: [
        { value: "urban-fiction", label: "Urban Fiction" },
        { value: "thriller-mystery", label: "Thriller / Mystery" },
        { value: "romance", label: "Romance" },
        { value: "sci-fi-fantasy", label: "Sci-Fi / Fantasy" },
        { value: "self-help-reentry", label: "Self-Help / Re-Entry" },
        { value: "true-crime", label: "True Crime" },
      ],
    },
  });
  const tierIn = Input({ id: "radar-price-tier", props: { name: "price_tier_usd", type: "text", label: "Target Price Tier (USD exact string)", value: "14.99" } });
  tierIn.inputElement.setAttribute("inputmode", "decimal");

  const resultsCard = node("section", { class: "cms-card", "aria-live": "polite" });
  resultsCard.appendChild(node("h2", {}, "Bestseller Radar Brief & Unit Economics"));
  const resultsMount = node("section", { class: "cms-stack" });
  resultsMount.appendChild(node("p", { class: "cms-muted" }, "Run Bestseller Radar against your GRAB-E402 allowlisted Groxy AI v1.8.0 origin."));
  resultsCard.appendChild(resultsMount);

  const queryBtn = node("button", { type: "submit" }, "Query Bestseller Radar");
  const form = Form({
    props: {
      method: "post",
      onSubmit: async () => {
        errSig.set("");
        okSig.set("");
        const tierVal = tierIn.value.peek().trim();
        if (tierVal && !isExactGrabWireString(tierVal)) {
          errSig.set("Price tier must be an exact GrabDecimal USD string (e.g. 14.99).");
          return;
        }
        try {
          const data = await api.post("/api/admin/author/radar/query", {
            genre_slug: genreSel.value.peek(),
            price_tier_usd: tierVal || "14.99",
          });
          clearEl(resultsMount);
          const brief = data.brief || {};
          resultsMount.appendChild(
            node("p", {}, "Genre: " + String(data.genre_slug || "") + " · Tier: $" + String(data.selected_price_tier_usd || "14.99") + " USD · Plan: " + String(data.radar_plan_id || ""))
          );
          if (brief.demand_signal_score !== undefined) {
            resultsMount.appendChild(
              node("p", { class: "cms-muted" }, "Demand Score: " + String(brief.demand_signal_score) + " · Competition Index: " + String(brief.competition_index))
            );
          }
          const importBtn = node("button", { type: "button", id: "radar-open-import-btn", class: "cms-btn" }, "Import Draft Outline (1-Click)");
          importBtn.addEventListener("click", () => dialogCtrl.openForProposal(data));
          resultsMount.appendChild(importBtn);
          okSig.set("Radar brief ready for review.");
        } catch (err) {
          errSig.set(err && err.message ? err.message : "Radar query failed.");
        }
      },
    },
    children: [genreSel.element, tierIn.element, queryBtn],
  });

  const queryCard = node("section", { class: "cms-card" });
  queryCard.appendChild(node("h2", {}, "Embedded Bestseller Radar (Groxy AI v1.8.0)"));
  queryCard.appendChild(form.element);

  root.appendChild(queryCard);
  root.appendChild(resultsCard);
  root.appendChild(dialogCtrl.modal.element);
}

export async function mountAuthor(root, api, page) {
  root.appendChild(buildAuthorSubnav(page));
  const tabsBanner = Tabs({
    id: "author-mode-policy",
    props: {
      tabs: [
        {
          id: "draft-guard",
          label: "Draft-Only & ADR-025c Policy",
          content: node(
            "p",
            { class: "cms-muted" },
            "All radar imports and AI drafts enforce status: draft, validate ISBN-13/ASIN and exact USD GrabDecimal strings, and preserve v1.1.0 products as the checkout source of truth."
          ),
        },
      ],
    },
  });
  root.appendChild(tabsBanner.element);

  if (page === "author") {
    await mountOverviewSection(root, api);
  } else if (page === "author_authors") {
    await mountAuthorsSection(root, api);
  } else if (page === "author_series") {
    await mountSeriesSection(root, api);
  } else if (page === "author_books") {
    await mountBooksSection(root, api);
  } else if (page === "author_chapters") {
    await mountChaptersSection(root, api);
  } else if (page === "author_radar") {
    await mountRadarSection(root, api);
  }
}
