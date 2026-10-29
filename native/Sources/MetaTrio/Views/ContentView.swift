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
            Text("Experimental prototype for staged, consenting scenarios. Not an operational law-enforcement, fire-detection, or enforcement system. This app never contacts police or emergency services, performs no face recognition or identity inference, and never dispatches or cites automatically.")
                .font(.caption)
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
            Text("Latest assessment")
                .font(.headline)
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
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                    Text("Waiting for the first assessment…")
                        .foregroundStyle(.secondary)
                }
                .accessibilityElement(children: .combine)
                .accessibilityLabel("Waiting for the first assessment")
            } else if case .error(let message) = model.backendStatus {
                Text(message)
                    .foregroundStyle(.red)
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                Text("No assessment received yet.")
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
            Text("Product")
                .font(.caption)
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
                Text(model.config.department)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                Text(model.config.tagline)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                // R2: Ignis-only flame chip — the header's accent dot is
                // shared across products, so Ignis gets its own flame
                // marker in the identity row, in the product accent.
                if model.selectedProduct == .ignis {
                    Label("Flame", systemImage: "flame.fill")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundStyle(accentColor)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(accentColor.opacity(0.12))
                        .cornerRadius(999)
                }
            }

            Text(model.config.limitations)
                .font(.caption)
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
                    Label("CAMERA LIVE", systemImage: "record.circle.fill")
                        .font(.caption)
                        .fontWeight(.bold)
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
                Text("A facing is a preference, not a requirement: a Mac with only one camera uses that camera whichever facing is chosen.")
                    .font(.caption)
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

            Text(model.config.inputGuidance)
                .font(.caption)
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

    @ViewBuilder
    private var stateText: some View {
        switch camera.state {
        case .idle:
            Text("Camera is off.")
                .foregroundStyle(.secondary)
        case .requestingPermission:
            Text("Waiting for camera permission…")
                .foregroundStyle(.secondary)
        case .running:
            Text("Camera is live. No frames are sent anywhere until analysis is started.")
                .foregroundStyle(.secondary)
        case .stopped:
            Text("Camera stopped.")
                .foregroundStyle(.secondary)
        case .denied:
            Text("Camera permission denied. Grant access in System Settings → Privacy & Security → Camera, then start the camera again.")
                .foregroundStyle(.red)
                .fixedSize(horizontal: false, vertical: true)
        case .noCamera:
            Text("No camera was found on this Mac.")
                .foregroundStyle(.red)
        case .failed(let message):
            Text("Camera error: \(message)")
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
            Text("Still image")
                .font(.headline)
            Text("For prerecorded or photographed scenes — the input Ignis and Sanitas demos use when a live camera is not the source. The image is sent once to the assessment endpoint, under the product selected above, and is logged exactly like a live frame. It is not stored by this app.")
                .font(.caption)
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

            if let name = model.stillImageName {
                Text("Image ready: \(name). Tap “Assess this image” to send it once.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                Text("No image chosen.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if let error = model.stillImageError {
                Text(error)
                    .font(.caption)
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
                        .font(.caption)
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
            Text("Prerecorded video")
                .font(.headline)
            Text("For a recorded clip when neither a live camera nor a still image is the source. Play the clip, pause on the frame you want assessed, and tap “Assess this frame”: only that one frame is sent to the assessment endpoint, under the product selected above, and logged exactly like a live frame. The whole video is never sent, and it is not stored by this app.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            if let player = model.videoPlayer {
                VideoPlayer(player: player)
                    .frame(minHeight: 240)
                    .background(Color.black)
                    .cornerRadius(6)
                    .accessibilityLabel("Prerecorded video player")
            }

            if let name = model.videoName {
                Text("Video ready: \(name). Play it, pause on the frame you want assessed, and tap “Assess this frame”. Only that frame is sent; the video is not stored by this app.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                Text("No video chosen.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if let error = model.videoError {
                Text(error)
                    .font(.caption)
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
                        .font(.caption)
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
                    Text("Assessment endpoint")
                        .font(.caption)
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
                    Text(model.backendHealth)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                        .accessibilityLabel("Backend health: \(model.backendHealth)")
                }

                Stepper(value: $model.intervalSeconds, in: 1...60) {
                    Text("Sample one frame every \(model.intervalSeconds) second\(model.intervalSeconds == 1 ? "" : "s")")
                }

                Text("Analysis uses sampled frames: one frame every \(model.intervalSeconds) second\(model.intervalSeconds == 1 ? "" : "s") is sent to the assessment endpoint. This is not continuous video analysis, and events between samples are not seen by the system.")
                    .font(.caption)
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
                    Text("Or a custom scenario label (overrides the choice above)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    TextField("Scenario label", text: $model.scenarioLabel)
                        .textFieldStyle(.roundedBorder)
                        .labelsHidden()
                        .accessibilityLabel("Scenario label")
                        .accessibilityHint("Optional custom label recorded in the session log for evaluation. It overrides the scenario choice above.")
                }

                Text("Categories the server may return: \(model.config.categories.joined(separator: ", ")).")
                    .font(.caption)
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
