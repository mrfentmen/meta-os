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
// LOGO-NATIVE-3 (Del direction, Oct 30): the Logo panel's title
// joins the other five panels on PanelHeading (ContentView.swift):
// until now it was a plain 15pt bold Text, so under Ignis, Vigiles,
// or Medicus it missed the console heading treatment the web
// .panel h2 carries for that product — Ignis/Vigiles uppercase
// mono 15pt bold with 1.8pt tracking and a 3pt accent tick,
// Medicus uppercase plain 15pt bold with 1.2pt tracking and no
// tick. PanelHeading already implements all three branches, so
// this slice only wires the Logo title into it, gated by the
// selected product exactly like the other panel titles; the
// original title stays the accessibility label, so VoiceOver
// still hears "Logo", not the shouted capitals. Presets, picker,
// value lines, slider, pause button, and the large-logo note are
// untouched.
// LOGO-NATIVE-4 (Del direction, Oct 30): VoiceOver state parity
// for the web LOGO-1/LOGO-2 aria-pressed states. The web swatches
// toggle aria-pressed and the web pause button toggles
// aria-pressed, but the native panel only showed the state
// visually — a white ring on the chosen swatch, a changed pause
// label — so VoiceOver never heard which preset was chosen or
// whether the loop was paused. Now the chosen preset carries the
// isSelected trait, gated by the same saved-hex match as its
// ring, and the pause button carries a Paused/Playing value, so
// the spoken state follows the stored state exactly. SwiftUI has
// no pressed trait for a plain Button, so the pause state is a
// value, not a trait — the trait is only where it fits, the
// preset choice. Heading, presets, picker, value lines, slider,
// pause label, and the large-logo note are untouched.
// LOGO-NATIVE-5 (Del direction, Oct 30): the Logo panel gains
// its intro note, the native counterpart to the web panel's
// opening paragraph. Until now the native panel jumped straight
// from its heading to the swatches, while every other native
// panel carries its intro note at 13pt — so a Mac user met the
// color, speed, and pause controls with no sentence saying what
// the loop is or that the choices persist. The note carries the
// web paragraph's meaning in Mac words: the choices are saved on
// this Mac (the panel's @AppStorage values) and come back on
// relaunch, and Reset returns the color to the selected product's
// color. It renders at 13pt muted with wrapping, the same note
// treatment the still-image and video intros carry. Heading,
// presets, picker, value lines, slider, pause button, and the
// large-logo note are untouched.

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
                PanelHeading(title: "Logo", isIgnis: model.selectedProduct == .ignis, isVigiles: model.selectedProduct == .vigiles, isMedicus: model.selectedProduct == .medicus)
                Text("The spinning ASCII Meta loop behind these panels. Pick a color to re-tint it, set its rotation speed, or pause it — the choices are saved on this Mac and come back on relaunch. Reset returns the color to the selected product's color.")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
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
                        .accessibilityAddTraits(customHex.lowercased() == preset.hex ? .isSelected : [])
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
                .accessibilityValue(paused ? "Paused" : "Playing")
                Text("Large logo stays in the web studio.")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
            }
        }
    }
}
