/* Session token resolution for the Embodier portal.
 *
 * The Brain mints the HMAC session token after phone+OTP verification. The
 * portal needs that token to call the backend API as `Authorization: Bearer`.
 * Sources, in priority order:
 *   1. URL fragment  #session=<token>  — one-time handoff from the Brain's
 *      panel page. Consumed immediately: stored, then scrubbed from the URL.
 *   2. localStorage  'embodier_session_token' — set by (1) or by the login flow.
 *   3. Cookie 'signup_session' — readable only when the Brain sets it WITHOUT
 *      HttpOnly. (The Brain's default Set-Cookie is HttpOnly, in which case
 *      this source is silently unavailable and (1)/(2) are the way in.)
 *
 * Nothing here mints or validates tokens — the backend verifies them.
 * Vanilla JS, no dependencies. Testable in Node with injected storage/location.
 */
(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.EmbodierPortalSession = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var LS_KEY = "embodier_session_token";
  var COOKIE_NAME = "signup_session";
  var FRAG_PARAM = "session";

  function readFragment(loc) {
    try {
      var hash = (loc && loc.hash) || "";
      if (!hash) return "";
      var params = new URLSearchParams(hash.replace(/^#/, ""));
      return params.get(FRAG_PARAM) || "";
    } catch (e) { return ""; }
  }

  function scrubFragment(loc, hist) {
    try {
      if (hist && hist.replaceState) {
        var url = loc.pathname + loc.search;
        hist.replaceState(null, "", url);
      } else if (loc) {
        loc.hash = "";
      }
    } catch (e) {}
  }

  function readCookie(doc) {
    try {
      var cookies = (doc && doc.cookie) || "";
      var parts = cookies.split(";");
      for (var i = 0; i < parts.length; i++) {
        var kv = parts[i].split("=");
        if (kv[0].trim() === COOKIE_NAME) return decodeURIComponent((kv[1] || "").trim());
      }
    } catch (e) {}
    return "";
  }

  function resolveToken(env) {
    // env: { location, history, localStorage, document } — injectable for tests.
    env = env || {};
    var loc = env.location || (typeof location !== "undefined" ? location : null);
    var hist = env.history || (typeof history !== "undefined" ? history : null);
    var ls = env.localStorage || (typeof localStorage !== "undefined" ? localStorage : null);
    var doc = env.document || (typeof document !== "undefined" ? document : null);

    var frag = readFragment(loc);
    if (frag) {
      try { if (ls) ls.setItem(LS_KEY, frag); } catch (e) {}
      scrubFragment(loc, hist);
      return frag;
    }
    try { if (ls) { var v = ls.getItem(LS_KEY); if (v) return v; } } catch (e) {}
    return readCookie(doc);
  }

  function storeToken(token, env) {
    env = env || {};
    var ls = env.localStorage || (typeof localStorage !== "undefined" ? localStorage : null);
    try { if (ls) { if (token) ls.setItem(LS_KEY, token); else ls.removeItem(LS_KEY); } } catch (e) {}
  }

  function clearToken(env) { storeToken("", env); }

  return {
    LS_KEY: LS_KEY,
    COOKIE_NAME: COOKIE_NAME,
    resolveToken: resolveToken,
    storeToken: storeToken,
    clearToken: clearToken,
  };
});
