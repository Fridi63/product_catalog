const TOKEN_KEY = "pc_token";
function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function authHeaders() {
  const t = getToken();
  return t ? { Authorization: "Bearer " + t } : {};
}

async function apiFetch(path, init = {}) {
  const h = { ...authHeaders(), ...(init.headers || {}) };
  if (init.body && !h["Content-Type"]) h["Content-Type"] = "application/json";
  const r = await fetch(path, { ...init, headers: h });
  if (r.status === 401 && getToken()) {
    localStorage.removeItem(TOKEN_KEY);
    if (!path.includes("auth/login")) location.href = "/login";
  }
  return r;
}

let __me = null;

async function loadMe() {
  if (!getToken()) {
    __me = null;
    return null;
  }
  const r = await apiFetch("/api/auth/me", { method: "GET" });
  if (!r.ok) {
    __me = null;
    return null;
  }
  __me = await r.json();
  return __me;
}

function isRole() {
  if (!__me) return false;
  for (let i = 0; i < arguments.length; i++) {
    if (arguments[i] === __me.role) return true;
  }
  return false;
}

function showNav() {
  const u = document.getElementById("nav-user");
  const login = document.getElementById("nav-login");
  const out = document.getElementById("nav-logout");
  const nAudit = document.getElementById("nav-audit");
  const nUsers = document.getElementById("nav-users");
  if (u) u.textContent = __me ? __me.username + " (" + __me.role_display + ")" : "Гость";
  if (login) login.classList.toggle("d-none", !!__me);
  if (out) {
    out.classList.toggle("d-none", !__me);
    out.onclick = (e) => {
      e.preventDefault();
      localStorage.removeItem(TOKEN_KEY);
      __me = null;
      location.href = "/";
    };
  }
  if (nAudit) nAudit.classList.toggle("d-none", !isRole("admin"));
  if (nUsers) nUsers.classList.toggle("d-none", !isRole("admin"));
}

let __productModal = null;
let __usdModal = null;

function fmtPrice(n) {
  return n === undefined || n === null ? "" : String(n);
}

function renderTable(rows) {
  const tbody = document.getElementById("tbody");
  if (!tbody) return;
  const showSpec = isRole("advanced", "admin");
  document.querySelectorAll(".col-spec").forEach((el) => {
    el.style.display = showSpec ? "" : "none";
  });
  const thAct = document.getElementById("th-actions");
  const canAct = isRole("simple", "advanced", "admin");
  if (thAct) thAct.style.display = canAct ? "" : "none";
  const canDel = isRole("advanced", "admin");
  tbody.innerHTML = "";
  for (const p of rows) {
    const tr = document.createElement("tr");
    const nameTd = document.createElement("td");
    nameTd.textContent = p.name;
    tr.appendChild(nameTd);
    const catTd = document.createElement("td");
    const a = document.createElement("a");
    a.href = "#";
    a.textContent = p.category_name;
    a.addEventListener("click", (e) => {
      e.preventDefault();
      const sel = document.getElementById("filter-cat");
      if (sel) {
        sel.value = String(p.category_id);
        loadProducts();
      }
    });
    catTd.appendChild(a);
    tr.appendChild(catTd);
    const dTd = document.createElement("td");
    dTd.textContent = p.description;
    tr.appendChild(dTd);
    const priceCell = document.createElement("td");
    priceCell.appendChild(document.createTextNode(fmtPrice(p.price) + " "));
    const usd = document.createElement("span");
    usd.className = "asterisk-cur";
    usd.setAttribute("data-byn", p.price);
    usd.setAttribute("title", "Стоимость в USD из BYN (НБ РБ)");
    usd.textContent = "*";
    usd.addEventListener("mouseenter", onHoverUsd);
    priceCell.appendChild(usd);
    tr.appendChild(priceCell);
    const gTd = document.createElement("td");
    gTd.textContent = p.general_note;
    tr.appendChild(gTd);
    if (showSpec) {
      const sTd = document.createElement("td");
      sTd.className = "col-spec";
      sTd.textContent = p.special_note == null ? "—" : p.special_note;
      tr.appendChild(sTd);
    }
    if (canAct) {
      const aTd = document.createElement("td");
      aTd.className = "text-end";
      const b1 = document.createElement("button");

      b1.className = "btn btn-sm btn-outline-primary me-1";
      b1.type = "button";
      b1.textContent = "Изм.";
      b1.addEventListener("click", () => openProductModal(p));
      aTd.appendChild(b1);
      if (canDel) {
        const b2 = document.createElement("button");
        b2.className = "btn btn-sm btn-outline-danger";
        b2.type = "button";
        b2.textContent = "Удал.";
        b2.addEventListener("click", () => delProduct(p.id, p.name));
        aTd.appendChild(b2);
      }
      tr.appendChild(aTd);
    }
    tbody.appendChild(tr);
  }
}

