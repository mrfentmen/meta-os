//! Meta Nuntius relay binary (batch B08).
//!
//! Thin entry point over the [`relay::http`] server layer: resolves
//! `RELAY_PORT` (default 8787) and `RELAY_STORE_FILE` (unset =
//! in-memory only), binds, and serves forever.

use std::net::TcpListener;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

fn main() {
    let port: u16 = std::env::var("RELAY_PORT")
        .ok()
        .filter(|raw| !raw.is_empty())
        .and_then(|raw| raw.parse::<u16>().ok())
        .unwrap_or(8787);
    let store_file: Option<PathBuf> = std::env::var("RELAY_STORE_FILE")
        .ok()
        .filter(|raw| !raw.is_empty())
        .map(PathBuf::from);

    let store = if store_file.is_some() { "file" } else { "memory" };
    let relay = Arc::new(Mutex::new(relay::http::Relay::new(store_file)));
    let listener = TcpListener::bind(format!("0.0.0.0:{port}")).unwrap_or_else(|err| {
        panic!("Meta Nuntius: failed to bind port {port}: {err}")
    });
    println!("Meta Nuntius relay listening on port {port} (store: {store})");
    relay::http::serve(listener, relay).expect("Meta Nuntius: serve failed");
}
