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
            }
        }
    }
    @Published var endpoint: String = AppModel.defaultEndpoint
    @Published var intervalSeconds: Int = 3 {
        didSet {
            sampler.setInterval(TimeInterval(intervalSeconds))
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
        Task {
            do {
                let health = try await healthClient.checkHealth(endpoint: trimmedEndpoint)
                let products = health.products.joined(separator: ", ")
                let modelState = health.modelLiveEnabled
                    ? "live calls on"
                    : health.modelConfigured
                        ? "key configured, live calls held"
                        : "key not configured, live calls held"
                backendHealth =
                    "Backend reachable: \(health.service) · products: \(products) · model: \(modelState). " +
                    "This does not mean an assessment is available — an assess request still has to succeed."
            } catch let error as AssessError {
                backendHealth = "Backend health check failed: \(error.message)"
            } catch {
                backendHealth = "Backend health check failed: \(error.localizedDescription)"
            }
            healthChecking = false
        }
    }

    // MARK: - Still-image input

    /// Opens an image-only file picker. Non-image files cannot be
    /// chosen: the panel's allowedContentTypes is [.image].
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
            return
        }
        stillImage = image
        stillImageName = url.lastPathComponent
        stillImageDataURL = dataURL
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
        // relabel this image's log and timeline entries.
        let requestProduct = selectedProduct
        // Plain Task awaiting a @MainActor method: the hop back onto
        // the main actor is explicit, and no capture-list/attribute
        // ordering question arises (this sandbox has no Swift compiler
        // to check it against).
        Task {
            await self.runStillImageAssessment(dataURL: dataURL, product: requestProduct)
        }
    }

    private func runStillImageAssessment(dataURL: String, product: ProductID) async {
        defer { stillImageAssessing = false }
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
            try await submitAssessment(product: product, timestamp: ISO8601.now(), imageDataURL: dataURL)
        } catch {
            // Outcome already logged and rendered by submitAssessment.
        }
    }

    func clearStillImage() {
        stillImage = nil
        stillImageName = nil
        stillImageDataURL = nil
        stillImageError = nil
        stillImageAssessing = false
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
        // relabel this frame's log and timeline entries.
        let requestProduct = selectedProduct
        // Plain Task awaiting a @MainActor method: same shape as the
        // still-image path (this sandbox has no Swift compiler to
        // check it against).
        Task {
            await self.runVideoFrameAssessment(url: url, seconds: seconds, product: requestProduct)
        }
    }

    private func runVideoFrameAssessment(url: URL, seconds: Double, product: ProductID) async {
        defer { videoAssessing = false }
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
            videoError = message
            let timestamp = ISO8601.now()
            recordLog(product: product, timestamp: timestamp, latencyMs: nil, status: .invalidResponse, error: message)
            // No request was made, so this is not a backend failure:
            // show the capture failure itself, not a backend message.
            backendStatus = .error(message)
            timeline.insert(
                TimelineItem(product: product, timestamp: timestamp, kind: .failure(message)),
                at: 0
            )
            return
        }
        do {
            try await submitAssessment(product: product, timestamp: ISO8601.now(), imageDataURL: dataURL)
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
        videoAssessing = false
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
            backendStatus = .error("Session log export failed: \(error.localizedDescription)")
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
        // one selected when the request happens to finish.
        let requestProduct = selectedProduct

        let image: String
        do {
            image = try camera.captureFrameDataURL()
        } catch {
            let message = "Frame capture failed: \(error.localizedDescription)"
            recordLog(product: requestProduct, timestamp: timestamp, latencyMs: nil, status: .invalidResponse, error: message)
            // Video-path parity: the video-frame path records a capture
            // failure directly in the timeline and the backend status,
            // in the same shapes as a backend failure. The live path
            // only logged it, so a failed tick during a run never
            // reached the timeline a reviewer reads, even though the
            // sampler counted it as a failed tick. No request was made,
            // so this shows the capture failure itself, not a backend
            // message, and leaves the last round trip alone.
            backendStatus = .error(message)
            timeline.insert(
                TimelineItem(product: requestProduct, timestamp: timestamp, kind: .failure(message)),
                at: 0
            )
            throw AssessError(kind: .invalid, message: message, latencyMs: nil)
        }

        try await submitAssessment(product: requestProduct, timestamp: timestamp, imageDataURL: image)
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
    /// label for the log, the timeline, and the announcement.
    private func submitAssessment(product: ProductID, timestamp: String, imageDataURL: String) async throws {
        requestInFlight = true
        defer { requestInFlight = false }

        do {
            let (response, latencyMs) = try await client.assess(
                endpoint: trimmedEndpoint,
                product: product,
                timestamp: timestamp,
                imageDataURL: imageDataURL
            )
            lastRoundTripMs = latencyMs
            recordLog(product: product, timestamp: timestamp, latencyMs: latencyMs, status: .ok, response: response)
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
        } catch let error as AssessError {
            // A failure with no request behind it (invalid endpoint URL,
            // request-body encode failure — AssessClient reports nil
            // latency there) leaves the previous round trip alone,
            // exactly like a frame-capture failure: no request was made,
            // so there is no new measurement, and the old value is real
            // information a typo'd endpoint should not erase. Only
            // Reset Session clears it. A failure of a request that was
            // actually attempted carries a measured latency and updates it.
            if let latencyMs = error.latencyMs {
                lastRoundTripMs = latencyMs
            }
            let status: LogStatus
            switch error.kind {
            case .http: status = .httpError
            case .invalid: status = .invalidResponse
            case .network: status = .networkError
            }
            recordLog(product: product, timestamp: timestamp, latencyMs: error.latencyMs, status: status, error: error.message)
            backendStatus = .error("Model backend not connected: \(error.message)")
            AccessibilityAnnouncement.backendFailure(message: error.message)
            timeline.insert(
                TimelineItem(product: product, timestamp: timestamp, kind: .failure(error.message)),
                at: 0
            )
            throw error
        }
    }

    private func recordLog(
        product: ProductID,
        timestamp: String,
        latencyMs: Int?,
        status: LogStatus,
        response: AssessmentResponse? = nil,
        error: String? = nil
    ) {
        log.record(
            requestTimestamp: timestamp,
            product: product,
            latencyMs: latencyMs,
            status: status,
            response: response,
            error: error,
            scenarioLabel: currentScenarioLabel
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
