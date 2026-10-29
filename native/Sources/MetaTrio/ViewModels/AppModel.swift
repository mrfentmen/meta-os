import AppKit
import AVFoundation
import Foundation
import UniformTypeIdentifiers

// AppModel: the wiring layer. Connects camera -> sampler -> assessment
// client -> latest assessment + timeline + session log, exactly like the
// web frontend's app.js. It contains no detection logic and no sample
// data: if the backend is unreachable, the UI shows the error and
// nothing else.

enum BackendStatus: Equatable {
    case unknown(String)
    case connected(String)
    case error(String)

    var message: String {
        switch self {
        case .unknown(let message), .connected(let message), .error(let message):
            return message
        }
    }
}

struct SamplerStats: Equatable {
    var ticks = 0
    var sent = 0
    var skipped = 0
    var failed = 0
}

struct TimelineItem: Identifiable {
    enum Kind {
        case assessment(AssessmentResponse)
        case failure(String)
    }

    let id = UUID()
    let product: ProductID
    let timestamp: String
    let kind: Kind

    var title: String {
        switch kind {
        case .assessment(let response):
            return response.assessment.requiresHumanReview
                ? "\(response.assessment.category) (human review)"
                : response.assessment.category
        case .failure:
            return "Analysis request failed"
        }
    }

    var detail: String {
        switch kind {
        case .assessment(let response):
            return response.assessment.summary
        case .failure(let message):
            return message
        }
    }
}

@MainActor
final class AppModel: ObservableObject {
    static let defaultEndpoint = "http://localhost:8080/api/assess"

    // User settings.
    @Published var selectedProduct: ProductID = .vigiles {
        didSet {
            if oldValue != selectedProduct {
                // Web parity: switching products resets the scenario
                // picker, so one product's scenario can never label
                // another product's log entries. The custom label field
                // is left alone, exactly like the web frontend, which
                // resets only the dropdown. Switching does NOT stop a
                // running analysis: like the web frontend, it applies
                // to the next sampled frame. That is safe because the
                // submit path takes the product captured at sample or
                // tap time, so every frame is assessed and logged under
                // the product selected when it started, a switch
                // mid-request cannot relabel it, and earlier entries
                // keep the product they were recorded under.
                selectedScenario = ""
                // Web parity: the web frontend's limitations line is a
                // polite live region, so a switch reads the new
                // product's safety limits aloud there. The native
                // header used to set the new limitations text
                // silently, so a VoiceOver user who had just switched
                // products heard the picker's new value but not the
                // limits that now apply — and the limits are the
                // safety text, not decoration. Announced verbatim, in
                // the header's own words: a switch touches no backend
                // and sends no frame. didSet does not run during
                // init, so launching on Vigiles announces nothing.
                AccessibilityAnnouncement.productLimitations(config.limitations)
            }
        }
    }
    @Published var endpoint: String = AppModel.defaultEndpoint
    @Published var intervalSeconds: Int = 3 {
        didSet {
            sampler.setInterval(TimeInterval(intervalSeconds))
            // Web parity: the web interval change handler rewords the
            // ANALYSIS ACTIVE banner through updateAnalysisActive, and
            // the banner is a polite, atomic live region, so a
            // VoiceOver user who changes the interval mid-run hears
            // the new interval there. The native banner's SwiftUI
            // label rewords the same way, but a label change posts no
            // announcement, so a VoiceOver user who stepped the
            // interval mid-run heard the Stepper's new number and
            // nothing confirming sampling was still active at that
            // interval. Post the banner's own words, through the same
            // helper as the start announcement, only while a run is
            // actually active: while idle the banner is hidden and
            // the next Start announces the interval then, so an
            // idle change stays silent. Starting never double
            // announces: startAnalysis sets the sampler interval
            // directly and never assigns intervalSeconds, and didSet
            // does not run during init. The announcement is polite,
            // so rapid stepping replaces rather than queues readings,
            // and an interval change sends no frame, so it is never
            // a backend or capture failure.
            if analysisRunning {
                AccessibilityAnnouncement.analysisStarted("Analysis active, sampling one frame every \(intervalSeconds) seconds")
            }
        }
    }
    @Published var scenarioLabel: String = ""
    /// Scenario picked from the current product's evaluation list
    /// (web parity with the web frontend's scenario dropdown). Empty
    /// means no scenario picked; the custom label above wins over it.
    @Published var selectedScenario: String = ""

