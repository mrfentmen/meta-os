import Foundation

// Per-product configuration as data (MASTER_DIRECTIVE_V2.md section 6):
// one config per product — name, department, categories, evaluation
// scenarios, input guidance, and the product's stated limitations. The
// shared pipeline (camera, sampler, client, validation, log) never
// branches on product identity; it only reads these values and sends the
// product id to the server, which applies the matching prompt profile.

enum ProductID: String, CaseIterable, Identifiable, Codable {
    case vigiles
    case ignis
    case medicus

    var id: String { rawValue }

    var config: ProductConfig { ProductConfig.config(for: self) }
}

struct ProductConfig {
    let product: ProductID
    let displayName: String
    let department: String
    let tagline: String
    /// Name of the product's accent color, mapped to a SwiftUI Color in the
    /// view layer so this file stays Foundation-only.
    let accentColorName: String
    /// Categories the server may return for this product (informational;
    /// the categories shown in results always come from the real response).
    let categories: [String]
    /// Evaluation scenarios from the directive, for the demo/eval workflow.
    let scenarios: [String]
    /// The product's limitations, stated plainly and always on screen.
    let limitations: String
    /// How visual input is meant to be supplied for this product.
    let inputGuidance: String

    static func config(for product: ProductID) -> ProductConfig {
        switch product {
        case .vigiles: return vigiles
        case .ignis: return ignis
        case .medicus: return medicus
        }
    }

    static let vigiles = ProductConfig(
        product: .vigiles,
        displayName: "Meta Vigiles",
        department: "NYPD-oriented — visual incident awareness",
        tagline: "Evidence-supported event assessments for human review.",
        accentColorName: "blue",
        categories: [
            "normal activity",
            "energetic movement",
            "ambiguous gesture",
            "staged verbal dispute",
            "physical contact",
            "person down",
            "possible altercation",
            "indeterminate",
        ],
        scenarios: [
            "Normal walking and standing",
            "Dancing and energetic movement",
            "Waving arms or ambiguous gestures",
            "A staged argument",
            "A staged physical altercation",
            "A person falling or deliberately lowering themselves",
            "Harmless actions that resemble aggression",
            "Difficult camera angle, lighting, or partial obstruction",
        ],
        limitations: "Prototype for visual incident awareness. It does not establish that a crime has occurred, determine guilt, or reliably infer criminal intent from body movements. No face recognition, no identity tracking, no automatic dispatch. Staged scenarios with consenting participants only; no public CCTV.",
        inputGuidance: "Live camera. Perform staged actions in view of the camera; analysis samples frames at the interval set below."
    )

    static let ignis = ProductConfig(
        product: .ignis,
        displayName: "Meta Ignis",
        department: "FDNY-oriented — fire and smoke hazard awareness",
        tagline: "Visible fire and smoke hazard indicators for human review.",
        accentColorName: "red",
        categories: [
            "visible smoke",
            "visible flame",
            "steam or fog",
            "flame-like lighting",
            "obscured or distant hazard",
            "no hazard visible",
            "indeterminate",
        ],
        scenarios: [
            "Visible smoke",
            "Visible flames",
            "Normal scenes without fire or smoke",
            "Steam or fog that might be mistaken for smoke",
            "Lighting conditions that resemble flames",
            "Partially obscured or distant visual hazards",
            "Scenes the model cannot confidently interpret",
        ],
        limitations: "Not a certified fire-detection system, and not a replacement for fire alarms, established detection systems, or professional emergency judgment. No automatic dispatch. Never create a real fire to test it — use prerecorded footage or safe visual demonstrations only.",
        inputGuidance: "Point the camera at prerecorded footage on another screen or at a safe, controlled visual demonstration. Never a real fire."
    )

    static let medicus = ProductConfig(
        product: .medicus,
        displayName: "Meta Medicus",
        department: "FDNY EMS-oriented — medical incident scene awareness",
        tagline: "Visible scene indicators for EMS crews, for human review.",
        accentColorName: "green",
        categories: [
            "person on ground",
            "crowd gathered around a person",
            "vehicle collision scene",
            "blocked crew access",
            "person motionless",
            "normal activity",
            "indeterminate",
        ],
        scenarios: [
            "A person on the ground",
            "A crowd gathered around a person",
            "A vehicle collision scene",
            "Blocked access for responding crews",
            "A person motionless",
            "Normal activity, no incident visible",
            "Poor visibility or ambiguous conditions",
        ],
        limitations: "Scene awareness only. It does not diagnose any condition, guess a cause, assess severity, or recommend treatment. A person who appears motionless may simply be resting. No automatic dispatch. Every assessment requires human verification. Location is used only if explicitly provided; this app never invents geographic coordinates.",
        inputGuidance: "Live camera aimed at the scene: people and vehicles visible from a safe distance. Never stage an emergency or put anyone at risk to test it; use prerecorded footage or safe visual demonstrations only."
    )
}
