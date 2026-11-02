// services/updater/delta.goose
//
// B-L1-122 — Updater delta manifests: component-level deltas, plan output unchanged in kind.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT "UNCHANGED IN KIND" MEANS
// ------------------------------
// A delta still produces a PLAN (B-L1-34's shape: a decision about a slot, never a write).
// What changes is the amount of data that plan needs: instead of shipping the whole new
// component, the manifest ships instructions that turn the installed bytes into the new
// bytes. Applying them is still the caller's job, still to the inactive slot, and still
// followed by a reboot and a health confirmation.
//
// A DELTA IS REFUSED UNLESS THE BASE IS EXACTLY WHAT IT WAS BUILT AGAINST
// ---------------------------------------------------------------------
// Each delta names the digest and length of the file it expects to find. If they do not
// match, the delta is not "probably fine" -- it is *wrong*, and applying it produces bytes
// that fail the new digest anyway. Refusing early (E_ROLLBACK) costs one retry; applying
// anyway costs a half-written slot on a machine that now cannot boot.
//
// THE THREE OPERATIONS, AND NOTHING ELSE
// --------------------------------------
//   COPY      copy [from_off, from_len) of the base to the output
//   LITERAL   insert bytes carried in the manifest
//   FILL      write one byte, n times (zero runs are most of a real binary diff)
//
// No move-with-overlap, no jump tables, no compression. Each of those is a real win and each
// one is a format the receiver must implement exactly; the point of this task is to get the
// *shape* of component deltas right before optimising what fills them.
//
// SIZE, STATED
// ------------
// Four operations per component, 8 components (the manifest's MF_MAX_FILES). A real delta
// tool would produce hundreds of operations; the format below is the same format, with a
// bound small enough to fit in a fixed buffer and be tested on the host.

import common.err.err;
import common.fmt.fmt;
import common.hash.hash;
import updater.updater;

let DL_OPS_MAX: i64 = 4;
let DL_LIT_MAX: i64 = 64;
let DL_DIGEST: i64 = 32;

let DL_COPY: i64 = 0;
let DL_LITERAL: i64 = 1;
let DL_FILL: i64 = 2;

struct DeltaOp {
    kind: i64,
    from_off: i64,     // COPY: source offset in the installed file
    from_len: i64,     // COPY: length; FILL: repeat count
    fill: i64,         // FILL: the byte
    lit_off: i64,      // LITERAL: offset into the manifest's literal pool
    lit_len: i64,
}

struct DeltaFile {
    path: u8[..32] = [0; 32],
    path_len: i64,
    base_len: i64,                    // required length of the installed file
    base_digest: u8[..32] = [0; 32],            // required digest of the installed file
    new_len: i64,
    new_digest: u8[..32] = [0; 32],
    ops: DeltaOp[..4] = [DeltaOp { .. }; 4],
    nops: i64,
}

struct DeltaPlan {
    action: i64,                      // UPD_APPLY_NONE / UPD_APPLY_SLOT / UPD_APPLY_REBOOT
    slot: i64,
    files: i64,
    bytes_to_write: i64,
    bytes_shipped: i64,               // literal bytes the update had to carry
    savings: i64,                     // bytes_to_write - bytes_shipped, can be negative
    refused: i64,                     // files refused because the base did not match
}

// ---------------------------------------------------------------------------
// Planning
// ---------------------------------------------------------------------------

// Build the plan for a delta against the INSTALLED files.
//
// `base_lens` and `base_digests` are parallel to dfiles: the caller reads them from the active
// slot. Returns (plan, code); E_ROLLBACK means at least one component's base did not match and
// `plan.refused` says how many. The caller must not apply a plan whose refused count is not
// zero -- the plan is returned anyway so the log can name the file that moved.
fn delta_plan(dfiles: DeltaFile[..8], count: i64, base_lens: i64[..8], base_digests: u8[..32][..8],
              active_slot: i64) -> DeltaPlan, i64 {
    var p: DeltaPlan = DeltaPlan {
        action: 0,
        slot: 0,
        files: 0,
        bytes_to_write: 0,
        bytes_shipped: 0,
        savings: 0,
        refused: 0,
    };
    p.action = UPD_APPLY_NONE;
    p.slot = active_slot;
    p.files = count;
    p.bytes_to_write = 0;
    p.bytes_shipped = 0;
    p.savings = 0;
    p.refused = 0;

    if count <= 0 { return p, E_INVAL; }
    if count > MF_MAX_FILES { return p, E_NOROOM; }

    var i: i64 = 0;
    while i < count {
        if base_lens[i] != dfiles[i].base_len { p.refused = p.refused + 1; }
        else if !delta_digest_eq(base_digests[i], dfiles[i].base_digest) { p.refused = p.refused + 1; }
        p.bytes_to_write = p.bytes_to_write + dfiles[i].new_len;
        p.bytes_shipped = p.bytes_shipped + delta_literal_bytes(dfiles[i]);
        i = i + 1;
    }
    p.savings = p.bytes_to_write - p.bytes_shipped;
    if p.refused > 0 { return p, E_ROLLBACK; }

    // The two-step shape from the update contract: write the inactive slot, then reboot. A
    // delta does not change that; activation is never something an updater does to itself.
    p.action = UPD_APPLY_SLOT;
    if p.bytes_to_write > 0 { p.action = UPD_APPLY_REBOOT; }
    return p, CODE_OK;
}

