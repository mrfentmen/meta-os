import AppKit
import AVKit
import SwiftUI

// Main window: product switcher and product identity on top, camera +
// controls + settings on the left, latest assessment + timeline on the
// right, and a status bar (backend state, sampler counters, measured
// latency, session log) along the bottom. Every status shown reflects
// real state — there are no decorative indicators.

struct ContentView: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        VStack(spacing: 0) {
            HeaderView(model: model)
            Divider()
            HSplitView {
                leftColumn
                    .frame(minWidth: 380, idealWidth: 440)
                rightColumn
                    .frame(minWidth: 420)
            }
            Divider()
            StatusBar(model: model)
            Divider()
            // Web parity: the web frontend carries this disclaimer as a
            // footer on every page. The native window had no equivalent
            // — its per-product limitations notice says what one
            // product never claims, but nothing in the window said the
            // whole app is a prototype that never contacts emergency
            // services, never dispatches or cites, and never identifies
            // anyone. A demo window without it could be read as an
            // operational system, so it sits below the status bar,
            // always visible, in the web footer's words.
            // UI-23: footer disclaimer at 13pt, the native
            // counterpart to the web .footer rule (13px, muted).
            // Until now the disclaimer used .caption (12pt), so it
            // read one point smaller than the web footer while the
            // Latest-panel notes (UI-21) already matched their own
            // 13px web rule. The size is the only change: the muted
            // color, the wrapping, the padding, and the wording —
            // the web footer's words verbatim — are untouched.
            Text("Experimental prototype for staged, consenting scenarios. Not an operational law-enforcement, fire-detection, or enforcement system. This app never contacts police or emergency services, performs no face recognition or identity inference, and never dispatches or cites automatically.")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
        }
        .frame(minWidth: 1020, minHeight: 660)
    }

    private var leftColumn: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                CameraPanel(model: model, camera: model.camera)
                StillImagePanel(model: model)
                VideoPanel(model: model)
                SettingsPanel(model: model)
            }
            .padding(12)
        }
    }

    private var rightColumn: some View {
        VStack(alignment: .leading, spacing: 10) {
            // UI-22: Latest-panel title at 15pt bold, the native
            // counterpart to the web .panel h2 rule (15px, weight
            // 700). Until now the title used .headline (17pt
            // semibold), so it read larger and one step lighter
            // than the web panel's title while the notes below it
            // (UI-21, 13pt) already matched their own web rule.
            // The size and weight are the only change: the wording,
            // the header trait, and the 10pt column spacing — the
            // native counterpart to the web h2's 10px bottom margin
            // — are untouched.
            Text("Latest assessment")
                .font(.system(size: 15, weight: .bold))
                .accessibilityAddTraits(.isHeader)
            if let note = model.displayedAssessmentNote {
                // UI-21: Latest-panel notes at 13pt, the native
                // counterpart to the web .note rule (13px, muted).
                // Until now both notes in this panel used .callout
                // (16pt), so the redisplayed-assessment note and the
                // observable-evidence note below both read larger
                // than the web panel's notes while the assessment
                // itself (UI-20 summary, UI-19 subline) already
                // matched its own web rules. The size is the only
                // change: the muted color, the wrapping, and the
                // wording are untouched, and the section title
                // keeps its headline size — the web panel title is
                // its own rule, not a note.
                Text(note)
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            if let assessment = model.displayedAssessment {
                ScrollView {
                    AssessmentView(response: assessment)
                }
                .frame(maxHeight: 320)
            } else if model.requestInFlight {
                // UI-24: Latest-panel placeholders at 13pt mono, the
                // native counterpart to the web #latest-assessment
                // container, which always carries class mono-block
                // (13px, ui-monospace stack) — so the waiting, error,
                // and no-assessment strings inherit that size and
                // face on the web. Until now all three native
                // placeholders were plain Text at the default body
                // size, so they read larger and in the default face
                // while the assessment itself (UI-20 summary, UI-19
                // subline, UI-15 processing line) already matched
                // its own web rules. Size and face are the only
                // change, following the UI-15 mono precedent
                // (.system monospaced design as the stand-in for
                // the web's ui-monospace stack): the waiting text
                // keeps its secondary color and combined VoiceOver
                // label, the error keeps its red color and wrapping,
                // and the no-assessment text keeps its secondary
                // color. No wording changes.
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                    Text("Waiting for the first assessment…")
                        .font(.system(size: 13, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                .accessibilityElement(children: .combine)
                .accessibilityLabel("Waiting for the first assessment")
            } else if case .error(let message) = model.backendStatus {
                Text(message)
                    .font(.system(size: 13, design: .monospaced))
                    .foregroundStyle(.red)
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                Text("No assessment received yet.")
                    .font(.system(size: 13, design: .monospaced))
                    .foregroundStyle(.secondary)
            }
            // Web parity: the web Latest panel carries this note under
            // the assessment, and the native panel had nothing
            // equivalent — a bare assessment with no reminder that it
            // describes observable evidence only could be read as more
            // than it claims. Same words as the web panel; the
            // limitations notice it points to sits in the header above.
            // UI-21: the note reads at 13pt, the native counterpart
            // to the web .note rule (13px, muted) — see the
            // displayed-assessment note above for the same mirror.
            Text("Assessments describe observable evidence only. Each product's limitations notice (above) states what its assessments never claim.")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            Divider()
            TimelineView(model: model)
        }
        .padding(12)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}

// MARK: - Header: product switcher + identity + limitations

private struct HeaderView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // IGNIS-UI-40: Product label at 13pt, the native
            // counterpart to the web label rule (13px, muted).
            // Until now the label used .caption (12pt), so it read
            // one point smaller than the web labels while the
            // endpoint and scenario labels (UI-33) already matched
            // their own 13px web rule. The size is the only change:
            // the muted color and the wording are untouched.
            Text("Product")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
            Picker("Product", selection: $model.selectedProduct) {
                ForEach(ProductID.allCases) { product in
                    Text(product.config.displayName).tag(product)
                }
            }
            .pickerStyle(.segmented)
            .labelsHidden()
            .accessibilityLabel("Product")
            .accessibilityHint("Switches the product for the next assessment. Earlier log entries keep the product they were assessed under.")

            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Circle()
                    .fill(accentColor)
                    .frame(width: 9, height: 9)
                    .accessibilityHidden(true)
                // IGNIS-UI-41: department at 13pt and tagline at
                // 14pt, the native counterparts to the web
                // .product-department rule (13px, muted) and the
                // .product-tagline rule (14px). Until now both used
                // .subheadline (15pt), so the department read two
                // points larger and the tagline one point larger
                // than the web identity row while the Product label
                // (UI-40) already matched its own 13px web rule.
                // The sizes are the only change: the department
                // keeps its semibold weight, the tagline keeps its
                // muted color, and the flame chip carries its own
                // UI-42 rule below.
                Text(model.config.department)
                    .font(.system(size: 13))
                    .fontWeight(.semibold)
                Text(model.config.tagline)
                    .font(.system(size: 14))
                    .foregroundStyle(.secondary)
                // R2: Ignis-only flame chip — the header's accent dot is
                // shared across products, so Ignis gets its own flame
                // marker in the identity row, in the product accent.
                // IGNIS-UI-42: flame chip at 13pt bold with 0.52pt
                // tracking, the native counterpart to the web
                // .product-badge rule (13px, weight 700,
                // letter-spacing 0.04em = 0.52pt at 13pt) — the
                // header's accent pill. Until now the chip used
                // .caption (12pt) semibold with no tracking, so it
                // read one point smaller, one step lighter, and
                // tighter than the web badge while the department
                // and tagline beside it (UI-41) already matched
                // their own web rules. Type is the only change:
                // the accent color, padding, corner radius, icon,
                // and wording are untouched.
                if model.selectedProduct == .ignis {
                    Label("Flame", systemImage: "flame.fill")
                        .font(.system(size: 13))
                        .fontWeight(.bold)
                        .tracking(0.52)
                        .foregroundStyle(accentColor)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(accentColor.opacity(0.12))
                        .cornerRadius(999)
                }
            }

            Text(model.config.limitations)
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
                .padding(8)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.secondary.opacity(0.08))
                // R2: accent leading rule, matching the web
                // .limitations border-left in --accent — red on Ignis.
                .overlay(alignment: .leading) {
                    Rectangle()
                        .fill(accentColor)
                        .frame(width: 3)
                }
                // UI-8: rounded box corners, the counterpart to the
                // UI-7 assessment-panel clip. The box's background used
                // to be rounded with cornerRadius(6), but the overlay
                // sits after that modifier, so the rule was never cut
                // to the rounded edge and ran square past the box's
                // corners at the leading edge. The clip sits after the
                // overlay, so the background and the rule share the
                // same 6px rounded edge; it changes no color, rule,
                // or content.
                .clipShape(RoundedRectangle(cornerRadius: 6))
        }
        .padding(12)
    }

    private var accentColor: Color {
        switch model.config.accentColorName {
        case "blue": return .blue
        case "red": return .red
        case "green": return .green
        default: return .accentColor
        }
    }
}

