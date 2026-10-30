import SwiftUI

// LOGO-NATIVE-1 (Del direction, Oct 30): the spinning ASCII loop
// behind the Mac console panels, native parity for the web
// background (js/logo-background.js). Honest scope note: this is a
// dim glyph field animated by phase, using the web's glyph set and
// 9-step ramps — it is NOT a port of the web canvas's 3D ribbon
// projection, which has no native equivalent in this app. The loop
// follows the web rules that do transfer: a user-picked color wins
// over product switches until Reset, the product palette returns on
// reset, reduced motion renders one still frame, the view ignores
// pointer input and is hidden from accessibility. Rotation speed
// and pause controls stay in the web studio for the follow-up
// slice, exactly as Hana scoped the web panel. No Swift toolchain
// exists in this sandbox, so this is checked by inspection and by
// the static tests in tests/native-logo-color.test.mjs.

struct LogoLoopView: View {
    @AppStorage("meta-trio-logo-color") private var customHex: String = ""
    @ObservedObject var model: AppModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private var palette: [Color] {
        if LogoColor.isValidHex(customHex) {
            return LogoColor.buildPalette(baseHex: customHex.lowercased())
        }
        return LogoColor.productPalette(for: model.selectedProduct)
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
            let phase = reduceMotion
                ? 0
                : Int(timeline.date.timeIntervalSinceReferenceDate * 2)
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
    }
}
