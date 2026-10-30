//! Service-loop caller for `watchman_tick()` (OS-122 follow-up).
//!
//! Port of `os/intel/watchman_loop.py`. `watchman_tick()` folds one
//! cycle's relay-watchman events per machine and judges them, but it is
//! a pure call: it keeps no state between cycles, runs no watchman, and
//! reads no stdout. This module is the caller that will sit in the
//! production loop, written against the interfaces that already exist so
//! it can be drilled on fixtures today and wired to the real
//! relay-watchman CLI later without changing its judgment:
//!
//! - One run per machine per cycle is a relay-watchman `--once` run:
//!   exit 0 means the run happened and its stdout is one JSON event
//!   object per line; anything else means the run failed and its stdout
//!   is unusable.
//! - [`loop_cycle`] takes `{machine: run}` for the cycle, plus the priors
//!   and journal the loop carries, and returns `(records, new_journal,
//!   diagnostics)`.
//!
//! Judgment rules, ported verbatim:
//! - A successful run folds through `watchman_tick()`, exactly as the
//!   bridge documents: a tick proves the watchman ran, a wake event
//!   proves the bell, a quiet tick keeps `last_bell` None and reads
//!   unknown, never alive.
//! - A failed run folds nothing fresh. Instead the machine's last real
//!   record, when one exists, is carried forward unchanged into the
//!   judge, so its bell ages honestly. A failed run for a machine with
//!   no prior record is unjudged, and the failure is recorded only in
//!   diagnostics, never as a watchman record.
//! - A carried record drops `restart_ok`: a restart outcome is a fact of
//!   the cycle that ran it, never something carried forward.
//! - Malformed stdout lines are contained per machine: a junk line counts
//!   in diagnostics and never breaks the machine's good events or any
//!   other machine.
//! - Inputs are never mutated; carried records are copies.
//!
//! What this module does not claim: it runs no subprocess itself, starts
//! no agent session, restarts no process, reassigns no job, and sends no
//! push. A failed run here is a diagnostic line, and the escalation the
//! judge builds is a payload, never a send.
//!
//! Representation notes:
//! - Python stdout is parsed with `json.loads` per line. This std-only
//!   port includes a small JSON-object parser for event lines (no serde
//!   is available); it accepts the same shapes the loop's fixtures use
//!   (objects with string/number/bool/null/array/object values) and
//!   counts anything else as malformed, exactly as Python does.
//! - A Python run pair that is not a `(ok, stdout)` pair of length >= 2
//!   reads as a failed run with empty stdout. That shape is
//!   [`LoopRun::Malformed`]; a usable pair is [`LoopRun::Run`].

use std::collections::HashMap;

use crate::watchman_bridge::{
    snapshot_from_records, watchman_tick, WatchEvent,
};
use crate::watchman_watch::{
    JournalEntry, WatchmanRecord, watchman_watch_tick,
};

/// One machine's watchman run for a cycle.
///
/// `Run(ok, stdout)`: `ok` true means the relay-watchman `--once` run
/// exited 0 and stdout holds its event lines. `Malformed` is a run value
/// that is not a usable pair at all; it reads as a failed run with
/// empty stdout, exactly as Python reads a short or non-pair run.
#[derive(Clone, Debug, PartialEq)]
pub enum LoopRun {
    /// A usable `(ok, stdout)` pair.
    Run(bool, String),
    /// A run value that is not a usable pair.
    Malformed,
}

/// Per-cycle diagnostics from [`loop_cycle`].
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Diagnostics {
    /// Machines whose runs failed, in machine-name order.
    pub run_failures: Vec<String>,
    /// Malformed stdout line counts, present only for machines that had
    /// malformed lines.
    pub malformed_lines: HashMap<String, usize>,
}

/// Stdout text -> `(events, malformed_count)`.
///
/// One JSON object per non-blank line. A line that is not a JSON object
/// is malformed: it is counted, skipped, and never breaks the good lines
/// around it. `None` (a non-string input in Python) yields no events and
/// counts as one malformed line.
pub fn parse_event_lines(text: Option<&str>) -> (Vec<WatchEvent>, usize) {
    let text = match text {
        Some(text) => text,
        None => return (Vec::new(), 1),
    };
    let mut events = Vec::new();
    let mut malformed = 0;
    for line in text.lines() {
        if line.trim().is_empty() {
            continue;
        }
        match parse_event_object(line) {
            Some(event) => events.push(event),
            None => malformed += 1,
        }
    }
    (events, malformed)
}