// MARK: - Camera panel

private struct CameraPanel: View {
    @ObservedObject var model: AppModel
    @ObservedObject var camera: CameraService

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ZStack(alignment: .topLeading) {
                CameraPreviewView(session: camera.session)
                    .aspectRatio(16.0 / 9.0, contentMode: .fit)
                    .frame(minHeight: 240)
                    .background(Color.black)
                    .cornerRadius(6)
                    .accessibilityLabel("Live camera preview")
                    .accessibilityValue(cameraAccessibilityValue)
                if camera.state == .running {
                    // IGNIS-UI-39: CAMERA LIVE label at 0.96pt tracking,
                    // the native counterpart to the web .camera-indicator
                    // rule (12px, weight 700, letter-spacing 0.08em).
                    // Until now the label used .caption (12pt) bold, so
                    // it already matched the web size and weight, but
                    // it carried no tracking, so its letters read tighter
                    // than the web indicator's letterspaced capitals
                    // while the review flag (UI-16) already matched its
                    // own 0.05em web tracking. The tracking is 0.08em of
                    // the label's own 12pt size (0.96pt). The tracking is
                    // the only change: the caption size, the bold weight,
                    // the white text, the red badge, and the wording are
                    // untouched.
                    Label("CAMERA LIVE", systemImage: "record.circle.fill")
                        .font(.caption)
                        .fontWeight(.bold)
                        .tracking(0.96)
                        .foregroundStyle(.white)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.red)
                        .cornerRadius(4)
                        .padding(8)
                        .accessibilityLabel("Camera live")
                }
            }

            stateText

            // Camera facing (web parity): the web frontend's picker
            // offers front vs rear as a preference, never a requirement.
            // The native picker does the same — CameraService.setFacing
            // records the choice while off and restarts the capture
            // while live, and falls back to the default camera when no
            // device sits at the chosen position, so a rear pick on a
            // single-camera Mac still shows the front camera rather
            // than failing. The note below says so in plain words, so
            // the picker never implies a second camera exists.
            VStack(alignment: .leading, spacing: 4) {
                Picker("Camera facing", selection: Binding(
                    get: { camera.facing },
                    set: { camera.setFacing($0) }
                )) {
                    ForEach(CameraService.Facing.allCases, id: \.self) { facing in
                        Text(facing.label).tag(facing)
                    }
                }
                .pickerStyle(.menu)
                .accessibilityLabel("Camera facing")
                .accessibilityHint("Front or rear camera. A preference, not a requirement: a Mac with only one camera uses that camera either way.")
                // UI-28: camera facing note at 13pt, the native
                // counterpart to the web .note rule (13px, muted).
                // Until now the note used .caption (12pt), so it read
                // one point smaller than the web panel's facing note
                // while the still-image and video intros (UI-25,
                // UI-26) and the header limitations (UI-27) already
                // matched their own 13px web rules. The size is the
                // only change: the muted color, the wrapping, and
                // the wording are untouched, and the picker above
                // keeps its menu style.
                Text("A facing is a preference, not a requirement: a Mac with only one camera uses that camera whichever facing is chosen.")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if model.analysisRunning {
                Label("ANALYSIS ACTIVE — sampling one frame every \(model.intervalSeconds) s", systemImage: "dot.radiowaves.left.and.right")
                    .font(.caption)
                    .fontWeight(.bold)
                    .foregroundStyle(.orange)
                    .accessibilityLabel("Analysis active, sampling one frame every \(model.intervalSeconds) seconds")
            }

            HStack(spacing: 8) {
                Button("Start Camera") { model.startCamera() }
                    .disabled(camera.state == .running || camera.state == .requestingPermission)
                // Stop stays enabled while permission is requested,
                // not just while the camera is running: stopCamera is
                // the cancel for a permission wait — CameraService.stop
                // bumps the start generation, so the permission
                // callback stands down instead of starting a camera
                // the user just stopped — but the button used to be
                // disabled exactly during that wait, so the only way
                // to abandon it was Reset Session, which also clears
                // the latest assessment and the timeline. A wait
                // cancelled this way leaves the view alone, matching
                // the web frontend's Stop button during its pending
                // start.
                Button("Stop Camera") { model.stopCamera() }
                    .disabled(camera.state != .running && camera.state != .requestingPermission)
                Button("Start Analysis") { model.startAnalysis() }
                    .disabled(camera.state != .running || model.analysisRunning)
                    .accessibilityHint("Starts sampling one frame every \(model.intervalSeconds) seconds and sending each frame to the assessment endpoint.")
                Button("Stop Analysis") { model.stopAnalysis() }
                    .disabled(!model.analysisRunning)
                Button("Reset Session") { model.resetSession() }
                    // Honest label, matching AppModel.resetSession: Reset
                    // clears only the on-screen preview, latest
                    // assessment, and timeline. The saved session log
                    // is kept, so the timeline comes back on relaunch
                    // from that log until Clear Log removes it. The old
                    // hint claimed Reset cleared the session log, which
                    // was false — a VoiceOver user would have believed
                    // the log was gone when it was not.
                    .accessibilityHint("Stops the camera and analysis and clears the on-screen preview and timeline. The saved session log is kept — use Clear Log to remove it.")
            }

            // UI-29: camera product-guidance note at 13pt, the native
            // counterpart to the web .note rule (13px, muted).
            // Until now the note used .caption (12pt), so it read
            // one point smaller than the web panel's product
            // guidance while the facing note (UI-28) and the
            // still-image and video intros (UI-25, UI-26) already
            // matched their own 13px web rules. The size is the
            // only change: the muted color, the wrapping, and
            // the per-product wording are untouched.
            Text(model.config.inputGuidance)
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    /// Plain-words camera state for VoiceOver, mirroring the on-screen
    /// state text. The preview itself carries no assessment information.
    private var cameraAccessibilityValue: String {
        switch camera.state {
        case .idle: return "Camera off"
        case .requestingPermission: return "Waiting for camera permission"
        case .running: return "Camera live"
        case .stopped: return "Camera stopped"
        case .denied: return "Camera permission denied"
        case .noCamera: return "No camera found"
        case .failed(_): return "Camera error"
        }
    }

    // UI-35: camera state texts at 13pt, the native counterparts
    // to the web #camera-state note (13px, muted or red). Until
    // now the state lines carried no font at all, so they read at
    // the default body size, larger than the web panel's state
    // line while the camera-facing note (UI-28) and the
    // product-guidance note (UI-29) already matched their own
    // 13px web rules. The size is the only change: the muted
    // color, the red error color, the wrapping on the denied
    // and failed lines, and the wording are untouched.
    @ViewBuilder
    private var stateText: some View {
        switch camera.state {
        case .idle:
            Text("Camera is off.")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
        case .requestingPermission:
            Text("Waiting for camera permission…")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
        case .running:
            Text("Camera is live. No frames are sent anywhere until analysis is started.")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
        case .stopped:
            Text("Camera stopped.")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
        case .denied:
            Text("Camera permission denied. Grant access in System Settings → Privacy & Security → Camera, then start the camera again.")
                .font(.system(size: 13))
                .foregroundStyle(.red)
                .fixedSize(horizontal: false, vertical: true)
        case .noCamera:
            Text("No camera was found on this Mac.")
                .font(.system(size: 13))
                .foregroundStyle(.red)
        case .failed(let message):
            Text("Camera error: \(message)")
                .font(.system(size: 13))
                .foregroundStyle(.red)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

// MARK: - Still image panel (web parity)

private struct StillImagePanel: View {
    @ObservedObject var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // UI-36: still-image title at 15pt bold, the native
            // counterpart to the web .panel h2 rule (15px, weight
            // 700). Until now the title used .headline (17pt
            // semibold), so it read larger and one step lighter
            // than the web panel's title while the Latest title
            // (UI-23) and the timeline title (UI-34) already
            // matched their own 15px web rules. The size and
            // weight are the only change: the wording is untouched.
            Text("Still image")
                .font(.system(size: 15, weight: .bold))
            // UI-25: still-image intro note at 13pt, the native
            // counterpart to the web .note rule (13px, muted).
            // Until now the intro used .caption (12pt), so it read
            // one point smaller than the web panel's intro while
            // the Latest-panel notes (UI-21) and footer (UI-23)
            // already matched their own 13px web rules. The size
            // is the only change: the muted color, the wrapping,
            // and the wording are untouched, and the panel title
            // keeps its headline size.
            Text("For prerecorded or photographed scenes — the input Ignis and Sanitas demos use when a live camera is not the source. The image is sent once to the assessment endpoint, under the product selected above, and is logged exactly like a live frame. It is not stored by this app.")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            if let image = model.stillImage {
                Image(nsImage: image)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(maxHeight: 240)
                    .background(Color.black)
                    .cornerRadius(6)
                    .accessibilityLabel("Chosen still image preview")
            }

            // UI-30: still-image state texts at 13pt, the native
            // counterparts to the web #image-state and
            // #image-assessing notes (13px, muted). Until now the
            // ready, no-image, error, and assessing lines used
            // .caption (12pt), so they read one point smaller than
            // the web panel's state lines while the still-image
            // intro (UI-25) already matched its own 13px web rule.
            // The size is the only change: the muted color, the
            // red error color, the wrapping, and the wording are
            // untouched.
            if let name = model.stillImageName {
                Text("Image ready: \(name). Tap “Assess this image” to send it once.")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                Text("No image chosen.")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
            }

            if let error = model.stillImageError {
                Text(error)
                    .font(.system(size: 13))
                    .foregroundStyle(.red)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack(spacing: 8) {
                Button("Choose Image") { model.chooseStillImage() }
                Button("Assess this image") { model.assessStillImage() }
                    .disabled(model.stillImage == nil || model.stillImageAssessing)
                    .accessibilityHint("Sends the chosen image once to the assessment endpoint.")
                Button("Clear") { model.clearStillImage() }
                    .disabled(model.stillImage == nil && model.stillImageError == nil)
            }
            if model.stillImageAssessing {
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                    Text("Sending still image…")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }
            }
        }
    }
}

// MARK: - Prerecorded video panel (web parity)

private struct VideoPanel: View {
    @ObservedObject var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // UI-36: video title at 15pt bold, the native
            // counterpart to the web .panel h2 rule (15px, weight
            // 700). Until now the title used .headline (17pt
            // semibold), so it read larger and one step lighter
            // than the web panel's title while the Latest title
            // (UI-23), the timeline title (UI-34), and the
            // still-image title above already matched their own
            // 15px web rules. The size and weight are the only
            // change: the wording is untouched.
            Text("Prerecorded video")
                .font(.system(size: 15, weight: .bold))
            // UI-26: video intro note at 13pt, the native
            // counterpart to the web .note rule (13px, muted).
            // Until now the intro used .caption (12pt), so it read
            // one point smaller than the web panel's intro while
            // the still-image intro (UI-25) already matched its own
            // 13px web rule. The size is the only change: the muted
            // color, the wrapping, and the wording are untouched,
            // and the panel title keeps its headline size.
            Text("For a recorded clip when neither a live camera nor a still image is the source. Play the clip, pause on the frame you want assessed, and tap “Assess this frame”: only that one frame is sent to the assessment endpoint, under the product selected above, and logged exactly like a live frame. The whole video is never sent, and it is not stored by this app.")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            if let player = model.videoPlayer {
                VideoPlayer(player: player)
                    .frame(minHeight: 240)
                    .background(Color.black)
                    .cornerRadius(6)
                    .accessibilityLabel("Prerecorded video player")
            }

            // UI-31: video state texts at 13pt, the native
            // counterparts to the web #video-state and
            // #video-assessing notes (13px, muted). Until now the
            // ready, no-video, error, and assessing lines used
            // .caption (12pt), so they read one point smaller than
            // the web panel's state lines while the video intro
            // (UI-26) already matched its own 13px web rule.
            // The size is the only change: the muted color, the
            // red error color, the wrapping, and the wording are
            // untouched.
            if let name = model.videoName {
                Text("Video ready: \(name). Play it, pause on the frame you want assessed, and tap “Assess this frame”. Only that frame is sent; the video is not stored by this app.")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                Text("No video chosen.")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
            }

            if let error = model.videoError {
                Text(error)
                    .font(.system(size: 13))
                    .foregroundStyle(.red)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack(spacing: 8) {
                Button("Choose Video") { model.chooseVideo() }
                Button("Assess this frame") { model.assessVideoFrame() }
                    .disabled(model.videoPlayer == nil || model.videoAssessing)
                    .accessibilityHint("Sends only the frame showing at the paused playback position to the assessment endpoint.")
                Button("Clear") { model.clearVideo() }
                    .disabled(model.videoPlayer == nil && model.videoError == nil)
            }
            if model.videoAssessing {
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                    Text("Sending video frame…")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }
            }
        }
    }
}

