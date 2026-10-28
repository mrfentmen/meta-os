import AppKit
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
    @Published var selectedProduct: ProductID = .sentinel {
        didSet {
            if oldValue != selectedProduct, sampler.isRunning {
                stopAnalysis()
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

    // Observable runtime state.
    @Published private(set) var backendStatus: BackendStatus =
        .unknown("Model backend status unknown. Start analysis to contact the endpoint.")
    @Published private(set) var displayedAssessment: AssessmentResponse?
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
    private let log = SessionLog()

    init() {
        sampler.onSample = { [weak self] in
            guard let self = self else { return }
            try await self.runSample()
        }
        sampler.onTick = { [weak self] in
            self?.syncSamplerStats()
        }
    }

    var config: ProductConfig { selectedProduct.config }

    var trimmedEndpoint: String {
        let trimmed = endpoint.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? Self.defaultEndpoint : trimmed
    }

    private var currentScenarioLabel: String? {
        let trimmed = scenarioLabel.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
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
    /// The session log is kept (export it before quitting if you need it).
    func resetSession() {
        stopAnalysis()
        camera.stop()
        displayedAssessment = nil
        timeline = []
        backendStatus = .unknown("Model backend status unknown. Start analysis to contact the endpoint.")
    }

    // MARK: - Timeline

    func display(_ item: TimelineItem) {
        if case .assessment(let response) = item.kind {
            displayedAssessment = response
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

    /// One end-to-end sample: capture a frame, POST it, validate the
    /// reply, record the outcome in the log, and update the display.
    /// Throws the AssessError on failure so the sampler counts it; the
    /// failure is also rendered and logged here before rethrowing.
    private func runSample() async throws {
        let timestamp = ISO8601.now()

        let image: String
        do {
            image = try camera.captureFrameDataURL()
        } catch {
            let message = "Frame capture failed: \(error.localizedDescription)"
            recordLog(timestamp: timestamp, latencyMs: nil, status: .invalidResponse, error: message)
            throw AssessError(kind: .invalid, message: message, latencyMs: nil)
        }

        requestInFlight = true
        defer { requestInFlight = false }

        do {
            let (response, latencyMs) = try await client.assess(
                endpoint: trimmedEndpoint,
                product: selectedProduct,
                timestamp: timestamp,
                imageDataURL: image
            )
            lastRoundTripMs = latencyMs
            recordLog(timestamp: timestamp, latencyMs: latencyMs, status: .ok, response: response)
            backendStatus = .connected("Model backend connected: \(trimmedEndpoint)")
            displayedAssessment = response
            timeline.insert(
                TimelineItem(product: selectedProduct, timestamp: response.timestamp, kind: .assessment(response)),
                at: 0
            )
        } catch let error as AssessError {
            lastRoundTripMs = error.latencyMs
            let status: LogStatus
            switch error.kind {
            case .http: status = .httpError
            case .invalid: status = .invalidResponse
            case .network: status = .networkError
            }
            recordLog(timestamp: timestamp, latencyMs: error.latencyMs, status: status, error: error.message)
            backendStatus = .error("Model backend not connected: \(error.message)")
            timeline.insert(
                TimelineItem(product: selectedProduct, timestamp: timestamp, kind: .failure(error.message)),
                at: 0
            )
            throw error
        }
    }

    private func recordLog(
        timestamp: String,
        latencyMs: Int?,
        status: LogStatus,
        response: AssessmentResponse? = nil,
        error: String? = nil
    ) {
        log.record(
            requestTimestamp: timestamp,
            product: selectedProduct,
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