let __usdTimer = null;
function onHoverUsd(e) {
  if (__usdTimer) clearTimeout(__usdTimer);
  const byn = e.currentTarget.getAttribute("data-byn");
  __usdTimer = setTimeout(() => showUsd(byn), 200);
}

async function showUsd(byn) {
  const body = document.getElementById("usd-body");
  if (!__usdModal) __usdModal = new bootstrap.Modal("#m-usd");
  body.textContent = "Запрос к API НБ РБ…";
  __usdModal.show();
  const u = new URLSearchParams();
  u.set("amount_byn", byn);
  const r = await apiFetch("/api/fx/byn-to-usd?" + u.toString(), { method: "GET" });
  if (!r.ok) {
    const j = await r.json().catch(() => ({}));
    body.innerHTML = "<p class='text-danger'>" + (j.detail || "Ошибка " + r.status) + "</p>";
    return;
  }
  const d = await r.json();
  body.innerHTML =
    "<p><strong>" + d.amount_byn + " BYN</strong> ≈ <strong>" + d.amount_usd + " USD</strong></p>" +
    "<p class='small text-muted'>Дата курса: " + d.on_date + "</p>";
}

async function loadCategories() {
  const r = await apiFetch("/api/categories", { method: "GET" });
  if (!r.ok) return;
  const data = await r.json();
  const f = document.getElementById("filter-cat");
  const pf = document.getElementById("pf-cat");
  const prevF = f ? f.value : "";
  if (f) {
    f.innerHTML = '<option value="">Все</option>';
    for (const c of data) {
      const o = document.createElement("option");
      o.value = c.id;
      o.textContent = c.name;
      f.appendChild(o);
    }
    f.value = prevF;
  }
  if (pf) {
    const prevP = pf.value;
    pf.innerHTML = "";
    for (const c of data) {
      const o = document.createElement("option");
      o.value = c.id;
      o.textContent = c.name;
      pf.appendChild(o);
    }
    if (prevP) pf.value = prevP;
  }
}

async function loadProducts() {
  const u = new URLSearchParams();
  const q = document.getElementById("filter-q");
  const c = document.getElementById("filter-cat");
  if (q && q.value.trim()) u.set("q", q.value.trim());
  if (c && c.value) u.set("category_id", c.value);
  const r = await apiFetch("/api/products?" + u.toString(), { method: "GET" });
  if (!r.ok) return;
  renderTable(await r.json());
}

let __editProductId = null;

function openProductModal(p) {
  if (!__productModal) __productModal = new bootstrap.Modal("#m-product");
  __editProductId = p ? p.id : null;
  document.getElementById("m-product-title").textContent = p ? "Правка" : "Новый продукт";
  document.getElementById("pf-err").textContent = "";
  document.getElementById("pf-name").value = p ? p.name : "";
  document.getElementById("pf-desc").value = p ? p.description : "";
  document.getElementById("pf-price").value = p ? p.price : "";
  document.getElementById("pf-g").value = p ? p.general_note : "";
  const w = document.getElementById("wrap-pf-s");
  if (isRole("advanced", "admin")) {
    w.classList.remove("d-none");
    document.getElementById("pf-s").value = p && p.special_note != null ? p.special_note : "";
  } else {
    w.classList.add("d-none");
  }
  const pc = document.getElementById("pf-cat");
  if (p) pc.value = String(p.category_id);
  else if (pc.options.length) pc.selectedIndex = 0;
  __productModal.show();
}

