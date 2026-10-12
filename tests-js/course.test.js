/* Course UI unit tests — node:test, no dependencies.
 * Run: node --test tests-js/
 */
"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const Course = require("../js/course.js");

const CONTENT_DIR = path.join(__dirname, "..", "course", "content");
const MODULE_IDS = ["module-01", "module-02", "module-03", "module-04", "module-05", "module-06"];

function loadModule(id) {
  return JSON.parse(fs.readFileSync(path.join(CONTENT_DIR, id + ".json"), "utf8"));
}

// --- pure helpers ------------------------------------------------------------

test("esc escapes HTML", () => {
  assert.equal(Course.esc('<b>"x"&\'y\'</b>'), "&lt;b&gt;&quot;x&quot;&amp;&#39;y&#39;&lt;/b&gt;");
  assert.equal(Course.esc(null), "");
});

test("scanCompliance catches yield promises", () => {
  assert.deepEqual(Course.scanCompliance("Get guaranteed returns now"), ["guaranteed return"]);
  assert.deepEqual(Course.scanCompliance("get rich quick"), ["get rich"]);
  assert.deepEqual(Course.scanCompliance("Nothing here is promised."), []);
});

test("scanCompliance catches live token-sale claims, allows negated mentions", () => {
  assert.ok(Course.scanCompliance("The token sale is live today").length > 0);
  assert.deepEqual(Course.scanCompliance("No token sale is live right now."), []);
  assert.deepEqual(Course.scanCompliance("Ninguna venta de tokens está activa ahora."), []);
});

test("buildShareText is EN/ES, carries the code, and is compliance-clean", () => {
  for (const lang of ["en", "es"]) {
    const text = Course.buildShareText(lang, "EMB-ABC123", "https://panel.test");
    assert.ok(text.includes("EMB-ABC123"), lang);
    assert.ok(text.includes("https://panel.test?ref=EMB-ABC123"), lang);
    assert.deepEqual(Course.scanCompliance(text), [], lang);
    // education framing, never a yield promise
    assert.match(text.toLowerCase(), /learn|aprende/);
  }
});

test("share URLs are well-formed", () => {
  const wa = Course.whatsappShareUrl("hello world");
  assert.ok(wa.startsWith("https://wa.me/?text="));
  assert.ok(wa.includes("hello%20world"));
  const sms = Course.smsShareUrl("hello world");
  assert.ok(sms.startsWith("sms:?&body="));
  assert.ok(sms.includes("hello%20world"));
});

test("computeProgress math", () => {
  assert.deepEqual(Course.computeProgress([]), { complete: 0, total: 0, pct: 0 });
  const mods = [
    { state: "complete" }, { state: "complete" }, { state: "in-progress" },
    { state: "not-started" }, { state: "not-started" }, { state: "not-started" },
  ];
  assert.deepEqual(Course.computeProgress(mods), { complete: 2, total: 6, pct: 33 });
  assert.equal(Course.computeProgress(mods.map(() => ({ state: "complete" }))).pct, 100);
});

test("validateQuizAnswers", () => {
  assert.deepEqual(Course.validateQuizAnswers([0, 1, 2, 3, 0], 5), { ok: true });
  assert.equal(Course.validateQuizAnswers([0, 1], 5).ok, false);
  assert.equal(Course.validateQuizAnswers([0, 1, 2, 3, 9], 5).ok, false);
  assert.equal(Course.validateQuizAnswers("nope", 5).ok, false);
});

test("stripAnswers removes keys but keeps questions/options", () => {
  const mod = loadModule("module-01");
  const clean = Course.stripAnswers(mod);
  assert.equal(clean.quiz.length, 5);
  for (const q of clean.quiz) {
    assert.ok(!("answer" in q));
    assert.equal(q.options.en.length, 4);
    assert.ok(q.question.en);
  }
  // original untouched
  assert.ok("answer" in mod.quiz[0]);
});

// --- renderers ---------------------------------------------------------------

test("renderCourseOffer: not enrolled shows Stripe CTA; enrolled shows continue; certified shows badge", () => {
  const cfg = { coursePaymentUrl: "https://buy.stripe.com/test123" };
  const notEnrolled = Course.renderCourseOffer(cfg, { enrolled: false }, "en");
  assert.ok(notEnrolled.includes("https://buy.stripe.com/test123"));
  assert.ok(notEnrolled.includes("$100"));

  const enrolled = Course.renderCourseOffer(cfg, { enrolled: true, certified: false }, "en");
  assert.ok(enrolled.includes("data-course-goto"));
  assert.ok(!enrolled.includes("buy.stripe.com"));

  const certified = Course.renderCourseOffer(cfg, { enrolled: true, certified: true }, "es");
  assert.ok(certified.includes("Certificado"));
  assert.deepEqual(Course.scanCompliance(notEnrolled + enrolled + certified), []);
});

test("renderReferrals: code, wa.me + sms links, stats", () => {
  const ref = {
    referral_code: "EMB-ABC123",
    signups: 2,
    referred: [
      { phone_masked: "••••3333", at: "2026-10-11T12:00:00+00:00" },
      { phone_masked: "••••4444", at: "2026-10-10T12:00:00+00:00" },
    ],
    program: { reward: "5% of referred buyers' token purchases, forever" },
  };
  const html = Course.renderReferrals(ref, "en", "https://panel.test");
  assert.ok(html.includes("EMB-ABC123"));
  assert.ok(html.includes("https://wa.me/?text="));
  assert.ok(html.includes("sms:?&amp;body=") || html.includes("sms:?&body="));
  assert.ok(html.includes("••••3333"));
  assert.ok(html.includes(">2<"));
  assert.deepEqual(Course.scanCompliance(html), []);
});

test("certifiedBadge renders in both languages", () => {
  assert.ok(Course.certifiedBadge("en").includes("Certified"));
  assert.ok(Course.certifiedBadge("es").includes("Certificado"));
});

// --- bundled content: schema + compliance ------------------------------------

test("course content: 6 modules, schema-valid, compliance-clean", () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(CONTENT_DIR, "course.json"), "utf8"));
  assert.equal(manifest.price_usd, 100);
  assert.deepEqual(manifest.modules, MODULE_IDS);
  for (const id of MODULE_IDS) {
    const m = loadModule(id);
    assert.equal(m.id, id);
    assert.ok(m.title.en && m.title.es, id);
    assert.ok(m.lessons.length >= 3, id);
    assert.equal(m.quiz.length, 5, id);
    for (const q of m.quiz) {
      assert.ok(q.question.en && q.question.es);
      assert.equal(q.options.en.length, 4);
      assert.equal(q.options.es.length, 4);
      assert.ok(q.answer >= 0 && q.answer <= 3);
    }
    // every copy string in the module scans clean
    const texts = [
      m.title.en, m.title.es, m.summary.en, m.summary.es,
      ...m.lessons.flatMap((l) => [l.title.en, l.title.es, ...l.body.en, ...l.body.es]),
      ...m.quiz.flatMap((q) => [q.question.en, q.question.es, ...q.options.en, ...q.options.es]),
    ];
    for (const text of texts) {
      assert.deepEqual(Course.scanCompliance(text), [], `${id}: ${text.slice(0, 60)}`);
    }
  }
});
