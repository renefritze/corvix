FROM node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    CHROME_PATH=/usr/bin/chromium

RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium ca-certificates fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @lhci/cli

WORKDIR /workspace
