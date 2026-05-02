(function () {
  function ensureModal() {
    if (document.getElementById("m-confirm-del")) return;
    if (!document.getElementById("pc-del-confirm-styles")) {
      var s = document.createElement("style");
      s.id = "pc-del-confirm-styles";
      s.textContent =
        "#m-confirm-del{position:fixed;inset:0;z-index:1055;background:rgba(0,0,0,.55);display:none;align-items:center;justify-content:center;padding:1rem;}" +
        "#m-confirm-del .pc-del-box{background:#fff;border:2px solid #111;padding:1rem 1.25rem;max-width:22rem;width:100%;box-shadow:4px 4px 0 #000;}" +
        "#m-confirm-del .pc-del-msg{margin:0 0 1rem;font-size:0.95rem;line-height:1.35;}" +
        "#m-confirm-del .pc-del-row{display:flex;flex-wrap:wrap;gap:0.5rem;justify-content:flex-end;}" +
        "#m-confirm-del button{font:inherit;padding:0.35rem 0.75rem;cursor:pointer;border:2px solid #111;background:#fff;}" +
        "#m-confirm-del button.pc-del-yes{background:#c00;color:#fff;border-color:#111;}" +
        "#m-confirm-del button:active{transform:translate(1px,1px);box-shadow:none;}";
      document.head.appendChild(s);
    }
    document.body.insertAdjacentHTML(
      "beforeend",
      '<div id="m-confirm-del" role="dialog" aria-modal="true">' +
        '<div class="pc-del-box">' +
        '<p class="pc-del-msg" id="m-confirm-del-body"></p>' +
        '<div class="pc-del-row">' +
        '<button type="button" id="m-confirm-del-no">Отмена</button>' +
        '<button type="button" class="pc-del-yes" id="m-confirm-del-yes">Удалить</button>' +
        "</div></div></div>"
    );
  }

  window.confirmDelete = function confirmDelete(message) {
    return new Promise(function (resolve) {
      ensureModal();
      var root = document.getElementById("m-confirm-del");
      var box = root.querySelector(".pc-del-box");
      var body = document.getElementById("m-confirm-del-body");
      var yes = document.getElementById("m-confirm-del-yes");
      var no = document.getElementById("m-confirm-del-no");
      body.textContent = message;
      var settled = false;
      function finish(v) {
        if (settled) return;
        settled = true;
        document.removeEventListener("keydown", onKey);
        root.removeEventListener("click", onBackdrop);
        box.removeEventListener("click", stopProp);
        yes.removeEventListener("click", onYes);
        no.removeEventListener("click", onNo);
        root.style.display = "none";
        resolve(v);
      }
      function onYes() {
        finish(true);
      }
      function onNo() {
        finish(false);
      }
      function onBackdrop(e) {
        if (e.target === root) finish(false);
      }
      function stopProp(e) {
        e.stopPropagation();
      }
      function onKey(e) {
        if (e.key === "Escape") finish(false);
      }
      yes.addEventListener("click", onYes);
      no.addEventListener("click", onNo);
      root.addEventListener("click", onBackdrop);
      box.addEventListener("click", stopProp);
      document.addEventListener("keydown", onKey);
      root.style.display = "flex";
      yes.focus();
    });
  };
})();
