#!/bin/sh
cat > app.log <<'LOG'
2026-11-03T01:00:00Z INFO boot ok
2026-11-03T01:00:04Z ERROR relay refused job j1
2026-11-03T01:00:09Z WARN queue slow
2026-11-03T01:00:11Z ERROR model unavailable
2026-11-03T01:00:15Z INFO retry
2026-11-03T01:00:20Z WARN disk 82%
2026-11-03T01:00:31Z ERROR relay refused job j2
2026-11-03T01:00:40Z INFO done
LOG
