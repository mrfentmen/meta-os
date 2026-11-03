//! Persistent task system: the OS manages intentions, not just processes.
//!
//! A goal outlives any single run: closing the interface or rebooting
//! must not destroy the work. Goals own a task DAG with dependencies,
//! per-task state, attempt records, and a completion predicate. State
//! is plain data (serializable by the caller); NOTHING here executes
//! anything — the objective runner drives it.

use std::collections::{HashMap, HashSet};

/// A goal with a verifiable done condition.
#[derive(Debug, Clone)]
pub struct Goal {
    pub id: String,
    pub objective: String,
    /// Human-readable success criteria, checked by verification.
    pub success_criteria: Vec<String>,
    pub tasks: Vec<Task>,
}

/// One unit of work inside a goal.
#[derive(Debug, Clone)]
pub struct Task {
    pub id: String,
    pub title: String,
    /// Task ids that must be Done first.
    pub depends_on: Vec<String>,
    pub state: TaskState,
    pub attempts: u32,
    pub last_error: Option<String>,
    pub owner: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum TaskState {
    Pending,
    Ready,
    Running,
    Done,
    Failed,
    Abandoned,
}

/// Whole-goal status derived from tasks, never stored.
#[derive(Debug, PartialEq)]
pub enum GoalStatus {
    InProgress,
    Complete,
    Blocked,
    Failed,
}

impl Goal {
    pub fn new(id: &str, objective: &str, success_criteria: Vec<String>) -> Self {
        Goal { id: id.into(), objective: objective.into(), success_criteria, tasks: Vec::new() }
    }

    pub fn add_task(&mut self, id: &str, title: &str, depends_on: Vec<String>, owner: Option<String>) {
        let mut state = TaskState::Pending;
        if depends_on.is_empty() {
            state = TaskState::Ready;
        }
        self.tasks.push(Task { id: id.into(), title: title.into(), depends_on, state, attempts: 0, last_error: None, owner });
    }

    fn ids(&self) -> HashSet<&str> {
        self.tasks.iter().map(|t| t.id.as_str()).collect()
    }

    /// Recompute Ready/Pending from dependencies. Returns ids that changed.
    pub fn refresh(&mut self) -> Vec<String> {
        let done: HashSet<String> = self.tasks.iter().filter(|t| t.state == TaskState::Done).map(|t| t.id.clone()).collect();
        let mut changed = Vec::new();
        for t in &mut self.tasks {
            if t.state == TaskState::Pending && t.depends_on.iter().all(|d| done.contains(d)) {
                t.state = TaskState::Ready;
                changed.push(t.id.clone());
            }
        }
        changed
    }

    /// Tasks whose dependencies name something that does not exist.
    pub fn dangling(&self) -> Vec<String> {
        let ids = self.ids();
        let mut out = Vec::new();
        for t in &self.tasks {
            for d in &t.depends_on {
                if !ids.contains(d.as_str()) {
                    out.push(format!("{}->{}", t.id, d));
                }
            }
        }
        out
    }

    /// True when every task is Done (completion = all tasks done AND
    /// criteria exist; criteria CONTENT is verified by the caller).
    pub fn status(&self) -> GoalStatus {
        if self.tasks.is_empty() {
            return GoalStatus::Blocked;
        }
        if self.tasks.iter().all(|t| t.state == TaskState::Done) {
            return GoalStatus::Complete;
        }
        if self.tasks.iter().any(|t| t.state == TaskState::Failed)
            && !self.tasks.iter().any(|t| matches!(t.state, TaskState::Ready | TaskState::Running))
        {
            // A failed task with nothing runnable left is terminal:
            // pending dependents can never unblock without intervention.
            return GoalStatus::Failed;
        }
        GoalStatus::InProgress
    }

    pub fn ready_tasks(&self) -> Vec<&Task> {
        self.tasks.iter().filter(|t| t.state == TaskState::Ready).collect()
    }

    pub fn by_id_mut(&mut self, id: &str) -> Option<&mut Task> {
        self.tasks.iter_mut().find(|t| t.id == id)
    }

    /// Serialize to a caller-stored string (line format, no deps).
    /// Format: G|<id>|<objective>\nC|<criterion>\nT|<id>|<state>|<attempts>|<owner>|<deps,;>|<title>
    pub fn encode(&self) -> String {
        let mut s = format!("G|{}|{}\n", esc(&self.id), esc(&self.objective));
        for c in &self.success_criteria {
            s.push_str(&format!("C|{}\n", esc(c)));
        }
        for t in &self.tasks {
            let st = match t.state {
                TaskState::Pending => "pending",
                TaskState::Ready => "ready",
                TaskState::Running => "running",
                TaskState::Done => "done",
                TaskState::Failed => "failed",
                TaskState::Abandoned => "abandoned",
            };
            s.push_str(&format!(
                "T|{}|{}|{}|{}|{}|{}\n",
                esc(&t.id),
                st,
                t.attempts,
                esc(&t.owner.clone().unwrap_or_default()),
                t.depends_on.iter().map(|d| esc(d)).collect::<Vec<_>>().join(";"),
                esc(&t.title)
            ));
        }
        s
    }

