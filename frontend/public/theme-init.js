(() => {
  try {
    const stored = localStorage.getItem("corvix.theme");
    let theme;
    if (stored === "light" || stored === "dark") {
      theme = stored;
    } else {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      theme = prefersDark ? "dark" : "light";
    }
    document.documentElement.dataset.theme = theme;
  } catch {
    document.documentElement.dataset.theme = "dark";
  }
})();
