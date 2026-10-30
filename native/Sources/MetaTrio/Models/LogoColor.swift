import AppKit
import SwiftUI

// LOGO-NATIVE-1 (Del direction, Oct 30): native parity for Hana's
// web LOGO-1 panel. Same storage key, same six studio presets, same
// 9-step ramp build as js/logo-background.js (shadows mixed toward
// near-black #020817, highlights toward white), same product
// palettes verbatim from the web background. A saved custom color
// wins over product switches until Reset clears it, exactly like
// the web panel. No Swift toolchain exists in this sandbox, so this
// file is checked by inspection and by the static tests in
// tests/native-logo-color.test.mjs, never by a Mac build run.

enum LogoColor {
    static let storageKey = "meta-trio-logo-color"

    static let presets: [(name: String, hex: String)] = [
        ("Meta blue", "#1877f2"),
        ("Cyan", "#00c8ff"),
        ("Violet", "#8b5cf6"),
        ("Pink", "#ff4f9a"),
        ("Emerald", "#20d6a3"),
        ("Gold", "#ffbd4a"),
    ]

    // Web GLYPHS string, verbatim (js/logo-background.js).
    static let glyphs = " .,:;irsXA253hMHGS#9B&@"

    static func isValidHex(_ value: String) -> Bool {
        guard value.hasPrefix("#"), value.count == 7 else { return false }
        return value.dropFirst().allSatisfy { $0.isHexDigit }
    }

    static func color(fromHex hex: String) -> Color? {
        guard isValidHex(hex) else { return nil }
        let clean = hex.dropFirst()
        var rgb: UInt64 = 0
        guard Scanner(string: String(clean)).scanHexInt64(&rgb) else { return nil }
        return Color(
            red: Double((rgb >> 16) & 0xff) / 255.0,
            green: Double((rgb >> 8) & 0xff) / 255.0,
            blue: Double(rgb & 0xff) / 255.0
        )
    }

    static func colorToHex(_ color: Color) -> String? {
        guard let nsColor = NSColor(color).usingColorSpace(.sRGB) else { return nil }
        let r = Int(round(nsColor.redComponent * 255))
        let g = Int(round(nsColor.greenComponent * 255))
        let b = Int(round(nsColor.blueComponent * 255))
        return String(format: "#%02x%02x%02x", r, g, b)
    }

    private static func rgb(of hex: String) -> (Double, Double, Double)? {
        guard isValidHex(hex) else { return nil }
        let clean = hex.dropFirst()
        var value: UInt64 = 0
        guard Scanner(string: String(clean)).scanHexInt64(&value) else { return nil }
        return (
            Double((value >> 16) & 0xff),
            Double((value >> 8) & 0xff),
            Double(value & 0xff)
        )
    }

    private static func hexString(r: Double, g: Double, b: Double) -> String {
        String(format: "#%02x%02x%02x", Int(round(r)), Int(round(g)), Int(round(b)))
    }

    private static func mix(_ first: String, _ second: String, _ amountSecond: Double) -> String {
        guard let a = rgb(of: first), let b = rgb(of: second) else { return first }
        return hexString(
            r: a.0 + (b.0 - a.0) * amountSecond,
            g: a.1 + (b.1 - a.1) * amountSecond,
            b: a.2 + (b.2 - a.2) * amountSecond
        )
    }

    // Web buildPalette, verbatim amounts (js/logo-background.js).
    static func buildPalette(baseHex: String) -> [Color] {
        let hexes = [
            mix(baseHex, "#020817", 0.88),
            mix(baseHex, "#020817", 0.72),
            mix(baseHex, "#020817", 0.53),
            mix(baseHex, "#020817", 0.31),
            baseHex,
            mix(baseHex, "#ffffff", 0.18),
            mix(baseHex, "#ffffff", 0.38),
            mix(baseHex, "#ffffff", 0.62),
            mix(baseHex, "#ffffff", 0.9),
        ]
        return hexes.compactMap { color(fromHex: $0) }
    }

    // Web PALETTES, verbatim (js/logo-background.js).
    static func productPalette(for product: ProductID) -> [Color] {
        let hexes: [String]
        switch product {
        case .vigiles:
            hexes = [
                "#062258", "#07357f", "#0750bc", "#4f7ec2",
                "#6a96d8", "#8ab4e8", "#a8c8f0", "#c8ddf8", "#eaf2ff",
            ]
        case .ignis:
            hexes = [
                "#3d0a08", "#5c1410", "#7f1d18", "#a32424",
                "#d92b2b", "#e85545", "#f07a68", "#ffa08e", "#ffd9d0",
            ]
        case .medicus:
            hexes = [
                "#0a2e12", "#123f1c", "#1e5429", "#2f6b3a",
                "#5da864", "#7cc47f", "#9ad69c", "#bfe8c2", "#e6f9e8",
            ]
        }
        return hexes.compactMap { color(fromHex: $0) }
    }
}
