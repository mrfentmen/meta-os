//! CB-036: enqueue/dequeue order holds under interleaved producers.

use queue_core::{
    deterministic_job_id, Envelope, EnvelopeImage, JobStore, MemoryBackend,
};

const TS: &str = "2026-11-02T00:00:00.000Z";

fn b64(data: &[u8]) -> String {
    const ALPHABET: &[u8; 64] =
        b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
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
            sha256: queue_core::sha256_hex(frame),
        },
    }
}

#[test]
fn interleaved_producers_keep_creation_order() {
    let mut store = JobStore::new(MemoryBackend::new(), "trio-code100");
    let second = envelope_for("ignis", &[2]);
    let first = envelope_for("vigiles", &[1]);
    let third = envelope_for("medicus", &[3]);

    // Two producers interleave: B, A, C by wall-clock arrival.
    store.submit(&second, "{}", 200);
    store.submit(&first, "{}", 100);
    store.submit(&third, "{}", 300);

    assert_eq!(
        store.open_job_ids(),
        vec![first.id.clone(), second.id.clone(), third.id.clone()]
    );
}

#[test]
fn dequeue_removes_only_the_finished_head() {
    let mut store = JobStore::new(MemoryBackend::new(), "trio-code100");
    let first = envelope_for("ignis", &[1]);
    let second = envelope_for("ignis", &[2]);
    store.submit(&first, "{}", 100);
    store.submit(&second, "{}", 200);

    store.finish(&first.id, "done", "first done", 300);
    assert_eq!(store.open_job_ids(), vec![second.id.clone()]);
    assert_eq!(
        store.job_fields(&first.id).get("status").map(String::as_str),
        Some("done")
    );
}
