"""Litestar app serving Corvix dashboard data and UI."""

from __future__ import annotations

from dataclasses import asdict
from os import environ
from pathlib import Path

import uvicorn
from litestar import Litestar, Response, get
from litestar.exceptions import HTTPException

from corvix.config import AppConfig, DashboardSpec, load_config
from corvix.dashboarding import build_dashboard_data
from corvix.storage import NotificationCache

THEMES: dict[str, dict[str, str]] = {
    "default": {
        "bg": "#f2efe8",
        "ink": "#181818",
        "surface": "#fffdf8",
        "accent": "#a13d2d",
        "line": "#d7cdbf",
        "ok": "#1e7a4f",
        "muted": "#5f5a50",
    },
    "dark": {
        "bg": "#1a1a2e",
        "ink": "#e0e0e0",
        "surface": "#16213e",
        "accent": "#e94560",
        "line": "#333355",
        "ok": "#4ecca3",
        "muted": "#8888aa",
    },
    "solarized": {
        "bg": "#fdf6e3",
        "ink": "#657b83",
        "surface": "#eee8d5",
        "accent": "#cb4b16",
        "line": "#93a1a1",
        "ok": "#859900",
        "muted": "#93a1a1",
    },
}

INDEX_HTML = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Corvix Dashboard</title>
  <style>
    :root {
      --bg: #f2efe8;
      --ink: #181818;
      --surface: #fffdf8;
      --accent: #a13d2d;
      --line: #d7cdbf;
      --ok: #1e7a4f;
      --muted: #5f5a50;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--ink);
      background: radial-gradient(circle at 20% 10%, #f7f3ea, var(--bg));
    }
    header {
      padding: 1rem 1.25rem;
      border-bottom: 2px solid var(--line);
      background: linear-gradient(120deg, #fff8ea, #f7f1e6);
      display: flex;
      gap: 1rem;
      align-items: center;
      flex-wrap: wrap;
    }
    h1 { margin: 0; font-size: 1.2rem; letter-spacing: 0.02em; }
    .meta { color: var(--muted); font-size: 0.9rem; }
    .controls {
      display: flex; gap: 0.5rem; align-items: center; margin-left: auto;
    }
    select, button {
      border: 1px solid var(--line);
      background: var(--surface);
      color: var(--ink);
      padding: 0.45rem 0.65rem;
      border-radius: 0.4rem;
      font: inherit;
    }
    button {
      background: var(--accent);
      color: #fff;
      border-color: transparent;
      cursor: pointer;
    }
    main { padding: 1rem; display: grid; gap: 1rem; }
    section {
      border: 1px solid var(--line);
      border-radius: 0.75rem;
      background: var(--surface);
      overflow: hidden;
      box-shadow: 0 2px 8px #00000010;
    }
    section h2 {
      margin: 0;
      padding: 0.7rem 0.9rem;
      background: #f5ecdd;
      font-size: 1rem;
      border-bottom: 1px solid var(--line);
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th, td { padding: 0.45rem 0.55rem; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
    th { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }
    .unread { color: var(--ok); font-weight: 700; }
    .empty { padding: 1rem; color: var(--muted); }
    @media (max-width: 900px) {
      th:nth-child(6), td:nth-child(6), th:nth-child(8), td:nth-child(8), th:nth-child(9), td:nth-child(9) { display: none; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Corvix Notifications</h1>
    <div class="meta" id="meta">Loading...</div>
    <div class="controls">
      <label for="theme">Theme</label>
      <select id="theme"></select>
      <label for="dashboard">Dashboard</label>
      <select id="dashboard"></select>
      <button id="refresh">Refresh</button>
    </div>
  </header>
  <main id="content"></main>
  <script>
    const THEMES = {
      default:   { bg: "#f2efe8", ink: "#181818", surface: "#fffdf8", accent: "#a13d2d", line: "#d7cdbf", ok: "#1e7a4f", muted: "#5f5a50" },
      dark:      { bg: "#1a1a2e", ink: "#e0e0e0", surface: "#16213e", accent: "#e94560", line: "#333355", ok: "#4ecca3", muted: "#8888aa" },
      solarized: { bg: "#fdf6e3", ink: "#657b83", surface: "#eee8d5", accent: "#cb4b16", line: "#93a1a1", ok: "#859900", muted: "#93a1a1" },
    };

    function applyTheme(name) {
      const vars = THEMES[name] || THEMES.default;
      Object.entries(vars).forEach(([k, v]) => document.documentElement.style.setProperty(`--${k}`, v));
      localStorage.setItem("corvix-theme", name);
    }

    const content = document.getElementById("content");
    const meta = document.getElementById("meta");
    const themeSelect = document.getElementById("theme");
    const dashboardSelect = document.getElementById("dashboard");
    const refreshButton = document.getElementById("refresh");
    let currentDashboard = null;

    // Populate theme selector and restore saved preference
    Object.keys(THEMES).forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name.charAt(0).toUpperCase() + name.slice(1);
      themeSelect.append(option);
    });
    const savedTheme = localStorage.getItem("corvix-theme") || "default";
    themeSelect.value = savedTheme;
    applyTheme(savedTheme);

    themeSelect.addEventListener("change", () => applyTheme(themeSelect.value));

    async function fetchSnapshot(selectedDashboard) {
      const query = selectedDashboard ? `?dashboard=${encodeURIComponent(selectedDashboard)}` : "";
      const response = await fetch(`/api/snapshot${query}`);
      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || "Failed to load snapshot.");
      }
      return response.json();
    }

    function renderTable(group) {
      if (!group.items.length) {
        return `<section><h2>${group.name}</h2><div class="empty">No notifications.</div></section>`;
      }
      const rows = group.items.map((item) => `
        <tr>
          <td>${item.score.toFixed(2)}</td>
          <td>${item.updated_at}</td>
          <td>${item.repository}</td>
          <td>${item.reason}</td>
          <td>${item.subject_type}</td>
          <td>${item.subject_title}</td>
          <td class="${item.unread ? "unread" : ""}">${item.unread ? "yes" : "no"}</td>
          <td>${item.matched_rules.join(", ")}</td>
          <td>${item.actions_taken.join(", ")}</td>
        </tr>
      `).join("");
      return `
        <section>
          <h2>${group.name}</h2>
          <table>
            <thead>
              <tr>
                <th>Score</th>
                <th>Updated</th>
                <th>Repo</th>
                <th>Reason</th>
                <th>Type</th>
                <th>Title</th>
                <th>Unread</th>
                <th>Rules</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </section>`;
    }

    function renderSnapshot(payload) {
      const generated = payload.generated_at ?? "unknown";
      meta.textContent = `Snapshot: ${generated} | Items: ${payload.total_items} | Auto-refresh: 15s`;
      content.innerHTML = payload.groups.map(renderTable).join("");
    }

    function updateDashboardOptions(names, selectedName) {
      const oldValue = dashboardSelect.value;
      dashboardSelect.innerHTML = "";
      names.forEach((name) => {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        dashboardSelect.append(option);
      });
      dashboardSelect.value = selectedName || oldValue || names[0] || "";
      currentDashboard = dashboardSelect.value;
    }

    async function refresh() {
      try {
        const payload = await fetchSnapshot(currentDashboard);
        updateDashboardOptions(payload.dashboard_names, payload.name);
        currentDashboard = payload.name;
        renderSnapshot(payload);
      } catch (error) {
        meta.textContent = `Load failed: ${error.message}`;
      }
    }

    dashboardSelect.addEventListener("change", () => {
      currentDashboard = dashboardSelect.value;
      refresh();
    });
    refreshButton.addEventListener("click", refresh);

    refresh();
    setInterval(refresh, 15000);
  </script>
</body>
</html>
"""


@get("/", sync_to_thread=False)
def index() -> Response[str]:
    """Serve the dashboard single-page UI."""
    return Response(content=INDEX_HTML, media_type="text/html")


@get("/api/health", sync_to_thread=False)
def health() -> dict[str, str]:
    """Health endpoint for container checks."""
    return {"status": "ok"}


@get("/api/themes", sync_to_thread=False)
def api_themes() -> dict[str, object]:
    """Return available theme presets."""
    return {"themes": THEMES}


@get("/api/dashboards", sync_to_thread=False)
def dashboards() -> dict[str, object]:
    """List configured dashboard names."""
    config = _load_runtime_config()
    names = _dashboard_names(config.dashboards)
    return {"dashboard_names": names}


@get("/api/snapshot", sync_to_thread=False)
def snapshot(dashboard: str | None = None) -> dict[str, object]:
    """Return the selected dashboard data from cache."""
    config = _load_runtime_config()
    generated_at, records = NotificationCache(path=config.resolve_cache_file()).load()
    selected_dashboard = _select_dashboard(config.dashboards, dashboard)
    data = build_dashboard_data(
        records=records,
        dashboard=selected_dashboard,
        generated_at=generated_at,
    )
    payload = asdict(data)
    payload["dashboard_names"] = _dashboard_names(config.dashboards)
    return payload


def _load_runtime_config() -> AppConfig:
    config_path = Path(environ.get("CORVIX_CONFIG", "corvix.yaml"))
    if not config_path.exists():
        msg = f"Config file '{config_path}' does not exist."
        raise HTTPException(status_code=500, detail=msg)
    try:
        return load_config(config_path)
    except ValueError as error:
        msg = f"Invalid config at '{config_path}': {error}"
        raise HTTPException(status_code=500, detail=msg) from error


def _select_dashboard(
    dashboards: list[DashboardSpec],
    selected_name: str | None,
) -> DashboardSpec:
    available = dashboards or [DashboardSpec(name="default", group_by="repository", sort_by="score")]
    if selected_name is None:
        return available[0]
    for dashboard in available:
        if dashboard.name == selected_name:
            return dashboard
    msg = f"Dashboard '{selected_name}' not found."
    raise HTTPException(status_code=404, detail=msg)


def _dashboard_names(dashboards: list[DashboardSpec]) -> list[str]:
    available = dashboards or [DashboardSpec(name="default", group_by="repository", sort_by="score")]
    return [dashboard.name for dashboard in available]


app = Litestar(route_handlers=[index, health, api_themes, dashboards, snapshot])


def run() -> None:
    """Run app with uvicorn."""
    host = environ.get("CORVIX_WEB_HOST", "0.0.0.0")
    port = int(environ.get("CORVIX_WEB_PORT", "8000"))
    reload_enabled = environ.get("CORVIX_WEB_RELOAD", "false").lower() in {"1", "true", "yes"}
    uvicorn.run(
        "corvix.web.app:app",
        host=host,
        port=port,
        reload=reload_enabled,
        reload_dirs=["src"],
    )
