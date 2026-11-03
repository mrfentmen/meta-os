//! CB2-326/327/328/348 — the agent registry, loaded strictly.
//!
//! The fixture case embeds the REAL `agents/registry.json` at compile time, so
//! the count it pins is the count the tree actually carries. If the registry
//! gains or loses an agent, this test is meant to notice.
use agent_runtime::registry::{
    drafts, is_placeholder, parse_registry, parse_registry_text, runnable, AgentDef,
    RegistryError, PLACEHOLDER_COMMAND,
};
use serde_json::json;

fn registry(entries: serde_json::Value) -> serde_json::Value {
    json!({ "agents": entries })
}

#[test]
fn agent_empty_command_refused() {
    let err = parse_registry(&registry(json!([{ "name": "bond", "command": [] }]))).unwrap_err();
    assert_eq!(err, RegistryError("registry: entry 0 (bond) command must not be empty".to_string()));

    // A missing command, a non-array command, and a blank argument are all
    // refusals with the position named — never an empty spawn.
    let missing = parse_registry(&registry(json!([{ "name": "bond" }]))).unwrap_err();
    assert!(missing.0.contains("command must be an array of strings"), "{missing:?}");

    let wrong = parse_registry(&registry(json!([{ "name": "bond", "command": "true" }]))).unwrap_err();
    assert!(wrong.0.contains("command must be an array of strings"), "{wrong:?}");

    let blank = parse_registry(&registry(json!([{ "name": "bond", "command": ["node", "  "] }]))).unwrap_err();
    assert_eq!(blank.0, "registry: entry 0 (bond) command[1] must be a non-empty string");

    // A nameless entry has nothing to spawn by name.
    let nameless = parse_registry(&registry(json!([{ "command": ["true"] }]))).unwrap_err();
    assert_eq!(nameless.0, "registry: entry 0 has no name");
}

#[test]
fn agent_draft_detected() {
    // The placeholder command is a draft even with no flag: it would exit zero
    // forever and look like success.
    let loaded = parse_registry(&registry(json!([
        { "name": "placeholder", "command": ["true"] },
        { "name": "flagged", "command": ["node", "server.mjs"], "draft": true },
        { "name": "real", "command": ["node", "server.mjs"] },
    ])))
    .expect("all three load");

    assert!(is_placeholder(&[PLACEHOLDER_COMMAND.to_string()]));
    assert!(!is_placeholder(&["node".to_string(), "server.mjs".to_string()]));

    let by_name = |name: &str| loaded.iter().find(|a| a.name == name).cloned().unwrap();

    let placeholder = by_name("placeholder");
    assert!(placeholder.draft, "placeholder command is a draft");
    assert!(!placeholder.declared_draft, "the flag was absent; detection did it");

    let flagged = by_name("flagged");
    assert!(flagged.draft);
    assert!(flagged.declared_draft);

    let real: AgentDef = by_name("real");
    assert!(!real.draft, "a real command is runnable");

    assert_eq!(runnable(&loaded).len(), 1);
    assert_eq!(drafts(&loaded).len(), 2);
    assert_eq!(runnable(&loaded)[0].name, "real");
}

#[test]
fn registry_duplicate_name() {
    let err = parse_registry(&registry(json!([
        { "name": "bond", "command": ["node", "a.mjs"] },
        { "name": "bond", "command": ["node", "b.mjs"] },
    ])))
    .unwrap_err();
    assert_eq!(
        err.0,
        "registry: duplicate agent name bond at entry 1 (first at entry 0)",
        "both indexes are named so the duplicate can be found",
    );

    // Not valid JSON at all is a named refusal, not a panic.
    let bad = parse_registry_text("{not json").unwrap_err();
    assert!(bad.0.starts_with("registry: not valid JSON:"), "{bad:?}");
    assert!(parse_registry(&json!({})).unwrap_err().0.contains("'agents' must be an array"));
}

#[test]
fn registry_fixture_loads() {
    // A compile-time copy of the real registry: the count below is the file's
    // own count, pinned so a silent drop is a red test.
    const REAL: &str = include_str!("../../../agents/registry.json");
    let agents = parse_registry_text(REAL).expect("the real registry loads");

    assert_eq!(agents.len(), 29, "the registry carries 29 agents");
    assert_eq!(drafts(&agents).len(), 23, "23 of them are drafts");
    assert_eq!(runnable(&agents).len(), 6, "6 are runnable");

    for agent in &agents {
        assert!(!agent.name.trim().is_empty());
        assert!(!agent.command.is_empty(), "{} has a command", agent.name);
        if agent.draft {
            assert!(
                agent.declared_draft || is_placeholder(&agent.command),
                "{} is a draft for a stated reason",
                agent.name,
            );
        }
    }
    // Every draft the file declares is also detected, so the flag and the
    // placeholder agree today.
    assert_eq!(
        agents.iter().filter(|a| a.declared_draft).count(),
        23,
        "the declared draft flags match the detected drafts",
    );
}
