#!/bin/sh
set -e
test "$(python3 app.py)" = "meta-os-native-desktop"
python3 -c "from helpers import slugify; assert slugify('  A  b ') == 'a-b', slugify('  A  b ')"