// MARK: - Settings

private struct SettingsPanel: View {
    @ObservedObject var model: AppModel

    var body: some View {
        GroupBox("Settings") {
            VStack(alignment: .leading, spacing: 10) {
                VStack(alignment: .leading, spacing: 4) {
                    // UI-33: endpoint label at 13pt, the native
                    // counterpart to the web label rule (13px, muted).
                    // Until now the label used .caption (12pt), so it
                    // read one point smaller than the web panel's
                    // endpoint label while the backend-health and
                    // sampling-disclosure lines (UI-32) already matched
                    // their own 13px web rules. The size is the only
                    // change: the muted color and the wording are
                    // untouched.
                    Text("Assessment endpoint")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                    TextField("Assessment endpoint", text: $model.endpoint)
                        .textFieldStyle(.roundedBorder)
                        .labelsHidden()
                        .accessibilityLabel("Assessment endpoint")
                }

                VStack(alignment: .leading, spacing: 4) {
                    Button("Check Backend Health") { model.checkBackendHealth() }
                        .disabled(model.healthChecking)
                        .accessibilityHint("Contacts the server's health route only. It never sends a frame and never returns an assessment.")
                    // UI-32: backend-health line at 13pt, the native
                    // counterpart to the web .note rule (13px, muted).
                    // Until now the line used .caption (12pt), so it
                    // read one point smaller than the web panel's
                    // backend-health note while the header limitations
                    // (UI-27) already matched their own 13px web rule.
                    // The size is the only change: the muted color,
                    // the wrapping, and the accessibility label are
                    // untouched.
                    Text(model.backendHealth)
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                        .accessibilityLabel("Backend health: \(model.backendHealth)")
                }

                Stepper(value: $model.intervalSeconds, in: 1...60) {
                    Text("Sample one frame every \(model.intervalSeconds) second\(model.intervalSeconds == 1 ? "" : "s")")
                }

                // UI-32: sampling-disclosure line at 13pt, the native
                // counterpart to the web .note rule (13px, muted).
                // Until now the line used .caption (12pt), so it read
                // one point smaller than the web panel's sampling
                // disclosure note while the backend-health line above
                // now matches its own 13px web rule. The size is the
                // only change: the muted color, the wrapping, and the
                // wording are untouched.
                Text("Analysis uses sampled frames: one frame every \(model.intervalSeconds) second\(model.intervalSeconds == 1 ? "" : "s") is sent to the assessment endpoint. This is not continuous video analysis, and events between samples are not seen by the system.")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                // Scenario picker (web parity): the current product's
                // evaluation scenarios as a dropdown, written to the
                // session log as ground-truth context. Switching
                // products resets the pick in AppModel, so one
                // product's scenario can never label another's entries.
                VStack(alignment: .leading, spacing: 4) {
                    Picker("Scenario (optional, written to the evaluation log as ground-truth context)", selection: $model.selectedScenario) {
                        Text("— no label —").tag("")
                        ForEach(model.config.scenarios, id: \.self) { scenario in
                            Text(scenario).tag(scenario)
                        }
                    }
                    .pickerStyle(.menu)
                    .accessibilityLabel("Scenario")
                    .accessibilityHint("Optional scenario for the current product, recorded in the session log for evaluation. Switching products resets this choice.")
                    // UI-33: custom-scenario label at 13pt, the native
                    // counterpart to the web label rule (13px, muted).
                    // Until now the label used .caption (12pt), so it
                    // read one point smaller than the web panel's
                    // scenario label while the endpoint label above
                    // now matches its own 13px web rule. The size is
                    // the only change: the muted color and the wording
                    // are untouched.
                    Text("Or a custom scenario label (overrides the choice above)")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                    TextField("Scenario label", text: $model.scenarioLabel)
                        .textFieldStyle(.roundedBorder)
                        .labelsHidden()
                        .accessibilityLabel("Scenario label")
                        .accessibilityHint("Optional custom label recorded in the session log for evaluation. It overrides the scenario choice above.")
                }

                // UI-38: categories line at 13pt, the native
                // counterpart to the web .note rule (13px, muted).
                // Until now the line used .caption (12pt), so it read
                // one point smaller than the web panel's Settings
                // notes while the backend-health and sampling-
                // disclosure lines (UI-32) and the endpoint and
                // scenario labels (UI-33) already matched their own
                // 13px web rules. The size is the only change: the
                // muted color, the wrapping, and the wording are
                // untouched.
                Text("Categories the server may return: \(model.config.categories.joined(separator: ", ")).")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(4)
        }
    }
}

// MARK: - Status bar

private struct StatusBar: View {
    @ObservedObject var model: AppModel

