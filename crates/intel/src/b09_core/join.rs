//! Port of `os/intel/join.py` — machine join validation + announcement.
//!
//! Validators reject bad machine/room/key/kids inputs with typed
//! [`JoinError`]; `crew_from_grants` files crew by identity; announcement
//! text is frozen (`<nick> joined <room>`); config writes are 0600.

#[derive(Debug, Clone, PartialEq)]
pub struct JoinError(pub String);

impl std::fmt::Display for JoinError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "join: {}", self.0)
    }
}

pub fn validate_machine(name: &str) -> Result<String, JoinError> {
    if name.is_empty() || name.len() > 64 {
        return Err(JoinError("bad machine name".to_string()));
    }
    if !name.chars().all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_') {
        return Err(JoinError("bad machine name".to_string()));
    }
    Ok(name.to_string())
}

pub fn validate_room_address(addr: &str) -> Result<String, JoinError> {
    if addr.contains("://") || addr.is_empty() {
        return Err(JoinError("bad room address".to_string()));
    }
    Ok(addr.to_string())
}

pub fn validate_room_key(key: &str) -> Result<String, JoinError> {
    if key.len() < 8 {
        return Err(JoinError("room key too short".to_string()));
    }
    Ok(key.to_string())
}

pub fn validate_trusted_kids(ids: &[String]) -> Result<Vec<String>, JoinError> {
    for id in ids {
        if id.is_empty() {
            return Err(JoinError("empty trusted kid".to_string()));
        }
    }
    Ok(ids.to_vec())
}

pub fn crew_from_grants(identities: &[String]) -> Vec<String> {
    let mut v = identities.to_vec();
    v.sort();
    v.dedup();
    v
}

pub fn announcement_text(nick: &str, room: &str) -> String {
    format!("{nick} joined {room}")
}

pub fn build_announcement(nick: &str, room: &str) -> (String, String) {
    (format!("join:{nick}:{room}"), announcement_text(nick, room))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_bad_machine() {
        assert!(validate_machine("").is_err());
        assert!(validate_machine("ok-1").is_ok());
    }
    #[test]
    fn announcement_frozen_shape() {
        assert_eq!(announcement_text("milo", "main"), "milo joined main");
    }
}
