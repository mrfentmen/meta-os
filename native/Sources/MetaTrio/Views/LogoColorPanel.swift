import SwiftUI

// LOGO-NATIVE-1 (Del direction, Oct 30): native parity for Hana's
// web LOGO-1 panel. Six studio presets plus a custom picker, the
// choice saved under the web panel's key so the Mac console and
// the web console share one name for it, live re-tint of
// LogoLoopView through the shared @AppStorage value, Reset back to
// the selected product's color. A saved color survives product
// switches until Reset, exactly like the web panel.
// LOGO-NATIVE-2 (Del direction, Oct 30): native parity for Hana's
// web LOGO-2 panel — a rotation speed slider (0-100, default 25)
// and a Pause/Resume button, saved under the web panel's own keys
// (meta-trio-logo-speed, meta-trio-logo-paused) and driving
// LogoLoopView live through the shared @AppStorage values. Only
// the large logo stays in the web studio now. No Swift toolchain
// exists in this sandbox, so this is checked by inspection and
// by the static tests in tests/native-logo-animation.test.mjs.

private struct LogoColorPanel: View {
    @AppStorage("meta-trio-logo-color") private var customHex: String = ""
    @AppStorage("meta-trio-logo-speed") private var speedPercent: Int = 25
    @AppStorage("meta-trio-logo-paused") private var paused: Bool = false
    @ObservedObject var model: AppModel

    private var productColor: Color {
        switch model.config.accentColorName {
        case "blue": return .blue
        case "red": return .red
        case "green": return .green
        default: return .accentColor
        }
    }

    private var pickerBinding: Binding<Color> {
        Binding(
            get: {
                if LogoColor.isValidHex(customHex),
                   let saved = LogoColor.color(fromHex: customHex) {
                    return saved
                }
                return productColor
            },
            set: { newValue in
                if let hex = LogoColor.colorToHex(newValue) {
                    customHex = hex
                }
            }
        )
    }

    private var valueLine: String {
        if LogoColor.isValidHex(customHex) {
            return "Logo color: \(customHex.uppercased())"
        }
        return "Logo color: product color"
    }

    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 10) {
                Text("Logo")
                    .font(.system(size: 15, weight: .bold))
                HStack(spacing: 10) {
                    ForEach(LogoColor.presets, id: \.hex) { preset in
                        Button {
                            customHex = preset.hex
                        } label: {
                            Circle()
                                .fill(LogoColor.color(fromHex: preset.hex) ?? .gray)
                                .frame(width: 28, height: 28)
                                .overlay(
                                    Circle()
                                        .stroke(
                                            Color.white,
                                            lineWidth: customHex.lowercased() == preset.hex ? 2 : 0
                                        )
                                )
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel(preset.name)
                    }
                }
                ColorPicker("Custom logo color", selection: pickerBinding)
                Text(valueLine)
                    .font(.system(size: 13, design: .monospaced))
                    .foregroundStyle(.secondary)
                Button("Reset to product color") {
                    customHex = ""
                }
                Slider(
                    value: Binding(
                        get: { Double(min(100, max(0, speedPercent))) },
                        set: { speedPercent = Int($0) }
                    ),
                    in: 0...100,
                    step: 1
                ) {
                    Text("Rotation speed")
                }
                Text("Rotation speed: \(min(100, max(0, speedPercent)))%")
                    .font(.system(size: 13, design: .monospaced))
                    .foregroundStyle(.secondary)
                Button(paused ? "Resume logo" : "Pause logo") {
                    paused.toggle()
                }
                Text("Large logo stays in the web studio.")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
            }
        }
    }
}