    var body: some View {
        HStack(spacing: 12) {
            statusIndicator
            Text(model.backendStatus.message)
                .font(.callout)
                .lineLimit(2)
            Spacer()
            if model.requestInFlight {
                ProgressView()
                    .controlSize(.small)
                Text("Assessment request in flight…")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
            if let lastRoundTripMs = model.lastRoundTripMs {
                Text("Last round trip: \(lastRoundTripMs) ms (client-measured)")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
            Text("Ticks: \(model.samplerStats.ticks) · Sent: \(model.samplerStats.sent) · Skipped (request in flight): \(model.samplerStats.skipped) · Failed: \(model.samplerStats.failed)")
                .font(.callout)
                .foregroundStyle(.secondary)
            Text("Session log entries: \(model.logCount)")
                .font(.callout)
                .foregroundStyle(.secondary)
            Button("Export Log") { model.exportLog() }
            Button("Clear Log") { model.clearLog() }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
    }

    private var statusIndicator: some View {
        Circle()
            .fill(statusColor)
            .frame(width: 10, height: 10)
            // Decorative only: the backend status text next to it
            // already states the state in words.
            .accessibilityHidden(true)
    }

    private var statusColor: Color {
        switch model.backendStatus {
        case .unknown: return .gray
        case .connected: return .green
        case .error: return .red
        }
    }
}