    // Still-image input (web parity): the chosen file lives in memory
    // only, exactly like the web frontend's preview + data URL. It is
    // never written to disk by this app and is cleared by Reset Session.
    @Published private(set) var stillImage: NSImage?
    @Published private(set) var stillImageName: String?
    @Published private(set) var stillImageAssessing = false
    @Published private(set) var stillImageError: String?
    private var stillImageDataURL: String?

    // Prerecorded-video input (web parity): the player plays the
    // user's file in place — the video is never copied or stored by
    // this app. "Assess this frame" extracts only the frame at the
    // current playback position and sends that one JPEG through the
    // same submit path as a live frame.
    @Published private(set) var videoPlayer: AVPlayer?
    @Published private(set) var videoName: String?
    @Published private(set) var videoAssessing = false
    @Published private(set) var videoError: String?
    private var videoURL: URL?

    // Observable runtime state.
    @Published private(set) var backendStatus: BackendStatus =
        .unknown("Model backend status unknown. Start analysis to contact the endpoint.")
    /// Backend health text, kept separate from backendStatus on purpose:
    /// this check contacts the health route only, never sends a frame
    /// and never returns an assessment, so it must never change the
    /// assessment status shown in the status bar. Mirrors the web
    /// frontend's backend-health paragraph.
    @Published private(set) var backendHealth: String =
        "Backend health not checked yet. Checking it contacts the server's health route only; it never sends a frame and never returns an assessment."
    @Published private(set) var healthChecking = false
    @Published private(set) var displayedAssessment: AssessmentResponse?
    /// Plain-words note shown under the "Latest assessment" heading when
    /// the panel shows a re-inspected past result instead of the newest
    /// assessment (web parity: the web "Show assessment" button labels
    /// the panel the same way). Nil when the panel shows the newest
    /// assessment, after a reset, or before anything is shown.
    @Published private(set) var displayedAssessmentNote: String?
    @Published private(set) var timeline: [TimelineItem] = []
    @Published private(set) var analysisRunning = false
    @Published private(set) var requestInFlight = false
    @Published private(set) var samplerStats = SamplerStats()
    @Published private(set) var logCount = 0
    /// Client-measured round-trip time of the most recent request that was
    /// actually attempted (nil before the first one). Never estimated.
    @Published private(set) var lastRoundTripMs: Int?
    /// View generation, bumped by resetSession. A request outstanding
    /// across a Reset must not repopulate the cleared view when it
    /// settles (same rule as the web frontend's viewGeneration): the
    /// session-log entry is still recorded — the request genuinely
    /// happened and the log survives Reset by design — but the latest
    /// panel, timeline, backend status, round trip, and announcement
    /// stay as Reset left them.
    private var viewGeneration = 0
    /// In-flight request count, backing the published requestInFlight
    /// flag (web parity with js/app.js inFlightCount): the status bar's
    /// "Assessment request in flight…" line is shared by every submit
    /// path — a live sampled frame, a still image, and a
    /// prerecorded-video frame can all be outstanding at once (the
    /// sampler guards only live-vs-live, and each panel guards only
    /// itself), so a single boolean hid the line as soon as the first
    /// of several requests settled, while another was still out. The
    /// flag stays true while at least one request is outstanding and
    /// clears only when the last one settles. Reset never touches the
    /// count — a request outstanding across Reset is still
    /// outstanding, and its settle path still clears the flag, exactly
    /// as before.
    private var inFlightCount = 0

    let camera = CameraService()
    private let sampler = FrameSampler(intervalSeconds: 3)
    private let client = AssessClient()
    private let healthClient = HealthClient()
    private let log = SessionLog()

    init() {
        sampler.onSample = { [weak self] in
            guard let self = self else { return }
            try await self.runSample()
        }
        sampler.onTick = { [weak self] in
            self?.syncSamplerStats()
        }
        // Web parity: the session log survives a relaunch, so the
        // timeline and the latest assessment are restored from it, the
        // same way the web frontend replays its saved log on load.
        // Reset Session still clears the on-screen timeline without
        // clearing the log; Clear Log clears both the saved and the
        // in-memory log, so a cleared log never comes back on relaunch.
        restoreTimelineFromLog()
    }

    var config: ProductConfig { selectedProduct.config }

    var trimmedEndpoint: String {
        let trimmed = endpoint.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? Self.defaultEndpoint : trimmed
    }

