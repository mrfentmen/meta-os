// Per-product configuration for the Meta Trio (MASTER_DIRECTIVE_V2.md
// section 6), mirrored from native/Sources/MetaTrio/Models/ProductConfig.swift.
// The shared pipeline (camera, sampler, client, validation, log) never
// branches on product identity; it only reads these values and sends the
// product id to the server, which applies the matching prompt profile.
// Pure data, no DOM access: safe to import from browser and node tests.

export const PRODUCTS = [
  {
    id: "vigiles",
    displayName: "Meta Vigiles",
    department: "NYPD-oriented — visual incident awareness",
    tagline: "Evidence-supported event assessments for human review.",
    accent: "#4f7ec2",
    categories: [
      "normal activity",
      "energetic movement",
      "ambiguous gesture",
      "staged verbal dispute",
      "physical contact",
      "person down",
      "possible altercation",
      "crowd gathered",
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
    limitations:
      "Prototype for visual incident awareness. It does not establish that a crime has occurred, determine guilt, or reliably infer criminal intent from body movements. No face recognition, no identity tracking, no automatic dispatch. Staged scenarios with consenting participants only; no public CCTV.",
    inputGuidance:
      "Live camera. Perform staged actions in view of the camera; analysis samples frames at the interval set below.",
  },
  {
    id: "ignis",
    displayName: "Meta Ignis",
    department: "FDNY-oriented — fire and smoke hazard awareness",
    tagline: "Visible fire and smoke hazard indicators for human review.",
    accent: "#d92b2b",
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
    limitations:
      "Not a certified fire-detection system, and not a replacement for fire alarms, established detection systems, or professional emergency judgment. No automatic dispatch. Never create a real fire to test it — use prerecorded footage or safe visual demonstrations only.",
    inputGuidance:
      "Point the camera at prerecorded footage on another screen or at a safe, controlled visual demonstration. Never a real fire.",
  },
  {
    id: "medicus",
    displayName: "Meta Medicus",
    department: "FDNY EMS-oriented — medical incident scene awareness",
    tagline: "Visible scene indicators for EMS crews, for human review.",
    accent: "#5da864",
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
    limitations:
      "Scene awareness only. It does not diagnose any condition, guess a cause, assess severity, or recommend treatment. A person who appears motionless may simply be resting. No automatic dispatch. Every assessment requires human verification. Location is used only if explicitly provided; this app never invents geographic coordinates.",
    inputGuidance:
      "Live camera aimed at the scene: people and vehicles visible from a safe distance. Never stage an emergency or put anyone at risk to test it; use prerecorded footage or safe visual demonstrations only.",
  },
  {
    id: "science-lab",
    displayName: "Meta Science Lab",
    department: "Research-oriented — autonomous scientific discovery",
    tagline: "Competing hypotheses, structured computation, and independent verification — every claim labelled with its evidence level.",
    accent: "#7c5cbf",
    // For Science Lab the categories are not scene types; they are the
    // claim vocabulary of the evidence ladder (LABORATORY section 7).
    // A finding's level is a field on its record, so the UI can only
    // ever display a claim at the level the record actually holds.
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
    limitations:
      "Partial build: the pack, its record schemas, and the Hortus breeding engine are built and recorded — Hortus runs are verifier-gated, its scorer was calibrated against real manufacturer datasheets, and its champion stands at rung 2 of 4 — but the lab is not yet a running discovery system and makes no discovery claims; the stage 1 reproduction gate has not been run. Every claim carries an evidence level from 0 to 6 and may never be shown above the level its record holds. Levels 4 to 6 require physical experiments by qualified humans and are unreachable by this system alone. Model agreement is not evidence; only retrieved sources, structured computation, and independent re-execution move a claim up the ladder. Failed hypotheses and failed runs are kept, never deleted. No autonomous synthesis, biological engineering, or human or animal experimentation pathways exist in this system; hazardous applications are blocked, not routed.",
    inputGuidance:
      "State a research problem or choose a staged scenario. The lab works from retrieved original sources and signed, structured compute jobs — never from a bare prompt, and never with unrestricted terminal access.",
  },
];

// One line per category, in the same words the app shows. A category without a
// definition is a word the operator cannot act on, so `definitionFor` refuses it
// instead of returning an empty string that renders as a blank row.
export const CATEGORY_DEFINITIONS = {
  // Vigiles
  "normal activity": "Ordinary movement or stillness with no hazard indicated.",
  "energetic movement": "Fast or large motion that may be play, sport, or urgency.",
  "ambiguous gesture": "A movement whose intent cannot be read from the frame alone.",
  "staged verbal dispute": "An argument performed for the camera, with no physical contact.",
  "physical contact": "People touching in a way that may be contact or collision.",
  "person down": "A person on the ground, whatever the cause.",
  "possible altercation": "Contact or posture that resembles a fight and may not be one.",
  "crowd gathered": "A stationary assembled crowd: a rally, an audience, a queue, onlookers. Ordinary pedestrian traffic in motion is normal activity.",
  indeterminate: "The frame does not support a category at all.",

  // Ignis
  "visible smoke": "Smoke is visible in the frame.",
  "visible flame": "Flame is visible in the frame.",
  "steam or fog": "Vapour that resembles smoke and is not burning.",
  "flame-like lighting": "Lighting that looks like flame and is not fire.",
  "obscured or distant hazard": "A hazard is suggested but the view does not settle it.",
  "no hazard visible": "Neither smoke nor flame is visible.",
  "electrical fire indicators": "Sparks or arcing from wiring, an outlet, or a panel.",
  "gas fire indicators": "A blue flame jet from a gas pipe, stove, or line.",
  "cooking oil fire indicators": "Flames rising from a fryer or a pan of oil.",
  "metal fire indicators": "An intensely bright white flame with a shower of sparks.",
  "battery fire indicators": "A battery venting sparks and intense flame.",
  "vehicle fire": "A vehicle with flame or heavy smoke.",
  "structure fire": "A building with flame or heavy smoke at its windows.",
  "smoldering fire": "Material producing smoke with no visible flame.",
  "dark smoke": "Thick dark smoke from fuel, plastics, or rubber.",
  "brown smoke": "Brown smoke from burning wood or building framing.",

  // Medicus
  "person on ground": "A person on the ground, seen from a safe distance.",
  "crowd gathered around a person": "People standing around someone on the ground.",
  "vehicle collision scene": "Vehicles and people after a collision.",
  "blocked crew access": "The scene cannot be reached by the usual route.",
  "person motionless": "A person not moving, who may simply be resting.",
  "person down in roadway": "A person on the ground in a travelled lane.",
  "person slumped in vehicle": "A person slumped over inside a parked vehicle.",
  "person in or near water": "A person at the edge of, or in, water.",
  "person trapped or pinned": "A person held by a vehicle or debris.",
  "bystander aid in progress": "Untrained people giving aid at the scene.",
  "multi-person incident scene": "More than one person down in one scene.",
  "blood visible at scene": "Blood visible on a person or on the ground.",

  // Science Lab evidence ladder
  "level 0: idea": "A hypothesis filed, with no evidence yet.",
  "level 1: evidence supported": "A claim with retrieved sources behind it.",
  "level 2: computationally tested": "A claim with a signed compute job behind it.",
  "level 3: independently reproduced": "A claim another party re-ran and reproduced.",
  "level 4: experimentally validated": "A claim tested in a physical experiment.",
  "level 5: independently replicated": "A level 4 claim replicated by another group.",
  "level 6: established application": "A claim in established use.",

  // Musica studio briefs
  chipsynth: "Fast square-wave chip music: bright leads, driving bass, noise hats.",
  ambient: "Slow pad music with a sparse melody and quiet hats.",
  "boom-bap": "Sampled-feel drum loops under a laid-back melodic line.",
};

// Throws on a category nobody defined: a blank definition in the UI is a lie of
// omission, and this is the one place that can refuse it.
export function definitionFor(category) {
  const text = CATEGORY_DEFINITIONS[category];
  if (typeof text !== "string" || text.trim() === "") {
    throw new Error("products: no definition for category " + JSON.stringify(category));
  }
  return text;
}

export const PRODUCT_BY_ID = Object.fromEntries(PRODUCTS.map((p) => [p.id, p]));

export const PRODUCT_IDS = PRODUCTS.map((p) => p.id);

// Studio products (NOT Trio assessment products). Musica is a Meta
// World studio, not a fourth 911 service: it must never enter the
// Trio PRODUCTS array, because that array drives the camera
// assessment contract (server/model.mjs PRODUCT_PROFILES, assess.mjs
// product validation) and the web<->native parity test pins it to
// the Trio three. The Swift Trio mirror (ProductConfig.swift) is
// therefore unaffected by Musica; if Musica ever becomes an
// assessment product, the Swift mirror needs a matching case first.
// HN-027: Musica's registry entry lives here, in js/products.js.
export const STUDIO_PRODUCTS = [
  {
    id: "musica",
    displayName: "Meta Musica",
    department: "Studio — generated music from written briefs",
    tagline: "The studio that never closes: real takes, logged, kept or rejected on the record.",
    accent: "#8b5cf6",
    categories: ["chipsynth", "ambient", "boom-bap"],
    scenarios: [
      "A chipsynth take from its genre brief",
      "An ambient take from its genre brief",
      "A boom-bap take from its genre brief",
    ],
    limitations:
      "A composition studio, not a record label and not a human performance. Every track is generated in-studio from a written genre brief and a seed; no track is a human performance, and no rights are claimed beyond the studio's own generated material. No live model calls are made from this sandbox; Spark assist records its prompts and its held/not-configured state, never a fabricated reply. Stage-1 studio: the loop, keeper bar, and catalogue are real, but Spark-assisted composition is not yet live.",
    inputGuidance:
      "Pick a genre brief and a seed; the loop renders real audio takes and logs every attempt. Keepers land in the catalogue with a licence line; rejects stay in the reject log.",
  },
];

export const STUDIO_PRODUCT_BY_ID = Object.fromEntries(
  STUDIO_PRODUCTS.map((p) => [p.id, p]),
);

export function isProductId(value) {
  return typeof value === "string" && Object.hasOwn(PRODUCT_BY_ID, value);
}

// World packs (Meta OS institutions) register here, NOT in PRODUCTS.
// PRODUCTS is the Trio camera-product list, guarded by the
// product-parity test (web must equal native, exactly three camera
// products). A machine watch is not a camera product: it has no
// observation categories and must never appear in the camera picker,
// so Custos registers as a world entry with its own shape and
// status, and the Trio list stays exactly vigiles / ignis / medicus.
// A workshop is not a camera product either, so Officina registers
// the same way.
export const WORLD_PRODUCTS = [
  {
    id: "custos",
    displayName: "Meta Custos",
    department: "Machine infrastructure watch — the night watch for machines",
    tagline: "A patrol that watches certificates, services, and known-exploited vulnerabilities while humans sleep.",
    accent: "#587b8f",
    status: "stage-1",
    pack: "os/worlds/custos",
    runtime: "os/worlds/custos/runtime/patrol.py",
  },
  {
    id: "officina",
    displayName: "Meta Officina",
    department: "Invention workshop — agent design iteration",
    tagline: "An agent that designs, simulates, breaks, and redesigns.",
    accent: "#b07d2b",
    status: "stage-1",
    pack: "os/worlds/officina",
    runtime: "os/worlds/officina/runtime/design_loop.py",
  },
];