async function delProduct(id, name) {
  if (!(await confirmDelete("Удалить «" + name + "»?"))) return;
  const r = await apiFetch("/api/products/" + id, { method: "DELETE" });
  if (r.status === 204) loadProducts();
  else {
    const j = await r.json().catch(() => ({}));
    alert(j.detail || "Ошибка");
  }
}


function buildProductBody() {
  const body = {
    name: document.getElementById("pf-name").value.trim(),
    description: document.getElementById("pf-desc").value,
    price: document.getElementById("pf-price").value,
    general_note: document.getElementById("pf-g").value,
    category_id: +document.getElementById("pf-cat").value,
  };
  if (isRole("advanced", "admin")) {
    body.special_note = document.getElementById("pf-s").value;
  } else {
    body.special_note = "";
  }
  return body;
}

function buildProductPatch() {
  const b = buildProductBody();
  if (isRole("simple")) delete b.special_note;
  return b;
}

async function initIndex() {
  await loadMe();
  showNav();
  document.getElementById("wrap-add-prod")?.classList.toggle("d-none", !isRole("simple", "advanced", "admin"));
  document.getElementById("wrap-cat-manage")?.classList.toggle("d-none", !isRole("advanced", "admin"));
  document.getElementById("btn-new-product")?.addEventListener("click", () => {
    if (isRole("simple", "advanced", "admin")) openProductModal(null);
  });
  document.getElementById("btn-apply")?.addEventListener("click", () => loadProducts());
  await loadCategories();
  await loadProducts();

  document.getElementById("f-product")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = document.getElementById("pf-err");
    err.textContent = "";
    const isEdit = __editProductId != null;
    const body = isEdit ? buildProductPatch() : buildProductBody();
    const url = isEdit ? "/api/products/" + __editProductId : "/api/products";
    const m = isEdit ? "PATCH" : "POST";
    const r = await apiFetch(url, { method: m, body: JSON.stringify(body) });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      if (Array.isArray(j.detail)) {
        err.textContent = j.detail.map((x) => (x.msg ? x.msg : JSON.stringify(x))).join(" ");
      } else {
        err.textContent = (typeof j.detail === "string" ? j.detail : null) || "Ошибка";
      }
      return;
    }
    if (__productModal) __productModal.hide();
    loadProducts();
  });
}


