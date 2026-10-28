import Foundation

// Shared ISO-8601 timestamp handling. Output always carries fractional
// seconds; validation accepts timestamps with or without them, matching
// what the server is expected to emit.

enum ISO8601 {
    private static let fractionalFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static let standardFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    static func string(from date: Date) -> String {
        fractionalFormatter.string(from: date)
    }

    static func now() -> String {
        string(from: Date())
    }

    static func isValid(_ value: String) -> Bool {
        fractionalFormatter.date(from: value) != nil || standardFormatter.date(from: value) != nil
    }
}
