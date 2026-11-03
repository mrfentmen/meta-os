//! CB2-333/334/349 — the dashboard's four machine-metric cards.
//!
//! The rule these tests protect: a missing reading and a reported zero are
//! never the same thing on screen. An empty snapshot says so in words, and a
//! wrong type is refused at the parse with the field named.
use dashboard::metrics::{
    cards, cpu_card, memory_card, network_card, parse_metric, parse_snapshot, storage_card,
    Metric, MetricsSnapshot, EMPTY_READING,
};

fn full_snapshot() -> MetricsSnapshot {
    MetricsSnapshot {
        cpu_pct: Some(Metric { value: 12.5, unit: "%" }),
        memory: Some(Metric { value: 2048.0, unit: "MiB" }),
        storage: Some(Metric { value: 41.25, unit: "GiB" }),
        network: Some(Metric { value: 0.0, unit: "Mbit/s" }),
    }
}

#[test]
fn dashboard_empty_snapshot() {
    let empty = MetricsSnapshot::default();
    assert!(empty.is_empty());

    let rendered = cards(&empty);
    assert_eq!(rendered.len(), 4, "the four cards are always present");
    assert_eq!(
        rendered.iter().map(|c| c.title).collect::<Vec<_>>(),
        vec!["CPU", "Memory", "Storage", "Network"],
        "card order never shuffles when a source goes quiet",
    );
    for card in &rendered {
        assert!(card.empty, "{} is in its empty state", card.title);
        assert_eq!(card.value, EMPTY_READING);
        assert_eq!(card.detail, "this source did not answer");
        assert_ne!(card.value, "0.0", "no reading is never shown as a zero");
    }
}

#[test]
fn dashboard_empty_snapshot_is_per_card() {
    // One quiet source empties one card; the other three keep their readings.
    let snapshot = MetricsSnapshot { cpu_pct: None, ..full_snapshot() };
    assert!(!snapshot.is_empty(), "one quiet source is not an empty machine");
    assert!(cpu_card(&snapshot).empty);
    assert_eq!(cpu_card(&snapshot).value, EMPTY_READING);
    for card in [memory_card(&snapshot), storage_card(&snapshot), network_card(&snapshot)] {
        assert!(!card.empty, "{} still has its reading", card.title);
    }
}

#[test]
fn dashboard_bad_metric_type() {
    // A non-numeric value is refused with the field named, never coerced to 0.
    assert_eq!(
        parse_metric("cpu", "busy", "%").unwrap_err(),
        "cpu: not a number: \"busy\"",
    );
    assert_eq!(
        parse_metric("memory", "2 GiB", "MiB").unwrap_err(),
        "memory: not a number: \"2 GiB\"",
    );
    // A blank value is "not reported", not zero.
    assert_eq!(
        parse_metric("storage", "   ", "GiB").unwrap_err(),
        "storage: no reading reported",
    );
    // Negative and non-finite values are refused by name.
    assert_eq!(
        parse_metric("network", "-1", "Mbit/s").unwrap_err(),
        "network: must not be negative, got \"-1\"",
    );
    assert_eq!(
        parse_metric("cpu", "NaN", "%").unwrap_err(),
        "cpu: must be a finite number, got \"NaN\"",
    );

    // The snapshot parser reports every bad field at once.
    let errors = parse_snapshot("busy", "2048", "-4", "1").unwrap_err();
    assert_eq!(errors.len(), 2, "one error per bad field: {errors:?}");
    assert!(errors[0].starts_with("cpu:"));
    assert!(errors[1].starts_with("storage:"));
}

#[test]
fn dashboard_parse_accepts_the_reported_forms() {
    let snapshot = parse_snapshot("12.5", "2048", "41.25", "0").expect("all four parse");
    assert_eq!(snapshot.cpu_pct, Some(Metric { value: 12.5, unit: "%" }));
    assert_eq!(snapshot.network, Some(Metric { value: 0.0, unit: "Mbit/s" }));
    assert!(!snapshot.is_empty());
}

#[test]
fn dashboard_card_cpu() {
    let snapshot = full_snapshot();
    let card = cpu_card(&snapshot);
    assert_eq!(card.title, "CPU");
    assert_eq!(card.value, "12.5");
    assert_eq!(card.detail, "%");
    assert!(!card.empty);
}

#[test]
fn dashboard_card_memory() {
    let card = memory_card(&full_snapshot());
    assert_eq!(card.title, "Memory");
    assert_eq!(card.value, "2048.0");
    assert_eq!(card.detail, "MiB");
}

#[test]
fn dashboard_card_storage() {
    let card = storage_card(&full_snapshot());
    assert_eq!(card.title, "Storage");
    assert_eq!(card.value, "41.2", "one decimal place, as the card renders it");
    assert_eq!(card.detail, "GiB");
}

#[test]
fn dashboard_card_network() {
    let card = network_card(&full_snapshot());
    assert_eq!(card.title, "Network");
    assert_eq!(card.value, "0.0", "a reported zero IS a reading, unlike an empty card");
    assert_eq!(card.detail, "Mbit/s");
    assert!(!card.empty);
}