    private var currentScenarioLabel: String? {
        // Web parity (js/app.js currentScenarioLabel): a custom label
        // wins over the picked scenario; otherwise the picked scenario
        // is the label; otherwise there is no label.
        let trimmed = scenarioLabel.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty { return trimmed }
        return selectedScenario.isEmpty ? nil : selectedScenario
    }

    // MARK: - Camera controls

    func startCamera() {
        camera.start()
    }

    func stopCamera() {
        stopAnalysis()
        camera.stop()
    }

    // MARK: - Analysis controls

    func startAnalysis() {
        backendStatus = .unknown("Contacting model backend: \(trimmedEndpoint) …")
        sampler.setInterval(TimeInterval(intervalSeconds))
        sampler.start()
        analysisRunning = sampler.isRunning
        // Announced in the camera panel banner's own words: the banner
        // appears silently, and the backend-status line changes
        // silently too on native, so without this a VoiceOver user who
        // had just tapped Start Analysis heard nothing confirming
        // sampling was running or at what interval. Announced only
        // when the sampler actually started; stopping stays silent,
        // like Clear — the user tapped Stop themselves.
        if analysisRunning {
            AccessibilityAnnouncement.analysisStarted("Analysis active, sampling one frame every \(intervalSeconds) seconds")
        }
    }

    func stopAnalysis() {
        sampler.stop()
        analysisRunning = false
        syncSamplerStats()
    }

    /// Stops capture and clears the displayed assessment and timeline.
    /// The session log is kept (export it before quitting if you need it),
    /// so the timeline comes back on relaunch from that log until Clear
    /// Log removes it — Reset Session never deletes saved entries.
    func resetSession() {
        // Bump the view generation first: a request outstanding across
        // this Reset still logs when it settles, but must not repaint
        // the view this method just cleared (see viewGeneration above).
        viewGeneration += 1
        stopAnalysis()
        camera.stop()
        clearStillImage()
        clearVideo()
        displayedAssessment = nil
        displayedAssessmentNote = nil
        timeline = []
        backendStatus = .unknown("Model backend status unknown. Start analysis to contact the endpoint.")
        // Web parity (js/app.js Reset handler): the web Reset also
        // clears the backend-health result, so a pre-reset check does
        // not linger on screen as if it were current, and the status
        // bar's last round trip is a pre-reset measurement, so it goes
        // too. Sampler counters are deliberately kept, exactly like the
        // web Reset, which stops the sampler without zeroing its counts;
        // product, endpoint, interval, and scenario choices are kept on
        // both sides as well.
        backendHealth = "Backend health not checked yet. Checking it contacts the server's health route only; it never sends a frame and never returns an assessment."
        lastRoundTripMs = nil
    }

    // MARK: - Backend health check

    /// Asks the server's health route whether it is up and what its
    /// model state is, exactly like the web frontend's backend-health
    /// check. A reachable server with the model held is reported exactly
    /// that way — reachable is not the same as ready to assess, and
    /// this check never sends a frame. It touches only backendHealth,
    /// never backendStatus, the displayed assessment, or the timeline.
    func checkBackendHealth() {
        guard !healthChecking else { return }
        healthChecking = true
        backendHealth = "Checking \(trimmedEndpoint) …"
        // The view generation is captured at tap time, like the
        // assessment paths capture it: a health check outstanding
        // across Reset Session must not repaint the health line Reset
        // just cleared ("Backend health not checked yet.") with a
        // pre-reset result, success or failure — Reset's whole point
        // for this line is that a pre-reset check does not linger as
        // if it were current. The checking flag still clears in every
        // case, so the button re-enables; only the text is guarded,
        // exactly like submitAssessment guards its display updates.
        let requestGeneration = viewGeneration
        Task {
            let resultText: String
            do {
                let health = try await healthClient.checkHealth(endpoint: trimmedEndpoint)
                let products = health.products.joined(separator: ", ")
                let modelState = health.modelLiveEnabled
                    ? "live calls on"
                    : health.modelConfigured
                        ? "key configured, live calls held"
                        : "key not configured, live calls held"
                resultText =
                    "Backend reachable: \(health.service) · products: \(products) · model: \(modelState). " +
                    "This does not mean an assessment is available — an assess request still has to succeed."
            } catch let error as AssessError {
                resultText = "Backend health check failed: \(error.message)"
            } catch {
                resultText = "Backend health check failed: \(error.localizedDescription)"
            }
            if requestGeneration == viewGeneration {
                backendHealth = resultText
                AccessibilityAnnouncement.healthResult(resultText)
            }
            healthChecking = false
        }
    }

