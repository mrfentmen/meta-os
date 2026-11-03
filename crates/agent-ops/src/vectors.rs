//! Lexical vector memory over ledger records.
//!
//! Cross-session recall ("what fixed this last time?") as TF-IDF term
//! vectors with cosine ranking. Zero model, zero network, deterministic.
//!
//! Honest boundary: these are LEXICAL vectors, not neural embeddings.
//! Paraphrase-level similarity needs an embedding backend; records keep
//! their raw text so a future backend can re-index without data loss.

use std::collections::HashMap;

/// Tokenize like the agent-ops JS reference: lowercase alphanumerics,
/// length 2..32.
pub fn tokenize(text: &str) -> Vec<String> {
    text.split(|c: char| !(c.is_ascii_alphanumeric() || c == '_'))
        .filter(|t| t.len() > 1 && t.len() < 33)
        .map(|t| t.to_ascii_lowercase())
        .collect()
}

/// Sparse term vector: weights are (1 + ln(count)) * idf.
pub type SparseVec = HashMap<String, f64>;

pub fn term_vector(tokens: &[String], idf: &HashMap<String, f64>) -> SparseVec {
    let mut counts: HashMap<&str, f64> = HashMap::new();
    for t in tokens {
        *counts.entry(t.as_str()).or_insert(0.0) += 1.0;
    }
    let mut vec = HashMap::new();
    for (t, c) in counts {
        let w = (1.0 + c.ln()) * idf.get(t).copied().unwrap_or(1.0);
        vec.insert(t.to_string(), w);
    }
    vec
}

fn cosine(a: &SparseVec, b: &SparseVec) -> f64 {
    let mut dot = 0.0;
    let mut na = 0.0;
    for (t, w) in a {
        na += w * w;
        if let Some(wb) = b.get(t) {
            dot += w * wb;
        }
    }
    let nb: f64 = b.values().map(|w| w * w).sum();
    if na == 0.0 || nb == 0.0 {
        return 0.0;
    }
    dot / (na.sqrt() * nb.sqrt())
}

/// A document in the index.
#[derive(Debug, Clone)]
pub struct Doc {
    pub id: String,
    pub text: String,
}

/// The index: raw texts + idf table + per-doc vectors.
#[derive(Debug, Clone)]
pub struct Index {
    pub method: &'static str,
    pub docs: Vec<Doc>,
    pub idf: HashMap<String, f64>,
    pub vectors: Vec<SparseVec>,
}

pub const METHOD: &str = "tfidf-cosine-v1 (lexical; not neural embeddings)";

/// Build an index over documents.
pub fn build_index(docs: Vec<Doc>) -> Index {
    let n = docs.len().max(1) as f64;
    let mut df: HashMap<String, usize> = HashMap::new();
    let tokenized: Vec<Vec<String>> = docs.iter().map(|d| tokenize(&d.text)).collect();
    for toks in &tokenized {
        let mut seen = std::collections::HashSet::new();
        for t in toks {
            if seen.insert(t) {
                *df.entry(t.clone()).or_insert(0) += 1;
            }
        }
    }
    let mut idf = HashMap::new();
    for (t, c) in df {
        idf.insert(t, (1.0 + n / c as f64).ln());
    }
    let vectors = tokenized.iter().map(|t| term_vector(t, &idf)).collect();
    Index { method: METHOD, docs, idf, vectors }
}

/// Top-k documents for a query string, highest score first.
#[derive(Debug)]
pub struct Hit {
    pub id: String,
    pub score: f64,
}

pub fn query(index: &Index, text: &str, k: usize) -> Vec<Hit> {
    let q = term_vector(&tokenize(text), &index.idf);
    let mut hits: Vec<Hit> = index
        .docs
        .iter()
        .enumerate()
        .map(|(i, d)| Hit { id: d.id.clone(), score: cosine(&q, &index.vectors[i]) })
        .collect();
    hits.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());
    hits.truncate(k);
    hits
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> Index {
        build_index(vec![
            Doc { id: "a".into(), text: "fix flaky clipboard test with a barrier".into() },
            Doc { id: "b".into(), text: "bake the plymouth splash theme".into() },
            Doc { id: "c".into(), text: "clipboard test sleeps hide the race".into() },
        ])
    }

    #[test]
    fn ranks_relevant_doc_first() {
        let idx = sample();
        let hits = query(&idx, "clipboard test race barrier", 3);
        assert_eq!(hits.len(), 3);
        // Both clipboard docs outrank the splash doc.
        assert!(hits[2].id == "b");
        assert!(hits[0].score > 0.0);
    }

    #[test]
    fn empty_query_scores_zero() {
        let idx = sample();
        for h in query(&idx, "", 3) {
            assert_eq!(h.score, 0.0);
        }
    }

    #[test]
    fn unrelated_text_scores_low() {
        let idx = sample();
        let hits = query(&idx, "zebra xylophone quantum", 3);
        for h in hits {
            assert!(h.score < 0.05, "unexpected similarity: {}", h.score);
        }
    }
}
