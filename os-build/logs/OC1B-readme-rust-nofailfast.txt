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
   Compiling os-workspace v0.1.0 (/private/tmp/oc500-baseline/crates/os-workspace)
   Compiling os-memory v0.1.0 (/private/tmp/oc500-baseline/crates/os-memory)
warning: unused import: `Path`
  --> crates/parity-tests/src/tests/test_os_tree.rs:11:17
   |
11 | use std::path::{Path, PathBuf};
   |                 ^^^^
   |
   = note: `#[warn(unused_imports)]` (part of `#[warn(unused)]`) on by default

warning: unused import: `os_misc::b27::validate as vp`
  --> crates/parity-tests/src/tests/test_worlds_pack.rs:10:5
   |
10 | use os_misc::b27::validate as vp;
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^

warning: variable does not need to be mutable
  --> crates/parity-tests/src/tests/test_os_base.rs:75:9
   |
75 |     let mut flush = |token: &mut String, found: &mut Option<String>| {
   |         ----^^^^^
   |         |
   |         help: remove this `mut`
   |
   = note: `#[warn(unused_mut)]` (part of `#[warn(unused)]`) on by default

warning: variable does not need to be mutable
   --> crates/parity-tests/src/tests/test_os_livebuild.rs:109:9
    |
109 |     let mut flush = |token: &mut String, found: &mut Option<String>| {
    |         ----^^^^^
    |         |
    |         help: remove this `mut`

warning: type `StrVal` is more private than the item `FakeUpstash::strings`
  --> crates/parity-tests/src/support/fake_redis.rs:17:5
   |
17 |     pub strings: HashMap<String, StrVal>,
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ field `FakeUpstash::strings` is reachable at visibility `pub`
   |
note: but type `StrVal` is only usable at visibility `pub(self)`
  --> crates/parity-tests/src/support/fake_redis.rs:10:1
   |
10 | struct StrVal {
   | ^^^^^^^^^^^^^
   = note: `#[warn(private_interfaces)]` on by default

warning: constant `I` is never used
  --> crates/parity-tests/src/tests/test_fdny_par_clock.rs:38:7
   |
38 | const I: i64 = pc::DEFAULT_INTERVAL_SECONDS;
   |       ^
   |
   = note: `#[warn(dead_code)]` (part of `#[warn(unused)]`) on by default

warning: constant `G` is never used
  --> crates/parity-tests/src/tests/test_fdny_par_clock.rs:39:7
   |
39 | const G: i64 = pc::DEFAULT_GRACE_SECONDS;
   |       ^

warning: function `entered` is never used
  --> crates/parity-tests/src/tests/test_fdny_par_clock.rs:41:4
   |
41 | fn entered(crew: &str, at: i64, location: Option<&str>) -> pc::ParState {
   |    ^^^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os021_update.rs:29:4
   |
29 | fn root() -> PathBuf {
   |    ^^^^

warning: function `script_path` is never used
  --> crates/parity-tests/src/tests/test_os021_update.rs:32:4
   |
32 | fn script_path() -> PathBuf {
   |    ^^^^^^^^^^^

warning: function `readme_path` is never used
  --> crates/parity-tests/src/tests/test_os021_update.rs:35:4
   |
35 | fn readme_path() -> PathBuf {
   |    ^^^^^^^^^^^

warning: function `git` is never used
  --> crates/parity-tests/src/tests/test_os021_update.rs:39:4
   |
39 | fn git(cwd: &Path, args: &[&str]) -> String {
   |    ^^^

warning: struct `Fixture` is never constructed
  --> crates/parity-tests/src/tests/test_os021_update.rs:54:8
   |
54 | struct Fixture {
   |        ^^^^^^^

warning: associated items `setup`, `make_repo`, `run`, `live_content`, and `live_head` are never used
   --> crates/parity-tests/src/tests/test_os021_update.rs:64:8
    |
 63 | impl Fixture {
    | ------------ associated items in this implementation
 64 |     fn setup() -> Self {
    |        ^^^^^
...
 77 |     fn make_repo(path: &Path, content: &str) -> String {
    |        ^^^^^^^^^
...
 85 |     fn run(&self, args: &[&str], relay_root: Option<&Path>) -> (i32, String, String) {
    |        ^^^
...
100 |     fn live_content(&self) -> String {
    |        ^^^^^^^^^^^^
...
103 |     fn live_head(&self) -> String {
    |        ^^^^^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os058_gateway_unit.rs:28:4
   |
28 | fn root() -> PathBuf {
   |    ^^^^

warning: function `os_inner` is never used
  --> crates/parity-tests/src/tests/test_os058_gateway_unit.rs:31:4
   |
31 | fn os_inner() -> PathBuf {
   |    ^^^^^^^^

warning: function `read` is never used
  --> crates/parity-tests/src/tests/test_os058_gateway_unit.rs:34:4
   |
34 | fn read(p: &std::path::Path) -> String {
   |    ^^^^

warning: function `unit_path` is never used
  --> crates/parity-tests/src/tests/test_os058_gateway_unit.rs:37:4
   |
37 | fn unit_path() -> PathBuf {
   |    ^^^^^^^^^

warning: function `target_path` is never used
  --> crates/parity-tests/src/tests/test_os058_gateway_unit.rs:40:4
   |
40 | fn target_path() -> PathBuf {
   |    ^^^^^^^^^^^

warning: function `build_image_path` is never used
  --> crates/parity-tests/src/tests/test_os058_gateway_unit.rs:43:4
   |
43 | fn build_image_path() -> PathBuf {
   |    ^^^^^^^^^^^^^^^^

warning: function `live_hook_path` is never used
  --> crates/parity-tests/src/tests/test_os058_gateway_unit.rs:46:4
   |
46 | fn live_hook_path() -> PathBuf {
   |    ^^^^^^^^^^^^^^

warning: function `readme_path` is never used
  --> crates/parity-tests/src/tests/test_os058_gateway_unit.rs:50:4
   |
50 | fn readme_path() -> PathBuf {
   |    ^^^^^^^^^^^

warning: function `spec_path` is never used
  --> crates/parity-tests/src/tests/test_os058_gateway_unit.rs:53:4
   |
53 | fn spec_path() -> PathBuf {
   |    ^^^^^^^^^

warning: constant `GATEWAY_UNIT` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:37:7
   |
37 | const GATEWAY_UNIT: &str = "relay-mcp-gateway.service";
   |       ^^^^^^^^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:39:4
   |
39 | fn root() -> PathBuf {
   |    ^^^^

warning: function `os_inner` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:42:4
   |
42 | fn os_inner() -> PathBuf {
   |    ^^^^^^^^

warning: function `read` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:45:4
   |
45 | fn read(p: &Path) -> String {
   |    ^^^^

warning: function `target` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:48:4
   |
48 | fn target() -> PathBuf {
   |    ^^^^^^

warning: function `unit` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:51:4
   |
51 | fn unit() -> PathBuf {
   |    ^^^^

warning: function `build_image` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:54:4
   |
54 | fn build_image() -> PathBuf {
   |    ^^^^^^^^^^^

warning: function `build_live` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:57:4
   |
57 | fn build_live() -> PathBuf {
   |    ^^^^^^^^^^

warning: function `hook` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:60:4
   |
60 | fn hook() -> PathBuf {
   |    ^^^^

warning: function `packer` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:63:4
   |
63 | fn packer() -> PathBuf {
   |    ^^^^^^

warning: function `sweep` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:66:4
   |
66 | fn sweep() -> PathBuf {
   |    ^^^^^

warning: function `readme` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:69:4
   |
69 | fn readme() -> PathBuf {
   |    ^^^^^^

warning: function `spec` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:72:4
   |
72 | fn spec() -> PathBuf {
   |    ^^^^

warning: function `enablement_loop` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:76:4
   |
76 | fn enablement_loop(text: &str) -> String {
   |    ^^^^^^^^^^^^^^^

warning: function `bake_section` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:80:4
   |
80 | fn bake_section(text: &str) -> String {
   |    ^^^^^^^^^^^^

warning: function `shell_check` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:92:4
   |
92 | fn shell_check(shell: &str, flag: &str, path: &Path) -> (i32, String) {
   |    ^^^^^^^^^^^

warning: function `gateway_rootfs` is never used
  --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:97:4
   |
97 | fn gateway_rootfs(extra: &[&str]) -> tempfile::TempDir {
   |    ^^^^^^^^^^^^^^

warning: function `run_sweep` is never used
   --> crates/parity-tests/src/tests/test_os059_gateway_bake.rs:112:4
    |
112 | fn run_sweep(rootfs: &Path) -> (i32, String) {
    |    ^^^^^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os065_skills_loader.rs:57:4
   |
57 | fn root() -> PathBuf {
   |    ^^^^

warning: function `os_inner` is never used
  --> crates/parity-tests/src/tests/test_os065_skills_loader.rs:60:4
   |
60 | fn os_inner() -> PathBuf {
   |    ^^^^^^^^

warning: function `read` is never used
  --> crates/parity-tests/src/tests/test_os065_skills_loader.rs:63:4
   |
63 | fn read(p: &Path) -> String {
   |    ^^^^

warning: function `fixtures` is never used
  --> crates/parity-tests/src/tests/test_os065_skills_loader.rs:66:4
   |
66 | fn fixtures() -> PathBuf {
   |    ^^^^^^^^

warning: function `skills_loader_py` is never used
  --> crates/parity-tests/src/tests/test_os065_skills_loader.rs:69:4
   |
69 | fn skills_loader_py() -> PathBuf {
   |    ^^^^^^^^^^^^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os083_artifact_store.rs:48:4
   |
48 | fn root() -> PathBuf {
   |    ^^^^

warning: function `os_inner` is never used
  --> crates/parity-tests/src/tests/test_os083_artifact_store.rs:51:4
   |
51 | fn os_inner() -> PathBuf {
   |    ^^^^^^^^

warning: function `read` is never used
  --> crates/parity-tests/src/tests/test_os083_artifact_store.rs:54:4
   |
54 | fn read(p: &Path) -> String {
   |    ^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os_boot_harness.rs:30:4
   |
30 | fn root() -> PathBuf {
   |    ^^^^

warning: function `script_path` is never used
  --> crates/parity-tests/src/tests/test_os_boot_harness.rs:33:4
   |
33 | fn script_path() -> PathBuf {
   |    ^^^^^^^^^^^

warning: function `readme_path` is never used
  --> crates/parity-tests/src/tests/test_os_boot_harness.rs:36:4
   |
36 | fn readme_path() -> PathBuf {
   |    ^^^^^^^^^^^

warning: function `read` is never used
  --> crates/parity-tests/src/tests/test_os_boot_harness.rs:39:4
   |
39 | fn read(p: &Path) -> String {
   |    ^^^^

warning: constant `QGA_DEVICE` is never used
  --> crates/parity-tests/src/tests/test_os_boot_harness.rs:43:7
   |
43 | const QGA_DEVICE: &str = "org.qemu.guest_agent.0";
   |       ^^^^^^^^^^

warning: constant `READY_MARKER` is never used
  --> crates/parity-tests/src/tests/test_os_boot_harness.rs:44:7
   |
44 | const READY_MARKER: &str = "/run/metaos/ready";
   |       ^^^^^^^^^^^^

warning: constant `VERSION_FILE` is never used
  --> crates/parity-tests/src/tests/test_os_boot_harness.rs:45:7
   |
45 | const VERSION_FILE: &str = "/etc/metaos-version";
   |       ^^^^^^^^^^^^

warning: function `heredoc_bodies` is never used
  --> crates/parity-tests/src/tests/test_os_boot_harness.rs:48:4
   |
48 | fn heredoc_bodies(text: &str) -> Vec<(String, String)> {
   |    ^^^^^^^^^^^^^^

warning: function `run_script` is never used
  --> crates/parity-tests/src/tests/test_os_boot_harness.rs:76:4
   |
76 | fn run_script(args: &[&str], path_override: Option<&std::ffi::OsStr>) -> (i32, String, String) {
   |    ^^^^^^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os_bus_unit.rs:26:4
   |
26 | fn root() -> PathBuf {
   |    ^^^^

warning: function `os_inner` is never used
  --> crates/parity-tests/src/tests/test_os_bus_unit.rs:29:4
   |
29 | fn os_inner() -> PathBuf {
   |    ^^^^^^^^

warning: function `read` is never used
  --> crates/parity-tests/src/tests/test_os_bus_unit.rs:32:4
   |
32 | fn read(p: &Path) -> String {
   |    ^^^^

warning: function `unit` is never used
  --> crates/parity-tests/src/tests/test_os_bus_unit.rs:35:4
   |
35 | fn unit() -> PathBuf {
   |    ^^^^

warning: function `target` is never used
  --> crates/parity-tests/src/tests/test_os_bus_unit.rs:38:4
   |
38 | fn target() -> PathBuf {
   |    ^^^^^^

warning: function `build_image` is never used
  --> crates/parity-tests/src/tests/test_os_bus_unit.rs:41:4
   |
41 | fn build_image() -> PathBuf {
   |    ^^^^^^^^^^^

warning: function `build_live` is never used
  --> crates/parity-tests/src/tests/test_os_bus_unit.rs:44:4
   |
44 | fn build_live() -> PathBuf {
   |    ^^^^^^^^^^

warning: function `watch_py` is never used
  --> crates/parity-tests/src/tests/test_os_bus_unit.rs:47:4
   |
47 | fn watch_py() -> PathBuf {
   |    ^^^^^^^^

warning: function `readme` is never used
  --> crates/parity-tests/src/tests/test_os_bus_unit.rs:50:4
   |
50 | fn readme() -> PathBuf {
   |    ^^^^^^

warning: function `spec` is never used
  --> crates/parity-tests/src/tests/test_os_bus_unit.rs:53:4
   |
53 | fn spec() -> PathBuf {
   |    ^^^^

warning: function `sections` is never used
  --> crates/parity-tests/src/tests/test_os_bus_unit.rs:57:4
   |
57 | fn sections(text: &str) -> HashMap<String, HashMap<String, Vec<String>>> {
   |    ^^^^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os_livebuild.rs:57:4
   |
57 | fn root() -> PathBuf {
   |    ^^^^

warning: function `os_inner` is never used
  --> crates/parity-tests/src/tests/test_os_livebuild.rs:60:4
   |
60 | fn os_inner() -> PathBuf {
   |    ^^^^^^^^

warning: function `live_dir` is never used
  --> crates/parity-tests/src/tests/test_os_livebuild.rs:63:4
   |
63 | fn live_dir() -> PathBuf {
   |    ^^^^^^^^

warning: function `config` is never used
  --> crates/parity-tests/src/tests/test_os_livebuild.rs:66:4
   |
66 | fn config() -> PathBuf {
   |    ^^^^^^

warning: function `package_list` is never used
  --> crates/parity-tests/src/tests/test_os_livebuild.rs:69:4
   |
69 | fn package_list() -> PathBuf {
   |    ^^^^^^^^^^^^

warning: function `hook` is never used
  --> crates/parity-tests/src/tests/test_os_livebuild.rs:72:4
   |
72 | fn hook() -> PathBuf {
   |    ^^^^

warning: function `wrapper` is never used
  --> crates/parity-tests/src/tests/test_os_livebuild.rs:75:4
   |
75 | fn wrapper() -> PathBuf {
   |    ^^^^^^^

warning: function `read` is never used
  --> crates/parity-tests/src/tests/test_os_livebuild.rs:78:4
   |
78 | fn read(p: &Path) -> String {
   |    ^^^^

warning: function `live_build_files` is never used
  --> crates/parity-tests/src/tests/test_os_livebuild.rs:82:4
   |
82 | fn live_build_files() -> Vec<PathBuf> {
   |    ^^^^^^^^^^^^^^^^

warning: function `name_list` is never used
   --> crates/parity-tests/src/tests/test_os_livebuild.rs:101:4
    |
101 | fn name_list(text: &str) -> Vec<String> {
    |    ^^^^^^^^^

warning: function `second_base_in` is never used
   --> crates/parity-tests/src/tests/test_os_livebuild.rs:105:4
    |
105 | fn second_base_in(text: &str) -> Option<String> {
    |    ^^^^^^^^^^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os_manifest.rs:36:4
   |
36 | fn root() -> PathBuf {
   |    ^^^^

warning: function `os_inner` is never used
  --> crates/parity-tests/src/tests/test_os_manifest.rs:39:4
   |
39 | fn os_inner() -> PathBuf {
   |    ^^^^^^^^

warning: function `manifest` is never used
  --> crates/parity-tests/src/tests/test_os_manifest.rs:42:4
   |
42 | fn manifest() -> PathBuf {
   |    ^^^^^^^^

warning: function `package_list` is never used
  --> crates/parity-tests/src/tests/test_os_manifest.rs:45:4
   |
45 | fn package_list() -> PathBuf {
   |    ^^^^^^^^^^^^

warning: function `readme` is never used
  --> crates/parity-tests/src/tests/test_os_manifest.rs:48:4
   |
48 | fn readme() -> PathBuf {
   |    ^^^^^^

warning: function `read` is never used
  --> crates/parity-tests/src/tests/test_os_manifest.rs:51:4
   |
51 | fn read(p: &Path) -> String {
   |    ^^^^

warning: function `names` is never used
  --> crates/parity-tests/src/tests/test_os_manifest.rs:54:4
   |
54 | fn names(p: &Path) -> Vec<String> {
   |    ^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:27:4
   |
27 | fn root() -> PathBuf {
   |    ^^^^

warning: function `os_inner` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:30:4
   |
30 | fn os_inner() -> PathBuf {
   |    ^^^^^^^^

warning: function `os_top` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:33:4
   |
33 | fn os_top() -> PathBuf {
   |    ^^^^^^

warning: function `read` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:36:4
   |
36 | fn read(p: &Path) -> String {
   |    ^^^^

warning: function `unit` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:39:4
   |
39 | fn unit() -> PathBuf {
   |    ^^^^

warning: function `timer` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:42:4
   |
42 | fn timer() -> PathBuf {
   |    ^^^^^

warning: function `target` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:45:4
   |
45 | fn target() -> PathBuf {
   |    ^^^^^^

warning: function `mos_shim` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:48:4
   |
48 | fn mos_shim() -> PathBuf {
   |    ^^^^^^^^

warning: function `mos_cli` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:51:4
   |
51 | fn mos_cli() -> PathBuf {
   |    ^^^^^^^

warning: function `overseer` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:54:4
   |
54 | fn overseer() -> PathBuf {
   |    ^^^^^^^^

warning: function `readme` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:57:4
   |
57 | fn readme() -> PathBuf {
   |    ^^^^^^

warning: function `spec` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:60:4
   |
60 | fn spec() -> PathBuf {
   |    ^^^^

warning: function `build_image` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:63:4
   |
63 | fn build_image() -> PathBuf {
   |    ^^^^^^^^^^^

warning: function `build_live` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:66:4
   |
66 | fn build_live() -> PathBuf {
   |    ^^^^^^^^^^

warning: function `sections` is never used
  --> crates/parity-tests/src/tests/test_os_overseer_unit.rs:70:4
   |
70 | fn sections(text: &str) -> HashMap<String, HashMap<String, Vec<String>>> {
   |    ^^^^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os_packer.rs:46:4
   |
46 | fn root() -> PathBuf {
   |    ^^^^

warning: function `os_inner` is never used
  --> crates/parity-tests/src/tests/test_os_packer.rs:49:4
   |
49 | fn os_inner() -> PathBuf {
   |    ^^^^^^^^

warning: function `read` is never used
  --> crates/parity-tests/src/tests/test_os_packer.rs:52:4
   |
52 | fn read(p: &Path) -> String {
   |    ^^^^

warning: function `template` is never used
  --> crates/parity-tests/src/tests/test_os_packer.rs:55:4
   |
55 | fn template() -> PathBuf {
   |    ^^^^^^^^

warning: function `wrapper` is never used
  --> crates/parity-tests/src/tests/test_os_packer.rs:58:4
   |
58 | fn wrapper() -> PathBuf {
   |    ^^^^^^^

warning: function `preseed` is never used
  --> crates/parity-tests/src/tests/test_os_packer.rs:61:4
   |
61 | fn preseed() -> PathBuf {
   |    ^^^^^^^

warning: function `readme` is never used
  --> crates/parity-tests/src/tests/test_os_packer.rs:64:4
   |
64 | fn readme() -> PathBuf {
   |    ^^^^^^

warning: function `second_base_in` is never used
  --> crates/parity-tests/src/tests/test_os_packer.rs:68:4
   |
68 | fn second_base_in(text: &str) -> Option<String> {
   |    ^^^^^^^^^^^^^^

warning: function `var_block` is never used
  --> crates/parity-tests/src/tests/test_os_packer.rs:85:4
   |
85 | fn var_block(text: &str, name: &str) -> Option<String> {
   |    ^^^^^^^^^

warning: function `literal_password_at` is never used
  --> crates/parity-tests/src/tests/test_os_packer.rs:93:4
   |
93 | fn literal_password_at(text: &str) -> Option<String> {
   |    ^^^^^^^^^^^^^^^^^^^

warning: function `sha40_in` is never used
  --> crates/parity-tests/src/tests/test_os_stackbake.rs:30:4
   |
30 | fn sha40_in(text: &str) -> Vec<String> {
   |    ^^^^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os_stackbake.rs:52:4
   |
52 | fn root() -> PathBuf {
   |    ^^^^

warning: function `os_inner` is never used
  --> crates/parity-tests/src/tests/test_os_stackbake.rs:55:4
   |
55 | fn os_inner() -> PathBuf {
   |    ^^^^^^^^

warning: function `read` is never used
  --> crates/parity-tests/src/tests/test_os_stackbake.rs:58:4
   |
58 | fn read(p: &Path) -> String {
   |    ^^^^

warning: function `script` is never used
  --> crates/parity-tests/src/tests/test_os_stackbake.rs:61:4
   |
61 | fn script() -> PathBuf {
   |    ^^^^^^

warning: function `readme` is never used
  --> crates/parity-tests/src/tests/test_os_stackbake.rs:64:4
   |
64 | fn readme() -> PathBuf {
   |    ^^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os_target_unit.rs:42:4
   |
42 | fn root() -> PathBuf {
   |    ^^^^

warning: function `os_inner` is never used
  --> crates/parity-tests/src/tests/test_os_target_unit.rs:45:4
   |
45 | fn os_inner() -> PathBuf {
   |    ^^^^^^^^

warning: function `read` is never used
  --> crates/parity-tests/src/tests/test_os_target_unit.rs:48:4
   |
48 | fn read(p: &Path) -> String {
   |    ^^^^

warning: function `target` is never used
  --> crates/parity-tests/src/tests/test_os_target_unit.rs:51:4
   |
51 | fn target() -> PathBuf {
   |    ^^^^^^

warning: function `ready` is never used
  --> crates/parity-tests/src/tests/test_os_target_unit.rs:54:4
   |
54 | fn ready() -> PathBuf {
   |    ^^^^^

warning: function `checklist` is never used
  --> crates/parity-tests/src/tests/test_os_target_unit.rs:57:4
   |
57 | fn checklist() -> PathBuf {
   |    ^^^^^^^^^

warning: function `build_image` is never used
  --> crates/parity-tests/src/tests/test_os_target_unit.rs:60:4
   |
60 | fn build_image() -> PathBuf {
   |    ^^^^^^^^^^^

warning: function `packer` is never used
  --> crates/parity-tests/src/tests/test_os_target_unit.rs:63:4
   |
63 | fn packer() -> PathBuf {
   |    ^^^^^^

warning: function `hook` is never used
  --> crates/parity-tests/src/tests/test_os_target_unit.rs:66:4
   |
66 | fn hook() -> PathBuf {
   |    ^^^^

warning: function `readme` is never used
  --> crates/parity-tests/src/tests/test_os_target_unit.rs:69:4
   |
69 | fn readme() -> PathBuf {
   |    ^^^^^^

warning: function `spec` is never used
  --> crates/parity-tests/src/tests/test_os_target_unit.rs:72:4
   |
72 | fn spec() -> PathBuf {
   |    ^^^^

warning: function `sections` is never used
  --> crates/parity-tests/src/tests/test_os_target_unit.rs:76:4
   |
76 | fn sections(text: &str) -> HashMap<String, HashMap<String, Vec<String>>> {
   |    ^^^^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os_tree.rs:73:4
   |
73 | fn root() -> PathBuf {
   |    ^^^^

warning: function `os_dir` is never used
  --> crates/parity-tests/src/tests/test_os_tree.rs:76:4
   |
76 | fn os_dir() -> PathBuf {
   |    ^^^^^^

warning: function `read_rel` is never used
  --> crates/parity-tests/src/tests/test_os_tree.rs:79:4
   |
79 | fn read_rel(rel: &str) -> String {
   |    ^^^^^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_os_uplink.rs:41:4
   |
41 | fn root() -> PathBuf {
   |    ^^^^

warning: function `os_inner` is never used
  --> crates/parity-tests/src/tests/test_os_uplink.rs:44:4
   |
44 | fn os_inner() -> PathBuf {
   |    ^^^^^^^^

warning: function `read` is never used
  --> crates/parity-tests/src/tests/test_os_uplink.rs:47:4
   |
47 | fn read(p: &Path) -> String {
   |    ^^^^

warning: function `root` is never used
  --> crates/parity-tests/src/tests/test_worlds_pack.rs:33:4
   |
33 | fn root() -> PathBuf {
   |    ^^^^

warning: function `pack_path` is never used
  --> crates/parity-tests/src/tests/test_worlds_pack.rs:36:4
   |
36 | fn pack_path(name: &str) -> PathBuf {
   |    ^^^^^^^^^

warning: function `read_manifest` is never used
  --> crates/parity-tests/src/tests/test_worlds_pack.rs:39:4
   |
39 | fn read_manifest(name: &str) -> Value {
   |    ^^^^^^^^^^^^^

warning: function `valid_manifest` is never used
  --> crates/parity-tests/src/tests/test_worlds_pack.rs:43:4
   |
43 | fn valid_manifest() -> Value {
   |    ^^^^^^^^^^^^^^

warning: type `StrVal` is more private than the item `fake_redis::FakeUpstash::strings`
  --> crates/parity-tests/src/support/fake_redis.rs:17:5
   |
17 |     pub strings: HashMap<String, StrVal>,
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ field `fake_redis::FakeUpstash::strings` is reachable at visibility `pub`
   |
note: but type `StrVal` is only usable at visibility `pub(self)`
  --> crates/parity-tests/src/support/fake_redis.rs:10:1
   |
10 | struct StrVal {
   | ^^^^^^^^^^^^^
   = note: `#[warn(private_interfaces)]` on by default

warning: field `src` is never read
  --> crates/parity-tests/src/tests/test_os021_update.rs:57:5
   |
54 | struct Fixture {
   |        ------- field in this struct
...
57 |     src: PathBuf,
   |     ^^^
   |
   = note: `#[warn(dead_code)]` (part of `#[warn(unused)]`) on by default

warning: `parity-tests` (lib) generated 140 warnings (run `cargo fix --lib -p parity-tests` to apply 4 suggestions)
warning: `parity-tests` (lib test) generated 5 warnings (3 duplicates)
   Compiling os-budget v0.1.0 (/private/tmp/oc500-baseline/crates/os-budget)
   Compiling ureq v2.12.1
   Compiling stack v0.1.0 (/private/tmp/oc500-baseline/crates/stack)
   Compiling os-jobs v0.1.0 (/private/tmp/oc500-baseline/crates/os-jobs)
   Compiling queue-core v0.1.0 (/private/tmp/oc500-baseline/crates/queue-core)
   Compiling relay v0.1.0 (/private/tmp/oc500-baseline/crates/relay)
   Compiling agent-runtime v0.1.0 (/private/tmp/oc500-baseline/crates/agent-runtime)
   Compiling queue-store v0.1.0 (/private/tmp/oc500-baseline/crates/queue-store)
   Compiling dashboard v0.1.0 (/private/tmp/oc500-baseline/crates/dashboard)
   Compiling assess-server v0.1.0 (/private/tmp/oc500-baseline/crates/assess-server)
   Compiling intel v0.1.0 (/private/tmp/oc500-baseline/crates/intel)
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
error[E0063]: missing field `spec` in initializer of `PlanJob`
  --> crates/intel/tests/error_paths.rs:31:5
   |
31 |     PlanJob {
   |     ^^^^^^^ missing `spec`

error: could not compile `intel` (test "error_paths") due to 1 previous error
exit: 101
