(function () {
  const config = window.SKILLBRIDGE_CONFIG || {
    API_URL: "/api/v1",
    TOKEN_KEY: "skillbridge_token"
  };

  const API_URL = String(config.API_URL || "/api/v1").replace(/\/+$/, "");
  const TOKEN_KEY = config.TOKEN_KEY || "skillbridge_token";

  function token() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setToken(value) {
    if (value) {
      localStorage.setItem(TOKEN_KEY, value);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  }

  function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
  }

  function esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function makeUrl(path) {
    if (/^https?:\/\//i.test(path)) {
      return path;
    }

    const cleanPath = String(path || "").startsWith("/")
      ? path
      : `/${path}`;

    return `${API_URL}${cleanPath}`;
  }

  async function request(method, path, body = undefined) {
    const headers = {
      Accept: "application/json"
    };

    const accessToken = token();

    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }

    let finalBody = body;

    if (
      body !== undefined &&
      body !== null &&
      !(body instanceof FormData)
    ) {
      headers["Content-Type"] = "application/json";
      finalBody = JSON.stringify(body);
    }

    let response;

    try {
      response = await fetch(makeUrl(path), {
        method,
        headers,
        body: finalBody
      });
    } catch (error) {
      throw new Error("Unable to connect to SkillBridge API.");
    }

    let data = {};

    try {
      data = await response.json();
    } catch (_) {}

    if (!response.ok) {
      const message =
        data?.detail ||
        data?.message ||
        `Request failed (${response.status})`;

      if (response.status === 401) {
        clearToken();
      }

      throw new Error(message);
    }

    return data;
  }

  function toast(message) {
    alert(message);
  }

  window.SB = {
    API_URL,
    TOKEN_KEY,
    token,
    setToken,
    clearToken,
    esc,
    request,

    get(path) {
      return request("GET", path);
    },

    post(path, body) {
      return request("POST", path, body);
    },

    put(path, body) {
      return request("PUT", path, body);
    },

    patch(path, body) {
      return request("PATCH", path, body);
    },

    delete(path, body) {
      return request("DELETE", path, body);
    },

    toast
  };
})();
