//! The agent registry, loaded strictly.
//!
//! `agents/registry.json` is the list of agents the runtime may spawn. Two
//! failures this module exists to prevent:
//!
//! 1. **A draft that looks runnable.** An entry whose command is the
//!    placeholder `["true"]` does nothing and exits zero, so a supervisor that
//!    runs it reports success forever. Such an entry loads as a *draft*: it is
//!    visible, and it is never counted as runnable.
//! 2. **A duplicate name.** Two entries with one name make "spawn bond" a coin
//!    flip, so the whole registry is refused and both indexes are named.
//!
//! Parsing is from `serde_json::Value`, the crate's existing JSON type: no
//! new dependency, and no second JSON dialect.

use serde_json::Value;

/// The placeholder command: an agent that runs `true` and exits zero without
/// doing anything. It is the draft marker.
pub const PLACEHOLDER_COMMAND: &str = "true";

/// One loaded agent definition.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AgentDef {
    pub name: String,
    pub command: Vec<String>,
    /// The entry's own `draft` flag, if it carried one.
    pub declared_draft: bool,
    /// `declared_draft` or the placeholder command. A draft is never spawned.
    pub draft: bool,
}

/// A registry that must not be used, with the reason named.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RegistryError(pub String);

/// True when a command is exactly the placeholder `["true"]`.
pub fn is_placeholder(command: &[String]) -> bool {
    command.len() == 1 && command[0] == PLACEHOLDER_COMMAND
}

fn strings(value: Option<&Value>, at: &str) -> Result<Vec<String>, RegistryError> {
    let arr = value
        .and_then(Value::as_array)
        .ok_or_else(|| RegistryError(format!("{at} command must be an array of strings")))?;
    if arr.is_empty() {
        return Err(RegistryError(format!("{at} command must not be empty")));
    }
    let mut out = Vec::with_capacity(arr.len());
    for (i, raw) in arr.iter().enumerate() {
        let s = raw
            .as_str()
            .filter(|s| !s.trim().is_empty())
            .ok_or_else(|| RegistryError(format!("{at} command[{i}] must be a non-empty string")))?;
        out.push(s.to_string());
    }
    Ok(out)
}

/// Parse a registry document. Refuses on the first structural error and on any
/// duplicate name; returns every entry otherwise, drafts included.
pub fn parse_registry(value: &Value) -> Result<Vec<AgentDef>, RegistryError> {
    let agents = value
        .get("agents")
        .and_then(Value::as_array)
        .ok_or_else(|| RegistryError("registry: 'agents' must be an array".to_string()))?;

    let mut out: Vec<AgentDef> = Vec::with_capacity(agents.len());
    let mut seen: Vec<(String, usize)> = Vec::new();

    for (index, entry) in agents.iter().enumerate() {
        if !entry.is_object() {
            return Err(RegistryError(format!("registry: entry {index} is not an object")));
        }
        let name = entry
            .get("name")
            .and_then(Value::as_str)
            .filter(|s| !s.trim().is_empty())
            .ok_or_else(|| RegistryError(format!("registry: entry {index} has no name")))?;
        let at = format!("registry: entry {index} ({name})");
        let command = strings(entry.get("command"), &at)?;

        if let Some((_, first)) = seen.iter().find(|(n, _)| n == name) {
            return Err(RegistryError(format!(
                "registry: duplicate agent name {name} at entry {index} (first at entry {first})"
            )));
        }
        seen.push((name.to_string(), index));

        let declared_draft = entry.get("draft").and_then(Value::as_bool).unwrap_or(false);
        let placeholder = is_placeholder(&command);
        out.push(AgentDef {
            name: name.to_string(),
            command,
            declared_draft,
            draft: declared_draft || placeholder,
        });
    }
    Ok(out)
}

/// Parse a registry from its file text. Separate from [`parse_registry`] so a
/// caller that already holds the bytes (a fixture, a fetched copy) needs no
/// filesystem.
pub fn parse_registry_text(text: &str) -> Result<Vec<AgentDef>, RegistryError> {
    let value: Value = serde_json::from_str(text)
        .map_err(|e| RegistryError(format!("registry: not valid JSON: {e}")))?;
    parse_registry(&value)
}

/// The entries that may actually be spawned: drafts excluded.
pub fn runnable(agents: &[AgentDef]) -> Vec<&AgentDef> {
    agents.iter().filter(|a| !a.draft).collect()
}

/// The entries that are drafts, in registry order.
pub fn drafts(agents: &[AgentDef]) -> Vec<&AgentDef> {
    agents.iter().filter(|a| a.draft).collect()
}
