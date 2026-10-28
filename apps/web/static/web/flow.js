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

  // Plan du car : les places saisies s'allument en direct.
  var map = document.querySelector(".seat-map");
  if (map) {
    var counter = document.getElementById("seat-count");
    var paint = function () {
      var chosen = {};
      Array.prototype.forEach.call(document.querySelectorAll("input[name$='-seat']"), function (input) {
        var value = input.value.trim();
        if (value) chosen[String(parseInt(value, 10))] = true;
      });
      Array.prototype.forEach.call(map.querySelectorAll(".seat"), function (cell) {
        cell.classList.toggle("seat-chosen", chosen[cell.textContent.trim()] === true);
      });
      if (counter) {
        var total = counter.getAttribute("data-total");
        counter.textContent = Object.keys(chosen).length + " sur " + total + " place" + (total > 1 ? "s" : "");
      }
    };
    document.addEventListener("input", paint);
    paint();
  }

  // Plan d'une voiture de train : la voiture et les places du premier voyageur s'allument.
  var carMap = document.querySelector(".car-map");
  if (carMap) {
    var title = document.getElementById("car-title");
    var paintCar = function () {
      var cars = document.querySelectorAll("input[name$='-car']");
      var seats = document.querySelectorAll("input[name$='-seat']");
      var shown = cars.length ? cars[0].value.trim() : "";
      if (title) title.textContent = shown || "?";
      var chosen = {};
      Array.prototype.forEach.call(cars, function (car, index) {
        var seat = seats[index] ? seats[index].value.trim() : "";
        if (seat && car.value.trim() === shown) chosen[String(parseInt(seat, 10))] = true;
      });
      Array.prototype.forEach.call(carMap.querySelectorAll(".seat"), function (cell) {
        cell.classList.toggle("seat-chosen", chosen[cell.textContent.trim()] === true);
      });
    };
    document.addEventListener("input", paintCar);
    paintCar();
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

  // Glissement entre étapes : le sens (avant/arrière) vient de l'étape précédente, gardée en session.
  var main = document.querySelector(".flow-main[data-step]");
  if (main) {
    try {
      var key = "flow-step-" + main.getAttribute("data-flow");
      var previous = parseInt(sessionStorage.getItem(key), 10);
      var current = parseInt(main.getAttribute("data-step"), 10);
      if (previous && current < previous) main.setAttribute("data-dir", "back");
      sessionStorage.setItem(key, String(current));
    } catch (error) { /* stockage indisponible : on glisse vers l'avant */ }
  }

  // Contrôle segmenté : l'indicateur glisse de l'ancien onglet vers le nouveau.
  Array.prototype.forEach.call(document.querySelectorAll(".seg"), function (seg, index) {
    var active = seg.querySelector('[aria-selected="true"]');
    if (!active) return;
    var pill = document.createElement("span");
    pill.className = "seg-pill";
    pill.setAttribute("aria-hidden", "true");
    seg.insertBefore(pill, seg.firstChild);
    var place = function (left) {
      seg.style.setProperty("--seg-x", left + "px");
      seg.style.setProperty("--seg-w", active.offsetWidth + "px");
    };
    var storeKey = "seg-left-" + index;
    var from = null;
    try { from = sessionStorage.getItem(storeKey); } catch (error) { from = null; }
    seg.classList.add("is-sliding");
    place(from !== null ? parseFloat(from) : active.offsetLeft);
    window.requestAnimationFrame(function () { place(active.offsetLeft); });
    try { sessionStorage.setItem(storeKey, String(active.offsetLeft)); } catch (error) { /* ignoré */ }
  });

  // Autocomplétion des villes : le <datalist> reste le repli sans JavaScript.
  function plain(text) {
    return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }
  Array.prototype.forEach.call(document.querySelectorAll("input[list]"), function (input) {
    var source = document.getElementById(input.getAttribute("list"));
    var host = input.closest(".control");
    if (!source || !host) return;
    var options = Array.prototype.map.call(source.options, function (option) { return option.value; });
    var box = document.createElement("ul");
    box.className = "combo";
    box.id = input.id + "-listbox";
    box.setAttribute("role", "listbox");
    box.hidden = true;
    host.appendChild(box);
    input.removeAttribute("list");
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-controls", box.id);
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("autocomplete", "off");
    var shown = [];
    var active = 0;

    function close() { box.hidden = true; input.setAttribute("aria-expanded", "false"); }
    function choose(value) { input.value = value; close(); input.dispatchEvent(new Event("input", { bubbles: true })); }
    function paintActive() {
      Array.prototype.forEach.call(box.children, function (item, position) {
        item.setAttribute("aria-selected", position === active ? "true" : "false");
      });
    }
    function render() {
      var query = plain(input.value.trim());
      shown = options.filter(function (name) { return !query || plain(name).indexOf(query) !== -1; });
      active = 0;
      box.textContent = "";
      shown.forEach(function (name, position) {
        var item = document.createElement("li");
        item.setAttribute("role", "option");
        var at = query ? plain(name).indexOf(query) : -1;
        if (at >= 0) {
          item.appendChild(document.createTextNode(name.slice(0, at)));
          var mark = document.createElement("mark");
          mark.textContent = name.slice(at, at + query.length);
          item.appendChild(mark);
          item.appendChild(document.createTextNode(name.slice(at + query.length)));
        } else {
          item.textContent = name;
        }
        item.addEventListener("mousedown", function (event) { event.preventDefault(); choose(shown[position]); });
        item.addEventListener("mouseenter", function () { active = position; paintActive(); });
        box.appendChild(item);
      });
      if (!shown.length) {
        var empty = document.createElement("li");
        empty.className = "combo-empty";
        empty.textContent = "Aucune ville ne correspond.";
        box.appendChild(empty);
      }
      paintActive();
      box.hidden = false;
      input.setAttribute("aria-expanded", "true");
    }
    input.addEventListener("input", render);
    input.addEventListener("focus", render);
    input.addEventListener("blur", close);
    input.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        if (box.hidden) render();
        active = event.key === "ArrowDown" ? Math.min(active + 1, shown.length - 1) : Math.max(active - 1, 0);
        paintActive();
      } else if (event.key === "Enter" && !box.hidden && shown[active]) {
        event.preventDefault();
        choose(shown[active]);
      } else if (event.key === "Escape") {
        close();
      }
    });
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