    // MARK: - Still-image input

    /// Opens an image-only file picker. Non-image files cannot be
    /// chosen: the panel's allowedContentTypes is [.image].
    /// The read below is fully synchronous (panel, NSImage, JPEG
    /// encode), so unlike the web file-input handler there is no
    /// suspension point a Reset Session could land inside — no
    /// read-generation guard is needed on this side.
    func chooseStillImage() {
        let panel = NSOpenPanel()
        panel.title = "Choose a still image"
        panel.allowedContentTypes = [.image]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        guard panel.runModal() == .OK, let url = panel.url else {
            return
        }
        stillImageError = nil
        guard let image = NSImage(contentsOf: url),
              let dataURL = Self.jpegDataURL(for: image)
        else {
            stillImage = nil
            stillImageName = nil
            stillImageDataURL = nil
            stillImageError = "Could not read that image as a JPEG."
            // Web parity: the web frontend's image-state line is a
            // polite live region, so this same failure is read aloud
            // there the moment it is set. The native panel used to
            // set this error text silently, so a VoiceOver user who
            // had just picked a file heard nothing about why the
            // Assess button stayed disabled — unlike the video-frame
            // capture failure and the export failure, which are both
            // announced. Announced verbatim: no backend and no frame
            // capture is involved, so neither backendFailure nor
            // captureFailure describes it.
            AccessibilityAnnouncement.inputError("Could not read that image as a JPEG.")
            return
        }
        stillImage = image
        stillImageName = url.lastPathComponent
        stillImageDataURL = dataURL
        // Web parity: the web frontend's image-state line is a polite
        // live region, so this same ready line is read aloud there the
        // moment it is set. The native panel used to set it silently,
        // so a VoiceOver user who had just picked a file heard nothing
        // confirming the Assess button was now enabled — only the read
        // failure was announced. Announced in the panel's own words.
        AccessibilityAnnouncement.inputReady("Image ready: \(url.lastPathComponent). Tap “Assess this image” to send it once.")
    }

    /// Sends the chosen still image once, under the product selected
    /// at assess time, through the same submit path — same validation,
    /// same history entry, same session-log entry — as a live frame.
    /// No camera is needed. With no backend running this fails exactly
    /// like a live frame: honest error, no assessment.
    func assessStillImage() {
        guard let dataURL = stillImageDataURL, !stillImageAssessing else {
            return
        }
        stillImageAssessing = true
        // Capture the product at tap time (see submitAssessment): a
        // product switch while the request is in flight must not
        // relabel this image's log and timeline entries. The scenario
        // label is captured the same way, for the same reason.
        let requestProduct = selectedProduct
        let requestScenarioLabel = currentScenarioLabel
        // The view generation is captured at tap time too, like the
        // product and the scenario: the Task below is a hop, and a
        // Reset tapped before it runs must not let this tap's request
        // repaint the view Reset just cleared.
        let requestGeneration = viewGeneration
        // Plain Task awaiting a @MainActor method: the hop back onto
        // the main actor is explicit, and no capture-list/attribute
        // ordering question arises (this sandbox has no Swift compiler
        // to check it against).
        Task {
            await self.runStillImageAssessment(dataURL: dataURL, product: requestProduct, scenarioLabel: requestScenarioLabel, generation: requestGeneration)
        }
    }

    private func runStillImageAssessment(dataURL: String, product: ProductID, scenarioLabel: String?, generation: Int) async {
        defer { stillImageAssessing = false }
        // A Reset tapped between the Assess tap and this Task running
        // clears the still-image input; a stale tap must set nothing
        // and send nothing — the image it would have sent was cleared.
        guard generation == viewGeneration else { return }
        // Web parity (js/app.js still-image handler): the web panel
        // sets the backend status to "Contacting…" while the request is
        // outstanding. The native path went straight to
        // submitAssessment, so the status bar kept showing the previous
        // state — a stale "connected" from an earlier success — for the
        // whole flight. submitAssessment overwrites this on settle
        // (connected or error), so it never sticks.
        backendStatus = .unknown("Contacting model backend: \(trimmedEndpoint) …")
        // submitAssessment already records the outcome in the timeline
        // and the session log and sets backendStatus, so a failure
        // here needs no extra handling.
        do {
            try await submitAssessment(product: product, timestamp: ISO8601.now(), imageDataURL: dataURL, scenarioLabel: scenarioLabel, generation: generation)
        } catch {
            // Outcome already logged and rendered by submitAssessment.
        }
    }