/// Minimal JSON value, just enough to parse event lines.
#[derive(Clone, Debug, PartialEq)]
enum JsonValue {
    /// JSON null.
    Null,
    /// JSON boolean.
    Bool(bool),
    /// JSON number.
    Num(f64),
    /// JSON string.
    Str(String),
    /// JSON array (contents kept only for validity checking).
    Arr(Vec<JsonValue>),
    /// JSON object (key/value pairs, in order).
    Obj(Vec<(String, JsonValue)>),
}

/// A tiny recursive-descent JSON parser for one event line.
struct JsonParser {
    chars: Vec<char>,
    pos: usize,
}

impl JsonParser {
    fn new(text: &str) -> Self {
        JsonParser {
            chars: text.chars().collect(),
            pos: 0,
        }
    }

    fn skip_ws(&mut self) {
        while self.pos < self.chars.len() && self.chars[self.pos].is_whitespace() {
            self.pos += 1;
        }
    }

    fn peek(&self) -> Option<char> {
        self.chars.get(self.pos).copied()
    }

    fn eat(&mut self, expected: char) -> bool {
        if self.peek() == Some(expected) {
            self.pos += 1;
            true
        } else {
            false
        }
    }

    fn parse_value(&mut self) -> Option<JsonValue> {
        self.skip_ws();
        match self.peek()? {
            '{' => self.parse_object(),
            '[' => self.parse_array(),
            '"' => self.parse_string().map(JsonValue::Str),
            't' => self.parse_literal("true", JsonValue::Bool(true)),
            'f' => self.parse_literal("false", JsonValue::Bool(false)),
            'n' => self.parse_literal("null", JsonValue::Null),
            '-' | '0'..='9' => self.parse_number(),
            _ => None,
        }
    }

    fn parse_literal(&mut self, word: &str, value: JsonValue) -> Option<JsonValue> {
        for expected in word.chars() {
            if self.peek() != Some(expected) {
                return None;
            }
            self.pos += 1;
        }
        Some(value)
    }

    fn parse_number(&mut self) -> Option<JsonValue> {
        let start = self.pos;
        if self.peek() == Some('-') {
            self.pos += 1;
        }
        match self.peek()? {
            '0' => {
                self.pos += 1;
            }
            '1'..='9' => {
                while matches!(self.peek(), Some('0'..='9')) {
                    self.pos += 1;
                }
            }
            _ => return None,
        }
        if self.peek() == Some('.') {
            self.pos += 1;
            if !matches!(self.peek(), Some('0'..='9')) {
                return None;
            }
            while matches!(self.peek(), Some('0'..='9')) {
                self.pos += 1;
            }
        }
        if matches!(self.peek(), Some('e') | Some('E')) {
            self.pos += 1;
            if matches!(self.peek(), Some('+') | Some('-')) {
                self.pos += 1;
            }
            if !matches!(self.peek(), Some('0'..='9')) {
                return None;
            }
            while matches!(self.peek(), Some('0'..='9')) {
                self.pos += 1;
            }
        }
        let text: String = self.chars[start..self.pos].iter().collect();
        text.parse::<f64>().ok().map(JsonValue::Num)
    }

    fn parse_hex4(&mut self) -> Option<u32> {
        let mut value: u32 = 0;
        for _ in 0..4 {
            let digit = self.peek()?.to_digit(16)?;
            value = value * 16 + digit;
            self.pos += 1;
        }
        Some(value)
    }

