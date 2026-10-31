import SwiftUI

// LOGO-NATIVE-3 (Del direction, Oct 30): the native loop is now a
// real port of the web canvas renderer (js/logo-background.js) —
// the same infinity-ribbon path, ribbon surface, lighting, glyph
// ramp, and palettes, drawn into a SwiftUI Canvas. It replaces the
// LOGO-NATIVE-1 glyph field, which only scrolled characters by
// formula and never drew the loop at all. The web LOGO-3 aspect
// rule is carried over: the Y projection is X times the canvas
// aspect, recomputed from the actual view size every frame, so
// the loop keeps its shape in any window (the web's fixed 1.76
// was only right at 16:9 and stretched the loop elsewhere).
// LOGO-NATIVE-1/2 contracts are unchanged: the Logo panel's color,
// rotation speed slider, and pause button drive this loop under
// the web panel's own storage keys (meta-trio-logo-color,
// meta-trio-logo-speed, meta-trio-logo-paused). Speed is a
// percent, 0 to 100, default 25: 25% is the web background's usual
// slow drift, 0% is still, 100% is four times that pace. Pause
// holds the loop on its last frame; Resume restarts it from that
// frame, never from the start. A speed change or a pause/resume
// re-bases the phase anchor, so neither jumps the loop, and a
// clock jump backwards never drives the phase negative. A
// user-picked color wins over product switches until Reset,
// reduced motion renders one still frame, and the view ignores
// pointer input and is hidden from accessibility. The one
// deliberate difference from the web: the web's specular pass
// glows through a canvas shadow; here the specular cells are
// simply overdrawn in the specular color, no shadow. No Swift
// toolchain exists in this sandbox, so this is checked by
// inspection and by the static tests in
// tests/native-logo-animation.test.mjs and
// tests/native-logo-color.test.mjs; a Mac build run is the real
// verification. The one-argument onChange form below is
// deliberate: it is the form this package already builds with.

private struct RibbonVec {
    var x: Double
    var y: Double
    var z: Double

    func normalized() -> RibbonVec {
        let length = (x * x + y * y + z * z).squareRoot()
        let safe = length == 0 ? 1 : length
        return RibbonVec(x: x / safe, y: y / safe, z: z / safe)
    }
}

private struct RibbonSample {
    var x: Double
    var y: Double
    var z: Double
    var nx: Double
    var ny: Double
    var nz: Double
    var colorWave: Double
}

struct LogoLoopView: View {
    @AppStorage("meta-trio-logo-color") private var customHex: String = ""
    @AppStorage("meta-trio-logo-speed") private var speedPercent: Int = 25
    @AppStorage("meta-trio-logo-paused") private var paused: Bool = false
    @ObservedObject var model: AppModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var anchorDate = Date()
    @State private var anchorPhase = 0.0

    // Web renderer constants (js/logo-background.js), verbatim
    // except SCALE, which carries the web LOGO-3 fit (0.9, so the
    // whole loop fits inside the view, never a crop).
    private static let gridW = 110
    private static let gridH = 46
    private static let ringPoints = 240
    private static let cameraDistance = 80.0
    private static let loopX = 24.5
    private static let loopY = 26.5
    private static let loopZ = 8.2
    private static let ribbonWidth = 3.65
    private static let ribbonThickness = 0.72
    private static let xProjection = 0.99
    private static let scale = 0.9
    // Radians of Y rotation per phase unit: the web drift is
    // 0.0022 rad per 60fps frame (0.132 rad/s) at the usual pace,
    // and the usual pace below is 2 phases a second, so one phase
    // is 0.066 rad — a full turn in about 48 seconds, like the web.
    private static let radiansPerPhase = 0.066
    private static let angleX = -0.045
    private static let initialAngleY = 0.045

    private static let glyphArray: [Character] = Array(LogoColor.glyphs)
    private static let lightDirection = RibbonVec(x: -0.38, y: 0.62, z: 0.91).normalized()
    private static let halfVector: RibbonVec = {
        let light = LogoLoopView.lightDirection
        return RibbonVec(x: light.x, y: light.y, z: light.z + 1).normalized()
    }()
    private static let surfaceSamples: [RibbonSample] = LogoLoopView.buildSurface()

    private var palette: [Color] {
        if LogoColor.isValidHex(customHex) {
            return LogoColor.buildPalette(baseHex: customHex.lowercased())
        }
        return LogoColor.productPalette(for: model.selectedProduct)
    }