fn delta_digest_eq(a: u8[..32], b: u8[..32]) -> bool {
    var i: i64 = 0;
    while i < DL_DIGEST {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn delta_literal_bytes(f: DeltaFile) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < f.nops {
        if f.ops[i].kind == DL_LITERAL { n = n + f.ops[i].lit_len; }
        i = i + 1;
    }
    return n;
}

// ---------------------------------------------------------------------------
// Applying one file
// ---------------------------------------------------------------------------

// Turn `base` into the new bytes in `out`. The caller compares the SHA-256 of `out` to
// `f.new_digest` before anything reaches the disk -- this function does not write.
//
// Every offset is bounds-checked against `base` and `out` before it is used: a delta is
// data from outside, and a delta that reads past the base is a crash in a slot that was
// about to be written.
fn delta_apply(f: DeltaFile&, base: const u8[:], lit: const u8[:], out: u8[>..]&, cap: i64) -> i64, i64 {
    if base.len != f.base_len { return 0, E_ROLLBACK; }
    if f.new_len > cap { return 0, E_NOROOM; }

    var produced: i64 = 0;
    var i: i64 = 0;
    while i < f.nops {
        let op = f.ops[i];
        if op.kind == DL_COPY {
            if op.from_off < 0 || op.from_len < 0 { return produced, E_CORRUPT; }
            if op.from_off + op.from_len > base.len { return produced, E_CORRUPT; }
            if out.len + op.from_len > cap { return produced, E_NOROOM; }
            var k: i64 = 0;
            while k < op.from_len {
                out.push(base[op.from_off + k]);
                k = k + 1;
            }
            produced = produced + op.from_len;
        } else if op.kind == DL_FILL {
            if op.from_len < 0 || op.from_len > f.new_len { return produced, E_CORRUPT; }
            if out.len + op.from_len > cap { return produced, E_NOROOM; }
            var k: i64 = 0;
            while k < op.from_len {
                out.push(op.fill as u8);
                k = k + 1;
            }
            produced = produced + op.from_len;
        } else if op.kind == DL_LITERAL {
            if op.lit_off < 0 || op.lit_len < 0 { return produced, E_CORRUPT; }
            if op.lit_off + op.lit_len > lit.len { return produced, E_CORRUPT; }
            if out.len + op.lit_len > cap { return produced, E_NOROOM; }
            var k: i64 = 0;
            while k < op.lit_len {
                out.push(lit[op.lit_off + k]);
                k = k + 1;
            }
            produced = produced + op.lit_len;
        } else {
            return produced, E_UNSUPPORTED;
        }
        i = i + 1;
    }

    // The length is the strongest cheap check that the operations add up. The digest is the
    // expensive one, and it belongs to the caller because hashing into a scratch buffer is
    // its choice.
    if produced != f.new_len { return produced, E_CORRUPT; }
    return produced, CODE_OK;
}

// Verify the bytes delta_apply produced. Split out so the digest path is one call and the
// caller can hash into its own buffer.
fn delta_verify(f: DeltaFile&, content: u8[:], got_digest: u8[..32]) -> i64 {
    var digest: u8[>..] = [];
    if !sha256(content, digest, 32) { return E_VERIFY; }
    if digest.len != DL_DIGEST { return E_VERIFY; }
    var i: i64 = 0;
    while i < DL_DIGEST {
        got_digest[i] = digest[i];
        i = i + 1;
    }
    if !delta_digest_eq(got_digest, f.new_digest) { return E_VERIFY; }
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Format, as text
// ---------------------------------------------------------------------------
//
// One line per operation, so a delta manifest stays greppable and diffable -- the same reason
// the update manifest is text:
//
//   delta 1
//   file path=vmlinuz base_len=8123 base_sha256=<64 hex> new_len=8301 new_sha256=<64 hex>
//   copy from=0 len=4096
//   fill byte=0 count=128
//   literal off=0 len=37
//   end
//
// Parsing it is deliberately NOT in this task: B-L1-131 (manifest hardening) owns the parser
// and its hostile inputs, and two parsers for one format is how they disagree.

fn delta_ops_max() -> i64 { return DL_OPS_MAX; }

fn delta_op_name(kind: i64) -> const u8[:] {
    if kind == DL_COPY { return "copy"; }
    if kind == DL_LITERAL { return "literal"; }
    if kind == DL_FILL { return "fill"; }
    return "?";
}

// One plan line for the report: "delta plan: slot=B files=3 write=8301 ship=4123 saved=4178".
fn delta_plan_line(p: DeltaPlan&, out: u8[>..]&, cap: i64) -> bool {
    if !append_str(out, cap, "delta plan: slot=") { return false; }
    if !append_int(out, cap, p.slot) { return false; }
    if !append_str(out, cap, " files=") { return false; }
    if !append_int(out, cap, p.files) { return false; }
    if !append_str(out, cap, " write=") { return false; }
    if !append_int(out, cap, p.bytes_to_write) { return false; }
    if !append_str(out, cap, " ship=") { return false; }
    if !append_int(out, cap, p.bytes_shipped) { return false; }
    if !append_str(out, cap, " saved=") { return false; }
    if !append_int(out, cap, p.savings) { return false; }
    if !append_str(out, cap, " refused=") { return false; }
    return append_int(out, cap, p.refused);
}
