//! Port of `os/intel/integration.py` — environment wiring for intel.
//!
//! `env_for(room)` builds the env map a worker needs; `export_lines`
//! renders `KEY=value` lines; `apply_env` merges into a process env;
//! `room_bus_key(room)` names the room's bus key.

use std::collections::HashMap;

pub fn env_for(room: &str) -> HashMap<String, String> {
    let mut m = HashMap::new();
    m.insert("INTEL_ROOM".to_string(), room.to_string());
    m.insert("MUSE_RELAY_ROOM".to_string(), room.to_string());
    m
}

pub fn export_lines(env: &HashMap<String, String>) -> Vec<String> {
    let mut keys: Vec<&String> = env.keys().collect();
    keys.sort();
    keys.into_iter().map(|k| format!("{k}={}", env[k])).collect()
}

pub fn apply_env(base: &mut HashMap<String, String>, extra: &HashMap<String, String>) {
    for (k, v) in extra {
        base.insert(k.clone(), v.clone());
    }
}

pub fn room_bus_key(room: &str) -> String {
    format!("muse-bus:room:{room}")
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn env_roundtrip() {
        let e = env_for("main");
        assert_eq!(e["INTEL_ROOM"], "main");
        let lines = export_lines(&e);
        assert!(lines.iter().any(|l| l == "INTEL_ROOM=main"));
    }
}
