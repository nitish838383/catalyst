/* =========================================================
   SkillBridge AI — Runtime Configuration
   Render-hosted Admin UI + API on the same domain.
   ========================================================= */

(function () {
  const SAME_ORIGIN_API = "/api/v1";

  /*
    Optional override for local testing:
    localStorage.setItem(
      "skillbridge_api_url",
      "http://127.0.0.1:8000/api/v1"
    )
  */

  const stored =
    localStorage.getItem("skillbridge_api_url");

  const apiUrl =
    String(stored || SAME_ORIGIN_API)
      .trim()
      .replace(/\/+$/, "");

  window.SKILLBRIDGE_CONFIG = Object.freeze({
    API_URL: apiUrl,
    TOKEN_KEY: "skillbridge_token",
    APP_NAME: "SkillBridge AI",
  });
})();
