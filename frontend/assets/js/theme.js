(() => {
  const root = document.documentElement;
  const storageKey = "skillbridge_theme";
  const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");

  function getSavedTheme() {
    try {
      const saved = localStorage.getItem(storageKey);
      return saved === "light" || saved === "dark" ? saved : null;
    } catch {
      return null;
    }
  }

  function getPreferredTheme() {
    return getSavedTheme() || (systemTheme.matches ? "dark" : "light");
  }

  function refreshIcons() {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  function updateButtons() {
    const isDark = root.dataset.theme === "dark";

    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      const label = button.querySelector("[data-theme-label]");
      const icon = button.querySelector("[data-theme-icon]");

      // New home-page theme button.
      if (label) {
        label.textContent = isDark ? "Light" : "Dark";
      }

      if (icon) {
        icon.innerHTML = isDark
          ? '<i data-lucide="sun"></i>'
          : '<i data-lucide="moon"></i>';
      }

      // Existing dashboard/theme buttons stay compatible.
      if (!label && !icon) {
        button.textContent = isDark ? "☀ Light" : "☾ Dark";
      }

      button.setAttribute(
        "aria-label",
        isDark ? "Switch to light theme" : "Switch to dark theme"
      );

      button.setAttribute("aria-pressed", String(isDark));

      button.setAttribute(
        "title",
        isDark ? "Switch to light theme" : "Switch to dark theme"
      );
    });

    refreshIcons();
  }

  function applyTheme(theme) {
    const value = theme === "dark" ? "dark" : "light";

    root.dataset.theme = value;
    root.style.colorScheme = value;

    updateButtons();
  }

  function saveTheme(theme) {
    try {
      localStorage.setItem(storageKey, theme);
    } catch {
      // Theme still works when storage is unavailable.
    }
  }

  function toggleTheme() {
    const next =
      root.dataset.theme === "dark"
        ? "light"
        : "dark";

    applyTheme(next);
    saveTheme(next);
  }

  // Apply immediately to avoid theme flash.
  applyTheme(getPreferredTheme());

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-theme-toggle]");
    if (!button) return;

    event.preventDefault();
    toggleTheme();
  });

  document.addEventListener("DOMContentLoaded", () => {
    updateButtons();
    refreshIcons();
  });

  // Keep multiple browser tabs in sync.
  window.addEventListener("storage", (event) => {
    if (event.key !== storageKey && event.key !== null) return;
    applyTheme(getPreferredTheme());
  });

  // Follow OS theme only if the user has not chosen one manually.
  systemTheme.addEventListener("change", (event) => {
    if (getSavedTheme()) return;
    applyTheme(event.matches ? "dark" : "light");
  });

  window.SkillBridgeTheme = {
    toggle: toggleTheme,

    setLight() {
      applyTheme("light");
      saveTheme("light");
    },

    setDark() {
      applyTheme("dark");
      saveTheme("dark");
    },

    reset() {
      try {
        localStorage.removeItem(storageKey);
      } catch {}

      applyTheme(systemTheme.matches ? "dark" : "light");
    },

    getTheme() {
      return root.dataset.theme || getPreferredTheme();
    }
  };
})();
