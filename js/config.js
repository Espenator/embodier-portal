/* Embodier portal — LIVE mode configuration.
 *
 * Copy to config.js (same directory as index.html) and set apiBase to enable
 * live mode. When apiBase is empty, the portal runs in demo mode with the
 * prototype's illustrative mock content.
 *
 *   apiBase:  base URL of the portal backend API, e.g.
 *             "https://portal-api-XXXX.us-east1.run.app" (no trailing slash).
 *             The API must allow this origin via CORS.
 *   loginUrl: where to send users with no (or expired) session — the Brain's
 *             phone+OTP login page, e.g. "https://brain.example.com/login".
 *             After login, the Brain should hand the portal the HMAC session
 *             token via URL fragment:  <portal>/#session=<token>
 *             (see js/session.js for the full token-source priority).
 */
window.EMBODIER_PORTAL_CONFIG = {
  apiBase: "",
  loginUrl: "/login",
};
