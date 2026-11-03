# Trio stack — container image (mirrors run-stack.sh)
#
# One image for all four processes; docker-compose.yml picks the
# command per service. Zero third-party dependencies: Node stdlib
# only (relay + app) and Python stdlib only (queue + agent), so
# there is no npm install and no pip install step.
#
# Ports mirror run-stack.sh defaults:
#   relay :8787 (RELAY_PORT) | queue :8935 | app :8080 (PORT)
# Env contract mirrors relay/README.md, server/queue/README.md and
# server/README.md — see docker-compose.yml for the full table.
FROM node:22-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Manifest first for layer caching (no dependencies to install).
COPY package.json ./
COPY relay/ ./relay/
COPY server/ ./server/
COPY js/ ./js/
COPY index.html styles.css ./

EXPOSE 8787 8935 8080

# Overridden per service in docker-compose.yml.
CMD ["node", "server/server.mjs"]
