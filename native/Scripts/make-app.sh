#!/bin/bash
# Builds MetaTrio.app from the SwiftPM package and ad-hoc signs it.
#
# A bundled .app is required for reliable camera access: macOS only grants
# camera permission (TCC) to a bundled app whose Info.plist carries
# NSCameraUsageDescription. A bare SwiftPM executable has no bundle, so
# this script assembles one. No Apple Developer account is needed; the
# signature is ad-hoc ("-"), for local demo use only.
#
# Usage:  ./Scripts/make-app.sh           (debug build, fast iteration)
#         CONFIG=release ./Scripts/make-app.sh
set -euo pipefail

cd "$(dirname "$0")/.."

CONFIG="${CONFIG:-debug}"
APP="MetaTrio.app"

echo "Building MetaTrio ($CONFIG)..."
swift build -c "$CONFIG"
BIN_PATH="$(swift build -c "$CONFIG" --show-bin-path)/MetaTrio"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"

cp "$BIN_PATH" "$APP/Contents/MacOS/MetaTrio"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleExecutable</key>
	<string>MetaTrio</string>
	<key>CFBundleIdentifier</key>
	<string>com.mrfentmen.metatrio</string>
	<key>CFBundleName</key>
	<string>MetaTrio</string>
	<key>CFBundleDisplayName</key>
	<string>MetaTrio</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleShortVersionString</key>
	<string>0.1.0</string>
	<key>CFBundleVersion</key>
	<string>1</string>
	<key>LSMinimumSystemVersion</key>
	<string>13.0</string>
	<key>NSPrincipalClass</key>
	<string>NSApplication</string>
	<key>NSCameraUsageDescription</key>
	<string>MetaTrio uses the camera to capture sampled frames for visual assessment, only while analysis is running.</string>
	<key>NSHighResolutionCapable</key>
	<true/>
</dict>
</plist>
PLIST

codesign --force --deep --sign - "$APP"

echo "Built $APP"
echo "Open it with:  open $APP"
echo "First launch only: if Gatekeeper objects, right-click the app and choose Open."