    fn parse_string(&mut self) -> Option<String> {
        if !self.eat('"') {
            return None;
        }
        let mut out = String::new();
        loop {
            let ch = self.peek()?;
            if ch == '"' {
                self.pos += 1;
                return Some(out);
            }
            if ch == '\\' {
                self.pos += 1;
                match self.peek()? {
                    '"' => {
                        out.push('"');
                        self.pos += 1;
                    }
                    '\\' => {
                        out.push('\\');
                        self.pos += 1;
                    }
                    '/' => {
                        out.push('/');
                        self.pos += 1;
                    }
                    'b' => {
                        out.push('\u{0008}');
                        self.pos += 1;
                    }
                    'f' => {
                        out.push('\u{000C}');
                        self.pos += 1;
                    }
                    'n' => {
                        out.push('\n');
                        self.pos += 1;
                    }
                    'r' => {
                        out.push('\r');
                        self.pos += 1;
                    }
                    't' => {
                        out.push('\t');
                        self.pos += 1;
                    }
                    'u' => {
                        self.pos += 1;
                        let code = self.parse_hex4()?;
                        out.push(char::from_u32(code).unwrap_or('\u{FFFD}'));
                    }
                    _ => return None,
                }
            } else {
                out.push(ch);
                self.pos += 1;
            }
        }
    }

    fn parse_array(&mut self) -> Option<JsonValue> {
        if !self.eat('[') {
            return None;
        }
        let mut items = Vec::new();
        self.skip_ws();
        if self.eat(']') {
            return Some(JsonValue::Arr(items));
        }
        loop {
            items.push(self.parse_value()?);
            self.skip_ws();
            if self.eat(']') {
                return Some(JsonValue::Arr(items));
            }
            if !self.eat(',') {
                return None;
            }
        }
    }

    fn parse_object(&mut self) -> Option<JsonValue> {
        if !self.eat('{') {
            return None;
        }
        let mut pairs = Vec::new();
        self.skip_ws();
        if self.eat('}') {
            return Some(JsonValue::Obj(pairs));
        }
        loop {
            self.skip_ws();
            let key = self.parse_string()?;
            self.skip_ws();
            if !self.eat(':') {
                return None;
            }
            let value = self.parse_value()?;
            pairs.push((key, value));
            self.skip_ws();
            if self.eat('}') {
                return Some(JsonValue::Obj(pairs));
            }
            if !self.eat(',') {
                return None;
            }
        }
    }
}

/// Parse one line as a JSON object event, or `None` when malformed.
fn parse_event_object(line: &str) -> Option<WatchEvent> {
    let mut parser = JsonParser::new(line);
    let value = parser.parse_value()?;
    parser.skip_ws();
    if parser.pos != parser.chars.len() {
        return None;
    }
    let pairs = match value {
        JsonValue::Obj(pairs) => pairs,
        _ => return None,
    };
    let mut kind = None;
    let mut ts = None;
    for (key, value) in pairs {
        match (key.as_str(), value) {
            ("kind", JsonValue::Str(text)) => kind = Some(text),
            ("ts", JsonValue::Num(number)) if !number.is_nan() => ts = Some(number),
            _ => {}
        }
    }
    Some(WatchEvent { kind, ts })
}

