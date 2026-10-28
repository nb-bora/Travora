/* Raccourcis clavier (Ctrl/⌘ K ou « / » pour chercher) et collage de billet. Aucune dépendance. */
(function () {
  "use strict";

  /* Coller un billet n'importe où sur la page : le texte part à l'analyse, sans rien enregistrer. */
  var form = document.getElementById("paste-form");
  var area = document.getElementById("paste-text");
  if (form && area) {
    document.addEventListener("paste", function (event) {
      var typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
      var text = event.clipboardData && event.clipboardData.getData("text");
      if (typing || !text || text.length < 40) return;
      event.preventDefault();
      area.value = text;
      form.requestSubmit();
    });
  }

  /* Ripple sur les boutons principaux, sans effet si l'utilisateur réduit les animations. */
  var calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!calm) {
    document.addEventListener("pointerdown", function (event) {
      var button = event.target.closest && event.target.closest(".btn-primary");
      if (!button || button.disabled) return;
      var box = button.getBoundingClientRect();
      var size = Math.max(box.width, box.height) * 2;
      var wave = document.createElement("span");
      wave.className = "ripple";
      wave.style.width = wave.style.height = size + "px";
      wave.style.left = event.clientX - box.left - size / 2 + "px";
      wave.style.top = event.clientY - box.top - size / 2 + "px";
      wave.addEventListener("animationend", function () { wave.remove(); });
      button.appendChild(wave);
    });
  }

  var search = document.getElementById("search");
  if (!search) return;
  document.addEventListener("keydown", function (event) {
    var typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
    var combo = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k";
    if (combo || (!typing && event.key === "/")) {
      event.preventDefault();
      search.focus();
      search.select();
    }
  });
})();
