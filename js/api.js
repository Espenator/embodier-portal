/* Embodier portal API client — vanilla JS, no dependencies.
 *
 * Talks to the portal backend (FastAPI):
 *   POST {apiBase}/api/session/verify   {token} -> {ok, member}
 *   GET  {apiBase}/api/me               -> {member, voice}
 *   GET  {apiBase}/api/portfolio        -> {title, empty_note, holdings[], exchange}
 *   GET  {apiBase}/api/interests        -> {title, cta, interests[]}
 *   POST {apiBase}/api/interests        {offering_id, note}
 *   GET  {apiBase}/api/documents        -> {title, documents[]}
 *   GET  {apiBase}/api/broker/deals | /pipeline | /commissions | /buybox
 *
 * Auth: Authorization: Bearer <redacted> (HMAC session token minted by the Brain
 * after phone+OTP verification). 401 anywhere -> onUnauthorized() so the app can
 * clear the session and send the user back to login. No mock data: every failure
 * surfaces as a typed ApiError the UI turns into loading/error/empty states.
 *
 * Works in browsers and in Node (tests inject a fetch implementation).
 */
(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.EmbodierPortalApi = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function ApiError(kind, message, status) {
    this.name = "ApiError";
    this.kind = kind; // 'network' | 'auth' | 'forbidden' | 'bad-request' | 'server'
    this.message = message || kind;
    this.status = status || 0;
  }
  ApiError.prototype = Object.create(Error.prototype);
  ApiError.prototype.constructor = ApiError;

  function PortalApi(opts) {
    opts = opts || {};
    if (!opts.apiBase) throw new Error("PortalApi: apiBase is required");
    this.apiBase = String(opts.apiBase).replace(/\/+$/, "");
    this._getToken = opts.getToken || function () { return ""; };
    this._setToken = opts.setToken || function () {};
    this.onUnauthorized = opts.onUnauthorized || function () {};
    this._fetch = opts.fetchImpl ||
      (typeof fetch !== "undefined" ? fetch.bind(typeof self !== "undefined" ? self : this) : null);
    if (!this._fetch) throw new Error("PortalApi: no fetch implementation available");
  }

  PortalApi.ApiError = ApiError;

  PortalApi.prototype._headers = function (json) {
    var h = {};
    if (json) h["Content-Type"] = "application/json";
    var t = this._getToken();
    if (t) h["Authorization"] = "Bearer " + t;
    return h;
  };

  PortalApi.prototype._request = async function (path, opts) {
    opts = opts || {};
    var method = opts.method || "GET";
    var init = { method: method, headers: this._headers(!!opts.body) };
    if (opts.body !== undefined) init.body = JSON.stringify(opts.body);
    var res;
    try {
      res = await this._fetch(this.apiBase + path, init);
    } catch (e) {
      throw new ApiError("network", "Network request failed — check your connection.");
    }
    if (res.status === 401) {
      try { this._setToken(""); } catch (e) {}
      try { this.onUnauthorized(); } catch (e) {}
      throw new ApiError("auth", "Session expired — please sign in again.", 401);
    }
    if (res.status === 403) {
      throw new ApiError("forbidden", "Not allowed for this account.", 403);
    }
    var data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    if (res.status === 400) {
      var msg = (data && (data.detail || data.message)) || "Invalid request.";
      throw new ApiError("bad-request", msg, 400);
    }
    if (!res.ok) {
      throw new ApiError("server", "Server error — please try again.", res.status);
    }
    return data;
  };

  // --- session -------------------------------------------------------------
  PortalApi.prototype.verifySession = async function (token) {
    if (token) this._setToken(token);
    return this._request("/api/session/verify", { method: "POST", body: { token: token } });
  };

  PortalApi.prototype.clearSession = function () {
    try { this._setToken(""); } catch (e) {}
  };

  // --- member ---------------------------------------------------------------
  PortalApi.prototype.me = function () { return this._request("/api/me"); };
  PortalApi.prototype.portfolio = function () { return this._request("/api/portfolio"); };
  PortalApi.prototype.interests = function () { return this._request("/api/interests"); };
  PortalApi.prototype.expressInterest = function (offeringId, note) {
    return this._request("/api/interests", {
      method: "POST", body: { offering_id: offeringId, note: note || "" },
    });
  };
  PortalApi.prototype.documents = function () { return this._request("/api/documents"); };

  // --- broker (403 for non-brokers) ------------------------------------------
  PortalApi.prototype.brokerDeals = function () { return this._request("/api/broker/deals"); };
  PortalApi.prototype.brokerPipeline = function () { return this._request("/api/broker/pipeline"); };
  PortalApi.prototype.brokerCommissions = function () { return this._request("/api/broker/commissions"); };
  PortalApi.prototype.brokerBuybox = function () { return this._request("/api/broker/buybox"); };

  return PortalApi;
});
