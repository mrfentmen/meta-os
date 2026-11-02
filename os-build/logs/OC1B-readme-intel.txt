warning: fields `gate` and `push` are never read
  --> crates/intel/src/b12a_drills/drills/attempt_gate.rs:56:5
   |
53 | struct Ctx<'a> {
   |        --- fields in this struct
...
56 |     gate: &'a dyn Gate,
   |     ^^^^
57 |     push: &'a dyn Push,
   |     ^^^^
   |
   = note: `#[warn(dead_code)]` (part of `#[warn(unused)]`) on by default

warning: function `find_sub` is never used
  --> crates/intel/src/b12a_drills/security_pass.rs:92:4
   |
92 | fn find_sub(chars: &[char], needle: &str) -> Option<usize> {
   |    ^^^^^^^^

warning: `intel` (lib) generated 2 warnings
   Compiling intel v0.1.0 (/private/tmp/oc500-baseline/crates/intel)
error[E0063]: missing field `spec` in initializer of `PlanJob`
  --> crates/intel/tests/error_paths.rs:31:5
   |
31 |     PlanJob {
   |     ^^^^^^^ missing `spec`

error[E0063]: missing field `spec` in initializer of `PlanJob`
   --> crates/intel/tests/edge_cases.rs:225:13
    |
225 |             PlanJob { key: "a".to_string(), title: "A".to_string(), files: vec![], deps: vec![], max_attempts: 0 },
    |             ^^^^^^^ missing `spec`

error[E0063]: missing field `spec` in initializer of `PlanJob`
   --> crates/intel/tests/edge_cases.rs:226:13
    |
226 |             PlanJob { key: "b".to_string(), title: "B".to_string(), files: vec![], deps: vec![], max_attempts: 11 },
    |             ^^^^^^^ missing `spec`

error[E0063]: missing field `spec` in initializer of `PlanJob`
   --> crates/intel/tests/edge_cases.rs:227:13
    |
227 |             PlanJob { key: "c".to_string(), title: "C".to_string(), files: vec![], deps: vec![], max_attempts: 1 },
    |             ^^^^^^^ missing `spec`

For more information about this error, try `rustc --explain E0063`.
error: could not compile `intel` (test "edge_cases") due to 3 previous errors
warning: build failed, waiting for other jobs to finish...
error: could not compile `intel` (test "error_paths") due to 1 previous error
warning: `intel` (lib test) generated 2 warnings (2 duplicates)
