//! B11 — Intel Spark client & mind images (`b11_spark` subtree).
//!
//! Ports (behavior, not redesign):
//! - `os/intel/mind_image.py` -> [`mind_image`]
//! - `os/intel/mind_loader.py` -> [`mind_loader`]
//! - `os/intel/skills_loader.py` -> [`skills_loader`]
//! - `os/intel/spark_agent.py` -> [`spark_agent`]
//! - `os/intel/spark_client.py` -> [`spark_client`]
//!
//! Frozen: Spark calls count against the $75 guardrail cap (B03) —
//! counting routes through the guardrail, never a private counter.
//! Stub/fake-transport tests port as-is via the injected [`spark_client::Transport`] trait.

pub mod mind_image;
pub mod mind_loader;
pub mod skills_loader;
pub mod spark_agent;
pub mod spark_client;
