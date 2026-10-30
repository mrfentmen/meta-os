import SwiftUI

// LOGO-NATIVE-2 (Del direction, Oct 30): native parity for Hana's
// web LOGO-2 panel — the Logo panel's rotation speed slider and
// pause button now drive this loop, under the web panel's own
// storage keys (meta-trio-logo-speed, meta-trio-logo-paused) so
// the Mac console and the web console share one name for each
// choice. Speed is a percent, 0 to 100, default 25: 25% is this
// loop's usual 2 phases a second, 0% is still, 100% is four times
// the usual pace (8 phases a second) — the web LOGO-2 scale
// carried over. Pause holds the loop on its last frame; Resume
// restarts it from that frame, never from the start. A speed
// change or a pause/resume re-bases the phase anchor, so neither
// jumps the loop, and a clock jump backwards never drives the
// phase negative. The large logo stays in the web studio.
// LOGO-NATIVE-1 scope note, unchanged: this is a dim glyph field
// animated by phase, using the web's glyph set and 9-step ramps —
// it is NOT a port of the web canvas's 3D ribbon projection,
// which has no native equivalent in this app. The loop follows
// the web rules that do transfer: a user-picked color wins over
// product switches until Reset, the product palette returns on
// reset, reduced motion renders one still frame, the view ignores
// pointer input and is hidden from accessibility. No Swift
// toolchain exists in this sandbox, so this is checked by
// inspection and by the static tests in
// tests/native-logo-animation.test.mjs. The one-argument
// onChange form below is deliberate: the package targets macOS
// 13, where the two-argument form is unavailable.

struct LogoLoopView: View {
    @AppStorage("meta-trio-logo-color") private var customHex: String = ""
    @AppStorage("meta-trio-logo-speed") private var speedPercent: Int = 25
    @AppStorage("meta-trio-logo-paused") private var paused: Bool = false
    @ObservedObject var model: AppModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var anchorDate = Date()
    @State private var anchorPhase = 0

    private var palette: [Color] {
        if LogoColor.isValidHex(customHex) {
            return LogoColor.buildPalette(baseHex: customHex.lowercased())
        }
        return LogoColor.productPalette(for: model.selectedProduct)
    }

    // Web LOGO-2 scale: 25% is the usual pace, 0% still, 100%
    // four times the usual pace. A stored value outside 0-100 is
    // clamped, never trusted.
    private var clampedSpeed: Int {
        min(100, max(0, speedPercent))
    }

    private var phasesPerSecond: Double {
        Double(clampedSpeed) / 25.0 * 2.0
    }

    private func runningPhase(at date: Date) -> Int {
        if reduceMotion { return 0 }
        let elapsed = max(0, date.timeIntervalSince(anchorDate))
        return anchorPhase + Int(elapsed * phasesPerSecond)
    }

    private func phase(at date: Date) -> Int {
        if paused { return anchorPhase }
        return runningPhase(at: date)
    }

    private func rowString(row: Int, phase: Int) -> String {
        let glyphs = Array(LogoColor.glyphs)
        guard !glyphs.isEmpty else { return "" }
        var line = ""
        for col in 0..<110 {
            line.append(glyphs[(col * 7 + row * 13 + phase) % glyphs.count])
        }
        return line
    }

    var body: some View {
        TimelineView(.animation) { timeline in
            let phase = phase(at: timeline.date)
            VStack(spacing: 0) {
                ForEach(0..<14, id: \.self) { row in
                    Text(rowString(row: row, phase: phase))
                        .font(.system(size: 9, design: .monospaced))
                        .foregroundStyle(
                            palette.isEmpty
                                ? Color.clear
                                : palette[(row + phase) % palette.count].opacity(0.35)
                        )
                        .lineLimit(1)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
        .accessibilityHidden(true)
        .allowsHitTesting(false)
        .onChange(of: paused) { isPaused in
            // Freezing captures the live frame; resuming keeps it
            // as the new anchor, so Resume restarts from the held
            // frame instead of jumping back to the start.
            if isPaused {
                anchorPhase = runningPhase(at: Date())
            }
            anchorDate = Date()
        }
        .onChange(of: speedPercent) { _ in
            // Re-base on a speed change so the loop keeps its
            // current frame and only its pace changes. Paused
            // stays frozen: the anchor is untouched until Resume.
            if !paused {
                anchorPhase = runningPhase(at: Date())
                anchorDate = Date()
            }
        }
    }
}