    func clearStillImage() {
        stillImage = nil
        stillImageName = nil
        stillImageDataURL = nil
        stillImageError = nil
        // The assessing flag is NOT cleared here, exactly like the web
        // frontend's Clear/Reset: web clearStillImageInput clears the
        // input but leaves stillImageAssessing alone, so a new image
        // chosen while the old request is still out cannot be sent
        // until that request settles (its Task defer clears the flag).
        // Clearing it here used to re-enable the Assess button for a
        // newly chosen image while the old request was still in
        // flight — a second send from the same panel, which the
        // guard in assessStillImage exists to prevent. With the image
        // nil the button stays disabled either way; the flag is owned
        // by the in-flight Task's defer, not by Clear or Reset Session.
    }

    // MARK: - Prerecorded-video input

    /// Opens a video-only file picker. The chosen file is played from
    /// its own location; this app never copies it. Play the clip and
    /// pause on the frame to assess, exactly like the web frontend.
    func chooseVideo() {
        let panel = NSOpenPanel()
        panel.title = "Choose a prerecorded video"
        panel.allowedContentTypes = [.movie, .mpeg4Movie, .quickTimeMovie]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        guard panel.runModal() == .OK, let url = panel.url else {
            return
        }
        videoError = nil
        videoURL = url
        videoName = url.lastPathComponent
        videoPlayer = AVPlayer(url: url)
        // Web parity: the web frontend's video-state line is a polite
        // live region, so its ready line is read aloud there the moment
        // a file is chosen. The native panel used to set its ready text
        // silently, so a VoiceOver user who had just picked a clip heard
        // nothing confirming the Assess button was now enabled.
        // Announced in the panel's own words.
        AccessibilityAnnouncement.inputReady("Video ready: \(url.lastPathComponent). Play it, pause on the frame you want assessed, and tap “Assess this frame”. Only that frame is sent; the video is not stored by this app.")
    }

    /// Sends only the frame at the player's current position, once,
    /// under the product selected at assess time, through the same
    /// submit path as a live frame. A frame-extraction failure is
    /// logged and shown as a failure, never papered over with a
    /// neighbouring frame or a placeholder.
    func assessVideoFrame() {
        guard let url = videoURL, let player = videoPlayer, !videoAssessing else {
            return
        }
        videoAssessing = true
        let seconds = player.currentTime().seconds
        // Capture the product at tap time (see submitAssessment): a
        // product switch while the request is in flight must not
        // relabel this frame's log and timeline entries. The scenario
        // label is captured the same way, for the same reason.
        let requestProduct = selectedProduct
        let requestScenarioLabel = currentScenarioLabel
        // The view generation is captured at tap time too, like the
        // product and the scenario: the Task below is a hop, and
        // extraction below awaits, so a Reset in either window must
        // not let this tap's request repaint the view Reset cleared.
        let requestGeneration = viewGeneration
        // Plain Task awaiting a @MainActor method: same shape as the
        // still-image path (this sandbox has no Swift compiler to
        // check it against).
        Task {
            await self.runVideoFrameAssessment(url: url, seconds: seconds, product: requestProduct, scenarioLabel: requestScenarioLabel, generation: requestGeneration)
        }
    }

