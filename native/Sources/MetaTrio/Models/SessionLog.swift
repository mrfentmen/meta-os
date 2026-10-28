import Foundation

// In-memory evaluation session log. Every analysis request the app makes is
// recorded exactly once: the request timestamp, the product, the measured
// client round-trip latency, the outcome status, and either the validated
// response or the real error. Latency is nil when no request was made
// (e.g. frame capture failed first) — it is never recorded as a fake 0.
// Nothing is persisted and nothing is uploaded; the operator exports the
// log as JSON for the evaluation lane (Agent 3).

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
        return entry
    }

    func clear() {
        entries = []
        seq = 0
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
