/* Raccourcis clavier : Ctrl/⌘ K ou « / » pour chercher. Aucune autre dépendance. */
(function () {
  "use strict";
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