    private func runVideoFrameAssessment(url: URL, seconds: Double, product: ProductID, scenarioLabel: String?, generation: Int) async {
        defer { videoAssessing = false }
        // Same Reset rule as submitAssessment, with the generation
        // captured at tap time (not here): extraction awaits, so a
        // Reset can land mid-extraction, and a Reset before this Task
        // runs clears the video input. A stale tap sets nothing and
        // extracts nothing; a Reset mid-extraction still logs the
        // failure, but must not repaint the cleared panel, status,
        // or timeline — and, now that submitAssessment takes this same
        // generation, neither may its success.
        guard generation == viewGeneration else { return }
        // Web parity (js/app.js video handler): the web panel sets the
        // backend status to "Contacting…" before it captures the frame,
        // so the status bar moves while the request is outstanding. The
        // native path left the previous state up for the whole flight.
        // A capture failure below overwrites this with the real error,
        // exactly like the web handler, and submitAssessment overwrites
        // it on settle, so it never sticks.
        backendStatus = .unknown("Contacting model backend: \(trimmedEndpoint) …")
        let dataURL: String
        do {
            dataURL = try await VideoFrameService.jpegDataURL(for: url, at: seconds)
        } catch {
            // Extraction failed before any request was made, so there
            // is no submitAssessment failure to reuse: record and show
            // this failure directly, in the same shapes as a backend
            // failure (timeline entry + session-log entry + status).
            let message = "Video frame capture failed: \(error.localizedDescription)"
            let timestamp = ISO8601.now()
            recordLog(product: product, timestamp: timestamp, latencyMs: nil, status: .invalidResponse, error: message, scenarioLabel: scenarioLabel)
            if generation == viewGeneration {
                videoError = message
                // No request was made, so this is not a backend failure:
                // show the capture failure itself, not a backend message.
                backendStatus = .error(message)
                // Web parity: the web frontend's backend-status line is
                // a polite live region, so this same error is read
                // aloud there the moment it is set. The native status
                // bar is not a live region, so without this call a
                // VoiceOver user would never hear that the frame
                // extraction failed, even though the error is on
                // screen. Announced verbatim, not as a backend failure.
                AccessibilityAnnouncement.captureFailure(message: message)
                timeline.insert(
                    TimelineItem(product: product, timestamp: timestamp, kind: .failure(message)),
                    at: 0
                )
            }
            return
        }
        do {
            try await submitAssessment(product: product, timestamp: ISO8601.now(), imageDataURL: dataURL, scenarioLabel: scenarioLabel, generation: generation)
        } catch {
            // Outcome already logged and rendered by submitAssessment.
        }
    }

    func clearVideo() {
        videoPlayer?.pause()
        videoPlayer = nil
        videoURL = nil
        videoName = nil
        videoError = nil
        // Same rule as clearStillImage above, and same as the web
        // frontend's clearVideoInput: the assessing flag is owned by
        // the in-flight Task's defer, not by Clear or Reset Session,
        // so a video chosen while the old frame's request is still out
        // cannot be sent until that request settles.
    }

    /// Frames are downscaled so the longest side is at most this many
    /// pixels before JPEG encoding, keeping request bodies reasonable —
    /// the same cap the live camera (CameraService) and the web
    /// frontend's still-image path use.
    private static let maxStillImageDimension: CGFloat = 1280
    private static let stillImageJPEGQuality: CGFloat = 0.8

    private static func jpegDataURL(for image: NSImage) -> String? {
        // Live-camera parity: the live camera downscales to the cap at
        // JPEG 0.8, and the still-image path did neither — it encoded
        // the chosen image at full size with the default quality, so a
        // phone photo could be several megabytes as a base64 data URL
        // and risk the server's request-body cap while a live frame
        // sails under it. Downscale only when the cap actually bites;
        // an image already under it keeps its size, and every still
        // image is encoded at the live camera's 0.8 quality.
        let size = image.size
        let longestSide = max(size.width, size.height)
        var source = image
        if longestSide > maxStillImageDimension {
            let scale = maxStillImageDimension / longestSide
            let newSize = NSSize(width: size.width * scale, height: size.height * scale)
            let resized = NSImage(size: newSize)
            resized.lockFocus()
            image.draw(
                in: NSRect(origin: .zero, size: newSize),
                from: NSRect(origin: .zero, size: size),
                operation: .copy,
                fraction: 1.0
            )
            resized.unlockFocus()
            source = resized
        }
        guard let tiff = source.tiffRepresentation,
              let rep = NSBitmapImageRep(data: tiff),
              let jpeg = rep.representation(using: .jpeg, properties: [.compressionFactor: stillImageJPEGQuality])
        else {
            return nil
        }
        return "data:image/jpeg;base64,\(jpeg.base64EncodedString())"
    }

    // MARK: - Timeline

    /// Replays the persisted session log oldest-first, inserting each
    /// entry at the top, so the newest entry ends up on top exactly as
    /// it would after live recording (mirrors the web frontend's
    /// restoreHistoryFromLog). The latest assessment shown is the
    /// newest successful one. A saved entry whose product key is
    /// unknown is shown under the currently selected product rather
    /// than dropped — the entry itself is never rewritten.
    private func restoreTimelineFromLog() {
        logCount = log.count
        var latestOk: AssessmentResponse?
        for entry in log.entries {
            let product = ProductID(rawValue: entry.product) ?? selectedProduct
            if entry.status == .ok, let response = entry.response {
                latestOk = response
                timeline.insert(
                    TimelineItem(product: product, timestamp: response.timestamp, kind: .assessment(response)),
                    at: 0
                )
            } else {
                let message = entry.error ?? "Unknown error."
                timeline.insert(
                    TimelineItem(product: product, timestamp: entry.requestTimestamp, kind: .failure(message)),
                    at: 0
                )
            }
        }
        if let latestOk = latestOk {
            displayedAssessment = latestOk
        }
    }