function initCategoryModal() {
  const m = document.getElementById("m-cat");
  const form = document.getElementById("f-new-cat");
  const list = document.getElementById("cat-list");
  if (!m || !form || !list) return;
  async function refillCategoryManageList() {
    if (!isRole("advanced", "admin")) return;
    const catErr = document.getElementById("cat-err");
    const r = await apiFetch("/api/categories", { method: "GET" });
    if (!r.ok) return;
    const cats = await r.json();
    list.innerHTML = "";
    function viewRow(li, c) {
      li.className = "list-group-item d-flex justify-content-between align-items-center flex-wrap gap-2";
      li.replaceChildren();
      const lab = document.createElement("span");
      lab.textContent = c.name + " (" + c.product_count + " товар.)";
      li.appendChild(lab);
      const d = document.createElement("div");
      d.className = "d-flex gap-1";
      const b1 = document.createElement("button");
      b1.className = "btn btn-sm btn-outline-primary";
      b1.type = "button";
      b1.textContent = "Переим.";
      b1.addEventListener("click", () => editRow(li, c));
      const b2 = document.createElement("button");
      b2.className = "btn btn-sm btn-outline-danger";
      b2.type = "button";
      b2.textContent = "Удалить";
      b2.addEventListener("click", async () => {
        if (!(await confirmDelete("Удалить категорию и ВСЕ товары в ней?"))) return;
        const pr = await apiFetch("/api/categories/" + c.id, { method: "DELETE" });
        if (pr.status === 204) {
          loadCategories();
          loadProducts();
          await refillCategoryManageList();
        } else {
          const j = await pr.json().catch(() => ({}));
          if (catErr) catErr.textContent = (j && j.detail) || "Ошибка";
        }
      });
      d.appendChild(b1);
      d.appendChild(b2);
      li.appendChild(d);
    }
    function editRow(li, c) {
      if (catErr) catErr.textContent = "";
      li.className = "list-group-item";
      li.replaceChildren();
      const row = document.createElement("div");
      row.className = "d-flex flex-wrap gap-2 align-items-center w-100";
      const inp = document.createElement("input");
      inp.className = "form-control form-control-sm";
      inp.maxLength = 128;
      inp.value = c.name;
      inp.style.flex = "1 1 10rem";
      const ok = document.createElement("button");
      ok.type = "button";
      ok.className = "btn btn-sm btn-primary";
      ok.textContent = "Ок";
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.className = "btn btn-sm btn-outline-secondary";
      cancel.textContent = "Отмена";
      const errLine = document.createElement("small");
      errLine.className = "text-danger d-block w-100 mt-1";
      row.appendChild(inp);
      row.appendChild(ok);
      row.appendChild(cancel);
      li.appendChild(row);
      li.appendChild(errLine);
      cancel.addEventListener("click", () => refillCategoryManageList());
      ok.addEventListener("click", async () => {
        errLine.textContent = "";
        const name = inp.value.trim();
        if (!name) return;
        const pr = await apiFetch("/api/categories/" + c.id, { method: "PATCH", body: JSON.stringify({ name }) });
        if (pr.ok) {
          loadCategories();
          loadProducts();
          await refillCategoryManageList();
        } else {
          const j = await pr.json().catch(() => ({}));
          if (Array.isArray(j.detail)) {
            errLine.textContent = j.detail.map((x) => (x.msg ? x.msg : JSON.stringify(x))).join(" ");
          } else {
            errLine.textContent = (typeof j.detail === "string" ? j.detail : null) || "Ошибка";
          }
        }
      });
      inp.focus();
      inp.select();
    }
    for (const c of cats) {
      const li = document.createElement("li");

      list.appendChild(li);
      viewRow(li, c);
    }
  }
  m.addEventListener("show.bs.modal", () => {
    refillCategoryManageList();
  });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = document.getElementById("cat-err");
    if (err) err.textContent = "";
    const name = document.getElementById("in-new-cat").value.trim();
    if (!name) return;
    const pr = await apiFetch("/api/categories", { method: "POST", body: JSON.stringify({ name }) });
    if (!pr.ok) {
      const j = await pr.json();
      if (err) err.textContent = j.detail || "Ошибка";
      return;
    }
    document.getElementById("in-new-cat").value = "";
    loadCategories();
    loadProducts();
  });
}

let __ueModal = null;
let __ueUser = null;

