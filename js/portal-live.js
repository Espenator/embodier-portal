/* Embodier portal LIVE data layer — vanilla JS, no dependencies.
 *
 * Takes over the prototype portal's sections with real backend data when a
 * session token and apiBase are configured. The prototype (index.html) keeps
 * working untouched in demo mode (no apiBase).
 *
 * How it hooks in: the prototype renders mock content into <section class="view">
 * blocks and switches tabs via [data-tab] buttons. This layer listens for tab
 * clicks (capture phase), lets the prototype do its thing, then re-renders the
 * active section with live API data. Pure render functions return HTML strings
 * (testable); thin mount functions touch the DOM.
 *
 * States per section: loading skeleton -> content | error (with retry) | empty.
 * 401 anywhere -> session cleared -> login gate. Exchange is ALWAYS
 * waitlist-only (pre-DASP): the backend's exchange block is rendered verbatim.
 */
(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory(root);
  } else {
    root.EmbodierPortalLive = factory(root);
  }
})(typeof self !== "undefined" ? self : this, function (root) {
  "use strict";

  var STR = {
    en: {
      loading: "Loading…",
      retry: "Try again",
      loadError: "Couldn't load this section. Check your connection and try again.",
      empty: "Nothing here yet.",
      loginTitle: "Sign in to your panel",
      loginBody: "This panel opens after phone verification. Enter your phone number to get your code.",
      loginCta: "Go to sign in",
      brokerTab: "Broker",
      brokerTitle: "Broker panel",
      deals: "Deals",
      pipeline: "Pipeline",
      commissions: "Commissions",
      buybox: "Buy box",
      noDeals: "No deals yet.",
      noCommissions: "No commissions yet.",
      noBuybox: "No buy-box criteria set.",
      stage: "Stage",
      expected: "Expected",
      status: "Status",
      expressInterest: "Express interest",
      offeringPlaceholder: "Offering ID (e.g. chable-maroma)",
      notePlaceholder: "Note (optional)",
      interestHeld: "Place held — we'll be in touch.",
      backToLogin: "Back to sign in",
    },
    es: {
      loading: "Cargando…",
      retry: "Reintentar",
      loadError: "No se pudo cargar esta sección. Revisa tu conexión e inténtalo de nuevo.",
      empty: "Nada por aquí todavía.",
      loginTitle: "Inicia sesión en tu panel",
      loginBody: "Este panel se abre después de verificar tu teléfono. Ingresa tu número para recibir tu código.",
      loginCta: "Ir a iniciar sesión",
      brokerTab: "Bróker",
      brokerTitle: "Panel del bróker",
      deals: "Negocios",
      pipeline: "Tubería",
      commissions: "Comisiones",
      buybox: "Criterios",
      noDeals: "Sin negocios todavía.",
      noCommissions: "Sin comisiones todavía.",
      noBuybox: "Sin criterios definidos.",
      stage: "Etapa",
      expected: "Esperado",
      status: "Estado",
      expressInterest: "Expresar interés",
      offeringPlaceholder: "ID de oferta (p. ej. chable-maroma)",
      notePlaceholder: "Nota (opcional)",
      interestHeld: "Lugar reservado — nos pondremos en contacto.",
      backToLogin: "Volver a iniciar sesión",
    },
  };

  function t(lang, key) {
    var pack = STR[lang] === undefined ? STR.en : STR[lang];
    return pack[key] !== undefined ? pack[key] : (STR.en[key] || key);
  }

  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function langOf(doc) {
    try {
      var l = (doc.documentElement.getAttribute("lang") || "en").slice(0, 2).toLowerCase();
      return l === "es" ? "es" : "en";
    } catch (e) { return "en"; }
  }

  // --- shared states ---------------------------------------------------------
  function renderLoading(lang) {
    return '<div class="live-state" data-live="loading"><div class="eyebrow">' +
      esc(t(lang, "loading")) + '</div><div class="card live-skeleton"></div></div>';
  }

  function renderError(lang, detail) {
    return '<div class="live-state" data-live="error"><div class="card live-error">' +
      '<p class="muted">' + esc(t(lang, "loadError")) + '</p>' +
      (detail ? '<p class="muted live-detail">' + esc(detail) + '</p>' : '') +
      '<button class="btn primary" data-live-retry>' + esc(t(lang, "retry")) + '</button>' +
      '</div></div>';
  }

  function renderEmpty(lang, text) {
    return '<div class="live-state" data-live="empty"><div class="card live-empty">' +
      '<p class="muted">' + esc(text || t(lang, "empty")) + '</p></div></div>';
  }

  // --- sections (pure: data + lang -> HTML) ------------------------------------
  function renderHome(member, lang) {
    var m = member || {};
    var name = m.display_name ? ", " + m.display_name : "";
    return '<div class="pagehead"><div><div class="eyebrow">Embodier</div>' +
      '<h1>' + esc(m.greeting || ("Welcome" + name)) + '</h1>' +
      '<p class="muted">' + esc(m.phone || "") +
      (m.tier ? ' · <span class="chip gold">' + esc(m.tier) + '</span>' : '') + '</p>' +
      '</div></div>';
  }

  function renderPortfolio(data, lang) {
    var out = '<div class="pagehead"><div><div class="eyebrow">Portfolio</div>' +
      '<h1>' + esc(data.title || "Portfolio") + '</h1></div></div>';
    var holdings = data.holdings || [];
    if (!holdings.length) {
      out += renderEmpty(lang, data.empty_note);
    } else {
      out += '<div class="card list">' + holdings.map(function (h) {
        return '<div class="listrow"><div><b>' + esc(h.asset_name) + '</b><br>' +
          '<small class="muted">' + esc(h.asset_kind || "") + ' · ' + esc(h.status || "") + '</small></div>' +
          '<span class="chip">' + esc(h.amount) + ' ' + esc(h.currency || "") + '</span></div>';
      }).join("") + '</div>';
    }
    if (data.exchange) {
      out += '<div class="banner"><i data-lucide="info"></i><div><small>' +
        esc(data.exchange.message || "") + '</small></div></div>';
    }
    return out;
  }

  function renderInterests(data, lang) {
    var out = '<div class="pagehead"><div><div class="eyebrow">Interests</div>' +
      '<h1>' + esc(data.title || "Interests") + '</h1>' +
      '<p class="muted">' + esc(data.cta || "") + '</p></div></div>';
    out += '<div class="card live-form"><div class="row">' +
      '<input id="live-offering" placeholder="' + esc(t(lang, "offeringPlaceholder")) + '">' +
      '<input id="live-note" placeholder="' + esc(t(lang, "notePlaceholder")) + '">' +
      '<button class="btn primary" data-live-express>' + esc(t(lang, "expressInterest")) + '</button>' +
      '</div><p class="muted live-detail" data-live-interest-msg></p></div>';
    var items = data.interests || [];
    if (!items.length) {
      out += renderEmpty(lang);
    } else {
      out += '<div class="card list">' + items.map(function (r) {
        return '<div class="listrow"><div><b>' + esc(r.offering_id) + '</b><br>' +
          (r.note ? '<small class="muted">' + esc(r.note) + '</small>' : '') + '</div>' +
          '<span class="chip">' + esc(r.status || "") + '</span></div>';
      }).join("") + '</div>';
    }
    return out;
  }

  function renderDocuments(data, lang) {
    var out = '<div class="pagehead"><div><div class="eyebrow">Documents</div>' +
      '<h1>' + esc(data.title || "Documents") + '</h1></div></div>';
    var docs = data.documents || [];
    if (!docs.length) { return out + renderEmpty(lang); }
    out += '<div class="card list">' + docs.map(function (d) {
      return '<div class="listrow"><div><i data-lucide="file-text"></i> <b>' +
        esc(d.title) + '</b><br><small class="muted">' + esc(d.doc_type || "") +
        '</small></div>' +
        (d.url ? '<a class="btn" href="' + esc(d.url) + '" target="_blank" rel="noopener">Open</a>' : '') +
        '</div>';
    }).join("") + '</div>';
    return out;
  }

  function renderExchange(portfolioData, voice, lang) {
    // Pre-DASP: exchange is ALWAYS waitlist-only. Render the backend's block
    // verbatim; never imply live trading.
    var ex = (portfolioData && portfolioData.exchange) || {};
    var out = '<div class="pagehead"><div><div class="eyebrow">Exchange</div>' +
      '<h1>Exchange</h1></div><span class="chip">' +
      esc(ex.status || "waitlist_only") + '</span></div>';
    out += '<div class="card live-exchange"><p>' + esc(ex.message || "") + '</p>';
    if (voice && voice.exchange_note) {
      out += '<p class="muted">' + esc(voice.exchange_note) + '</p>';
    }
    out += '</div>';
    return out;
  }

  function renderAccount(member, lang) {
    var m = member || {};
    return '<div class="pagehead"><div><div class="eyebrow">Account</div>' +
      '<h1>' + esc(m.display_name || m.phone || "Account") + '</h1></div></div>' +
      '<div class="card list">' +
      '<div class="listrow"><div><small class="muted">Phone</small><br><b>' + esc(m.phone || "—") + '</b></div></div>' +
      '<div class="listrow"><div><small class="muted">Tier</small><br><b>' + esc(m.tier || "—") + '</b></div></div>' +
      '<div class="listrow"><div><small class="muted">Status</small><br><b>' + esc(m.status || "—") + '</b></div></div>' +
      '</div>' +
      '<div class="btnrow"><button class="btn" data-live-signout>' + esc(t(lang, "backToLogin")) + '</button></div>';
  }

  function renderBroker(bundle, lang) {
    var out = '<div class="pagehead"><div><div class="eyebrow">' + esc(t(lang, "brokerTab")) + '</div>' +
      '<h1>' + esc(t(lang, "brokerTitle")) + '</h1></div></div>';

    // deals
    out += '<h2>' + esc(t(lang, "deals")) + '</h2>';
    var deals = (bundle.deals && bundle.deals.deals) || [];
    if (!deals.length) { out += renderEmpty(lang, t(lang, "noDeals")); }
    else {
      out += '<div class="card list">' + deals.map(function (d) {
        return '<div class="listrow"><div><b>' + esc(d.property_name) + '</b><br>' +
          '<small class="muted">' + esc(t(lang, "stage")) + ': ' + esc(d.stage || "") + '</small></div>' +
          '<span class="chip">' + esc(d.commission_status || "") + '</span></div>';
      }).join("") + '</div>';
    }

    // pipeline
    out += '<h2>' + esc(t(lang, "pipeline")) + '</h2>';
    var pipe = bundle.pipeline || {};
    var byStage = pipe.by_stage || [];
    if (!byStage.length) { out += renderEmpty(lang); }
    else {
      out += '<div class="card list">' + byStage.map(function (s) {
        return '<div class="listrow"><div><b>' + esc(s.stage) + '</b></div>' +
          '<span class="chip gold">' + esc(String(s.count)) + '</span></div>';
      }).join("") + '</div>';
    }

    // commissions
    out += '<h2>' + esc(t(lang, "commissions")) + '</h2>';
    var comms = (bundle.commissions && bundle.commissions.commissions) || [];
    if (!comms.length) { out += renderEmpty(lang, t(lang, "noCommissions")); }
    else {
      out += '<div class="card list">' + comms.map(function (c) {
        return '<div class="listrow"><div><b>' + esc(c.property_name) + '</b><br>' +
          '<small class="muted">' + esc(t(lang, "status")) + ': ' + esc(c.commission_status || "") + '</small></div>' +
          '<span class="chip">' + esc(t(lang, "expected")) + ': ' +
          esc(c.expected_amount === null || c.expected_amount === undefined ? "—" : c.expected_amount) +
          '</span></div>';
      }).join("") + '</div>';
    }

    // buybox
    out += '<h2>' + esc(t(lang, "buybox")) + '</h2>';
    var box = (bundle.buybox && bundle.buybox.buybox) || [];
    if (!box.length) { out += renderEmpty(lang, t(lang, "noBuybox")); }
    else {
      out += '<div class="card list">' + box.map(function (b) {
        return '<div class="listrow"><div><b>' + esc(b.region || "") + '</b><br>' +
          '<small class="muted">' + esc(b.min_keys || "") + '–' + esc(b.max_keys || "") + ' keys' +
          (b.notes ? ' · ' + esc(b.notes) : '') + '</small></div></div>';
      }).join("") + '</div>';
    }
    return out;
  }

  function renderLoginGate(lang, loginUrl) {
    return '<div class="pagehead"><div><div class="eyebrow">Embodier</div>' +
      '<h1>' + esc(t(lang, "loginTitle")) + '</h1>' +
      '<p class="muted">' + esc(t(lang, "loginBody")) + '</p>' +
      '<div class="btnrow"><a class="btn primary" href="' + esc(loginUrl) + '">' +
      esc(t(lang, "loginCta")) + '</a></div></div></div>';
  }

  // --- boot / DOM binding ------------------------------------------------------
  function boot(opts) {
    // opts: { api, session, config: {loginUrl}, document, onReady }
    var doc = opts.document || (typeof document !== "undefined" ? document : null);
    if (!doc) return null;
    var lang = langOf(doc);
    var state = {
      api: opts.api, session: opts.session, config: opts.config || {},
      member: null, voice: null, cache: {},
    };
    var loginUrl = state.config.loginUrl || "/login";

    function section(id) { return doc.getElementById(id); }

    function showLoginGate() {
      var content = doc.getElementById("content");
      if (content) content.innerHTML = renderLoginGate(lang, loginUrl);
    }

    // Any 401 (stale/expired token) anywhere -> clear + gate, no matter which
    // section triggered it.
    (function () {
      var prev = state.api.onUnauthorized;
      state.api.onUnauthorized = function () {
        try { if (prev) prev(); } catch (e) {}
        showLoginGate();
      };
    })();

    function loadSection(id) {
      var el = section(id);
      if (!el) return;
      el.innerHTML = renderLoading(lang);
      var p;
      if (id === "home") {
        p = Promise.resolve({ member: state.member });
      } else if (id === "wallet") {
        p = state.api.portfolio();
      } else if (id === "offerings") {
        p = state.api.interests();
      } else if (id === "assets") {
        p = state.api.documents();
      } else if (id === "exchange") {
        p = state.api.portfolio().then(function (pf) {
          return state.api.me().then(function (me) { return { pf: pf, me: me }; });
        });
      } else if (id === "account") {
        p = Promise.resolve({ member: state.member });
      } else if (id === "broker") {
        p = Promise.all([
          state.api.brokerDeals(), state.api.brokerPipeline(),
          state.api.brokerCommissions(), state.api.brokerBuybox(),
        ]).then(function (r) {
          return { deals: r[0], pipeline: r[1], commissions: r[2], buybox: r[3] };
        });
      } else {
        return; // unknown tab (e.g. prototype-only 'learn') — leave prototype content
      }
      p.then(function (data) {
        state.cache[id] = data;
        paintSection(id, data);
      }).catch(function (err) {
        if (err && err.kind === "auth") return; // onUnauthorized already redirected
        el.innerHTML = renderError(lang,
          err && err.message ? String(err.message) : "");
        bindRetry(el, id);
      });
    }

    function paintSection(id, data) {
      var el = section(id);
      if (!el) return;
      var html = "";
      if (id === "home") html = renderHome(state.member, lang);
      else if (id === "wallet") html = renderPortfolio(data, lang);
      else if (id === "offerings") html = renderInterests(data, lang);
      else if (id === "assets") html = renderDocuments(data, lang);
      else if (id === "exchange") html = renderExchange(data.pf, (data.me && data.me.voice) || null, lang);
      else if (id === "account") html = renderAccount(state.member, lang);
      else if (id === "broker") html = renderBroker(data, lang);
      el.innerHTML = html;
      bindSectionActions(el, id);
      if (root.lucide && root.lucide.createIcons) { try { root.lucide.createIcons(); } catch (e) {} }
    }

    function bindRetry(el, id) {
      var btn = el.querySelector("[data-live-retry]");
      if (btn) btn.addEventListener("click", function () { loadSection(id); });
    }

    function bindSectionActions(el, id) {
      bindRetry(el, id);
      if (id === "offerings") {
        var btn = el.querySelector("[data-live-express]");
        if (btn) btn.addEventListener("click", function () {
          var off = el.querySelector("#live-offering");
          var note = el.querySelector("#live-note");
          var msg = el.querySelector("[data-live-interest-msg]");
          var offeringId = off ? off.value.trim() : "";
          if (!offeringId) { if (msg) msg.textContent = t(lang, "offeringPlaceholder"); return; }
          btn.disabled = true;
          state.api.expressInterest(offeringId, note ? note.value : "").then(function () {
            if (msg) msg.textContent = t(lang, "interestHeld");
            loadSection("offerings");
          }).catch(function (err) {
            if (msg) msg.textContent = err && err.message ? String(err.message) : t(lang, "loadError");
            btn.disabled = false;
          });
        });
      }
      if (id === "account") {
        var out = el.querySelector("[data-live-signout]");
        if (out) out.addEventListener("click", function () {
          state.session.clearToken();
          state.api.clearSession();
          showLoginGate();
        });
      }
    }

    function ensureBrokerNav() {
      if (!state.member || !state.member.is_broker) return;
      var side = doc.getElementById("sideNav");
      if (!side || side.querySelector('[data-tab="broker"]')) return;
      var btn = doc.createElement("button");
      btn.setAttribute("data-tab", "broker");
      btn.innerHTML = '<i data-lucide="briefcase"></i>' + esc(t(lang, "brokerTab"));
      side.appendChild(btn);
      var bottom = doc.getElementById("bottomNav");
      if (bottom && !bottom.querySelector('[data-tab="broker"]')) {
        var b2 = btn.cloneNode(true);
        bottom.appendChild(b2);
      }
      var sec = section("broker");
      if (!sec) {
        var main = doc.getElementById("content");
        if (main) {
          sec = doc.createElement("section");
          sec.className = "view";
          sec.id = "broker";
          main.appendChild(sec);
        }
      }
      if (root.lucide && root.lucide.createIcons) { try { root.lucide.createIcons(); } catch (e) {} }
    }

    // Intercept tab clicks: let the prototype switch, then paint live content.
    doc.addEventListener("click", function (ev) {
      var btn = ev.target && ev.target.closest ? ev.target.closest("[data-tab]") : null;
      if (!btn) return;
      var id = btn.getAttribute("data-tab");
      setTimeout(function () {
        ensureBrokerNav();
        if (id === "learn") return; // prototype-only content
        loadSection(id);
      }, 0);
    }, true);

    // --- auth gate + initial paint -------------------------------------------
    var token = "";
    try { token = state.session.resolveToken() || ""; } catch (e) {}
    if (!token) { showLoginGate(); return state; }

    state.api.verifySession(token).then(function (res) {
      state.member = (res && res.member) || null;
      if (!state.member) { showLoginGate(); return; }
      ensureBrokerNav();
      var active = doc.querySelector(".view.active");
      loadSection(active && active.id ? active.id : "home");
      if (opts.onReady) opts.onReady(state);
    }).catch(function () {
      // verifySession rejects on 401 (handled) or network error -> gate with retry
      var content = doc.getElementById("content");
      if (content && !doc.querySelector(".view.active")) showLoginGate();
    });
    return state;
  }

  return {
    t: t,
    esc: esc,
    renderLoading: renderLoading,
    renderError: renderError,
    renderEmpty: renderEmpty,
    renderHome: renderHome,
    renderPortfolio: renderPortfolio,
    renderInterests: renderInterests,
    renderDocuments: renderDocuments,
    renderExchange: renderExchange,
    renderAccount: renderAccount,
    renderBroker: renderBroker,
    renderLoginGate: renderLoginGate,
    boot: boot,
  };
});
