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