async function initUsers() {
  await loadMe();
  showNav();
  if (!isRole("admin")) {
    document.querySelector("main")?.insertAdjacentHTML(
      "afterbegin",
      "<p class='alert alert-warning'>Нужны права администратора.</p>"
    );
    return;
  }
  const tb = document.getElementById("users-table");
  const newWrap = document.getElementById("new-user-wrap");
  if (tb) tb.style.display = "";
  if (newWrap) newWrap.style.display = "";
  const r = await apiFetch("/api/users", { method: "GET" });
  if (!r.ok) return;
  const data = await r.json();
  const list = document.getElementById("user-list");
  if (!list) return;
  list.textContent = "";
  for (const u of data) {
    const tr = document.createElement("tr");
    const t1 = document.createElement("td");
    t1.textContent = u.username;
    const t2 = document.createElement("td");
    t2.textContent = u.role_display;
    const t3 = document.createElement("td");
    t3.textContent = u.is_blocked ? "да" : "нет";
    const t4 = document.createElement("td");
    const b1 = document.createElement("button");
    b1.className = "btn btn-sm btn-primary";
    b1.type = "button";
    b1.textContent = "Изменить";
    b1.addEventListener("click", () => {
      __ueUser = u;
      if (!__ueModal) __ueModal = new bootstrap.Modal("#m-user");
      document.getElementById("u-err").textContent = "";
      document.getElementById("u-id").value = u.id;
      document.getElementById("u-pass").value = "";
      document.getElementById("u-role").value = u.role;
      document.getElementById("u-block").checked = u.is_blocked;
      __ueModal.show();
    });
    const b2 = document.createElement("button");
    b2.className = "btn btn-sm btn-outline-danger";
    b2.type = "button";
    b2.textContent = "Удалить";
    b2.addEventListener("click", async () => {
      if (!(await confirmDelete("Удалить " + u.username + "?"))) return;
      apiFetch("/api/users/" + u.id, { method: "DELETE" }).then((x) => {
        if (x.status === 204) initUsers();
        else
          x.json().then((j) => {
            alert(j.detail || "Ошибка");
          });
      });
    });
    t4.appendChild(b1);
    t4.appendChild(b2);
    tr.appendChild(t1);
    tr.appendChild(t2);
    tr.appendChild(t3);
    tr.appendChild(t4);
    list.appendChild(tr);
  }
  const fu = document.getElementById("f-user");
  if (fu && !fu.dataset.bound) {
    fu.dataset.bound = "1";
    fu.addEventListener("submit", async (e) => {
      e.preventDefault();
      const err = document.getElementById("u-err");
      err.textContent = "";
      const id = +document.getElementById("u-id").value;
      const body = {
        role: document.getElementById("u-role").value,
        is_blocked: document.getElementById("u-block").checked,
      };
      const pw = document.getElementById("u-pass").value;
      if (pw) body.password = pw;
      const rs = await apiFetch("/api/users/" + id, { method: "PATCH", body: JSON.stringify(body) });
      if (rs.ok) {
        if (__ueModal) __ueModal.hide();
        initUsers();
      } else {
        const j = await rs.json();
        err.textContent = j.detail || "Ошибка";
      }
    });
  }
  const fnu = document.getElementById("f-new-user");
  if (fnu && !fnu.dataset.bound) {
    fnu.dataset.bound = "1";

    fnu.addEventListener("submit", async (e) => {
      e.preventDefault();
      const ne = document.getElementById("nu-err");
      ne.textContent = "";
      const fd = new FormData(fnu);
      const body = {
        username: fd.get("username"),
        password: fd.get("password"),
        role: fd.get("role"),
      };
      const rs = await apiFetch("/api/users", { method: "POST", body: JSON.stringify(body) });
      if (rs.ok) {
        fnu.reset();
        initUsers();
      } else {
        const j = await rs.json();
        ne.textContent = (typeof j.detail === "string" ? j.detail : "Ошибка");
      }
    });
  }
}

async function initLogs() {
  await loadMe();
  showNav();
  if (!isRole("admin")) {
    document.querySelector("main")?.insertAdjacentHTML(
      "afterbegin",
      "<p class='alert alert-warning'>Нужны права администратора.</p>"
    );
    return;
  }
  const t = document.getElementById("log-body");
  const table = document.getElementById("log-table");
  if (table) table.style.display = "";
  if (!t) return;
  const r = await apiFetch("/api/audit-logs", { method: "GET" });
  if (!r.ok) return;
  const data = await r.json();
  t.textContent = "";
  for (const row of data) {
    const tr = document.createElement("tr");
    for (const col of [row.created_at, row.username, row.action, row.detail]) {
      const td = document.createElement("td");
      if (row.detail && col === row.detail) {
        td.className = "small";
      } else {
        td.className = "text-nowrap small";
      }
      td.textContent = col == null ? "" : String(col);
      tr.appendChild(td);
    }
    t.appendChild(tr);
  }
}
document.addEventListener("DOMContentLoaded", () => {
  const path = location.pathname;
  if (path === "/") {
    initIndex();
    initCategoryModal();
  } else if (path === "/admin/users") {
    if (document.getElementById("user-list")) initUsers();
  } else if (path === "/admin/logs") {
    if (document.getElementById("log-body")) initLogs();
  } else if (path === "/login") {
    loadMe().then((m) => {
      showNav();
      if (m) location.href = "/";
    });
  } else {
    loadMe().then(() => showNav());
  }
});