    func display(_ item: TimelineItem) {
        if case .assessment(let response) = item.kind {
            displayedAssessment = response
            displayedAssessmentNote = "Showing an earlier assessment from \(item.timestamp). This is a past result shown again for review, not a new assessment."
        }
    }

    // MARK: - Session log

    func clearLog() {
        log.clear()
        logCount = 0
    }

    func exportLog() {
        let panel = NSSavePanel()
        panel.title = "Export session log"
        panel.nameFieldStringValue = "meta-trio-session-log-\(Self.fileTimestamp()).json"
        panel.allowedContentTypes = [.json]
        guard panel.runModal() == .OK, let url = panel.url else {
            return
        }
        do {
            let data = try log.exportData(
                endpoint: trimmedEndpoint,
                samplingIntervalSeconds: Double(intervalSeconds),
                currentProduct: selectedProduct
            )
            try data.write(to: url, options: .atomic)
        } catch {
            // The status bar is not a live region, so without this a
            // VoiceOver user would never hear that the export they
            // just asked for failed, even though the error is on
            // screen — the same silent-status hole the capture-failure
            // and health-result announcements already closed. Announced
            // verbatim, not as a backend failure: the export writes a
            // file, it sends nothing to the backend, and the backend
            // may be perfectly fine.
            let message = "Session log export failed: \(error.localizedDescription)"
            backendStatus = .error(message)
            AccessibilityAnnouncement.exportFailure(message)
        }
    }

    // MARK: - Sampling pipeline

    /// One end-to-end sample: capture a frame, then submit it.
    /// Throws the AssessError on failure so the sampler counts it; the
    /// failure is also rendered and logged by submitAssessment before
    /// rethrowing.
    private func runSample() async throws {
        let timestamp = ISO8601.now()
        // Web parity (js/app.js runSample): the product is captured
        // before the frame is captured, so a switch mid-sample labels
        // the entry with the product the sample started under, not the
        // one selected when the request happens to finish. The scenario
        // label is captured the same way, for the same reason.
        let requestProduct = selectedProduct
        let requestScenarioLabel = currentScenarioLabel
        // The view generation is captured at sample time too, like the
        // product and the scenario, so submitAssessment never re-reads
        // it after an await (see its comment below).
        let requestGeneration = viewGeneration

        let image: String
        do {
            image = try camera.captureFrameDataURL()
        } catch {
            let message = "Frame capture failed: \(error.localizedDescription)"
            recordLog(product: requestProduct, timestamp: timestamp, latencyMs: nil, status: .invalidResponse, error: message, scenarioLabel: requestScenarioLabel)
            // Video-path parity: the video-frame path records a capture
            // failure directly in the timeline and the backend status,
            // in the same shapes as a backend failure. The live path
            // only logged it, so a failed tick during a run never
            // reached the timeline a reviewer reads, even though the
            // sampler counted it as a failed tick. No request was made,
            // so this shows the capture failure itself, not a backend
            // message, and leaves the last round trip alone.
            backendStatus = .error(message)
            // Web parity: the web frontend's backend-status line is a
            // polite live region, so this same error is read aloud
            // there the moment it is set. The native status bar is not
            // a live region, so without this call a VoiceOver user
            // would never hear that the tick failed, even though the
            // error is on screen. Announced verbatim, not as a backend
            // failure, because no request was made.
            AccessibilityAnnouncement.captureFailure(message: message)
            timeline.insert(
                TimelineItem(product: requestProduct, timestamp: timestamp, kind: .failure(message)),
                at: 0
            )
            throw AssessError(kind: .invalid, message: message, latencyMs: nil)
        }

        try await submitAssessment(product: requestProduct, timestamp: timestamp, imageDataURL: image, scenarioLabel: requestScenarioLabel, generation: requestGeneration)
    }

