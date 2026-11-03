#!/bin/sh
cat > app.py <<'PY'
from helpers import slugify

print(slugify("Meta OS: Native Desktop!"))
PY
