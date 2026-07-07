FROM node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    CHROME_PATH=/usr/bin/chromium

# Use Playwright's Chromium instead of Debian's `chromium` package. The Debian
# build tracks a moving version (150.0.7871.x broke headless startup under lhci
# -- Chrome hung and never opened its DevTools port), whereas Playwright ships a
# Chromium build locked to the playwright npm package and validated for headless
# use inside containers. `--with-deps` pulls the required shared libraries, and
# the binary is symlinked to /usr/bin/chromium so CHROME_PATH / .lighthouserc.json
# keep working unchanged.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates fonts-liberation dbus \
    && npm install -g @lhci/cli playwright \
    && playwright install --with-deps chromium \
    && ln -sf "$(ls /opt/pw-browsers/chromium-*/chrome-linux/chrome | head -n1)" /usr/bin/chromium \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