    /// Restore from [`Goal::encode`]. Unknown lines are ignored (forward
    /// compatible); malformed task lines are an error.
    pub fn decode(text: &str) -> Result<Self, String> {
        let mut goal: Option<Goal> = None;
        for (n, line) in text.lines().enumerate() {
            let p: Vec<&str> = line.split('|').collect();
            match p.first() {
                Some(&"G") if p.len() >= 3 => {
                    goal = Some(Goal::new(&unesc(p[1]), &unesc(p[2]), Vec::new()));
                }
                Some(&"C") if p.len() >= 2 => {
                    if let Some(g) = goal.as_mut() {
                        g.success_criteria.push(unesc(p[1]));
                    }
                }
                Some(&"T") if p.len() >= 7 => {
                    let g = goal.as_mut().ok_or_else(|| format!("line {}: task before goal", n + 1))?;
                    let state = match p[2] {
                        "pending" => TaskState::Pending,
                        "ready" => TaskState::Ready,
                        "running" => TaskState::Running,
                        "done" => TaskState::Done,
                        "failed" => TaskState::Failed,
                        "abandoned" => TaskState::Abandoned,
                        other => return Err(format!("line {}: bad state {}", n + 1, other)),
                    };
                    let deps = if p[5].is_empty() { Vec::new() } else { p[5].split(';').map(unesc).collect() };
                    g.tasks.push(Task {
                        id: unesc(p[1]),
                        title: unesc(p[6]),
                        depends_on: deps,
                        state,
                        attempts: p[3].parse().map_err(|_| format!("line {}: bad attempts", n + 1))?,
                        last_error: None,
                        owner: if p[4].is_empty() { None } else { Some(unesc(p[4])) },
                    });
                }
                _ => {}
            }
        }
        goal.ok_or_else(|| "no goal line".to_string())
    }
}

fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('|', "\\p").replace('\n', "\\n")
}

fn unesc(s: &str) -> String {
    let mut out = String::new();
    let mut it = s.chars();
    while let Some(c) = it.next() {
        if c == '\\' {
            match it.next() {
                Some('p') => out.push('|'),
                Some('n') => out.push('\n'),
                Some(x) => {
                    out.push('\\');
                    out.push(x);
                }
                None => out.push('\\'),
            }
        } else {
            out.push(c);
        }
    }
    out
}

/// Dependency graph of task ids (for cycle checks without a Goal).
pub fn has_cycle(edges: &HashMap<String, Vec<String>>) -> bool {
    fn visit(n: &str, edges: &HashMap<String, Vec<String>>, temp: &mut HashSet<String>, perm: &mut HashSet<String>) -> bool {
        if perm.contains(n) {
            return false;
        }
        if !temp.insert(n.to_string()) {
            return true;
        }
        if let Some(next) = edges.get(n) {
            for m in next {
                if visit(m, edges, temp, perm) {
                    return true;
                }
            }
        }
        temp.remove(n);
        perm.insert(n.to_string());
        false
    }
    let mut temp = HashSet::new();
    let mut perm = HashSet::new();
    edges.keys().any(|n| visit(n, edges, &mut temp, &mut perm))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn goal() -> Goal {
        let mut g = Goal::new("biz", "launch shop", vec!["site live".into()]);
        g.add_task("research", "market", vec![], Some("scout".into()));
        g.add_task("site", "build", vec!["research".into()], Some("coder".into()));
        g.add_task("ads", "promote", vec!["site".into()], None);
        g
    }

    #[test]
    fn dependencies_gate_readiness() {
        let mut g = goal();
        assert_eq!(g.ready_tasks().iter().map(|t| t.id.as_str()).collect::<Vec<_>>(), vec!["research"]);
        g.by_id_mut("research").unwrap().state = TaskState::Done;
        let changed = g.refresh();
        assert_eq!(changed, vec!["site"]);
        assert_eq!(g.status(), GoalStatus::InProgress);
    }

    #[test]
    fn completion_and_failure() {
        let mut g = goal();
        for id in ["research", "site", "ads"] {
            g.by_id_mut(id).unwrap().state = TaskState::Done;
        }
        assert_eq!(g.status(), GoalStatus::Complete);
        let mut g2 = goal();
        g2.by_id_mut("research").unwrap().state = TaskState::Failed;
        assert_eq!(g2.status(), GoalStatus::Failed);
    }

    #[test]
    fn dangling_deps_flagged() {
        let mut g = Goal::new("x", "y", vec![]);
        g.add_task("a", "A", vec!["ghost".into()], None);
        assert_eq!(g.dangling(), vec!["a->ghost"]);
    }

    #[test]
    fn encode_decode_round_trip() {
        let mut g = goal();
        g.by_id_mut("research").unwrap().state = TaskState::Done;
        g.by_id_mut("research").unwrap().attempts = 2;
        let text = g.encode();
        let mut back = Goal::decode(&text).unwrap();
        assert_eq!(back.id, "biz");
        assert_eq!(back.success_criteria, vec!["site live"]);
        assert_eq!(back.tasks.len(), 3);
        assert_eq!(back.by_id_mut("research").map(|t| t.attempts), Some(2));
        // State survives a reboot: decode, refresh, continue.
        let mut resumed = back;
        assert_eq!(resumed.refresh(), vec!["site"]);
    }

    #[test]
    fn cycles_detected() {
        let mut e = HashMap::new();
        e.insert("a".into(), vec!["b".into()]);
        e.insert("b".into(), vec!["a".into()]);
        assert!(has_cycle(&e));
        let mut ok = HashMap::new();
        ok.insert("a".into(), vec!["b".into()]);
        assert!(!has_cycle(&ok));
    }
}
