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
    case scienceLab = "science-lab"

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
        case .scienceLab: return scienceLab
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
            "electrical fire indicators",
            "gas fire indicators",
            "cooking oil fire indicators",
            "metal fire indicators",
            "battery fire indicators",
            "vehicle fire",
            "structure fire",
            "smoldering fire",
            "dark smoke",
            "brown smoke",
        ],
        scenarios: [
            "Visible smoke",
            "Visible flames",
            "Normal scenes without fire or smoke",
            "Steam or fog that might be mistaken for smoke",
            "Lighting conditions that resemble flames",
            "Partially obscured or distant visual hazards",
            "Scenes the model cannot confidently interpret",
            "Sparks or arcing from wiring, an outlet, or an electrical panel",
            "A blue flame jet from a gas pipe, stove, or gas line",
            "Flames rising from a fryer or a pan of cooking oil",
            "An intensely bright white flame with a shower of sparks",
            "An e-bike or device battery venting sparks and intense flame",
            "A vehicle on fire",
            "A building with flame or heavy smoke at its windows",
            "Thick dark smoke from burning fuel, plastics, or rubber",
            "Brown smoke from burning wood or building framing",
            "Smoldering material producing smoke with no visible flame",
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
            "person down in roadway",
            "person slumped in vehicle",
            "person in or near water",
            "person trapped or pinned",
            "bystander aid in progress",
            "multi-person incident scene",
            "blood visible at scene",
        ],
        scenarios: [
            "A person on the ground",
            "A crowd gathered around a person",
            "A vehicle collision scene",
            "Blocked access for responding crews",
            "A person motionless",
            "Normal activity, no incident visible",
            "Poor visibility or ambiguous conditions",
            "A person down in the roadway",
            "A person slumped over in a parked vehicle",
            "A person in or at the edge of a body of water",
            "A person trapped or pinned by a vehicle or debris",
            "Bystanders giving aid to a person on the ground",
            "Several people down in one scene",
            "Blood visible on a person or on the ground",
            "A person sleeping on a bench",
            "A person sunbathing",
            "A person doing yoga or stretching",
            "A CPR training manikin on the ground",
        ],
        limitations: "Scene awareness only. It does not diagnose any condition, guess a cause, assess severity, or recommend treatment. A person who appears motionless may simply be resting. No automatic dispatch. Every assessment requires human verification. Location is used only if explicitly provided; this app never invents geographic coordinates.",
        inputGuidance: "Live camera aimed at the scene: people and vehicles visible from a safe distance. Never stage an emergency or put anyone at risk to test it; use prerecorded footage or safe visual demonstrations only."
    )

    // HN-077 Swift mirror: science-lab config, strings byte-identical to
    // the web entry in js/products.js (accent #7c5cbf, carried here as
    // the color name "purple" — the parity test maps it to that hex).
    static let scienceLab = ProductConfig(
        product: .scienceLab,
        displayName: "Meta Science Lab",
        department: "Research-oriented — autonomous scientific discovery",
        tagline: "Competing hypotheses, structured computation, and independent verification — every claim labelled with its evidence level.",
        accentColorName: "purple",
        categories: [
            "level 0: idea",
            "level 1: evidence supported",
            "level 2: computationally tested",
            "level 3: independently reproduced",
            "level 4: experimentally validated",
            "level 5: independently replicated",
            "level 6: established application",
        ],
        scenarios: [
            "Reproducing a published computational result end to end (the stage 1 gate)",
            "A hypothesis filed without a disproof condition is refused",
            "A finding the verifier cannot reproduce is vetoed and stays at its level",
            "A failed run is kept in the record, not deleted",
            "An empty literature search is not treated as proof of novelty",
            "A docking-style prediction is labelled a prediction, never a discovery",
        ],
        limitations: "Partial build: the pack, its record schemas, and the Hortus breeding engine are built and recorded — Hortus runs are verifier-gated, its scorer was calibrated against real manufacturer datasheets, and its champion stands at rung 2 of 4 — but the lab is not yet a running discovery system and makes no discovery claims; the stage 1 reproduction gate has not been run. Every claim carries an evidence level from 0 to 6 and may never be shown above the level its record holds. Levels 4 to 6 require physical experiments by qualified humans and are unreachable by this system alone. Model agreement is not evidence; only retrieved sources, structured computation, and independent re-execution move a claim up the ladder. Failed hypotheses and failed runs are kept, never deleted. No autonomous synthesis, biological engineering, or human or animal experimentation pathways exist in this system; hazardous applications are blocked, not routed.",
        inputGuidance: "State a research problem or choose a staged scenario. The lab works from retrieved original sources and signed, structured compute jobs — never from a bare prompt, and never with unrestricted terminal access."
    )
}
