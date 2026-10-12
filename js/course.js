/* Embodier $100 Investment Real Estate Course — panel UI.
 *
 * Vanilla JS, no dependencies. UMD like js/api.js: works in the browser and
 * in Node (tests inject nothing — all helpers are pure).
 *
 * Live mode: portal-live.js mounts the learn tab through mountLearnTab() and
 * injects the offer card on home through renderCourseOffer(). All copy is
 * education-framed: no yield/return promises, no live token-sale claims
 * (pre-DASP). scanCompliance() enforces this and is unit-tested.
 *
 * Demo mode (no apiBase): the prototype's own learn tab stays untouched.
 */
(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.EmbodierCourse = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // --- pure helpers ----------------------------------------------------------

  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // Non-negotiable compliance scanner. Returns violation phrases found.
  // Negated mentions ("no token sale is live") are allowed.
  var BANNED_YIELD = [
    "guaranteed return", "guaranteed profit", "guaranteed income",
    "get rich", "risk-free", "can't lose", "double your money",
  ];
  var BANNED_LIVE_SALE = [
    /(?<!no )(?<!not )token sale is live/i,
    /(?<!no )(?<!not )buy tokens now/i,
    /(?<!no )(?<!not )offering is open/i,
    /(?<!no )(?<!not )tokens are on sale/i,
    /(?<!no )(?<!not )venta de tokens est\u00e1 abierta/i,
    /(?<!no )(?<!not )compra tokens ahora/i,
  ];

  function scanCompliance(text) {
    var lower = String(text || "").toLowerCase();
    var hits = [];
    BANNED_YIELD.forEach(function (p) {
      if (lower.indexOf(p) !== -1) hits.push(p);
    });
    BANNED_LIVE_SALE.forEach(function (re) {
      var m = String(text || "").match(re);
      if (m) hits.push(m[0]);
    });
    return hits;
  }

  // Pre-filled share text — education framing only, never a yield promise.
  function buildShareText(lang, code, portalUrl) {
    var url = (portalUrl || "") + "?ref=" + code;
    if (lang === "es") {
      return "Estoy tomando el Curso de Inversi\u00f3n en Bienes Ra\u00edces de " +
        "Embodier ($100): educaci\u00f3n real sobre c\u00f3mo funcionan los " +
        "negocios comerciales y hoteleros. Aprende c\u00f3mo invierten los " +
        "profesionales: " + url;
    }
    return "I\u2019m taking Embodier\u2019s $100 Investment Real Estate " +
      "Course \u2014 real education on how commercial and hospitality deals " +
      "actually work. Learn how the pros invest: " + url;
  }

  function whatsappShareUrl(text) {
    return "https://wa.me/?text=" + encodeURIComponent(text);
  }

  function smsShareUrl(text) {
    return "sms:?&body=" + encodeURIComponent(text);
  }

  function computeProgress(modules) {
    var mods = modules || [];
    var complete = mods.filter(function (m) { return m.state === "complete"; }).length;
    var total = mods.length;
    return {
      complete: complete,
      total: total,
      pct: total ? Math.round((100 * complete) / total) : 0,
    };
  }

  function validateQuizAnswers(answers, count) {
    if (!Array.isArray(answers)) return { ok: false, error: "answers must be an array" };
    if (answers.length !== count) {
      return { ok: false, error: "expected " + count + " answers" };
    }
    for (var i = 0; i < answers.length; i++) {
      if (typeof answers[i] !== "number" || answers[i] < 0 || answers[i] > 3) {
        return { ok: false, error: "answer " + (i + 1) + " must be 0-3" };
      }
    }
    return { ok: true };
  }

  // Strip answer keys from a module payload (demo-mode sanitizer).
  function stripAnswers(mod) {
    var copy = JSON.parse(JSON.stringify(mod || {}));
    (copy.quiz || []).forEach(function (q) { delete q.answer; });
    return copy;
  }

  // --- copy ------------------------------------------------------------------

  var STR = {
    en: {
      courseEyebrow: "Education",
      offerTitle: "Investment Real Estate Course",
      offerPrice: "$100",
      offerTag: "Learn how the pros invest \u2014 commercial, hospitality & tokenized real estate, taught straight.",
      offerBullets: ["6 modules \u00b7 24 lessons \u00b7 EN + ES", "Quizzes with instant grading", "Certificate when you complete"],
      getCourse: "Get the course \u2014 $100",
      continueLearning: "Continue learning",
      certifiedBadge: "Certified \uD83C\uDF93",
      notEnrolledTitle: "Learn how the pros invest",
      notEnrolledBody: "A real $100 course on commercial and hospitality real estate \u2014 how deals are found, underwritten, structured and closed, plus how tokenization works. No hype, no guaranteed outcomes. Education from people who do deals.",
      whatYouLearn: "What you\u2019ll learn",
      startLearning: "Start learning",
      yourProgress: "Your progress",
      modulesComplete: "modules complete",
      takeQuiz: "Take the quiz",
      retakeQuiz: "Retake quiz",
      submitQuiz: "Submit answers",
      answerAll: "Please answer every question before submitting.",
      quizPassed: "Passed \u2014 nice work.",
      quizFailed: "Not quite \u2014 review the lessons and try again.",
      yourScore: "Your score",
      toPass: "to pass",
      markRead: "Mark as read",
      markedRead: "\u2713 Read",
      lessons: "Lessons",
      quiz: "Quiz",
      questions: "questions",
      viewCertificate: "View certificate",
      certificateTitle: "Certificate of Completion",
      certifiedOn: "Certified on",
      referralTitle: "Refer & earn",
      referralBody: "Share your personal code. When someone you refer buys tokens in a future offering, you earn 5% of their token purchases \u2014 forever.",
      referralNote: "No token sale is live right now, so rewards accrue against future offerings.",
      shareWhatsApp: "Share on WhatsApp",
      shareSMS: "Share by text",
      copyCode: "Copy code",
      codeCopied: "Code copied",
      friendsJoined: "friends joined with your code",
      noReferrals: "No referrals yet \u2014 be the first to share.",
      backToModules: "\u2190 All modules",
      complete: "Complete",
      inProgress: "In progress",
      notStarted: "Not started",
      questionsCount: "5 questions",
      loading: "Loading\u2026",
    },
    es: {
      courseEyebrow: "Educaci\u00f3n",
      offerTitle: "Curso de Inversi\u00f3n en Bienes Ra\u00edces",
      offerPrice: "$100",
      offerTag: "Aprende c\u00f3mo invierten los profesionales \u2014 bienes ra\u00edces comerciales, hoteler\u00eda y tokenizaci\u00f3n, sin rodeos.",
      offerBullets: ["6 m\u00f3dulos \u00b7 24 lecciones \u00b7 EN + ES", "Cuestionarios con calificaci\u00f3n inmediata", "Certificado al completar"],
      getCourse: "Obtener el curso \u2014 $100",
      continueLearning: "Continuar aprendiendo",
      certifiedBadge: "Certificado \uD83C\uDF93",
      notEnrolledTitle: "Aprende c\u00f3mo invierten los profesionales",
      notEnrolledBody: "Un curso real de $100 sobre bienes ra\u00edces comerciales y hoteleros \u2014 c\u00f3mo se encuentran, analizan, estructuran y cierran los negocios, y c\u00f3mo funciona la tokenizaci\u00f3n. Sin exageraciones ni resultados garantizados. Educaci\u00f3n de personas que hacen negocios.",
      whatYouLearn: "Lo que aprender\u00e1s",
      startLearning: "Empezar a aprender",
      yourProgress: "Tu progreso",
      modulesComplete: "m\u00f3dulos completados",
      takeQuiz: "Hacer el cuestionario",
      retakeQuiz: "Reintentarlo",
      submitQuiz: "Enviar respuestas",
      answerAll: "Responde todas las preguntas antes de enviar.",
      quizPassed: "Aprobado \u2014 buen trabajo.",
      quizFailed: "Casi \u2014 repasa las lecciones e int\u00e9ntalo de nuevo.",
      yourScore: "Tu puntaje",
      toPass: "para aprobar",
      markRead: "Marcar como le\u00edda",
      markedRead: "\u2713 Le\u00edda",
      lessons: "Lecciones",
      quiz: "Cuestionario",
      questions: "preguntas",
      viewCertificate: "Ver certificado",
      certificateTitle: "Certificado de Finalizaci\u00f3n",
      certifiedOn: "Certificado el",
      referralTitle: "Refiere y gana",
      referralBody: "Comparte tu c\u00f3digo personal. Cuando alguien que refieras compre tokens en una oferta futura, ganas el 5% de sus compras \u2014 para siempre.",
      referralNote: "Ninguna venta de tokens est\u00e1 activa ahora, as\u00ed que las recompensas aplican a ofertas futuras.",
      shareWhatsApp: "Compartir por WhatsApp",
      shareSMS: "Compartir por SMS",
      copyCode: "Copiar c\u00f3digo",
      codeCopied: "C\u00f3digo copiado",
      friendsJoined: "amigos se unieron con tu c\u00f3digo",
      noReferrals: "Sin referidos todav\u00eda \u2014 s\u00e9 el primero en compartir.",
      backToModules: "\u2190 Todos los m\u00f3dulos",
      complete: "Completado",
      inProgress: "En curso",
      notStarted: "Sin empezar",
      questionsCount: "5 preguntas",
      loading: "Cargando\u2026",
    },
  };

  function t(lang, key) {
    var pack = STR[lang] === undefined ? STR.en : STR[lang];
    return pack[key] !== undefined ? pack[key] : (STR.en[key] || key);
  }

  function langOf(doc) {
    try {
      var l = (doc.documentElement.getAttribute("lang") || "en").slice(0, 2).toLowerCase();
      return l === "es" ? "es" : "en";
    } catch (e) { return "en"; }
  }

  // --- renderers (pure: data -> HTML) ----------------------------------------

  function stateChip(state, lang) {
    if (state === "complete") {
      return '<span class="chip verified">\u2713 ' + esc(t(lang, "complete")) + "</span>";
    }
    if (state === "in-progress") {
      return '<span class="chip gold">' + esc(t(lang, "inProgress")) + "</span>";
    }
    return '<span class="chip">' + esc(t(lang, "notStarted")) + "</span>";
  }

  // Offer card for the panel home (Inner Circle+). Not enrolled -> Stripe CTA;
  // enrolled -> continue; certified -> badge.
  function renderCourseOffer(cfg, status, lang) {
    cfg = cfg || {};
    var payUrl = cfg.coursePaymentUrl || "";
    var enrolled = !!(status && status.enrolled);
    var certified = !!(status && status.certified);
    var cta;
    if (certified) {
      cta = '<span class="chip verified" style="font-size:14px;padding:10px 14px">' +
        esc(t(lang, "certifiedBadge")) + "</span>";
    } else if (enrolled) {
      cta = '<button class="btn primary" data-course-goto>' +
        esc(t(lang, "continueLearning")) + "</button>";
    } else if (payUrl) {
      cta = '<a class="btn primary" href="' + esc(payUrl) +
        '" target="_blank" rel="noopener">' + esc(t(lang, "getCourse")) + "</a>";
    } else {
      cta = '<button class="btn primary" data-course-soon>' +
        esc(t(lang, "getCourse")) + "</button>";
    }
    return '<div class="card course-offer"><div class="eyebrow">' +
      esc(t(lang, "courseEyebrow")) + "</div>" +
      '<h2>' + esc(t(lang, "offerTitle")) + ' \u2014 ' + esc(t(lang, "offerPrice")) + "</h2>" +
      '<p class="muted">' + esc(t(lang, "offerTag")) + "</p>" +
      '<ul class="course-bullets">' +
      t(lang, "offerBullets").map(function (b) {
        return "<li>\u2713 " + esc(b) + "</li>";
      }).join("") + "</ul>" +
      '<div class="btnrow">' + cta + "</div></div>";
  }

  function renderProgressBar(status, lang) {
    var p = computeProgress(status.modules);
    return '<div class="card course-progress"><div class="row"><div><b>' +
      esc(t(lang, "yourProgress")) + "</b><br><small class=\"muted\">" +
      p.complete + " / " + p.total + " " + esc(t(lang, "modulesComplete")) +
      "</small></div>" +
      (status.certified
        ? '<span class="chip verified">' + esc(t(lang, "certifiedBadge")) + "</span>"
        : "") +
      '</div><div class="progress"><span style="width:' + p.pct + '%"></span></div></div>';
  }

  function renderModuleList(status, lang) {
    return '<div class="card list">' + (status.modules || []).map(function (m) {
      return '<div class="listrow" data-course-module="' + esc(m.id) + '">' +
        '<div class="roundicon">' + esc(String(m.order)) + "</div>" +
        '<div class="grow"><b>' + esc(m.title[lang] || m.title.en) + "</b>" +
        "<p>" + esc(m.summary[lang] || m.summary.en) + "</p></div>" +
        stateChip(m.state, lang) + "</div>";
    }).join("") + "</div>";
  }

  // Learn-tab root.
  function renderCourseHome(status, catalog, lang) {
    var out = '<div class="pagehead"><div><div class="eyebrow">' +
      esc(t(lang, "courseEyebrow")) + "</div><h1>" +
      esc((catalog && catalog.course && (catalog.course.title[lang] || catalog.course.title.en)) ||
        t(lang, "offerTitle")) + "</h1>";
    if (catalog && catalog.course && catalog.course.tagline) {
      out += '<p class="muted">' + esc(catalog.course.tagline[lang] || catalog.course.tagline.en) + "</p>";
    }
    out += "</div></div>";
    if (!status || !status.enrolled) {
      var cfg = (typeof window !== "undefined" && window.__courseCfg) || {};
      out += renderCourseOffer(cfg, status, lang);
      out += '<h2 class="feature-head">' + esc(t(lang, "whatYouLearn")) + "</h2>";
    } else {
      out += renderProgressBar(status, lang);
      if (status.certified) {
        out += '<div class="btnrow"><button class="btn primary" data-course-cert>' +
          esc(t(lang, "viewCertificate")) + "</button></div>";
      }
    }
    out += renderModuleList(status, lang);
    return out;
  }

  function renderModuleDetail(mod, state, readSet, lang) {
    var lessons = mod.lessons || [];
    var out = '<div class="btnrow"><button class="btn" data-course-back>' +
      esc(t(lang, "backToModules")) + "</button></div>";
    out += '<div class="pagehead" style="margin-top:16px"><div><div class="eyebrow">' +
      esc(t(lang, "lessons")) + "</div><h1>" + esc(mod.title[lang] || mod.title.en) +
      "</h1><p class=\"muted\">" + esc(mod.summary[lang] || mod.summary.en) + "</p></div>" +
      stateChip(state && state.state, lang) + "</div>";
    out += lessons.map(function (l, i) {
      var read = readSet && readSet.has(l.id);
      var paras = (l.body[lang] || l.body.en).map(function (p) {
        return "<p>" + esc(p) + "</p>";
      }).join("");
      return '<article class="card course-lesson' + (read ? " read" : "") + '">' +
        "<h3>" + esc(l.title[lang] || l.title.en) + "</h3>" + paras +
        '<div class="btnrow"><button class="btn' + (read ? "" : " primary") +
        '" data-course-read="' + esc(l.id) + '">' +
        esc(read ? t(lang, "markedRead") : t(lang, "markRead")) + "</button></div></article>";
    }).join("");
    var allRead = lessons.length && lessons.every(function (l) {
      return readSet && readSet.has(l.id);
    });
    var passed = !!(state && state.quiz_passed);
    out += '<div class="btnrow" style="margin:22px 0"><button class="btn primary full" data-course-quiz="' +
      esc(mod.id) + '"' + (allRead || passed ? "" : " disabled") + ">" +
      esc(passed ? t(lang, "retakeQuiz") : t(lang, "takeQuiz")) + " \u00b7 " +
      esc(t(lang, "questionsCount")) + "</button></div>";
    return out;
  }

  function renderQuiz(mod, lang) {
    var out = '<div class="btnrow"><button class="btn" data-course-back-module="' +
      esc(mod.id) + '">' + esc(t(lang, "backToModules")) + "</button></div>";
    out += '<div class="pagehead" style="margin-top:16px"><div><div class="eyebrow">' +
      esc(t(lang, "quiz")) + "</div><h1>" + esc(mod.title[lang] || mod.title.en) +
      "</h1></div></div>";
    out += '<div data-course-quizform="' + esc(mod.id) + '">';
    out += (mod.quiz || []).map(function (q, qi) {
      var opts = (q.options[lang] || q.options.en).map(function (o, oi) {
        var name = "cq-" + mod.id + "-" + qi;
        return '<label class="quiz-option"><input type="radio" name="' + esc(name) +
          '" value="' + oi + '"><span>' + esc(o) + "</span></label>";
      }).join("");
      return '<div class="card course-quizq"><b>' + (qi + 1) + ". " +
        esc(q.question[lang] || q.question.en) + "</b>" + opts + "</div>";
    }).join("");
    out += '<p class="muted" data-course-quizmsg style="min-height:20px"></p>';
    out += '<div class="btnrow" style="margin-bottom:22px"><button class="btn primary full" data-course-submit="' +
      esc(mod.id) + '">' + esc(t(lang, "submitQuiz")) + "</button></div></div>";
    return out;
  }

  function renderQuizResult(mod, result, lang) {
    var out = '<div class="success' + (result.passed ? "" : "") + '" style="text-align:center;padding:8px 0 18px">';
    out += '<div class="successmark"><i data-lucide="' +
      (result.passed ? "graduation-cap" : "book-open") + '"></i></div>';
    out += "<h2>" + esc(result.passed ? t(lang, "quizPassed") : t(lang, "quizFailed")) + "</h2>";
    out += '<p class="muted">' + esc(t(lang, "yourScore")) + ": <b>" + result.score +
      " / " + result.total + "</b> \u00b7 " + result.pass_score + " " + esc(t(lang, "toPass")) + "</p></div>";
    out += '<div class="card list">' + (mod.quiz || []).map(function (q, qi) {
      var ok = result.correct && result.correct[qi];
      return '<div class="listrow"><div class="grow"><b>' + (qi + 1) + ". " +
        esc(q.question[lang] || q.question.en) + "</b></div>" +
        '<span class="chip ' + (ok ? "verified" : "disabled") + '">' +
        (ok ? "\u2713" : "\u2717") + "</span></div>";
    }).join("") + "</div>";
    out += '<div class="btnrow" style="margin:18px 0"><button class="btn primary full" data-course-back-module="' +
      esc(mod.id) + '">' + esc(t(lang, "backToModules")) + "</button>";
    if (result.certified) {
      out += '<button class="btn full" data-course-cert>' + esc(t(lang, "viewCertificate")) + "</button>";
    }
    out += "</div>";
    return out;
  }

  function renderCertificate(cert, lang) {
    var date = "";
    try { date = new Date(cert.certified_at).toLocaleDateString(lang === "es" ? "es-ES" : "en-US", { year: "numeric", month: "long", day: "numeric" }); }
    catch (e) { date = String(cert.certified_at || ""); }
    return '<div class="btnrow"><button class="btn" data-course-back>' +
      esc(t(lang, "backToModules")) + "</button></div>" +
      '<div class="card cert-card"><div class="eyebrow">' +
      esc(t(lang, "certificateTitle")) + '</div><div class="cert-seal">\uD83C\uDF93</div>' +
      "<h2>" + esc(cert.name || "") + "</h2>" +
      '<p class="muted">' + esc(cert.course_title && (cert.course_title[lang] || cert.course_title.en) || "") + "</p>" +
      '<div class="cert-id"><small class="muted">ID</small><br><b class="code">' +
      esc(cert.certificate_id) + "</b></div>" +
      '<p class="muted"><small>' + esc(t(lang, "certifiedOn")) + ": " + esc(date) + "</small></p></div>";
  }

  function renderReferrals(ref, lang, portalUrl) {
    var text = buildShareText(lang, ref.referral_code, portalUrl);
    var out = '<div class="card referral"><div class="eyebrow">' +
      esc(t(lang, "referralTitle")) + "</div><h2>" + esc(t(lang, "referralTitle")) + "</h2>" +
      '<p class="muted">' + esc(t(lang, "referralBody")) + "</p>" +
      '<div class="ref-link"><code>' + esc(ref.referral_code) + '</code>' +
      '<button class="btn" data-course-copy="' + esc(ref.referral_code) + '">' +
      esc(t(lang, "copyCode")) + "</button></div>" +
      '<div class="btnrow">' +
      '<a class="btn primary" href="' + esc(whatsappShareUrl(text)) +
      '" target="_blank" rel="noopener"><i data-lucide="message-circle"></i>' +
      esc(t(lang, "shareWhatsApp")) + "</a>" +
      '<a class="btn" href="' + esc(smsShareUrl(text)) + '"><i data-lucide="message-square"></i>' +
      esc(t(lang, "shareSMS")) + "</a></div>" +
      '<p class="muted" style="font-size:11px;margin-top:12px">' +
      esc(t(lang, "referralNote")) + "</p></div>";
    var rows = ref.referred || [];
    out += '<div class="card list" style="margin-top:14px"><div class="listrow"><div class="grow"><b>' +
      esc(String(ref.signups || 0)) + "</b><p>" + esc(t(lang, "friendsJoined")) + "</p></div></div>";
    if (!rows.length) {
      out += '<div class="listrow"><div class="grow"><p>' + esc(t(lang, "noReferrals")) + "</p></div></div>";
    } else {
      out += rows.map(function (r) {
        var when = "";
        try { when = new Date(r.at).toLocaleDateString(lang === "es" ? "es-ES" : "en-US"); } catch (e) {}
        return '<div class="listrow"><div class="grow"><b>' + esc(r.phone_masked || "") +
          "</b><p>" + esc(when) + "</p></div>" +
          '<span class="chip verified">\u2713</span></div>';
      }).join("");
    }
    out += "</div>";
    return out;
  }

  function certifiedBadge(lang) {
    return '<span class="chip verified">' + esc(t(lang, "certifiedBadge")) + "</span>";
  }

  // --- live mount --------------------------------------------------------------

  function mountLearnTab(opts) {
    // opts: {api, config, document}
    var doc = opts.document;
    var api = opts.api;
    var cfg = opts.config || {};
    var section = doc.getElementById("learn");
    if (!section) return null;
    try { window.__courseCfg = cfg; } catch (e) {}

    var state = {
      status: null, catalog: null, referrals: null,
      view: { name: "home" }, readSets: {}, moduleCache: {},
    };

    function lang() { return langOf(doc); }
    function portalUrl() {
      return cfg.portalUrl || (doc.location && doc.location.origin) || "";
    }
    function icons() {
      try {
        var lz = (typeof window !== "undefined" && window.lucide) ||
          (typeof self !== "undefined" && self.lucide);
        if (lz && lz.createIcons) lz.createIcons();
      } catch (e) {}
    }
    function toast(msg) {
      var el = doc.getElementById("toast");
      if (!el) return;
      el.textContent = msg;
      el.classList.add("show");
      setTimeout(function () { el.classList.remove("show"); }, 2200);
    }

    function paint() {
      var L = lang();
      var html = "";
      var v = state.view;
      if (v.name === "module" && state.moduleCache[v.id]) {
        var st = (state.status.modules || []).filter(function (m) {
          return m.id === v.id;
        })[0];
        html = renderModuleDetail(state.moduleCache[v.id], st,
          state.readSets[v.id] || new Set(), L);
      } else if (v.name === "quiz" && state.moduleCache[v.id]) {
        html = renderQuiz(state.moduleCache[v.id], L);
      } else if (v.name === "result" && state.moduleCache[v.id]) {
        html = renderQuizResult(state.moduleCache[v.id], v.result, L);
      } else if (v.name === "certificate" && v.cert) {
        html = renderCertificate(v.cert, L);
      } else {
        html = renderCourseHome(state.status, state.catalog, L);
        if (state.status && state.status.enrolled && state.referrals) {
          html += '<h2 class="feature-head">' + esc(t(L, "referralTitle")) + "</h2>" +
            renderReferrals(state.referrals, L, portalUrl());
        }
      }
      section.innerHTML = html;
      bind();
      icons();
    }

    function moduleState(id) {
      return (state.status.modules || []).filter(function (m) {
        return m.id === id;
      })[0];
    }

    function refreshStatus(then) {
      api.courseStatus().then(function (s) {
        state.status = s;
        if (then) then();
        else paint();
      }).catch(function () { /* keep last good paint */ });
    }

    function openModule(id) {
      var done = function () {
        // seed read-set from server progress
        var st = moduleState(id);
        var set = state.readSets[id] || new Set();
        if (st && st.lessons_done > 0) {
          var mod = state.moduleCache[id];
          (mod.lessons || []).slice(0, st.lessons_done).forEach(function (l) {
            set.add(l.id);
          });
          state.readSets[id] = set;
        }
        state.view = { name: "module", id: id };
        paint();
      };
      if (state.moduleCache[id]) { done(); return; }
      api.courseModule(id).then(function (mod) {
        state.moduleCache[id] = mod;
        done();
      });
    }

    function collectAnswers(mod) {
      var answers = [];
      for (var qi = 0; qi < (mod.quiz || []).length; qi++) {
        var sel = section.querySelector(
          'input[name="cq-' + mod.id + "-" + qi + '"]:checked');
        if (!sel) return null;
        answers.push(parseInt(sel.value, 10));
      }
      return answers;
    }

    function bind() {
      var L = lang();
      section.querySelectorAll("[data-course-module]").forEach(function (el) {
        el.addEventListener("click", function () {
          if (!state.status.enrolled) {
            var url = cfg.coursePaymentUrl || "";
            if (url && typeof window !== "undefined") window.open(url, "_blank");
            return;
          }
          openModule(el.getAttribute("data-course-module"));
        });
      });
      section.querySelectorAll("[data-course-goto]").forEach(function (el) {
        el.addEventListener("click", function () {
          state.view = { name: "home" };
          paint();
          section.scrollIntoView();
        });
      });
      section.querySelectorAll("[data-course-back]").forEach(function (el) {
        el.addEventListener("click", function () {
          state.view = { name: "home" };
          refreshStatus();
        });
      });
      section.querySelectorAll("[data-course-back-module]").forEach(function (el) {
        el.addEventListener("click", function () {
          openModule(el.getAttribute("data-course-back-module"));
          refreshStatus(function () {});
        });
      });
      section.querySelectorAll("[data-course-read]").forEach(function (el) {
        el.addEventListener("click", function () {
          var lid = el.getAttribute("data-course-read");
          var mid = state.view.id;
          var set = state.readSets[mid] || new Set();
          if (set.has(lid)) set.delete(lid); else set.add(lid);
          state.readSets[mid] = set;
          var mod = state.moduleCache[mid];
          api.saveLessons(mid, set.size).catch(function () {});
          paint();
        });
      });
      section.querySelectorAll("[data-course-quiz]").forEach(function (el) {
        el.addEventListener("click", function () {
          var mid = el.getAttribute("data-course-quiz");
          state.view = { name: "quiz", id: mid };
          paint();
        });
      });
      section.querySelectorAll("[data-course-submit]").forEach(function (el) {
        el.addEventListener("click", function () {
          var mid = el.getAttribute("data-course-submit");
          var mod = state.moduleCache[mid];
          var answers = collectAnswers(mod);
          var msg = section.querySelector("[data-course-quizmsg]");
          var chk = validateQuizAnswers(answers || [], (mod.quiz || []).length);
          if (!chk.ok || answers === null) {
            if (msg) msg.textContent = t(L, "answerAll");
            return;
          }
          el.disabled = true;
          api.submitQuiz(mid, answers).then(function (res) {
            state.view = { name: "result", id: mid, result: res };
            refreshStatus(function () { paint(); });
          }).catch(function (err) {
            el.disabled = false;
            if (msg) msg.textContent = (err && err.message) || t(L, "answerAll");
          });
        });
      });
      section.querySelectorAll("[data-course-cert]").forEach(function (el) {
        el.addEventListener("click", function () {
          api.courseCertificate().then(function (cert) {
            state.view = { name: "certificate", cert: cert };
            paint();
          });
        });
      });
      section.querySelectorAll("[data-course-copy]").forEach(function (el) {
        el.addEventListener("click", function () {
          var code = el.getAttribute("data-course-copy");
          var done = function () { toast(t(lang(), "codeCopied")); };
          try {
            if (doc.defaultView && doc.defaultView.navigator &&
              doc.defaultView.navigator.clipboard) {
              doc.defaultView.navigator.clipboard.writeText(code).then(done, done);
            } else { done(); }
          } catch (e) { done(); }
        });
      });
      var soon = section.querySelector("[data-course-soon]");
      if (soon) soon.addEventListener("click", function () {
        toast(t(lang(), "getCourse"));
      });
    }

    // initial load
    section.innerHTML = '<div class="pagehead"><div><div class="eyebrow">' +
      esc(t(lang(), "courseEyebrow")) + "</div><h1>" + esc(t(lang(), "offerTitle")) +
      '</h1><p class="muted">' + esc(t(lang(), "loading")) + "</p></div></div>";
    api.courseStatus().then(function (s) {
      state.status = s;
      return api.courseModules().then(function (c) {
        state.catalog = c;
        if (s.enrolled) {
          return api.courseReferrals().then(function (r) {
            state.referrals = r;
          }).catch(function () {});
        }
      });
    }).then(function () { paint(); })
      .catch(function () { paint(); });

    // re-render on EN/ES toggle (prototype sets documentElement.lang)
    doc.addEventListener("click", function (ev) {
      var b = ev.target && ev.target.closest ?
        ev.target.closest("[data-lang]") : null;
      if (b) setTimeout(paint, 30);
    }, true);

    return state;
  }

  // Inject the course offer card at the top of the home tab (live mode).
  function mountHomeOffer(opts) {
    var doc = opts.document;
    var api = opts.api;
    var cfg = opts.config || {};
    var home = doc.getElementById("home");
    if (!home) return;
    if (home.querySelector("[data-course-offer-root]")) return;
    api.courseStatus().then(function (status) {
      var L = langOf(doc);
      var wrap = doc.createElement("div");
      wrap.setAttribute("data-course-offer-root", "1");
      wrap.innerHTML = renderCourseOffer(cfg, status, L);
      home.insertBefore(wrap, home.firstChild);
      var goto = wrap.querySelector("[data-course-goto]");
      if (goto) goto.addEventListener("click", function () {
        var tab = doc.querySelector('[data-tab="learn"]');
        if (tab) tab.click();
      });
      try {
        var lz = (typeof window !== "undefined" && window.lucide);
        if (lz && lz.createIcons) lz.createIcons();
      } catch (e) {}
      // Certified badge next to the tier chip
      if (status && status.certified) {
        var head = home.querySelector(".pagehead p");
        if (head && !head.querySelector('[data-cert-badge]')) {
          var s = doc.createElement("span");
          s.setAttribute("data-cert-badge", "1");
          s.innerHTML = " " + certifiedBadge(L);
          head.appendChild(s);
        }
      }
    }).catch(function () {});
  }

  return {
    esc: esc,
    scanCompliance: scanCompliance,
    buildShareText: buildShareText,
    whatsappShareUrl: whatsappShareUrl,
    smsShareUrl: smsShareUrl,
    computeProgress: computeProgress,
    validateQuizAnswers: validateQuizAnswers,
    stripAnswers: stripAnswers,
    t: t,
    renderCourseOffer: renderCourseOffer,
    renderCourseHome: renderCourseHome,
    renderModuleList: renderModuleList,
    renderModuleDetail: renderModuleDetail,
    renderQuiz: renderQuiz,
    renderQuizResult: renderQuizResult,
    renderCertificate: renderCertificate,
    renderReferrals: renderReferrals,
    certifiedBadge: certifiedBadge,
    mountLearnTab: mountLearnTab,
    mountHomeOffer: mountHomeOffer,
  };
});
