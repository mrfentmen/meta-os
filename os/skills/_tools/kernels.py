"""Verified example kernels for the Meta OS skill catalog.

Every entry is a complete, runnable program. `generate_catalog.py` embeds
them verbatim; `verify_catalog.py` executes them. Nothing here is a sketch:
the Python runs under python3, the JavaScript under node, the Rust under
rustc -O.
"""

KERNELS = {
    "rust": {
        "python": '''class Config:
    def __init__(self, name, retries):
        self.name, self.retries = name, retries


def describe(config):
    return f"{config.name}:{config.retries}"


config = Config("relay", 3)
print(describe(config))''',
        "javascript": '''const config = { name: "relay", retries: 3 };
const describe = (c) => `${c.name}:${c.retries}`;
console.log(describe(config));''',
        "rust": '''struct Config {
    name: String,
    retries: u32,
}

fn describe(c: &Config) -> String {
    format!("{}:{}", c.name, c.retries)
}

fn main() {
    let c = Config { name: "relay".into(), retries: 3 };
    println!("{}", describe(&c));
}''',
    },
    "linux": {
        "python": '''unit = """[Unit]
Description=relay
[Service]
ExecStart=/usr/local/bin/relay
Restart=always"""

required = ["Description", "ExecStart"]
present = {line.split("=", 1)[0] for line in unit.splitlines() if "=" in line}
print("missing:", [key for key in required if key not in present])''',
        "javascript": '''const unit = "[Unit]\\nDescription=relay\\n[Service]\\nExecStart=/usr/local/bin/relay";
const present = new Set(unit.split("\\n").filter(l => l.includes("=")).map(l => l.split("=")[0]));
console.log("missing:", ["Description", "ExecStart"].filter(k => !present.has(k)));''',
        "rust": '''fn main() {
    let unit = "[Unit]\\nDescription=relay\\n[Service]\\nExecStart=/usr/local/bin/relay";
    let keys: Vec<&str> = unit
        .lines()
        .filter(|line| line.contains('='))
        .map(|line| line.split('=').next().unwrap())
        .collect();
    let missing: Vec<&str> = ["Description", "ExecStart"]
        .iter()
        .copied()
        .filter(|key| !keys.contains(key))
        .collect();
    println!("missing: {:?}", missing);
}''',
    },
    "debian": {
        "python": '''import hashlib

expected = {"os.img": hashlib.sha256(b"image-bytes").hexdigest()}
actual = {"os.img": hashlib.sha256(b"image-bytes").hexdigest()}
print("manifest ok:", expected == actual)

actual["os.img"] = hashlib.sha256(b"tampered").hexdigest()
print("after tamper:", expected == actual)''',
        "javascript": '''const crypto = require("node:crypto");
const digest = (data) => crypto.createHash("sha256").update(data).digest("hex");
const expected = { "os.img": digest("image-bytes") };
const actual = { "os.img": digest("image-bytes") };
console.log("manifest ok:", expected["os.img"] === actual["os.img"]);
actual["os.img"] = digest("tampered");
console.log("after tamper:", expected["os.img"] === actual["os.img"]);''',
        "rust": '''fn digest(bytes: &[u8]) -> u64 {
    let mut value: u64 = 0xcbf29ce484222325;
    for byte in bytes {
        value ^= *byte as u64;
        value = value.wrapping_mul(0x100000001b3);
    }
    value
}

fn main() {
    let expected = digest(b"image-bytes");
    let actual = digest(b"image-bytes");
    println!("manifest ok: {}", expected == actual);
    println!("after tamper: {}", expected == digest(b"tampered"));
}''',
    },
    "network": {
        "python": '''import random

random.seed(7)


def delays(attempts, base=0.2):
    return [round(base * 2 ** n * (0.5 + random.random() / 2), 2)
            for n in range(attempts)]


print("delays:", delays(4))''',
        "javascript": '''let seed = 7;
const rand = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const delays = (n, base = 0.2) => Array.from({ length: n },
  (_, i) => Number((base * 2 ** i * (0.5 + rand() / 2)).toFixed(2)));
console.log("delays:", delays(4));''',
        "rust": '''fn main() {
    let mut seed: u64 = 7;
    let delays: Vec<f64> = (0..4)
        .map(|n| {
            seed = seed.wrapping_mul(16807) % 2147483647;
            let jitter = 0.5 + (seed as f64 / 2147483647.0) / 2.0;
            (0.2 * 2f64.powi(n) * jitter * 100.0).round() / 100.0
        })
        .collect();
    println!("delays: {:?}", delays);
}''',
    },
    "data": {
        "python": '''import json

lines = ['{"id": 1}', '{"id": 2}', 'not json', '{"id": 3}']
bad = []
for number, line in enumerate(lines, 1):
    try:
        json.loads(line)
    except json.JSONDecodeError:
        bad.append(number)

print("records:", len(lines) - len(bad), "bad:", bad)''',
        "javascript": '''const lines = ['{"id": 1}', '{"id": 2}', "not json", '{"id": 3}'];
const bad = [];
lines.forEach((line, index) => {
  try { JSON.parse(line); } catch { bad.push(index + 1); }
});
console.log("records:", lines.length - bad.length, "bad:", bad);''',
        "rust": '''fn valid(line: &str) -> bool {
    line.starts_with('{') && line.ends_with('}') && line.contains("\\"id\\"")
}

fn main() {
    let lines = ["{\\"id\\": 1}", "{\\"id\\": 2}", "not json", "{\\"id\\": 3}"];
    let bad: Vec<usize> = lines
        .iter()
        .enumerate()
        .filter(|(_, line)| !valid(line))
        .map(|(index, _)| index + 1)
        .collect();
    println!("records: {} bad: {:?}", lines.len() - bad.len(), bad);
}''',
    },
    "security": {
        "python": '''import re

text = "key sk-abcdef123456 token=abcd1234 ok"
clean = re.sub(r"sk-[A-Za-z0-9]{8,}", "[redacted]", text)
clean = re.sub(r"token=\\w+", "token=[redacted]", clean)
print(clean)''',
        "javascript": '''const text = "key sk-abcdef123456 token=abcd1234 ok";
const clean = text
  .replace(/sk-[A-Za-z0-9]{8,}/g, "[redacted]")
  .replace(/token=\\w+/g, "token=[redacted]");
console.log(clean);''',
        "rust": '''fn redact(text: &str) -> String {
    text.split_whitespace()
        .map(|word| {
            if word.starts_with("sk-") {
                "[redacted]"
            } else if word.starts_with("token=") {
                "token=[redacted]"
            } else {
                word
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

fn main() {
    println!("{}", redact("key sk-abcdef123456 token=abcd1234 ok"));
}''',
    },
    "testing": {
        "python": '''checks = [("unit", 0), ("lint", 0), ("types", 2)]
failed = next((name for name, code in checks if code != 0), None)
print("passed:", failed is None, "failed:", failed)''',
        "javascript": '''const checks = [["unit", 0], ["lint", 0], ["types", 2]];
const failed = checks.find(([, code]) => code !== 0);
console.log("passed:", failed === undefined, "failed:", failed ? failed[0] : null);''',
        "rust": '''fn main() {
    let checks = [("unit", 0), ("lint", 0), ("types", 2)];
    let failed = checks
        .iter()
        .find(|(_, code)| *code != 0)
        .map(|(name, _)| *name);
    println!("passed: {} failed: {:?}", failed.is_none(), failed);
}''',
    },
    "debugging": {
        "python": '''def first_bad(low, high, bad):
    while low < high:
        mid = (low + high) // 2
        if bad(mid):
            high = mid
        else:
            low = mid + 1
    return low


print("first bad:", first_bad(0, 100, lambda n: n >= 37))''',
        "javascript": '''function firstBad(low, high, bad) {
  while (low < high) {
    const mid = Math.floor((low + high) / 2);
    if (bad(mid)) high = mid; else low = mid + 1;
  }
  return low;
}
console.log("first bad:", firstBad(0, 100, (n) => n >= 37));''',
        "rust": '''fn main() {
    let (mut low, mut high) = (0, 100);
    while low < high {
        let mid = (low + high) / 2;
        if mid >= 37 {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    println!("first bad: {}", low);
}''',
    },
    "performance": {
        "python": '''samples = sorted([12, 40, 33, 51, 22, 48, 60])


def pct(p):
    index = round((p / 100) * (len(samples) - 1))
    return samples[min(index, len(samples) - 1)]


print("p50:", pct(50), "p95:", pct(95))''',
        "javascript": '''const samples = [12, 40, 33, 51, 22, 48, 60].sort((a, b) => a - b);
const pct = (p) => samples[Math.min(Math.round((p / 100) * (samples.length - 1)), samples.length - 1)];
console.log("p50:", pct(50), "p95:", pct(95));''',
        "rust": '''fn main() {
    let mut samples = vec![12, 40, 33, 51, 22, 48, 60];
    samples.sort();
    let pct = |p: f64| {
        let index = ((p / 100.0) * (samples.len() - 1) as f64).round() as usize;
        samples[index.min(samples.len() - 1)]
    };
    println!("p50: {} p95: {}", pct(50.0), pct(95.0));
}''',
    },
    "docs": {
        "python": '''import os
import re
import tempfile

with tempfile.TemporaryDirectory() as root:
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("[a](a.md) [b](missing.md)")
    with open(os.path.join(root, "README.md"), encoding="utf-8") as fh:
        text = fh.read()
    links = re.findall(r"\\]\\(([^)]+)\\)", text)
    broken = [link for link in links
              if not os.path.exists(os.path.join(root, link))]
    print("broken:", broken)''',
        "javascript": '''const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const root = fs.mkdtempSync(path.join(os.tmpdir(), "docs-"));
fs.writeFileSync(path.join(root, "README.md"), "[a](a.md) [b](missing.md)");
const text = fs.readFileSync(path.join(root, "README.md"), "utf8");
const links = [...text.matchAll(/\\]\\(([^)]+)\\)/g)].map((m) => m[1]);
console.log("broken:", links.filter((link) => !fs.existsSync(path.join(root, link))));''',
        "rust": '''use std::fs;

fn main() {
    let text = "[a](a.md) [b](missing.md)";
    let broken: Vec<&str> = text
        .split("](")
        .skip(1)
        .map(|part| part.split(')').next().unwrap())
        .filter(|link| fs::metadata(*link).is_err())
        .collect();
    println!("broken: {:?}", broken);
}''',
    },
    "release": {
        "python": '''def bump(version, part="patch"):
    major, minor, patch = (int(piece) for piece in version.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


print(bump("1.4.2"), bump("1.4.2", "minor"))''',
        "javascript": '''function bump(version, part = "patch") {
  const [major, minor, patch] = version.split(".").map(Number);
  if (part === "major") return `${major + 1}.0.0`;
  if (part === "minor") return `${major}.${minor + 1}.0`;
  return `${major}.${minor}.${patch + 1}`;
}
console.log(bump("1.4.2"), bump("1.4.2", "minor"));''',
        "rust": '''fn bump(version: &str, part: &str) -> String {
    let mut pieces: Vec<u32> = version.split('.').map(|p| p.parse().unwrap()).collect();
    match part {
        "major" => { pieces[0] += 1; pieces[1] = 0; pieces[2] = 0; }
        "minor" => { pieces[1] += 1; pieces[2] = 0; }
        _ => pieces[2] += 1,
    }
    format!("{}.{}.{}", pieces[0], pieces[1], pieces[2])
}

fn main() {
    println!("{} {}", bump("1.4.2", "patch"), bump("1.4.2", "minor"));
}''',
    },
    "ops": {
        "python": '''events = [("detected", 100), ("ack", 160),
          ("mitigated", 400), ("resolved", 520)]

for (name, start), (next_name, end) in zip(events, events[1:]):
    print(f"{name}_to_{next_name}: {end - start}")''',
        "javascript": '''const events = [["detected", 100], ["ack", 160], ["mitigated", 400], ["resolved", 520]];
for (let i = 0; i < events.length - 1; i += 1) {
  const [name, start] = events[i];
  const [nextName, end] = events[i + 1];
  console.log(`${name}_to_${nextName}: ${end - start}`);
}''',
        "rust": '''fn main() {
    let events = [("detected", 100), ("ack", 160), ("mitigated", 400), ("resolved", 520)];
    for pair in events.windows(2) {
        println!("{}_to_{}: {}", pair[0].0, pair[1].0, pair[1].1 - pair[0].1);
    }
}''',
    },
    "agent": {
        "python": '''ledger = [0.40, 0.30]
cap = 1.00
estimate = 0.40
spent = sum(ledger)

print("ok:", spent + estimate <= cap, "headroom:", round(cap - spent, 2))''',
        "javascript": '''const ledger = [0.40, 0.30];
const cap = 1.00;
const estimate = 0.40;
const spent = ledger.reduce((total, usd) => total + usd, 0);
console.log("ok:", spent + estimate <= cap, "headroom:", Number((cap - spent).toFixed(2)));''',
        "rust": '''fn main() {
    let ledger = [0.40, 0.30];
    let cap = 1.00;
    let estimate = 0.40;
    let spent: f64 = ledger.iter().sum();
    println!("ok: {} headroom: {:.2}", spent + estimate <= cap, cap - spent);
}''',
    },
    "science": {
        "python": '''import math

xs = [1.0, 2.0, 3.0, 4.0]
mean = sum(xs) / len(xs)
sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / (len(xs) - 1))
print("mean:", round(mean, 3), "sd:", round(sd, 3))''',
        "javascript": '''const xs = [1.0, 2.0, 3.0, 4.0];
const mean = xs.reduce((a, x) => a + x, 0) / xs.length;
const variance = xs.reduce((a, x) => a + (x - mean) ** 2, 0) / (xs.length - 1);
console.log("mean:", mean.toFixed(3), "sd:", Math.sqrt(variance).toFixed(3));''',
        "rust": '''fn main() {
    let xs = [1.0_f64, 2.0, 3.0, 4.0];
    let mean = xs.iter().sum::<f64>() / xs.len() as f64;
    let variance = xs.iter().map(|x| (x - mean).powi(2)).sum::<f64>()
        / (xs.len() - 1) as f64;
    println!("mean: {:.3} sd: {:.3}", mean, variance.sqrt());
}''',
    },
    "product": {
        "python": '''criteria = [("signup works", True), ("error shown", True),
            ("mobile layout", False)]
failed = [name for name, ok in criteria if not ok]
print("accepted:", not failed, "failed:", failed)''',
        "javascript": '''const criteria = [["signup works", true], ["error shown", true], ["mobile layout", false]];
const failed = criteria.filter(([, ok]) => !ok).map(([name]) => name);
console.log("accepted:", failed.length === 0, "failed:", failed);''',
        "rust": '''fn main() {
    let criteria = [
        ("signup works", true),
        ("error shown", true),
        ("mobile layout", false),
    ];
    let failed: Vec<&str> = criteria
        .iter()
        .filter(|(_, ok)| !ok)
        .map(|(name, _)| *name)
        .collect();
    println!("accepted: {} failed: {:?}", failed.is_empty(), failed);
}''',
    },
}
