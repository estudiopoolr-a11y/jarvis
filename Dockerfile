FROM node:24-alpine AS config-validator

WORKDIR /build
COPY openclaw_config/config.json ./config.json
RUN node -e 'JSON.parse(require("node:fs").readFileSync("config.json", "utf8"))'

FROM ghcr.io/openclaw/openclaw:latest AS runtime

ENV HOME=/home/node \
    OPENCLAW_HOME=/home/node \
    OPENCLAW_STATE_DIR=/home/node/.openclaw \
    OPENCLAW_CONFIG_DIR=/home/node/.openclaw \
    OPENCLAW_CONFIG_PATH=/home/node/.openclaw/openclaw.json \
    OPENCLAW_WORKSPACE_DIR=/home/node/.openclaw/workspace \
    OPENCLAW_GATEWAY_PORT=8080

COPY --from=config-validator --chown=node:node /build/config.json /home/node/.openclaw/openclaw.json

EXPOSE 8080

CMD ["node", "dist/index.js", "gateway", "--bind", "lan", "--port", "8080"]
