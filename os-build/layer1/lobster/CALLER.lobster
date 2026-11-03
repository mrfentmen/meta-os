// os-build/layer1/lobster/CALLER.lobster — the caller skeleton (BF6-04 / F1)
//
// STATUS: NOT COMPILED, NOT RUN. There is no `svc_call` builtin in any Lobster
// build in this repo, and no Lobster host has been built from source. This file
// is the shape the host must satisfy, written down so the host work has a target
// instead of a vibe. It is not evidence that anything works.
//
// The three calls below are the whole contract:
//   1. resolve a name to a dispatcher entry
//   2. call it with an argument blob and an output buffer
//   3. read the service's own code back, unchanged

// One round trip against logd. `logd.log_info(tag, msg) -> code` is the smallest
// callable function worth having: it takes two slices, returns one code, and the
// service writes an independent line to the serial port, so both sides of the
// trip are visible in one transcript.
let code = svc_call("logd.log_info", "smoke", "round trip")

// A service-level refusal is a code, not an exception: 5xxx means the service
// said no and said why, and this layer must not flatten that distinction.
if code == 0:
    print("service answered: 0 (accepted)\n")
else:
    print("service refused: " + string(code) + "\n")

// The read-back half: fs.stat on the root, which returns two values and therefore
// proves the dispatcher can carry more than one return through the ABI.
let out = svc_call2("fs.stat", "1")
print("fs.stat root: ino=" + string(out[0]) + " code=" + string(out[1]) + "\n")

// NOT BUILT, in order:
//   - no `svc_call` / `svc_call2` builtin exists (host_roundtrip needs a Lobster
//     build with the dispatcher registered; see HOST_REQUIREMENTS.md §3)
//   - no service exports a callable function yet (`grep -rn '^export fn' services/`)
//   - no transcript exists, so this file must never be cited as one
