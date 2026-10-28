import Foundation

// The unified v2 assessment contract shared by Meta Sentinel, Meta Ember,
// and Meta Sanitas (MASTER_DIRECTIVE_V2.md section 9, frozen in
// FIRST_RESPONSE.md). The server returns exactly this shape or an
// {"error": "..."} object. Instances are only ever created by
// ContractValidator after strict validation of a real server response —
// nothing in this app fabricates an assessment.
//
// Honesty rules baked into the types:
// - Observation.confidence is Optional: null unless the model returned a
//   real number. Never defaulted, never invented.
// - ProcessingInfo.latencyMs is Optional: null unless the server reported
//   it. The client-side round-trip time is measured separately by
//   AssessClient and recorded in the session log; the two are never mixed.

struct AssessmentResponse: Codable, Equatable {
    let product: String
    let timestamp: String
    let observations: [Observation]
    let assessment: AssessmentDetail
    let processing: ProcessingInfo
}

struct Observation: Codable, Equatable {
    let category: String
    let description: String
    let evidence: String
    let confidence: Double?

    enum CodingKeys: String, CodingKey {
        case category
        case description
        case evidence
        case confidence
    }
}

struct AssessmentDetail: Codable, Equatable {
    let category: String
    let summary: String
    let uncertainty: [String]
    let requiresHumanReview: Bool

    enum CodingKeys: String, CodingKey {
        case category
        case summary
        case uncertainty
        case requiresHumanReview = "requires_human_review"
    }
}

struct ProcessingInfo: Codable, Equatable {
    let model: String
    let latencyMs: Double?

    enum CodingKeys: String, CodingKey {
        case model
        case latencyMs = "latency_ms"
    }
}
