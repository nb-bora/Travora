/* Connexion : afficher le mot de passe, alerte majuscules, bouton occupé pendant l'envoi. */
(function () {
  "use strict";
  var form = document.getElementById("login-form");
  if (!form) return;

  var toggle = form.querySelector("[data-toggle-password]");
  var password = document.getElementById("id_password");
  if (toggle && password) {
    toggle.addEventListener("click", function () {
      var show = password.type === "password";
      password.type = show ? "text" : "password";
      toggle.setAttribute("aria-pressed", String(show));
      toggle.setAttribute("aria-label", show ? "Masquer le mot de passe" : "Afficher le mot de passe");
    });
  }

  var caps = document.getElementById("caps-hint");
  if (password && caps) {
    password.addEventListener("keyup", function (event) {
      caps.hidden = !(event.getModifierState && event.getModifierState("CapsLock"));
    });
    password.addEventListener("blur", function () { caps.hidden = true; });
  }

  form.addEventListener("submit", function () {
    var button = form.querySelector(".auth-submit");
    if (!button) return;
    window.setTimeout(function () {
      button.setAttribute("aria-busy", "true");
      button.disabled = true;
      button.querySelector(".auth-submit-label").textContent = "Connexion…";
    }, 0);
  });
})();