/// One service-loop cycle over every machine's watchman run.
///
/// `runs` is `{machine: run}`: `Run(true, stdout)` means the
/// relay-watchman `--once` run exited 0 and stdout holds its event
/// lines; any other run means the run failed and stdout is ignored.
/// `priors` is `{machine: prior record}` carried from the previous
/// cycle; `journal` is the caller's journal list for episode dedupe.
/// `restart_ok` is an optional `{machine: bool}` of caller-supplied
/// restart outcomes for machines whose runs succeeded.
///
/// Returns `(records, new_journal, diagnostics)`. Records is the
/// board's latest picture: fresh records for machines whose runs
/// succeeded, carried prior records (`restart_ok` stripped, copied)
/// for machines whose runs failed and that have a prior. New journal
/// holds only this cycle's new records. Inputs are never mutated.
pub fn loop_cycle(
    runs: &HashMap<String, LoopRun>,
    now: f64,
    priors: &HashMap<String, WatchmanRecord>,
    journal: &[JournalEntry],
    restart_ok: &HashMap<String, bool>,
) -> (
    HashMap<String, WatchmanRecord>,
    Vec<JournalEntry>,
    Diagnostics,
) {
    let mut names: Vec<&String> = runs.keys().collect();
    names.sort();
    let mut ok_events: HashMap<String, Vec<WatchEvent>> = HashMap::new();
    let mut ok_priors: HashMap<String, WatchmanRecord> = HashMap::new();
    let mut carried: HashMap<String, WatchmanRecord> = HashMap::new();
    let mut diagnostics = Diagnostics::default();

    for name in names {
        let (ok, stdout) = match &runs[name] {
            LoopRun::Run(ok, stdout) => (*ok, stdout.clone()),
            LoopRun::Malformed => (false, String::new()),
        };
        if !ok {
            diagnostics.run_failures.push(name.clone());
            if let Some(prior) = priors.get(name) {
                let mut record = prior.clone();
                record.restart_ok = None;
                carried.insert(name.clone(), record);
            }
            continue;
        }
        let (events, malformed) = parse_event_lines(Some(&stdout));
        if malformed > 0 {
            diagnostics
                .malformed_lines
                .insert(name.clone(), malformed);
        }
        ok_events.insert(name.clone(), events);
        if let Some(prior) = priors.get(name) {
            ok_priors.insert(name.clone(), prior.clone());
        }
    }

    let (fresh, mut journal_new) =
        watchman_tick(&ok_events, now, &ok_priors, journal, restart_ok);
    if !carried.is_empty() {
        let snapshot = snapshot_from_records(&carried);
        let mut combined: Vec<JournalEntry> = journal.to_vec();
        combined.extend(journal_new.iter().cloned());
        let carried_new = watchman_watch_tick(&snapshot, &combined, now);
        journal_new.extend(carried_new);
    }

    let mut records = fresh;
    records.extend(carried);
    (records, journal_new, diagnostics)
}

#[cfg(test)]
mod tests {
    use super::*;

    const NOW: f64 = 1_000_000.0;
    const STALE: f64 = 5.0 * 60.0;

    /// Stdout lines for a relay-watchman tick that rings once at `at`.
    /// The Python tests generate these via the real relay-watchman
    /// tick(); relay-watchman is another batch's module, so literal
    /// wake-event lines are used here instead.
    fn stdout_for(at: f64) -> String {
        format!(
            "{{\"job_id\": \"j1\", \"kind\": \"wake\", \"ts\": {}}}\n",
            at as i64
        )
    }

    fn kinds(journal: &[JournalEntry]) -> Vec<&str> {
        journal.iter().map(|r| r.kind.as_str()).collect()
    }

    #[test]
    fn test_valid_lines_parse() {
        // Mirrors TestParseEventLines.test_valid_lines_parse.
        let (events, malformed) =
            parse_event_lines(Some("{\"kind\": \"wake\", \"ts\": 7}\n\n{\"kind\": \"nudge\"}\n"));
        assert_eq!(events.len(), 2);
        assert_eq!(malformed, 0);
        assert_eq!(events[0].ts, Some(7.0));
    }

    #[test]
    fn test_junk_and_non_object_lines_counted() {
        // Mirrors test_junk_and_non_object_lines_counted.
        let (events, malformed) =
            parse_event_lines(Some("junk\n[1, 2]\n{\"kind\": \"wake\"}\n"));
        assert_eq!(events.len(), 1);
        assert_eq!(malformed, 2);
    }

    #[test]
    fn test_non_string_input_is_one_malformed() {
        // Mirrors test_non_string_input_is_one_malformed.
        let (events, malformed) = parse_event_lines(None);
        assert!(events.is_empty());
        assert_eq!(malformed, 1);
    }