    // Web specular colors, verbatim (js/logo-background.js
    // SPECULARS). A custom color's specular is its own palette's
    // lightest step, which is the web's mix toward white at 0.9.
    private var specularColor: Color {
        if LogoColor.isValidHex(customHex) {
            return palette.last ?? .white
        }
        switch model.selectedProduct {
        case .vigiles:
            return LogoColor.color(fromHex: "#eafcff") ?? .white
        case .ignis:
            return LogoColor.color(fromHex: "#ffe8e0") ?? .white
        case .medicus:
            return LogoColor.color(fromHex: "#e8fbe9") ?? .white
        }
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

    private func runningPhase(at date: Date) -> Double {
        if reduceMotion { return 0 }
        let elapsed = max(0, date.timeIntervalSince(anchorDate))
        return anchorPhase + elapsed * phasesPerSecond
    }

    private func phase(at date: Date) -> Double {
        if paused { return anchorPhase }
        return runningPhase(at: date)
    }

    // The web ribbon path (loopPoint in js/logo-background.js).
    private static func loopPoint(_ u: Double) -> RibbonVec {
        let s = sin(u)
        let c = cos(u)
        return RibbonVec(
            x: loopX * s * (1 + 0.018 * s),
            y: loopY * s * c * (1 + 0.025 * s),
            z: loopZ * c + 0.65 * sin(2 * u)
        )
    }

    // The web ribbon surface (buildSurface in
    // js/logo-background.js): broad face samples on both sides,
    // then rounded edge samples, each with its lighting normal.
    private static func buildSurface() -> [RibbonSample] {
        var samples: [RibbonSample] = []
        let frameStep = 0.0025
        let widthSteps = 18
        let edgeSteps = 9
        for j in 0..<ringPoints {
            let u = (Double(j) / Double(ringPoints)) * Double.pi * 2
            let center = loopPoint(u)
            let before = loopPoint(u - frameStep)
            let after = loopPoint(u + frameStep)
            let tangent = RibbonVec(
                x: after.x - before.x,
                y: after.y - before.y,
                z: after.z - before.z
            ).normalized()
            var nx = -tangent.y
            var ny = tangent.x
            let nz = 0.0
            let nLength = (nx * nx + ny * ny).squareRoot()
            let safeLength = nLength == 0 ? 1 : nLength
            nx /= safeLength
            ny /= safeLength
            let binormal = RibbonVec(
                x: tangent.y * nz - tangent.z * ny,
                y: tangent.z * nx - tangent.x * nz,
                z: tangent.x * ny - tangent.y * nx
            ).normalized()
            let localWidth =
                ribbonWidth * (0.9 + 0.1 * pow(abs(sin(u)), 1.15))
            let colorWave = 0.5 + 0.5 * sin(u + 0.65)
            for k in 0...widthSteps {
                let across = -1 + (2 * Double(k)) / Double(widthSteps)
                let crown = 1 - 0.045 * across * across
                for side in [-1.0, 1.0] {
                    let faceNormal = RibbonVec(
                        x: side * binormal.x - 0.09 * across * nx,
                        y: side * binormal.y - 0.09 * across * ny,
                        z: side * binormal.z - 0.09 * across * nz
                    ).normalized()
                    samples.append(RibbonSample(
                        x: center.x + localWidth * across * nx + side * ribbonThickness * crown * binormal.x,
                        y: center.y + localWidth * across * ny + side * ribbonThickness * crown * binormal.y,
                        z: center.z + localWidth * across * nz + side * ribbonThickness * crown * binormal.z,
                        nx: faceNormal.x,
                        ny: faceNormal.y,
                        nz: faceNormal.z,
                        colorWave: colorWave
                    ))
                }
            }
            for edgeSide in [-1.0, 1.0] {
                for e in 0..<edgeSteps {
                    let theta = -Double.pi / 2 + (Double.pi * Double(e)) / Double(edgeSteps - 1)
                    let st = sin(theta)
                    let ct = cos(theta)
                    let edgeNormal = RibbonVec(
                        x: edgeSide * ct * nx + st * binormal.x,
                        y: edgeSide * ct * ny + st * binormal.y,
                        z: edgeSide * ct * nz + st * binormal.z
                    ).normalized()
                    samples.append(RibbonSample(
                        x: center.x + localWidth * edgeSide * nx + ribbonThickness * st * binormal.x,
                        y: center.y + localWidth * edgeSide * ny + ribbonThickness * st * binormal.y,
                        z: center.z + localWidth * edgeSide * nz + ribbonThickness * st * binormal.z,
                        nx: edgeNormal.x,
                        ny: edgeNormal.y,
                        nz: edgeNormal.z,
                        colorWave: colorWave
                    ))
                }
            }
        }
        return samples
    }

    private static func clamp(_ value: Double, _ minValue: Double, _ maxValue: Double) -> Double {
        max(minValue, min(maxValue, value))
    }

    // One frame of the web renderer (renderFrame in
    // js/logo-background.js): project every surface sample into
    // the glyph grid with a depth buffer, shade by the same
    // diffuse + specular + rim terms, then draw the winning
    // glyph per cell, with the specular cells overdrawn.
    private func drawFrame(context: inout GraphicsContext, size: CGSize, phase: Double) {
        let palette = self.palette
        let glyphs = Self.glyphArray
        guard !palette.isEmpty, glyphs.count > 1, size.width > 0, size.height > 0 else { return }

        let gridW = Self.gridW
        let gridH = Self.gridH
        let cellCount = gridW * gridH
        var glyphBuffer = [UInt8](repeating: 0, count: cellCount)
        var colorBuffer = [UInt8](repeating: 0, count: cellCount)
        var specBuffer = [Double](repeating: 0, count: cellCount)
        var zBuffer = [Double](repeating: -Double.infinity, count: cellCount)

        // LOGO-3 aspect rule: Y projection follows the real
        // canvas aspect, recomputed from this frame's size.
        let yProjection = Self.xProjection * (size.width / size.height)
        let angleY = Self.initialAngleY + phase * Self.radiansPerPhase
        let angleX = Self.angleX
        let cosY = cos(angleY)
        let sinY = sin(angleY)
        let cosX = cos(angleX)
        let sinX = sin(angleX)
        let light = Self.lightDirection
        let half = Self.halfVector

        for p in Self.surfaceSamples {
            let x1 = p.x * cosY + p.z * sinY
            let z1 = -p.x * sinY + p.z * cosY
            let nx1 = p.nx * cosY + p.nz * sinY
            let nz1 = -p.nx * sinY + p.nz * cosY
            let y2 = p.y * cosX - z1 * sinX
            let z2 = p.y * sinX + z1 * cosX
            let ny2 = p.ny * cosX - nz1 * sinX
            let nz2 = p.ny * sinX + nz1 * cosX
            let depth = Self.cameraDistance - z2
            if depth <= 1 { continue }
            let invDepth = 1 / depth
            let xp = Int((Double(gridW) / 2 + x1 * Self.scale * invDepth * Double(gridW) * Self.xProjection).rounded())
            let yp = Int((Double(gridH) / 2 - y2 * Self.scale * invDepth * Double(gridH) * yProjection).rounded())
            if xp < 0 || xp >= gridW || yp < 0 || yp >= gridH { continue }
            let index = xp + yp * gridW
            if invDepth <= zBuffer[index] { continue }
            let diffuse = max(0, nx1 * light.x + ny2 * light.y + nz2 * light.z)
            let halfDot = max(0, nx1 * half.x + ny2 * half.y + nz2 * half.z)
            let specular = pow(halfDot, 28)
            let rimBase = 1 - min(1, abs(nz2))
            let rim = rimBase * rimBase
            let glyphBrightness = Self.clamp(
                0.13 + diffuse * 0.43 + specular * 0.92 + rim * 0.18, 0, 1)
            let glyphIndex = Int(Self.clamp(
                (glyphBrightness * Double(glyphs.count - 1)).rounded(),
                1, Double(glyphs.count - 1)))
            let colorBrightness = Self.clamp(
                0.12 + diffuse * 0.48 + specular * 0.73 + rim * 0.13 + p.colorWave * 0.1, 0, 1)
            let colorIndex = Int(Self.clamp(
                (colorBrightness * Double(palette.count - 1)).rounded(),
                0, Double(palette.count - 1)))
            zBuffer[index] = invDepth
            glyphBuffer[index] = UInt8(glyphIndex)
            colorBuffer[index] = UInt8(colorIndex)
            specBuffer[index] = specular
        }

        let cellWidth = size.width / Double(gridW)
        let cellHeight = size.height / Double(gridH)
        let fontSize = min(cellHeight * 1.01, cellWidth / 0.59)
        let font = Font.system(size: fontSize, weight: .bold, design: .monospaced)

        for c in 0..<cellCount {
            let glyphIndex = Int(glyphBuffer[c])
            if glyphIndex == 0 { continue }
            let character = glyphs[glyphIndex]
            if character == " " { continue }
            let point = CGPoint(
                x: (Double(c % gridW) + 0.5) * cellWidth,
                y: (Double(c / gridW) + 0.5) * cellHeight
            )
            context.draw(
                Text(String(character))
                    .font(font)
                    .foregroundColor(palette[Int(colorBuffer[c])]),
                at: point
            )
        }

        // Specular pass: the web overdraws its hottest cells in
        // the specular color under a glow; here they are simply
        // overdrawn in the specular color (see header note).
        for s in 0..<cellCount {
            if specBuffer[s] < 0.66 || glyphBuffer[s] == 0 { continue }
            let character = glyphs[Int(glyphBuffer[s])]
            if character == " " { continue }
            let point = CGPoint(
                x: (Double(s % gridW) + 0.5) * cellWidth,
                y: (Double(s / gridW) + 0.5) * cellHeight
            )
            context.draw(
                Text(String(character))
                    .font(font)
                    .foregroundColor(specularColor),
                at: point
            )
        }
    }

    var body: some View {
        SwiftUI.TimelineView(.animation) { timeline in
            let phase = phase(at: timeline.date)
            Canvas { context, size in
                drawFrame(context: &context, size: size, phase: phase)
            }
        }
        .opacity(0.5)
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
