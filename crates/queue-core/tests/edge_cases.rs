//! B111 — the four edge classes: empty, maximum, duplicate, out-of-order.

use queue_core::{
    deterministic_job_id, index_key, job_key, sha256_hex, validate_envelope, Backend, Envelope,
    EnvelopeImage, JobStore, MemoryBackend,
};

const PRODUCTS: [&str; 3] = ["vigiles", "ignis", "medicus"];
const TS: &str = "2026-11-02T00:00:00.000Z";

fn b64(data: &[u8]) -> String {
    const ALPHABET: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::new();
    for chunk in data.chunks(3) {
        let b = [
            chunk[0],
            *chunk.get(1).unwrap_or(&0),
            *chunk.get(2).unwrap_or(&0),
        ];
        let n = ((b[0] as u32) << 16) | ((b[1] as u32) << 8) | b[2] as u32;
        out.push(ALPHABET[(n >> 18) as usize & 63] as char);
        out.push(ALPHABET[(n >> 12) as usize & 63] as char);
        out.push(if chunk.len() > 1 {
            ALPHABET[(n >> 6) as usize & 63] as char
        } else {
            '='
        });
        out.push(if chunk.len() > 2 {
            ALPHABET[n as usize & 63] as char
        } else {
            '='
        });
    }
    out
}

fn envelope_for(product: &str, frame: &[u8]) -> Envelope {
    Envelope {
        version: 1,
        kind: "trio-assessment".to_string(),
        id: deterministic_job_id(product, TS, frame),
        product: product.to_string(),
        timestamp: TS.to_string(),
        image: EnvelopeImage {
            data_url: format!("data:image/jpeg;base64,{}", b64(frame)),
            byte_length: frame.len(),
            sha256: sha256_hex(frame),
        },
    }
}

#[test]
fn empty_frame_is_a_valid_envelope() {
    let env = envelope_for("ignis", &[]);
    assert_eq!(env.image.data_url, "data:image/jpeg;base64,");
    assert_eq!(env.image.byte_length, 0);
    assert_eq!(
        env.image.sha256,
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    );
    assert_eq!(validate_envelope(&env, &PRODUCTS), None);
}

#[test]
fn maximum_frame_validates() {
    // 1,000,000 bytes crosses every SHA-256 padding boundary in one go.
    let raw = vec![0xA5u8; 1_000_000];
    let env = envelope_for("medicus", &raw);
    assert_eq!(validate_envelope(&env, &PRODUCTS), None);
}

#[test]
fn duplicate_submit_is_idempotent_and_indexes_once() {
    let mut store = JobStore::new(MemoryBackend::new(), "trio-test");
    let env = envelope_for("ignis", &[1, 2, 3]);
    assert!(store.submit(&env, "{}", 100).1);
    assert!(!store.submit(&env, "{}", 101).1);
    assert_eq!(store.open_job_ids(), vec![env.id.clone()]);
    let index = index_key(&store.ns);
    assert_eq!(store.backend.zrange(&index), vec![env.id.clone()]);
}

#[test]
fn out_of_order_submit_orders_the_index_by_created_at() {
    let mut store = JobStore::new(MemoryBackend::new(), "trio-test");
    let late = envelope_for("ignis", &[9]);
    let early = envelope_for("ignis", &[1]);
    let middle = envelope_for("ignis", &[5]);
    store.submit(&late, "{}", 300);
    store.submit(&early, "{}", 100);
    store.submit(&middle, "{}", 200);
    assert_eq!(
        store.backend.zrange(&index_key(&store.ns)),
        vec![early.id, middle.id, late.id]
    );
}

#[test]
fn duplicate_claim_first_caller_wins() {
    let mut store = JobStore::new(MemoryBackend::new(), "trio-test");
    let env = envelope_for("ignis", &[7]);
    store.submit(&env, "{}", 100);
    assert!(store.claim(&env.id, "agent-a", 60, 110));
    assert!(!store.claim(&env.id, "agent-b", 60, 111));
    assert_eq!(
        store.job_fields(&env.id).get("claim").map(String::as_str),
        Some("agent-a")
    );
}

#[test]
fn claiming_an_unfiled_job_creates_claim_state() {
    // Faithful to trio_store.JobStore.claim: there is no existence check,
    // so a claim on an unknown id writes the claim key and the job hash.
    let mut store = JobStore::new(MemoryBackend::new(), "trio-test");
    assert!(store.claim("ghost", "agent-a", 60, 110));
    assert_eq!(
        store.job_fields("ghost").get("status").map(String::as_str),
        Some("claimed")
    );
    assert!(store.open_job_ids().is_empty());
}

#[test]
fn finish_then_claim_is_allowed_and_claim_then_finish_releases() {
    let mut store = JobStore::new(MemoryBackend::new(), "trio-test");
    let env = envelope_for("ignis", &[4]);
    store.submit(&env, "{}", 100);
    store.finish(&env.id, "done", "late note", 120);
    assert_eq!(
        store.job_fields(&env.id).get("status").map(String::as_str),
        Some("done")
    );
    // finish always releases the claim, so a late claim can take the lock.
    assert!(store.claim(&env.id, "agent-b", 60, 130));
    assert_eq!(
        job_key(&store.ns, &env.id),
        format!("trio-test:{}", env.id)
    );
}

#[test]
fn empty_namespace_keeps_the_same_key_shape() {
    assert_eq!(job_key("", "j1"), ":j1");
    assert_eq!(index_key(""), "index");
}

#[test]
fn product_matching_is_exact_not_case_folded() {
    let mut env = envelope_for("ignis", &[1]);
    env.product = "IGNIS".to_string();
    assert_eq!(
        validate_envelope(&env, &PRODUCTS).as_deref(),
        Some("unknown product 'IGNIS'")
    );
}
