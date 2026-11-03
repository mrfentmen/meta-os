use queue_core::{
    deterministic_job_id, sha256_hex, validate_envelope, Envelope, EnvelopeImage, JobStore,
    MemoryBackend, PriorityQueue, MAX_IMAGE_BYTES,
};

const PRODUCTS: [&str; 3] = ["vigiles", "ignis", "medicus"];
const TS: &str = "2026-11-02T00:00:00.000Z";

fn b64(data: &[u8]) -> String {
    const A: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::new();
    for chunk in data.chunks(3) {
        let b = [chunk[0], *chunk.get(1).unwrap_or(&0), *chunk.get(2).unwrap_or(&0)];
        let n = ((b[0] as u32) << 16) | ((b[1] as u32) << 8) | b[2] as u32;
        out.push(A[(n >> 18) as usize & 63] as char);
        out.push(A[(n >> 12) as usize & 63] as char);
        out.push(if chunk.len() > 1 { A[(n >> 6) as usize & 63] as char } else { '=' });
        out.push(if chunk.len() > 2 { A[n as usize & 63] as char } else { '=' });
    }
    out
}

fn env(frame: &[u8]) -> Envelope {
    Envelope {
        version: 1,
        kind: "trio-assessment".to_string(),
        id: deterministic_job_id("ignis", TS, frame),
        product: "ignis".to_string(),
        timestamp: TS.to_string(),
        image: EnvelopeImage {
            data_url: format!("data:image/jpeg;base64,{}", b64(frame)),
            byte_length: frame.len(),
            sha256: sha256_hex(frame),
        },
    }
}

#[test]
fn envelope_empty_id_refused() {
    let mut e = env(&[1]);
    e.id.clear();
    assert!(validate_envelope(&e, &PRODUCTS).unwrap().contains("no job id"));
}

#[test]
fn envelope_unknown_kind_refused() {
    let mut e = env(&[1]);
    e.kind = "unknown".to_string();
    assert!(validate_envelope(&e, &PRODUCTS).unwrap().contains("not a trio-assessment"));
}

#[test]
fn dequeue_priority_order() {
    let mut q = PriorityQueue::new();
    q.push("low", 1);
    q.push("high", 9);
    q.push("mid", 5);
    assert_eq!(q.pop(), Some("high"));
    assert_eq!(q.pop(), Some("mid"));
    assert_eq!(q.pop(), Some("low"));
}

#[test]
fn dequeue_fifo_within_priority() {
    let mut q = PriorityQueue::new();
    q.push("first", 3);
    q.push("second", 3);
    assert_eq!(q.pop(), Some("first"));
    assert_eq!(q.pop(), Some("second"));
}

#[test]
fn dequeue_empty() {
    let mut q: PriorityQueue<u8> = PriorityQueue::new();
    assert_eq!(q.pop(), None);
    assert!(q.is_empty());
}

#[test]
fn duplicate_id() {
    let mut s = JobStore::new(MemoryBackend::new(), "ns");
    let e = env(&[1]);
    assert!(s.submit(&e, "{}", 1).1);
    assert!(!s.submit(&e, "{}", 2).1);
    assert_eq!(s.len(), 1);
}

#[test]
fn payload_size_bounds() {
    let frame = vec![0u8; MAX_IMAGE_BYTES];
    let e = env(&frame);
    assert!(validate_envelope(&e, &PRODUCTS).is_none());
    let mut over = e;
    over.image.byte_length = MAX_IMAGE_BYTES + 1;
    assert!(validate_envelope(&over, &PRODUCTS).unwrap().contains("cap"));
}

#[test]
fn deser_wrong_type() {
    let mut e = env(&[1]);
    e.version = 2;
    assert!(validate_envelope(&e, &PRODUCTS).unwrap().contains("not a trio-assessment"));
}

#[test]
fn len_after_mixed() {
    let mut s = JobStore::new(MemoryBackend::new(), "ns");
    let a = env(&[1]);
    let b = env(&[2]);
    assert!(s.submit(&a, "{}", 1).1);
    assert!(!s.submit(&a, "{}", 2).1);
    assert!(s.submit(&b, "{}", 3).1);
    assert_eq!(s.len(), 2);
}
