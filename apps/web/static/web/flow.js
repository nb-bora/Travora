/* Parcours guidés : totaux en direct, montants rapides, monnaie à rendre. Sans dépendance. */
(function () {
  "use strict";
  var NARROW = " ";

  function value(token) {
    var number = Number(token);
    if (!Number.isNaN(number) && token !== "") return number;
    var field = document.getElementById(token);
    return field ? parseInt(field.value, 10) || 0 : 0;
  }

  function evaluate(terms) {
    // « a*b + c*2 - d » : sommes et produits d'identifiants de champs ou de nombres.
    var total = 0;
    var parts = terms.split(/ ([+-]) /);
    var sign = 1;
    for (var i = 0; i < parts.length; i += 1) {
      if (parts[i] === "+") { sign = 1; continue; }
      if (parts[i] === "-") { sign = -1; continue; }
      var product = 1;
      parts[i].split("*").forEach(function (token) { product *= value(token.trim()); });
      total += sign * product;
    }
    return total;
  }

  function format(amount) {
    return String(Math.abs(amount)).replace(/\B(?=(\d{3})+(?!\d))/g, NARROW) + " FCFA";
  }

  var calculators = Array.prototype.slice.call(document.querySelectorAll("[data-terms]"));
  function refresh() {
    calculators.forEach(function (node) {
      var result = evaluate(node.getAttribute("data-terms"));
      node.textContent = (result < 0 ? "−" : "") + format(result);
    });
  }
  if (calculators.length) {
    document.addEventListener("input", refresh);
    refresh();
  }

  // Montants rapides du paiement : « Tout le solde », « 50 % », « Autre montant ».
  var amount = document.getElementById("id_amount_xaf");
  Array.prototype.forEach.call(document.querySelectorAll("[data-preset]"), function (radio) {
    radio.addEventListener("change", function () {
      if (!amount || !radio.checked) return;
      var due = parseInt(amount.getAttribute("data-due"), 10) || 0;
      var share = radio.getAttribute("data-preset");
      if (share === "all") amount.value = due;
      if (share === "half") amount.value = Math.round(due / 2);
      if (share === "other") { amount.value = ""; amount.focus(); }
      amount.dispatchEvent(new Event("input", { bubbles: true }));
    });
  });

  // Solde restant après l'encaissement et monnaie à rendre (espèces).
  var remaining = document.getElementById("remaining-after");
  var change = document.getElementById("change-due");
  var given = document.getElementById("id_given_xaf");
  function updatePayment() {
    if (!amount) return;
    var due = parseInt(amount.getAttribute("data-due"), 10) || 0;
    var paid = parseInt(amount.value, 10) || 0;
    if (remaining) remaining.textContent = format(Math.max(due - paid, 0));
    if (change && given) {
      var handed = parseInt(given.value, 10) || 0;
      change.textContent = format(Math.max(handed - paid, 0));
    }
  }
  if (amount) {
    amount.addEventListener("input", updatePayment);
    if (given) given.addEventListener("input", updatePayment);
    updatePayment();
  }

  // Copier le message de remise, imprimer.
  Array.prototype.forEach.call(document.querySelectorAll("[data-copy]"), function (button) {
    button.addEventListener("click", function () {
      var source = document.getElementById(button.getAttribute("data-copy"));
      if (source && navigator.clipboard) {
        navigator.clipboard.writeText(source.innerText.trim());
        button.textContent = "Copié";
      }
    });
  });
  Array.prototype.forEach.call(document.querySelectorAll("[data-print]"), function (button) {
    button.addEventListener("click", function () { window.print(); });
  });

  // Double clic : le bouton principal se bloque après l'envoi.
  var form = document.getElementById("flow-form");
  if (form) {
    form.addEventListener("submit", function (event) {
      var submitter = event.submitter;
      if (submitter && submitter.classList.contains("btn-primary")) {
        setTimeout(function () { submitter.disabled = true; }, 0);
      }
    });
  }
})();
