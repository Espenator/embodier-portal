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
 *   coursePaymentUrl: Stripe payment link for the $100 Investment Real Estate
 *             Course (env STRIPE_COURSE_URL value), e.g.
 *             "https://buy.stripe.com/...". Apple Pay one-tap is handled by
 *             Stripe. When empty, the course offer card shows without a live
 *             buy link. After purchase, the Brain's Stripe webhook enrolls
 *             the buyer by verified phone.
 *   portalUrl: canonical public URL of this portal, used to build referral
 *             share links (defaults to the page origin when empty).
 */
window.EMBODIER_PORTAL_CONFIG = {
  apiBase: "",
  loginUrl: "/login",
  coursePaymentUrl: "",
  portalUrl: "",
};
