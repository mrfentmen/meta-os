//! A job as an ordered list of steps.
//!
//! The store layer keeps jobs as records; this module is the job itself, and
//! it enforces the three rules a step-based job needs:
//!
//! 1. **A job with no steps is not a job.** It is refused at construction,
//!    because a job that "runs" nothing reports success while doing nothing.
//! 2. **Step order is the contract.** A round trip through [`Job::to_text`] and
//!    [`Job::from_text`] returns the same steps in the same order — a
//!    reordering would silently change what the job does.
//! 3. **A finished job cannot be cancelled.** Cancel says which of the three
//!    things happened instead of pretending every cancel worked.
//!
//! The text format is one record per line, so it is diffable and has no
//! dependency: `job`, `title`, `state`, then one `step` line per step in order.

/// One step: a name and the command it runs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Step {
    pub name: String,
    pub command: Vec<String>,
}

impl Step {
    /// A step from a name and its command words.
    pub fn new(name: &str, command: &[&str]) -> Result<Step, JobError> {
        if name.trim().is_empty() {
            return Err(JobError::BlankStepName);
        }
        if command.is_empty() || command.iter().any(|c| c.trim().is_empty()) {
            return Err(JobError::EmptyStepCommand(name.to_string()));
        }
        Ok(Step {
            name: name.trim().to_string(),
            command: command.iter().map(|c| c.trim().to_string()).collect(),
        })
    }
}

/// Where a job is in its life.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JobState {
    Pending,
    Running,
    Finished,
    Cancelled,
}

impl JobState {
    pub fn as_str(self) -> &'static str {
        match self {
            JobState::Pending => "pending",
            JobState::Running => "running",
            JobState::Finished => "finished",
            JobState::Cancelled => "cancelled",
        }
    }

    fn parse(text: &str) -> Option<JobState> {
        match text {
            "pending" => Some(JobState::Pending),
            "running" => Some(JobState::Running),
            "finished" => Some(JobState::Finished),
            "cancelled" => Some(JobState::Cancelled),
            _ => None,
        }
    }
}

/// What a cancel attempt actually did.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CancelOutcome {
    /// The job is now cancelled and will run no further step.
    Cancelled,
    /// The job had already finished: cancelling it is a no-op, stated.
    AlreadyFinished,
    /// The job was already cancelled: the second cancel is a no-op, stated.
    AlreadyCancelled,
}

/// A job that must not be built or read.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum JobError {
    /// A job with no steps: nothing to run.
    NoSteps,
    BlankStepName,
    EmptyStepCommand(String),
    BadLine(String),
    UnknownState(String),
}

/// An ordered job.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Job {
    id: String,
    title: String,
    state: JobState,
    steps: Vec<Step>,
}

impl Job {
    /// Build a job. An empty step list is refused: see the module docs.
    pub fn new(id: &str, title: &str, steps: Vec<Step>) -> Result<Job, JobError> {
        if id.trim().is_empty() || title.trim().is_empty() {
            return Err(JobError::BadLine("job: id and title are required".to_string()));
        }
        if steps.is_empty() {
            return Err(JobError::NoSteps);
        }
        Ok(Job {
            id: id.trim().to_string(),
            title: title.trim().to_string(),
            state: JobState::Pending,
            steps,
        })
    }

    pub fn id(&self) -> &str {
        &self.id
    }

    pub fn title(&self) -> &str {
        &self.title
    }

    pub fn state(&self) -> JobState {
        self.state
    }

    pub fn steps(&self) -> &[Step] {
        &self.steps
    }

    /// Move to running. A finished or cancelled job stays where it is.
    pub fn start(&mut self) -> bool {
        if self.state != JobState::Pending {
            return false;
        }
        self.state = JobState::Running;
        true
    }

    /// Mark the job done. A cancelled job never finishes.
    pub fn finish(&mut self) -> bool {
        if self.state != JobState::Running {
            return false;
        }
        self.state = JobState::Finished;
        true
    }

    /// Cancel the job, saying which of the three things happened. A finished
    /// job is not "cancelled" — it already ran, and saying otherwise would
    /// rewrite history.
    pub fn cancel(&mut self) -> CancelOutcome {
        match self.state {
            JobState::Finished => CancelOutcome::AlreadyFinished,
            JobState::Cancelled => CancelOutcome::AlreadyCancelled,
            JobState::Pending | JobState::Running => {
                self.state = JobState::Cancelled;
                CancelOutcome::Cancelled
            }
        }
    }

    /// One line per record, steps in order.
    pub fn to_text(&self) -> String {
        let mut out = String::new();
        out.push_str(&format!("job {}\n", self.id));
        out.push_str(&format!("title {}\n", self.title));
        out.push_str(&format!("state {}\n", self.state.as_str()));
        for step in &self.steps {
            out.push_str(&format!("step {} :: {}\n", step.name, step.command.join(" ")));
        }
        out
    }

    /// Read [`Job::to_text`] back, preserving step order.
    pub fn from_text(text: &str) -> Result<Job, JobError> {
        let mut id = None;
        let mut title = None;
        let mut state = None;
        let mut steps = Vec::new();
        for raw in text.lines() {
            let line = raw.trim();
            if line.is_empty() {
                continue;
            }
            if let Some(rest) = line.strip_prefix("job ") {
                id = Some(rest.trim().to_string());
            } else if let Some(rest) = line.strip_prefix("title ") {
                title = Some(rest.trim().to_string());
            } else if let Some(rest) = line.strip_prefix("state ") {
                state = Some(
                    JobState::parse(rest.trim())
                        .ok_or_else(|| JobError::UnknownState(rest.trim().to_string()))?,
                );
            } else if let Some(rest) = line.strip_prefix("step ") {
                let (name, command) = rest
                    .split_once(" :: ")
                    .ok_or_else(|| JobError::BadLine(raw.to_string()))?;
                let words: Vec<&str> = command.split_whitespace().collect();
                steps.push(Step::new(name, &words)?);
            } else {
                return Err(JobError::BadLine(raw.to_string()));
            }
        }
        let id = id.ok_or_else(|| JobError::BadLine("job: no id line".to_string()))?;
        let title = title.ok_or_else(|| JobError::BadLine("job: no title line".to_string()))?;
        let mut job = Job::new(&id, &title, steps)?;
        job.state = state.ok_or_else(|| JobError::BadLine("job: no state line".to_string()))?;
        Ok(job)
    }
}
