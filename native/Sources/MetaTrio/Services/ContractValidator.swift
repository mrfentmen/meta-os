import CoreFoundation
import Foundation

// Strict validation of server replies against the unified v2 contract
// (see Models/Assessment.swift). This is deliberately stricter than plain
// Codable decoding: every field's presence and JSON type is checked, the
// product must match the product that was requested, timestamps must
// parse as ISO-8601, confidence must be null or a number in 0...1, and
// latency_ms must be null or a non-negative number. Any violation fails
// the whole response with a list of specific problems — the app displays
// the failure, never a partially trusted assessment.

struct ContractValidationError: Error {
    let problems: [String]
}

enum ContractValidator {
    static func validate(_ data: Data, expectedProduct: ProductID) -> Result<AssessmentResponse, ContractValidationError> {
        let parsed: Any
        do {
            parsed = try JSONSerialization.jsonObject(with: data)
        } catch {
            return .failure(ContractValidationError(problems: ["response is not valid JSON: \(error.localizedDescription)"]))
        }
        guard let root = parsed as? [String: Any] else {
            return .failure(ContractValidationError(problems: ["response is not a JSON object"]))
        }

        var problems: [String] = []

        let product = nonEmptyString(root["product"], field: "product", problems: &problems)
        if let product = product, product != expectedProduct.rawValue {
            problems.append("product: expected \"\(expectedProduct.rawValue)\", got \"\(product)\"")
        }

        let timestamp = nonEmptyString(root["timestamp"], field: "timestamp", problems: &problems)
        if let timestamp = timestamp, !ISO8601.isValid(timestamp) {
            problems.append("timestamp: not a parseable ISO-8601 date")
        }

        var observations: [Observation] = []
        if let rawObservations = root["observations"] as? [Any] {
            for (index, item) in rawObservations.enumerated() {
                if let observation = parseObservation(item, index: index, problems: &problems) {
                    observations.append(observation)
                }
            }
        } else {
            problems.append("observations: missing or not an array")
        }

        var assessment: AssessmentDetail?
        if let rawAssessment = root["assessment"] as? [String: Any] {
            assessment = parseAssessment(rawAssessment, problems: &problems)
        } else {
            problems.append("assessment: missing or not an object")
        }

        var processing: ProcessingInfo?
        if let rawProcessing = root["processing"] as? [String: Any] {
            processing = parseProcessing(rawProcessing, problems: &problems)
        } else {
            problems.append("processing: missing or not an object")
        }

        guard problems.isEmpty,
              let product = product,
              let timestamp = timestamp,
              let assessment = assessment,
              let processing = processing
        else {
            return .failure(ContractValidationError(problems: problems))
        }

        return .success(AssessmentResponse(
            product: product,
            timestamp: timestamp,
            observations: observations,
            assessment: assessment,
            processing: processing
        ))
    }

    // MARK: - Field parsers

    private static func parseObservation(_ value: Any, index: Int, problems: inout [String]) -> Observation? {
        guard let dict = value as? [String: Any] else {
            problems.append("observations[\(index)]: not an object")
            return nil
        }
        let prefix = "observations[\(index)]"
        let category = nonEmptyString(dict["category"], field: "\(prefix).category", problems: &problems)
        let description = nonEmptyString(dict["description"], field: "\(prefix).description", problems: &problems)

        var evidence: String?
        if let value = dict["evidence"] as? String {
            evidence = value
        } else {
            problems.append("\(prefix).evidence: missing or not a string")
        }

        var confidence: Double?
        var confidenceValid = false
        if let raw = dict["confidence"] {
            if raw is NSNull {
                confidenceValid = true
            } else if let number = jsonNumber(raw) {
                if number < 0 || number > 1 {
                    problems.append("\(prefix).confidence: out of range 0...1")
                } else {
                    confidence = number
                    confidenceValid = true
                }
            } else {
                problems.append("\(prefix).confidence: must be null or a number")
            }
        } else {
            problems.append("\(prefix).confidence: missing (must be present, null when unreported)")
        }

        guard let category = category, let description = description, let evidence = evidence, confidenceValid else {
            return nil
        }
        return Observation(category: category, description: description, evidence: evidence, confidence: confidence)
    }

    private static func parseAssessment(_ dict: [String: Any], problems: inout [String]) -> AssessmentDetail? {
        let category = nonEmptyString(dict["category"], field: "assessment.category", problems: &problems)

        var summary: String?
        if let value = dict["summary"] as? String {
            summary = value
        } else {
            problems.append("assessment.summary: missing or not a string")
        }

        var uncertainty: [String]?
        if let rawList = dict["uncertainty"] as? [Any] {
            var list: [String] = []
            var allStrings = true
            for (index, item) in rawList.enumerated() {
                if let string = item as? String {
                    list.append(string)
                } else {
                    problems.append("assessment.uncertainty[\(index)]: not a string")
                    allStrings = false
                }
            }
            if allStrings {
                uncertainty = list
            }
        } else {
            problems.append("assessment.uncertainty: missing or not an array")
        }

        var requiresHumanReview: Bool?
        if let raw = dict["requires_human_review"] {
            if let bool = jsonBool(raw) {
                requiresHumanReview = bool
            } else {
                problems.append("assessment.requires_human_review: missing or not a boolean")
            }
        } else {
            problems.append("assessment.requires_human_review: missing or not a boolean")
        }

        guard let category = category, let summary = summary, let uncertainty = uncertainty,
              let requiresHumanReview = requiresHumanReview
        else {
            return nil
        }
        return AssessmentDetail(
            category: category,
            summary: summary,
            uncertainty: uncertainty,
            requiresHumanReview: requiresHumanReview
        )
    }

    private static func parseProcessing(_ dict: [String: Any], problems: inout [String]) -> ProcessingInfo? {
        let model = nonEmptyString(dict["model"], field: "processing.model", problems: &problems)

        var latencyMs: Double?
        var latencyValid = false
        if let raw = dict["latency_ms"] {
            if raw is NSNull {
                latencyValid = true
            } else if let number = jsonNumber(raw) {
                if number < 0 {
                    problems.append("processing.latency_ms: must not be negative")
                } else {
                    latencyMs = number
                    latencyValid = true
                }
            } else {
                problems.append("processing.latency_ms: must be null or a number")
            }
        } else {
            problems.append("processing.latency_ms: missing (must be present, null when unreported)")
        }

        guard let model = model, latencyValid else {
            return nil
        }
        return ProcessingInfo(model: model, latencyMs: latencyMs)
    }

    // MARK: - JSON primitives

    private static func nonEmptyString(_ value: Any?, field: String, problems: inout [String]) -> String? {
        if let string = value as? String,
           !string.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return string
        }
        problems.append("\(field): missing or not a non-empty string")
        return nil
    }

    /// JSONSerialization represents JSON booleans and numbers both as
    /// NSNumber; the CoreFoundation type id is the reliable way to tell
    /// them apart, so `1` is never accepted as `true` or vice versa.
    private static func jsonBool(_ value: Any) -> Bool? {
        guard let number = value as? NSNumber, CFGetTypeID(number) == CFBooleanGetTypeID() else {
            return nil
        }
        return number.boolValue
    }

    private static func jsonNumber(_ value: Any) -> Double? {
        guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID() else {
            return nil
        }
        return number.doubleValue
    }
}