    #[test]
    fn test_successful_ring_and_quiet() {
        // Mirrors TestLoopCycle.test_successful_ring_and_quiet.
        let mut runs: HashMap<String, LoopRun> = HashMap::new();
        runs.insert("alpha".to_string(), LoopRun::Run(true, stdout_for(NOW)));
        runs.insert("beta".to_string(), LoopRun::Run(true, String::new()));
        let (records, new, diagnostics) = loop_cycle(
            &runs,
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert_eq!(records["alpha"].last_bell, Some(NOW));
        assert_eq!(records["beta"].last_bell, None);
        assert!(new.is_empty());
        assert!(diagnostics.run_failures.is_empty());
        assert!(diagnostics.malformed_lines.is_empty());
    }

    #[test]
    fn test_failed_run_carries_prior_and_ages_dark() {
        // Mirrors test_failed_run_carries_prior_and_ages_dark.
        let mut runs: HashMap<String, LoopRun> = HashMap::new();
        runs.insert("alpha".to_string(), LoopRun::Run(true, stdout_for(NOW)));
        let mut restart_ok: HashMap<String, bool> = HashMap::new();
        restart_ok.insert("alpha".to_string(), true);
        let (records, _, _) = loop_cycle(
            &runs,
            NOW,
            &HashMap::new(),
            &[],
            &restart_ok,
        );
        let mut runs2: HashMap<String, LoopRun> = HashMap::new();
        runs2.insert("alpha".to_string(), LoopRun::Run(false, "unused".to_string()));
        let (records, new, diagnostics) = loop_cycle(
            &runs2,
            NOW + STALE + 100.0,
            &records,
            &[],
            &HashMap::new(),
        );
        assert_eq!(diagnostics.run_failures, ["alpha"]);
        assert_eq!(records["alpha"].restart_ok, None);
        assert_eq!(records["alpha"].last_bell, Some(NOW));
        assert_eq!(
            kinds(&new),
            ["crew-dark", "watchman-restart", "escalation"]
        );
        let restart = new
            .iter()
            .find(|e| e.kind == "watchman-restart")
            .unwrap();
        assert_eq!(restart.restart_ok, Some(false));
    }

    #[test]
    fn test_open_episode_stays_silent_on_repeat_failure() {
        // Mirrors test_open_episode_stays_silent_on_repeat_failure.
        let mut runs: HashMap<String, LoopRun> = HashMap::new();
        runs.insert("alpha".to_string(), LoopRun::Run(true, stdout_for(NOW)));
        let (records, _, _) = loop_cycle(
            &runs,
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        let mut runs2: HashMap<String, LoopRun> = HashMap::new();
        runs2.insert("alpha".to_string(), LoopRun::Run(false, String::new()));
        let (_, new, _) = loop_cycle(
            &runs2,
            NOW + STALE + 100.0,
            &records,
            &[],
            &HashMap::new(),
        );
        let journal = new;
        let mut runs3: HashMap<String, LoopRun> = HashMap::new();
        runs3.insert("alpha".to_string(), LoopRun::Run(false, String::new()));
        let (_, new2, _) = loop_cycle(
            &runs3,
            NOW + STALE + 200.0,
            &records,
            &journal,
            &HashMap::new(),
        );
        assert!(new2.is_empty());
    }

    #[test]
    fn test_fresh_ring_recovers_after_failed_runs() {
        // Mirrors test_fresh_ring_recovers_after_failed_runs.
        let mut runs: HashMap<String, LoopRun> = HashMap::new();
        runs.insert("alpha".to_string(), LoopRun::Run(true, stdout_for(NOW)));
        let (records, _, _) = loop_cycle(
            &runs,
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        let mut runs2: HashMap<String, LoopRun> = HashMap::new();
        runs2.insert("alpha".to_string(), LoopRun::Run(false, String::new()));
        let (_, new, _) = loop_cycle(
            &runs2,
            NOW + STALE + 100.0,
            &records,
            &[],
            &HashMap::new(),
        );
        let journal = new;
        let ring_at = NOW + STALE + 300.0;
        let mut runs3: HashMap<String, LoopRun> = HashMap::new();
        runs3.insert(
            "alpha".to_string(),
            LoopRun::Run(true, stdout_for(ring_at)),
        );
        let (_, new2, _) = loop_cycle(
            &runs3,
            ring_at,
            &records,
            &journal,
            &HashMap::new(),
        );
        assert_eq!(kinds(&new2), ["watchman-recovered"]);
    }

    #[test]
    fn test_malformed_stdout_contained_per_machine() {
        // Mirrors test_malformed_stdout_contained_per_machine.
        let dirty = format!("{}junk\n", stdout_for(NOW));
        let mut runs: HashMap<String, LoopRun> = HashMap::new();
        runs.insert("alpha".to_string(), LoopRun::Run(true, dirty));
        runs.insert("beta".to_string(), LoopRun::Run(true, String::new()));
        let (records, new, diagnostics) = loop_cycle(
            &runs,
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert_eq!(diagnostics.malformed_lines["alpha"], 1);
        assert_eq!(records["alpha"].last_bell, Some(NOW));
        assert!(new.is_empty());
    }

    #[test]
    fn test_no_prior_failure_unjudged() {
        // Mirrors test_no_prior_failure_unjudged.
        let mut runs: HashMap<String, LoopRun> = HashMap::new();
        runs.insert("gamma".to_string(), LoopRun::Run(false, String::new()));
        let (records, new, diagnostics) = loop_cycle(
            &runs,
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        assert!(!records.contains_key("gamma"));
        assert!(new.is_empty());
        assert_eq!(diagnostics.run_failures, ["gamma"]);
    }

    #[test]
    fn test_failed_run_stdout_ignored() {
        // Mirrors test_failed_run_stdout_ignored.
        let mut runs: HashMap<String, LoopRun> = HashMap::new();
        runs.insert("alpha".to_string(), LoopRun::Run(true, stdout_for(NOW)));
        let (records, _, _) = loop_cycle(
            &runs,
            NOW,
            &HashMap::new(),
            &[],
            &HashMap::new(),
        );
        let mut runs2: HashMap<String, LoopRun> = HashMap::new();
        runs2.insert(
            "alpha".to_string(),
            LoopRun::Run(false, stdout_for(NOW + STALE + 100.0)),
        );
        let (records, new, _) = loop_cycle(
            &runs2,
            NOW + STALE + 100.0,
            &records,
            &[],
            &HashMap::new(),
        );
        assert_eq!(records["alpha"].last_bell, Some(NOW));
        assert_eq!(
            kinds(&new),
            ["crew-dark", "watchman-restart", "escalation"]
        );
    }

    #[test]
    fn test_inputs_never_mutated() {
        // Mirrors test_inputs_never_mutated.
        let mut runs: HashMap<String, LoopRun> = HashMap::new();
        runs.insert("alpha".to_string(), LoopRun::Run(true, stdout_for(NOW)));
        runs.insert("beta".to_string(), LoopRun::Run(false, String::new()));
        let mut priors: HashMap<String, WatchmanRecord> = HashMap::new();
        priors.insert(
            "beta".to_string(),
            WatchmanRecord {
                watchman_alive: Some(true),
                last_tick: Some(NOW),
                last_bell: Some(NOW),
                last_wake: Some(NOW),
                ..Default::default()
            },
        );
        let journal = vec![JournalEntry::new("crew-dark", "beta")];
        let runs_before = runs.clone();
        let priors_before = priors.clone();
        let journal_before = journal.clone();
        loop_cycle(&runs, NOW, &priors, &journal, &HashMap::new());
        assert_eq!(runs, runs_before);
        assert_eq!(priors, priors_before);
        assert_eq!(journal, journal_before);
    }

    #[test]
    fn test_malformed_run_reads_as_failed_run() {
        // Python loop behavior for a run that is not a usable pair:
        // it counts as a failed run and carries a prior forward.
        let mut runs: HashMap<String, LoopRun> = HashMap::new();
        runs.insert("alpha".to_string(), LoopRun::Malformed);
        let mut priors: HashMap<String, WatchmanRecord> = HashMap::new();
        priors.insert(
            "alpha".to_string(),
            WatchmanRecord {
                watchman_alive: Some(true),
                last_bell: Some(NOW),
                ..Default::default()
            },
        );
        let (records, new, diagnostics) = loop_cycle(
            &runs,
            NOW + STALE + 100.0,
            &priors,
            &[],
            &HashMap::new(),
        );
        assert_eq!(diagnostics.run_failures, ["alpha"]);
        assert_eq!(records["alpha"].last_bell, Some(NOW));
        assert_eq!(
            kinds(&new),
            ["crew-dark", "watchman-restart", "escalation"]
        );
    }
}
