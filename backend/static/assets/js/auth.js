/* =========================================================
   SkillBridge AI — Authentication Helper
   Requires: config.js + api.js
   ========================================================= */

(function () {
  if (!window.SB) {
    throw new Error(
      "api.js must load before auth.js"
    );
  }


  function unwrap(response) {
    return (
      response?.data ??
      response
    );
  }


  function roleOf(user) {
    return String(
      user?.role?.value ||
      user?.role ||
      ""
    )
      .trim()
      .toLowerCase();
  }


  async function login(
    emailOrPayload,
    maybePassword
  ) {
    let payload;

    if (
      typeof emailOrPayload === "object" &&
      emailOrPayload !== null
    ) {
      payload = {
        email:
          String(
            emailOrPayload.email || ""
          )
            .trim()
            .toLowerCase(),

        password:
          String(
            emailOrPayload.password || ""
          ),
      };
    } else {
      payload = {
        email:
          String(emailOrPayload || "")
            .trim()
            .toLowerCase(),

        password:
          String(maybePassword || ""),
      };
    }

    const response =
      await SB.post(
        "/auth/login",
        payload
      );

    const accessToken =
      response?.access_token ||
      response?.data?.access_token ||
      response?.token ||
      response?.data?.token;

    if (!accessToken) {
      throw new Error(
        "Login succeeded but the backend did not return an access token."
      );
    }

    SB.setToken(
      accessToken
    );

    return response;
  }


  async function me() {
    const response =
      await SB.get(
        "/auth/me"
      );

    return unwrap(
      response
    );
  }


  function logout(
    redirectTo = null
  ) {
    SB.clearToken();

    if (redirectTo) {
      window.location.href =
        redirectTo;
    }
  }


  async function requireRole(
    role,
    redirectTo = "/admin/login"
  ) {
    const token =
      SB.token();

    if (!token) {
      window.location.replace(
        redirectTo
      );

      return null;
    }

    try {
      const user =
        await me();

      if (
        roleOf(user) !==
        String(role).toLowerCase()
      ) {
        SB.clearToken();

        window.location.replace(
          redirectTo
        );

        return null;
      }

      return user;
    } catch (error) {
      SB.clearToken();

      window.location.replace(
        redirectTo
      );

      return null;
    }
  }


  async function redirectByRole(
    user = null
  ) {
    const currentUser =
      user || await me();

    const role =
      roleOf(currentUser);

    const routes = {
      student:
        "/student/dashboard.html",

      college:
        "/college/dashboard.html",

      recruiter:
        "/recruiter/dashboard.html",

      admin:
        "/admin/dashboard",
    };

    const destination =
      routes[role];

    if (!destination) {
      throw new Error(
        "Unknown account role."
      );
    }

    window.location.href =
      destination;
  }


  window.Auth = {
    login,
    me,
    logout,
    roleOf,
    requireRole,
    redirectByRole,
  };
})();