    /// Shared submit path for live frames and still images: POST the
    /// image, validate the reply, record the outcome in the log, and
    /// update the display. Throws on failure after rendering and
    /// logging it, so callers that count failures (the sampler) can
    /// count it and callers that do not (still-image assess) can
    /// swallow it safely.
    ///
    /// The product is a parameter, captured by the caller at sample or
    /// tap time — never read from selectedProduct after an await.
    /// The old code read selectedProduct after the request returned,
    /// so switching products while a request was in flight relabelled
    /// that request's log and timeline entries under the new product.
    /// The web frontend does not have this bug: its submitAssessment
    /// takes the product as a parameter, and its history title uses the
    /// assessment's own product. Here the validated response product
    /// equals the request product, so the request product is the honest
    /// label for the log, the timeline, and the announcement. The
    /// scenario label is a parameter for the same reason: a scenario
    /// change mid-request must not relabel the entry with ground
    /// truth it was never assessed under. The view generation is a
    /// parameter for the same reason again, and it must be captured by
    /// the caller at sample or tap time, never re-read here: submit
    /// used to capture it itself, so a Reset during the prerecorded-
    /// video frame extraction — an await that sits between the tap and
    /// this call — gave submit the post-reset generation, and its
    /// settle path then repainted the view Reset had just cleared,
    /// even though the extraction failure path (which kept the
    /// pre-extraction generation) correctly stayed dark. A Reset while
    /// the request itself is out still bumps viewGeneration, and the
    /// settle path below then logs only, without repainting.
    private func submitAssessment(product: ProductID, timestamp: String, imageDataURL: String, scenarioLabel: String?, generation: Int) async throws {
        requestInFlight = true
        inFlightCount += 1
        defer {
            inFlightCount -= 1
            if inFlightCount == 0 {
                requestInFlight = false
            }
        }

        do {
            let (response, latencyMs) = try await client.assess(
                endpoint: trimmedEndpoint,
                product: product,
                timestamp: timestamp,
                imageDataURL: imageDataURL
            )
            recordLog(product: product, timestamp: timestamp, latencyMs: latencyMs, status: .ok, response: response, scenarioLabel: scenarioLabel)
            if generation == viewGeneration {
                lastRoundTripMs = latencyMs
                backendStatus = .connected("Model backend connected: \(trimmedEndpoint)")
                displayedAssessment = response
                displayedAssessmentNote = nil
                AccessibilityAnnouncement.newAssessment(
                    productDisplayName: product.config.displayName,
                    response: response
                )
                timeline.insert(
                    TimelineItem(product: product, timestamp: response.timestamp, kind: .assessment(response)),
                    at: 0
                )
            }
        } catch let error as AssessError {
            // A failure with no request behind it (invalid endpoint URL,
            // request-body encode failure — AssessClient reports nil
            // latency there) leaves the previous round trip alone,
            // exactly like a frame-capture failure: no request was made,
            // so there is no new measurement, and the old value is real
            // information a typo'd endpoint should not erase. Only
            // Reset Session clears it. A failure of a request that was
            // actually attempted carries a measured latency and updates it.
            let status: LogStatus
            switch error.kind {
            case .http: status = .httpError
            case .invalid: status = .invalidResponse
            case .network: status = .networkError
            }
            recordLog(product: product, timestamp: timestamp, latencyMs: error.latencyMs, status: status, error: error.message, scenarioLabel: scenarioLabel)
            if generation == viewGeneration {
                if let latencyMs = error.latencyMs {
                    lastRoundTripMs = latencyMs
                }
                backendStatus = .error("Model backend not connected: \(error.message)")
                AccessibilityAnnouncement.backendFailure(message: error.message)
                timeline.insert(
                    TimelineItem(product: product, timestamp: timestamp, kind: .failure(error.message)),
                    at: 0
                )
            }
            throw error
        }
    }

    private func recordLog(
        product: ProductID,
        timestamp: String,
        latencyMs: Int?,
        status: LogStatus,
        response: AssessmentResponse? = nil,
        error: String? = nil,
        scenarioLabel: String?
    ) {
        log.record(
            requestTimestamp: timestamp,
            product: product,
            latencyMs: latencyMs,
            status: status,
            response: response,
            error: error,
            scenarioLabel: scenarioLabel
        )
        logCount = log.count
    }

    private func syncSamplerStats() {
        samplerStats = SamplerStats(
            ticks: sampler.tickCount,
            sent: sampler.sampledCount,
            skipped: sampler.skippedCount,
            failed: sampler.errorCount
        )
    }

    private static func fileTimestamp() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd-HHmmss"
        return formatter.string(from: Date())
    }
}
