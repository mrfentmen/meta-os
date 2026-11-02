# New service checklist (B-L1-119)

Copy `TEMPLATE.goose` to `services/<name>/<name>.goose`, add a README, and work down this
list. Every item traces to a pattern that already exists in this build-out — the point is not
new rules, it is that a new service starts from the same shape as the eighteen that came
before it.

## Before the first line

- [ ] A directory under `services/`, one service per folder. The module name matches the
      folder: `services/foo/foo.goose`, imported as `foo.foo`.
- [ ] A `README.md` with the same three sections every other service has: what it is, what it
      refuses, what it does not own. Start from `services/README_TEMPLATE.md`.
- [ ] A `Status:` line in both files: `WRITTEN (not COMPILED, not RUN)` until the Mac build
      says otherwise. Nothing in this layer may claim COMPILED without a build log to name.
- [ ] An id in `services/callmatrix/callmatrix.goose` **appended** (never renumbered — ids are
      also the numbers services report to the supervisor), plus a row listing exactly the
      services it may call.
- [ ] A row in `services/supervisor/bootorder.goose` with its `needs` mask, and `order` placed
      after everything it needs. `bo_order_ok()` is checked at start-up and will fail loudly.
- [ ] `python3 os-build/layer1/callmatrix_audit.py` reports no MISSING edge for the new
      service. (Today that script reports twelve pre-existing findings; do not add a
      thirteenth.)

## Shape of the code

- [ ] Fixed buffers only. No allocation, anywhere — the layer has no allocator.
- [ ] Every struct field has a size or a meaning in a comment; every `let X_MAX` says why that
      number.
- [ ] `init` that cannot block, cannot call the network, and leaves every other function safe
      to call even if it half-failed.
- [ ] One mutating function per concept. A second "convenience" setter is a second place for
      the invariant to be missed.
- [ ] Lookups return `(value, bool)` or an id plus a code — never a sentinel that a caller can
      use by accident.
- [ ] Error codes come from `common.err.err`. No literals: the registry is audited
      (`B-L1-137`) and a local `return 42` is invisible to that audit.
- [ ] A health line (`<name>_health`) that is cheap, cannot fail, and prints the two or three
      numbers a person would ask for. Register metrics with `watchdog.metrics` (B-L1-124).
- [ ] Log through `logd` at a level that means what it says. `tpl_fail`-style helper so no call
      site invents its own level choice.

## Tests

- [ ] A `services/tests/tNN_<name>.goose` with `say`/`check(name, cond)` in the house style,
      `t_pass`/`t_fail` counters, and `sys_exit(1)` when anything failed.
- [ ] At least one case per refusal, asserting the exact code.
- [ ] At least one hostile input, with the expected failure written next to the bytes.
- [ ] No ternary operator, no `print_*` helpers: this tree's tests use `sys_write_serial`.

## Before claiming done

- [ ] `python3 os-build/layer1/source_audit.py` reports zero findings.
- [ ] `python3 os-build/layer1/callmatrix_audit.py` shows no new MISSING edge.
- [ ] `os-build/layer1/LINK_MAP.md` regenerated (B-L1-138 keeps it current).
- [ ] The report entry says `WRITTEN` or `COMPILED` — and says which, with the file that
      proves it.
- [ ] If it touches the kernel or the boot path: `kernel/MAC_QUESTIONS.md` gets the exact API
      point it needs, not a description of a problem.

## What this checklist is not

It is not a code review. It catches the mistakes that are mechanical — a missing matrix row, a
missing test, a status word that got ahead of the build — and the design review still has to
happen with the lane that owns the area, on the branch, before a merge.
