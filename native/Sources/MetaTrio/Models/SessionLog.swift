import Foundation

// Evaluation session log, persisted across relaunches (web parity with
// the web frontend's browser-storage log). Every analysis request the app
// makes is recorded exactly once: the request timestamp, the product, the
// measured client round-trip latency, the outcome status, and either the
// validated response or the real error. Latency is nil when no request was
// made (e.g. frame capture failed first) — it is never recorded as a fake 0.
// Entries hold assessments and errors only, never frames, and nothing is
// uploaded; the operator exports the log as JSON for the evaluation lane
// (Agent 3). A missing, corrupt, or unwritable saved file never breaks
// logging: the log keeps working in memory, and the next record overwrites
// the bad file.

enum LogStatus: String, Codable {
    case ok
    case networkError = "network_error"
    case httpError = "http_error"
    case invalidResponse = "invalid_response"
}

struct SessionLogEntry: Codable, Identifiable {
    let seq: Int
    let recordedAt: String
    let requestTimestamp: String
    let product: String
    let latencyMs: Int?
    let status: LogStatus
    let scenarioLabel: String?
    let response: AssessmentResponse?
    let error: String?

    var id: Int { seq }

    enum CodingKeys: String, CodingKey {
        case seq
        case recordedAt = "recorded_at"
        case requestTimestamp = "request_timestamp"
        case product
        case latencyMs = "latency_ms"
        case status
        case scenarioLabel = "scenario_label"
        case response
        case error
    }
}

private struct SessionLogExport: Codable {
    let app: String
    let exportedAt: String
    let product: String
    let endpoint: String?
    let samplingIntervalSeconds: Double?
    let entryCount: Int
    let entries: [SessionLogEntry]

    enum CodingKeys: String, CodingKey {
        case app
        case exportedAt = "exported_at"
        case product
        case endpoint
        case samplingIntervalSeconds = "sampling_interval_seconds"
        case entryCount = "entry_count"
        case entries
    }
}

final class SessionLog {
    private(set) var entries: [SessionLogEntry] = []
    private var seq = 0

    var count: Int { entries.count }

    /// Restores previously saved entries on launch, exactly like the web
    /// frontend restores its log from browser storage. The sequence
    /// counter resumes past the highest saved sequence number, so a
    /// restored entry and a new entry can never share a seq.
    init() {
        entries = Self.loadSavedEntries()
        seq = entries.map { $0.seq }.max() ?? 0
    }

    /// Application Support/MetaTrio/session-log.json. Nil only when the
    /// system cannot give this app an Application Support directory.
    private static var persistenceURL: URL? {
        guard let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first else {
            return nil
        }
        return base
            .appendingPathComponent("MetaTrio", isDirectory: true)
            .appendingPathComponent("session-log.json")
    }

    private static func loadSavedEntries() -> [SessionLogEntry] {
        guard let url = persistenceURL,
              let data = try? Data(contentsOf: url),
              let saved = try? JSONDecoder().decode([SessionLogEntry].self, from: data)
        else {
            return []
        }
        return saved
    }

    /// Best effort, like the web log's storage writes: a failed save
    /// leaves the in-memory log untouched, and the next record retries.
    private func save() {
        guard let url = Self.persistenceURL else { return }
        do {
            try FileManager.default.createDirectory(
                at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
            let data = try JSONEncoder().encode(entries)
            try data.write(to: url, options: .atomic)
        } catch {
            // Unwritable disk or a full volume: in-memory logging
            // continues, and the next relaunch simply starts empty.
        }
    }

    private func removeSaved() {
        guard let url = Self.persistenceURL else { return }
        // Same as save: clearing the in-memory log still succeeds.
        try? FileManager.default.removeItem(at: url)
    }

    @discardableResult
    func record(
        requestTimestamp: String,
        product: ProductID,
        latencyMs: Int?,
        status: LogStatus,
        response: AssessmentResponse? = nil,
        error: String? = nil,
        scenarioLabel: String? = nil
    ) -> SessionLogEntry {
        seq += 1
        let entry = SessionLogEntry(
            seq: seq,
            recordedAt: ISO8601.now(),
            requestTimestamp: requestTimestamp,
            product: product.rawValue,
            latencyMs: latencyMs,
            status: status,
            scenarioLabel: scenarioLabel,
            response: response,
            error: error
        )
        entries.append(entry)
        save()
        return entry
    }

    func clear() {
        entries = []
        seq = 0
        removeSaved()
    }

    /// JSON export in the same shape the web frontend produces, consumed by
    /// the Agent 3 evaluation harness.
    func exportData(endpoint: String?, samplingIntervalSeconds: Double?, currentProduct: ProductID) throws -> Data {
        let export = SessionLogExport(
            app: "meta-trio-macos",
            exportedAt: ISO8601.now(),
            product: currentProduct.rawValue,
            endpoint: endpoint,
            samplingIntervalSeconds: samplingIntervalSeconds,
            entryCount: entries.count,
            entries: entries
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(export)
    }
}
