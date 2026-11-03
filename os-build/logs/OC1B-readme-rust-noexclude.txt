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
   Compiling os-workspace v0.1.0 (/private/tmp/oc500-baseline/crates/os-workspace)
   Compiling os-supervisor v0.1.0 (/private/tmp/oc500-baseline/crates/os-supervisor)
   Compiling os-memory v0.1.0 (/private/tmp/oc500-baseline/crates/os-memory)
   Compiling os-identity v0.1.0 (/private/tmp/oc500-baseline/crates/os-identity)
   Compiling os-boot v0.1.0 (/private/tmp/oc500-baseline/crates/os-boot)
   Compiling dashboard v0.1.0 (/private/tmp/oc500-baseline/crates/dashboard)
   Compiling os-worker v0.1.0 (/private/tmp/oc500-baseline/crates/os-worker)
   Compiling queue-core v0.1.0 (/private/tmp/oc500-baseline/crates/queue-core)
   Compiling os-jobs v0.1.0 (/private/tmp/oc500-baseline/crates/os-jobs)
   Compiling os-budget v0.1.0 (/private/tmp/oc500-baseline/crates/os-budget)
   Compiling stack v0.1.0 (/private/tmp/oc500-baseline/crates/stack)
   Compiling relay v0.1.0 (/private/tmp/oc500-baseline/crates/relay)
    Finished `test` profile [unoptimized + debuginfo] target(s) in 5.11s
     Running unittests src/lib.rs (target/debug/deps/agent_runtime-322cd80992ec482a)

running 3 tests
test tests::invalid_then_valid_retries_once ... ok
test tests::full_contract_vectors ... ok
test tests::valid_first_output_is_exactly_one_call ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-3b67a3d89873d6be)

running 11 tests
test empty_observations_array_is_valid ... ok
test empty_image_bytes_reach_the_generator_as_empty ... ok
test long_ascii_error_is_capped_at_200_in_the_finish_note ... ok
test duplicate_submit_keeps_the_first_envelope ... ok
test empty_job_id_is_served_and_echoed ... ok
test confidence_boundaries_are_inclusive ... ok
test out_of_order_serve_loses_the_claim_then_wins_after_release ... ok
test duplicate_serve_skips_before_generating ... ok
test long_ascii_error_is_capped_at_500_in_the_result ... ok
test utf8_error_is_capped_without_panicking ... ok
test five_hundred_observations_are_accepted ... ok

test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/error_paths.rs (target/debug/deps/error_paths-a679197256012c4d)

running 12 tests
test relay_ok_payload_does_not_panic_and_is_capped ... ok
test claim_race_lost_writes_nothing ... ok
test non_jpeg_data_url_refuses ... ok
test relay_failed_payload_is_a_warning_and_names_the_error ... ok
test validator_refuses_a_non_object ... ok
test validator_names_an_empty_expected_product ... ok
test retry_generation_error_refuses_with_first_model_and_latency ... ok
test invalid_after_exactly_one_retry_refuses ... ok
test first_generation_error_refuses ... ok
test bad_base64_refuses ... ok
test sha256_mismatch_refuses ... ok
test missing_envelope_refuses ... ok

test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/gap_close.rs (target/debug/deps/gap_close-e5d50c103bc6c7e9)

running 17 tests
test extra_fields_are_tolerated_and_do_not_change_the_result ... ok
test an_empty_evidence_string_is_accepted ... ok
test confidence_key_must_be_present_even_when_null ... ok
test now_iso_is_epoch_millis_not_iso8601 ... ok
test observation_category_cannot_be_whitespace_only ... ok
test iso8601_accepts_zulu_seconds_fractions_and_numeric_offsets ... ok
test observation_item_must_be_an_object ... ok
test iso8601_rejects_impossible_dates_times_and_offsets ... ok
test observations_must_be_an_array_not_null ... ok
test observation_evidence_must_be_present_and_a_string ... ok
test summary_must_be_a_string ... ok
test outcome_values_are_distinct ... ok
test processing_block_is_required_with_model_and_latency ... ok
test requires_human_review_must_be_boolean ... ok
test relay_payload_needs_a_job_id ... ok
test product_must_match_exactly_including_case_and_spacing ... ok
test uncertainty_must_be_an_array_of_strings ... ok

test result: ok. 17 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running unittests src/main.rs (target/debug/deps/assess_server-84d67a329414f118)

running 40 tests
test tests::fetch_refuses_disabled_and_unconfigured_before_transport ... ok
test tests::edge_poll_out_of_order_returns_done_after_two_pending ... ok
test tests::edge_duplicate_json_keys_keep_the_last_value ... ok
test tests::direct_model_held_returns_503 ... ok
test tests::build_job_refuses_bad_product_timestamp_and_empty_frame ... ok
test tests::fetch_refuses_an_empty_job_id_before_transport ... ok
test tests::guardrail_stop_refuses_before_send ... ok
test tests::edge_poll_with_zero_bound_still_fetches_once ... ok
test tests::bad_request_is_400 ... ok
test tests::direct_model_ok_returns_200 ... ok
test tests::http_content_types_are_the_documented_five ... ok
test tests::http_caps_are_the_documented_values ... ok
test tests::image_refuses_a_non_string_and_bad_base64 ... ok
test tests::image_rejects_a_non_data_url_and_zero_bytes ... ok
test tests::image_requires_the_jpeg_magic_bytes ... ok
test tests::model_held_and_not_configured_are_distinct_refusals ... ok
test tests::parse_refuses_malformed_envelopes ... ok
test tests::invalid_model_answer_is_502_never_silent_fallback ... ok
test tests::poll_propagates_a_transport_error_without_retrying ... ok
test tests::poll_timeout_is_typed_queue_error ... ok
test tests::prompt_refuses_an_unknown_product ... ok
test tests::http_refuses_oversize_body_with_413_before_reading ... ok
test tests::proposed_shape_refuses_a_mismatched_job_and_non_string_error ... ok
test tests::queue_disabled_never_touched ... ok
test tests::queue_done_answer_is_returned_without_calling_the_model ... ok
test tests::http_invalid_json_is_a_400 ... ok
test tests::queue_done_off_contract_is_502 ... ok
test tests::queue_failure_and_submit_failure_fall_back_to_the_direct_path ... ok
test tests::queue_first_invalid_answer_is_502 ... ok
test tests::queue_job_id_deterministic ... ok
test tests::result_shapes_normalize ... ok
test tests::http_static_refuses_traversal_and_missing_files ... ok
test tests::submit_refuses_layers_before_any_transport ... ok
test tests::timestamp_strict ... ok
test tests::validate_collects_every_missing_field ... ok
test tests::validate_rejects_non_object_bodies ... ok
test tests::http_routes_refuse_unknown_routes_and_wrong_methods ... ok
test tests::http_answers_options_with_204_and_wrong_methods_with_405 ... ok
test tests::image_refuses_one_byte_over_the_cap ... ok
test tests::image_accepts_exactly_the_cap ... ok

test result: ok. 40 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.13s

     Running unittests src/lib.rs (target/debug/deps/dashboard-9d40519f2ac5c4b1)

running 7 tests
test contract::tests::brief_contract_validates ... ok
test contract::tests::deep_links_parse ... ok
test contract::tests::demo_prefix_trap ... ok
test contract::tests::staleness_threshold ... ok
test contract::tests::today_briefs_dedupe ... ok
test contract::tests::today_records_match_fixture ... ok
test contract::tests::verdicts_never_remapped ... ok

test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/b15_crewboard.rs (target/debug/deps/b15_crewboard-0589bafb82c38632)

running 23 tests
test test_crewboard_artifact_old_job_has_no_links ... ok
test test_crewboard_artifact_links_store_paths ... ok
test test_crewboard_artifact_bad_paths_dropped ... ok
test test_crewboard_attempts_thresholds ... ok
test test_crewboard_files_deps_old_and_blank_render_nothing ... ok
test test_crewboard_files_names_escaped ... ok
test test_crewboard_ribbon_acknowledged_keeps_ribbon ... ok
test test_crewboard_files_and_deps_lines ... ok
test test_crewboard_attempts_absent_blank_junk_no_badge ... ok
test test_crewboard_artifact_paths_escaped ... ok
test test_crewboard_ribbon_bare_subject_links_to_alert ... ok
test test_crewboard_ribbon_first_matching_critical_wins ... ok
test test_crewboard_ribbon_kind_and_id_are_escaped ... ok
test test_crewboard_ribbon_job_form_matches_case_insensitively ... ok
test test_crewboard_ribbon_other_job_and_no_alerts_get_none ... ok
test test_crewboard_ribbon_resolved_gets_none ... ok
test test_crewboard_ribbon_uppercase_severity_matches ... ok
test test_crewboard_ribbon_warning_and_info_get_none ... ok
test test_crewboard_ribbon_without_id_has_no_link ... ok
test test_crewboard_signing_hash_and_history_entry_shapes ... ok
test test_crewboard_signing_log_entry_is_keyless_json ... ok
test test_crewboard_signing_nonce_shape ... ok
test test_crewboard_signing_pystr_matches_json_dumps ... ok

test result: ok. 23 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/b15_parity.rs (target/debug/deps/b15_parity-55675d219c26d949)

running 26 tests
test test_dashboard_accessibility_palette_contrast_meets_aa ... ok
test test_dashboard_accessibility_spec_carries_contrast_notes ... ok
test test_dashboard_alert_feed_dsh013 ... ok
test test_dashboard_alert_lifecycle_ack_persists_and_idempotent ... ok
test test_dashboard_alert_lifecycle_feed_rows_carry_wdg014_status ... ok
test test_dashboard_alert_lifecycle_legacy_record_derives_status ... ok
test test_dashboard_alert_lifecycle_live_write_gate_off ... ok
test test_dashboard_alert_lifecycle_resolve_unblocks_header ... ok
test test_dashboard_alert_lifecycle_resolved_collapse_count ... ok
test test_dashboard_alert_lifecycle_resolved_refuses_ack ... ok
test test_dashboard_brief_payload_contract_brf042 ... ok
test test_dashboard_brief_sections_default_open_map ... ok
test test_dashboard_brief_sections_titles_and_order ... ok
test test_dashboard_deploy_runbook_honest_limits ... ok
test test_dashboard_dsh038_request_only ... ok
test test_dashboard_rollback_int031_exact_steps ... ok
test test_dashboard_rollback_int031_rejects_invented_id ... ok
test test_dashboard_deploy_runbook_sections_and_gates ... ok
test test_dashboard_smoke_checklist_covers_deploy_gates ... ok
test test_dashboard_smoke_checklist_every_check_names_pass_criteria ... ok
test test_dashboard_smoke_checklist_exactly_ten_checks ... ok
test test_dashboard_smoke_checklist_spec_documents_it ... ok
test test_dashboard_smoke_checklist_run_procedure_and_log ... ok
test test_dashboard_spec_docs_carried ... ok
test test_dashboard_stale_labels_brf043 ... ok
test test_dashboard_today_counters_record_rules ... ok

test result: ok. 26 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s

     Running tests/b15_rollback_parity.rs (target/debug/deps/b15_rollback_parity-a2773a4747e17c85)

running 5 tests
test test_rollback_previous_id_no_invented_id ... ok
test test_rollback_failover_card_copy_present ... ok
test test_rollback_project_restore_still_marked_unconfirmed ... ok
test test_rollback_verified_by_previous_marker ... ok
test test_rollback_no_credential_recorded ... ok

test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/b15_spec_notes.rs (target/debug/deps/b15_spec_notes-0bbd16e0f4b7ef4b)

running 21 tests
test test_dashboard_cross_browser_log_records_no_safari_only_bug_verdict ... ok
test test_dashboard_cross_browser_log_states_ios_device_caveat_plainly ... ok
test test_dashboard_cross_browser_log_records_all_four_runs_pass ... ok
test test_dashboard_brief_sections_spec_notes_dsh031 ... ok
test test_dashboard_dsh038_spec_decision_gives_real_cli_flow ... ok
test test_dashboard_demo_mode_spec_documents_demo_mode ... ok
test test_dashboard_deep_links_spec_documents_deep_links ... ok
test test_dashboard_dsh038_spec_has_request_only_decision_section ... ok
test test_dashboard_dsh038_spec_decision_reopens_only_on_dale_plus_server ... ok
test test_dashboard_dsh038_spec_decision_names_why_not_deferred ... ok
test test_dashboard_dsp039_spec_lists_all_six_states_with_exact_labels ... ok
test test_dashboard_error_states_spec_documents_error_states ... ok
test test_dashboard_dsh038_spec_no_longer_waits_on_viewer_posting_rule ... ok
test test_dashboard_os043_spec_documents_boot_checklist_contract ... ok
test test_dashboard_intel_focus_spec_and_demo_notes_document_shortcut ... ok
test test_dashboard_performance_spec_documents_the_cap ... ok
test test_dashboard_os084_spec_documents_refusal_banner_contract ... ok
test test_dashboard_readonly_token_spec_notes_dsh033 ... ok
test test_dashboard_str005_spec_notes_str005 ... ok
test test_dashboard_help_spec_documents_help_panel ... ok
test test_dashboard_today_counters_spec_notes_dsh032 ... ok

test result: ok. 21 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-161bf64cd744cd99)

running 16 tests
test duplicate_alert_ids_keep_input_order_on_a_tie ... ok
test duplicate_deps_tokens_are_rendered_as_given ... ok
test duplicate_lifecycle_id_acks_only_the_first_record ... ok
test empty_inputs_return_empty_results_not_errors ... ok
test escape_is_applied_in_the_documented_order ... ok
test maximum_brief_history_dedupes_to_distinct_timestamps ... ok
test maximum_feed_sorts_ten_thousand_cards_newest_first ... ok
test maximum_length_room_still_validates_against_its_own_id ... ok
test out_of_order_feed_is_sorted_by_time_then_id_descending ... ok
test out_of_order_history_counts_the_same_day_once ... ok
test route_encoding_covers_every_non_unreserved_byte ... ok
test out_of_order_jobs_and_alerts_are_counted_independently ... ok
test same_day_boundary_is_utc_midnight ... ok
test stale_boundary_is_exactly_two_hours ... ok
test zero_max_attempts_is_already_danger ... ok
test maximum_files_line_keeps_every_name ... ok

test result: ok. 16 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s

     Running tests/error_paths.rs (target/debug/deps/error_paths-c2c3b10be76a605c)

running 19 tests
test bad_brief_kind_is_refused_with_the_kind_named ... ok
test a_complete_runbook_is_accepted ... ok
test an_empty_runbook_fails_on_the_first_step ... ok
test bad_brief_id_is_refused_with_the_id_named ... ok
test empty_room_is_refused ... ok
test every_missing_step_names_itself ... ok
test missing_docs_citation_is_refused ... ok
test missing_id_field_is_refused ... ok
test a_short_colour_panics_in_the_wcag_helper - should panic ... ok
test missing_preview_rule_is_refused ... ok
test missing_valid_target_rule_is_refused ... ok
test negative_age_is_refused ... ok
test negative_generated_at_is_refused ... ok
test non_hex_digits_read_as_zero_channels ... ok
test non_intel_and_id_less_deep_links_are_none ... ok
test token_rejection_names_the_panel_and_the_fix ... ok
test unsafe_or_missing_artifact_paths_are_dropped ... ok
test unreachable_names_the_panel_and_spares_the_log ... ok
test unparseable_attempts_have_no_badge ... ok

test result: ok. 19 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/gap_close.rs (target/debug/deps/gap_close-1b00f7074a5f9b0a)

running 13 tests
test addressable_cards_preserve_order_and_drop_resolved ... ok
test an_unrecognised_status_falls_back_to_the_timestamps ... ok
test default_open_is_closed_for_every_known_section_but_blocked ... ok
test nonce_shape_is_lowercase_hex_and_exactly_sixteen ... ok
test brief_kinds_are_exactly_the_three_spec_kinds ... ok
test py_str_json_handles_control_bytes_and_del ... ok
test resolve_brief_link_only_accepts_a_timestamp_in_the_window ... ok
test resolving_an_acknowledged_record_keeps_the_ack_stamp ... ok
test rollback_steps_are_the_four_int031_names_in_order ... ok
test route_encode_id_passes_unreserved_bytes_through ... ok
test stale_label_humanises_hours_and_minutes ... ok
test verdicts_are_the_three_str004_ground_truth_words ... ok
test unresolved_critical_count_is_case_insensitive_and_skips_resolved ... ok

test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running unittests src/lib.rs (target/debug/deps/guardrail-6afd912e1f709648)

running 5 tests
test tests::test_estimate_math ... ok
test tests::test_check_passes_under_budget ... ok
test tests::test_unwrap_fence ... ok
test tests::test_stop_at_budget ... ok
test tests::test_record_counts_and_cumulates ... ok

test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-c5eb19e0b3fa0b52)

running 10 tests
test one_input_token_costs_the_published_rate ... ok
test status_goes_negative_once_the_budget_is_passed ... ok
test product_and_profile_fields_appear_verbatim_in_the_prompt ... ok
test a_fence_after_prose_still_yields_the_object ... ok
test zero_tokens_cost_nothing_but_still_count_the_call ... ok
test cumulative_cost_is_rounded_to_six_decimals ... ok
test empty_input_builds_a_prompt_without_panicking ... ok
test out_of_order_latency_is_kept_in_call_order ... ok
test duplicate_input_is_counted_each_time_not_deduplicated ... ok
test maximum_input_builds_a_prompt_and_a_finite_estimate ... ok

test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/error_paths.rs (target/debug/deps/error_paths-5a83234f3eb19e49)

running 19 tests
test check_just_under_budget_passes ... ok
test check_over_budget_refuses ... ok
test check_at_budget_refuses_with_the_python_message ... ok
test an_unclosed_fence_keeps_its_body ... ok
test build_prompt_appends_the_correction_block_when_given ... ok
test build_prompt_omits_the_correction_block_without_one ... ok
test a_non_object_with_braces_is_returned_as_the_slice ... ok
test empty_model_text_unwraps_to_an_empty_string ... ok
test estimate_never_mixes_the_two_rates ... ok
test a_logged_record_carries_the_fixed_timestamp ... ok
test prose_around_the_object_is_dropped ... ok
test missing_ledger_reads_as_zero ... ok
test a_hand_written_state_with_a_log_round_trips ... ok
test record_into_an_unwritable_path_still_returns_the_estimate ... ok
test save_to_an_unwritable_path_is_silent ... ok
test corrupt_ledger_reads_as_zero_instead_of_refusing ... ok
test text_without_an_object_is_returned_trimmed ... ok
test empty_object_uses_serde_defaults ... ok
test wrong_shape_ledger_reads_as_zero ... ok

test result: ok. 19 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/gap_close.rs (target/debug/deps/gap_close-326722706e64c34f)

running 9 tests
test the_rate_card_and_public_endpoints_are_the_documented_values ... ok
test a_negative_budget_state_still_passes_check ... ok
test an_empty_object_model_text_is_its_own_object ... ok
test status_of_reports_the_four_contract_fields ... ok
test status_remaining_is_exactly_zero_at_the_budget ... ok
test saved_state_survives_the_pretty_json_writer ... ok
test one_record_leaves_the_log_and_the_state_agreeing ... ok
test a_partial_state_object_loads_with_defaults ... ok
test via_helper_is_true_only_for_the_literal_one ... ok

test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running unittests src/lib.rs (target/debug/deps/os_boot-79100c735c5ada3c)

running 23 tests
test carried::tests::test_carried_manifest_count ... ok
test cli::tests::test_caps_empty_and_listed ... ok
test cli::tests::test_dispatch_at_file_error ... ok
test cli::tests::test_reconcile_passthrough ... ok
test cli::tests::test_expand_text_plain_and_empty ... ok
test cli::tests::test_register_backend_error ... ok
test cli::tests::test_dispatch_with_and_without_workers ... ok
test cli::tests::test_register_output_sorted_raw_caps ... ok
test cli::tests::test_run_cli_arg_errors ... ok
test cli::tests::test_review_and_merge_fake_backend ... ok
test cli::tests::test_run_cli_dispatch_defaults ... ok
test cli::tests::test_tick_clean_and_errors ... ok
test cli::tests::test_verify_ok_and_fail ... ok
test cli::tests::test_split_caps_filters_and_keeps_raw ... ok
test cli::tests::test_worker_once_claim_skip_and_empty ... ok
test cli::tests::test_worker_once_claim_failed_no_no_dispatches_line ... ok
test cli::tests::test_expand_text_at_file ... ok
test carried::tests::test_carried_units_look_like_units ... ok
test carried::tests::test_carried_files_byte_identical ... ok
test git::tests::test_gitops_merge_refuses_dirty_and_self ... ok
test git::tests::test_gitops_review_rejects_self_unknown_and_non_repo ... ok
test git::tests::test_gitops_review_branch_via_cli ... ok
test git::tests::test_gitops_approve_merge_via_cli ... ok

test result: ok. 23 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.42s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-4199c647dcf159f1)

running 10 tests
test an_at_sign_alone_is_an_empty_path_and_refuses ... ok
test duplicate_caps_are_kept_in_order ... ok
test duplicate_flags_take_the_first_value ... ok
test empty_argv_is_the_empty_case ... ok
test empty_caps_string_registers_with_no_capabilities ... ok
test equals_form_and_space_form_agree ... ok
test flags_in_reverse_order_parse_the_same ... ok
test whitespace_only_caps_is_empty ... ok
test maximum_caps_string_keeps_every_entry ... ok
test maximum_input_passes_through_untouched ... ok

test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/error_paths.rs (target/debug/deps/error_paths-2204b3a60cd40b45)

running 13 tests
test dispatch_refuses_an_unreadable_spec_file_as_exit_one ... ok
test register_reports_a_backend_failure_as_exit_one ... ok
test expand_text_refuses_a_missing_at_file ... ok
test tick_prints_errors_on_stderr_and_exits_two ... ok
test usage_refusals_are_exit_two ... ok
test verify_failure_exits_one_and_says_not_verified ... ok
test worker_loop_mode_is_refused_with_the_agent_driven_line ... ok
test review_refuses_a_plain_directory ... ok
test merge_refuses_base_into_itself ... ok
test review_refuses_base_against_itself_before_touching_git_refs ... ok
test merge_refuses_a_dirty_working_tree ... ok
test review_refuses_an_unknown_branch ... ok
test merge_refuses_an_unknown_branch_on_a_clean_tree ... ok

test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.32s

     Running tests/gap_close.rs (target/debug/deps/gap_close-73204d2bdcdb2191)

running 13 tests
test custos_group_has_four_entries ... ok
test loop_group_has_four_entries ... ok
test every_entry_is_a_relative_path_without_traversal ... ok
test manifest_has_no_duplicate_entries ... ok
test manifest_has_no_empty_entries ... ok
test t153_group_has_ten_systemd_entries ... ok
test asset_path_mirrors_the_entry_under_assets ... ok
test every_asset_is_non_empty ... ok
test every_asset_is_a_regular_file ... ok
test source_path_resolves_under_the_repo_os_tree ... ok
test t154_group_has_ten_systemd_entries ... ok
test t155_group_has_ten_docs_and_build_entries ... ok
test t156_group_has_nine_image_entries ... ok

test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running unittests src/lib.rs (target/debug/deps/os_budget-6a1323d4f85bd1c3)

running 61 tests
test tests::budgets_spend_ratio_edges ... ok
test tests::cgroup_slice_parses_expected_values ... ok
test tests::budgets_env_int_falls_back_on_bad_input ... ok
test tests::cgroup_slice_mismatch_fails_file_phase ... ok
test tests::cgroup_real_slice_file_carries_expected_values ... ok
test tests::budgets_from_snapshot_skips_malformed ... ok
test tests::cgroup_gate_needs_cpu_and_memory ... ok
test tests::disk_audit_artifact_verification_layers ... ok
test tests::disk_audit_artifact_bytes_unreadable_is_a_leak ... ok
test tests::disk_audit_clean_job_passes_and_reconstructs ... ok
test tests::disk_audit_decisions_shared_agent_and_missing ... ok
test tests::disk_audit_goal_from_spec_line ... ok
test tests::disk_audit_progress_falls_back_to_latest_note ... ok
test tests::disk_audit_record_shape_errors ... ok
test tests::disk_audit_shared_journal_error_is_a_leak ... ok
test tests::disk_audit_journal_leaks_filed_once_per_agent ... ok
test tests::disk_audit_spec_baton_and_claim_leaks ... ok
test tests::forecast_already_paused_never_paused_twice ... ok
test tests::forecast_confidence_comes_from_elapsed_hours_alone ... ok
test tests::forecast_drill_phases ... ok
test tests::forecast_entry_carries_basis_and_verdict ... ok
test tests::forecast_high_priority_never_paused ... ok
test tests::forecast_line_names_figures_basis_confidence_verdict ... ok
test tests::forecast_malformed_job_yields_none ... ok
test tests::forecast_pause_decision_uses_the_os085_warning_band ... ok
test tests::forecast_pause_only_low_running_in_warning_lane ... ok
test tests::forecast_projection_scales_the_ledger_rate ... ok
test tests::forecast_projection_at_or_past_day_end_is_spent ... ok
test tests::forecast_resume_only_when_budget_freed ... ok
test tests::forecast_preempt_record_names_job_lane_action ... ok
test tests::forecast_unprojectable_inputs_yield_none ... ok
test tests::forecast_unusable_entries_and_empty_input_yield_no_lines ... ok
test tests::forecast_unusable_entries_yield_none ... ok
test tests::cost_check_passes_with_exact_totals ... ok
test tests::cost_table_renders_rows_budgets_and_headroom ... ok
test tests::forecast_within_cap_entry_has_no_breach ... ok
test tests::forecast_within_cap_line_says_within_cap ... ok
test tests::gate_cap_includes_overspend ... ok
test tests::gate_budget_state_names_all_three_states ... ok
test tests::gate_claim_gate_follows_cap_only ... ok
test tests::gate_entry_without_flag_renders_as_before ... ok
test tests::gate_drill_phases ... ok
test tests::gate_held_lane_line_names_the_hold ... ok
test tests::gate_duplicate_lane_warns_once ... ok
test tests::gate_hold_entry_flags_only_at_cap ... ok
test tests::gate_malformed_budget_entries_do_not_crash_detector ... ok
test tests::gate_no_warning_below_threshold_or_at_cap ... ok
test tests::gate_unbudgeted_and_malformed_never_warned_or_held ... ok
test tests::gate_unheld_lane_line_unchanged ... ok
test tests::gate_warning_band_is_threshold_to_cap_exclusive ... ok
test tests::gate_warning_fires_at_threshold_with_lane_figures ... ok
test tests::missing_dispatch_is_an_error ... ok
test tests::spend_line_formats_match_brief_renderer ... ok
test tests::value_py_repr_matches_python ... ok
test tests::value_rate_parsing_falls_back ... ok
test tests::value_estimate_tokens_matches_client ... ok
test tests::value_trim_to_budget_drops_bullets_from_the_end ... ok
test tests::cost_check_twice_identical ... ok
test tests::brief_template_record_carries_null_spend ... ok
test tests::brief_cost_script_main_passes ... ok
test tests::brief_cost_check_passes_with_exact_totals ... ok

test result: ok. 61 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-e3f8686e1f9dd067)

running 4 tests
test out_of_order_input_keeps_input_order ... ok
test duplicate_input_is_kept_and_deduped_where_documented ... ok
test empty_input_is_handled_everywhere ... ok
test maximum_input_stays_finite ... ok

test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/error_paths.rs (target/debug/deps/error_paths-954df2055545fe2a)

running 23 tests
test breach_flips_passed_and_headroom ... ok
test audit_empty_list_passes_vacuously ... ok
test budgets_from_snapshot_skips_bad_entries ... ok
test audit_refuses_non_list_records ... ok
test bad_rate_falls_back_to_default ... ok
test empty_snapshot_is_unbudgeted_not_zero ... ok
test budget_gate_never_warns_or_holds_malformed_figures ... ok
test cgroup_gate_reports_missing_controllers ... ok
test audit_files_record_and_spec_leaks ... ok
test env_int_refuses_blank_bad_and_out_of_range ... ok
test cost_totals_panics_without_a_boot_row - should panic ... ok
test fixtures_used_by_this_file_are_the_public_shapes ... ok
test fake_queue_refuses_claim_at_cap_and_keeps_job_open ... ok
test forecast_refuses_unprojectable_inputs ... ok
test preempt_refuses_every_other_state ... ok
test parse_artifact_ref_refuses_every_malformed_shape ... ok
test slice_mismatch_fails_file_phase ... ok
test render_tables_mark_fail_for_breach ... ok
test spend_line_refuses_entries_without_a_usable_figure ... ok
test spend_ratio_refuses_non_int_zero_cap_and_negative ... ok
test empty_snapshot_yields_empty_sections ... ok
test unreadable_artifact_store_is_a_leak ... ok
test unreadable_journal_is_one_leak_per_agent ... ok

test result: ok. 23 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/gap_close.rs (target/debug/deps/gap_close-ab07ed9db1c4c04b)

running 30 tests
test brief_budget_kinds ... ok
test brief_cost_claims_are_ten_and_match_the_manifest ... ok
test busy_snapshot_has_22_jobs_and_6_owners ... ok
test brief_prompt_names_kind_and_budget ... ok
test cost_uses_both_rates ... ok
test cost_zero_tokens_is_zero ... ok
test demo_snapshot_shape ... ok
test estimate_tokens_counts_characters_not_bytes ... ok
test build_rows_has_five_classes_and_counts ... ok
test cost_totals_excludes_boot_from_headline ... ok
test build_rows_matches_the_disk_reader ... ok
test busy_snapshot_long_titles_variant ... ok
test cost_totals_zero_worst_has_zero_breakeven ... ok
test measure_scored_variant_shape ... ok
test polish_prompt_carries_the_facts_rule ... ok
test render_brief_cost_table_breakeven_uses_the_worst_row ... ok
test build_rows_expected_output_for_dispatch_is_the_proxy ... ok
test measure_tokens_in_matches_brief_prompt ... ok
test round6_rounds_to_six_places ... ok
test render_cost_table_names_every_class ... ok
test measure_long_variant_shape ... ok
test measure_actual_spend_is_zero ... ok
test run_cost_check_returns_a_passing_code ... ok
test template_record_passes_kind_through ... ok
test build_rows_returns_both_variants ... ok
test measure_template_fits_the_morning_budget ... ok
test render_brief_cost_table_passes_under_the_caps ... ok
test build_rows_is_deterministic ... ok
test run_brief_cost_check_returns_zero ... ok
test render_brief_cost_table_names_the_ledger_note ... ok

test result: ok. 30 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.07s

     Running unittests src/lib.rs (target/debug/deps/os_identity-860966273d64765a)

running 20 tests
test tests::cap_set_drops_empties_from_ragged_caps ... ok
test tests::config_defaults_and_key_shapes ... ok
test tests::get_returns_none_for_unknown ... ok
test tests::find_for_bad_max_jobs_falls_back_to_one ... ok
test tests::find_for_ignores_non_claimed_and_other_agents_jobs ... ok
test tests::is_fresh_boundaries_and_bad_updated ... ok
test tests::find_for_skips_stale_agents ... ok
test tests::agents_skips_index_members_without_a_hash ... ok
test tests::find_for_results_are_sorted ... ok
test tests::find_for_matches_caps_freshness_and_capacity ... ok
test tests::record_fields_round_trip_skip_empty ... ok
test tests::register_empty_host_is_not_stored ... ok
test tests::prune_stale_removes_only_stale_sorted ... ok
test tests::register_refresh_overwrites_caps_and_keeps_index_single ... ok
test tests::register_rejects_blank_nick_and_empty_caps ... ok
test tests::store_error_paths_match_python_fallbacks ... ok
test tests::register_normalizes_caps_sorted_lower_deduped ... ok
test tests::register_stores_optional_fields_only_when_nonempty ... ok
test tests::touch_heartbeat_unknown_false_known_true ... ok
test tests::unregister_removes_hash_and_index ... ok

test result: ok. 20 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-9c073fb8247e328a)

running 12 tests
test future_and_unparseable_updated_values ... ok
test extreme_positive_updated_does_not_overflow ... ok
test empty_capability_slice_is_refused ... ok
test duplicate_capabilities_are_deduped_and_sorted ... ok
test capacity_zero_behaves_as_one ... ok
test out_of_order_index_scores_list_in_score_order ... ok
test duplicate_registration_updates_one_record_and_one_index_member ... ok
test maximum_nick_length_round_trips ... ok
test empty_requirement_list_matches_every_fresh_agent_with_capacity ... ok
test out_of_order_registration_returns_sorted_nicks ... ok
test staleness_boundary_is_inclusive ... ok
test maximum_capability_list_and_job_capacity ... ok

test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/error_paths.rs (target/debug/deps/error_paths-39a5317da6bf7787)

running 12 tests
test active_claims_job_error_is_zero ... ok
test agents_index_error_is_an_empty_list_not_an_error ... ok
test find_for_propagates_a_per_agent_read_error ... ok
test prune_stale_propagates_a_delete_error ... ok
test register_store_failure_is_wrapped_as_store_error ... ok
test register_without_a_usable_capability_refused ... ok
test store_error_display_and_conversion ... ok
test register_blank_nick_refused_with_python_wording ... ok
test get_store_failure_propagates ... ok
test agents_per_agent_hash_error_propagates ... ok
test unregister_store_failure_propagates ... ok
test touch_unknown_is_false_and_store_failure_propagates ... ok

test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/gap_close.rs (target/debug/deps/gap_close-76accadebef6b958)

running 11 tests
test all_three_error_types_are_std_errors ... ok
test config_defaults_are_the_documented_constants ... ok
test cap_set_drops_empties_from_ragged_caps ... ok
test memory_store_job_claims_reflect_set_jobs ... ok
test memory_store_round_trips_direct_operations ... ok
test memory_store_zrange_orders_equal_scores_by_member ... ok
test negative_max_jobs_behaves_as_one ... ok
test register_error_messages_are_python_exact ... ok
test registry_error_display_covers_both_variants ... ok
test from_fields_defaults_and_ignores_unknown_fields ... ok
test to_fields_skips_empty_values ... ok

test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s

     Running unittests src/lib.rs (target/debug/deps/os_jobs-cca0c04e02a11afb)

running 101 tests
test tests::cancel_tests::test_cancel_missing_job_refused ... ok
test tests::claim_tests::test_claim_mutex_rolled_back_when_hset_fails ... ok
test tests::claim_tests::test_claim_missing_job ... ok
test tests::cancel_tests::test_cancelled_job_cannot_be_claimed ... ok
test tests::cancel_tests::test_cancel_open_job ... ok
test tests::cancel_tests::test_cancel_twice_refused ... ok
test tests::claim_tests::test_claim_lifecycle ... ok
test tests::claim_tests::test_claim_twice_fails ... ok
test tests::cancel_tests::test_list_status_cancelled ... ok
test tests::encoding_tests::test_hgetall_roundtrips_literal_percent ... ok
test tests::cancel_tests::test_cancel_claimed_job_refused ... ok
test tests::claim_tests::test_lost_race ... ok
test tests::claim_tests::test_ids_increment ... ok
test tests::environment_jobs_tests::test_boot_template_brief_carries_builder_working_line ... ok
test tests::environment_jobs_tests::test_no_claimed_job_returns_empty_not_none ... ok
test tests::environment_jobs_tests::test_builder_record_renders_working_line_and_others_not_reported ... ok
test tests::environment_jobs_tests::test_non_list_returns_none_so_line_reads_not_reported ... ok
test tests::environment_jobs_tests::test_only_claimed_jobs_with_nick_and_title_survive_in_order ... ok
test tests::environment_jobs_tests::test_unusable_id_is_left_out_not_invented ... ok
test tests::hardening_tests::test_post_defaults_to_first_kid ... ok
test tests::hardening_tests::test_claim_refuses_expired_and_alerts ... ok
test tests::hardening_tests::test_legacy_single_token_file_still_works ... ok
test tests::hardening_tests::test_post_unknown_kid_rejected ... ok
test tests::hardening_tests::test_show_displays_sig_fields ... ok
test tests::hardening_tests::test_unsigned_claim_still_allowed_with_warning ... ok
test tests::hardening_tests::test_expiry ... ok
test tests::hardening_tests::test_post_explicit_kid ... ok
test tests::job_fields_tests::test_attempts_unlimited_requeues ... ok
test tests::job_fields_tests::test_attempts_walk_to_failed_final ... ok
test tests::job_fields_tests::test_deps_missing_warns_but_posts ... ok
test tests::hardening_tests::test_claim_refuses_tampered_and_alerts ... ok
test tests::job_fields_tests::test_deps_stored_and_shown ... ok
test tests::job_fields_tests::test_list_json_empty ... ok
test tests::job_fields_tests::test_files_stored_and_shown ... ok
test tests::jobs_unit_tests::test_exec_runs_jobs_sweep_with_no_secret_on_command_line ... ok
test tests::job_fields_tests::test_list_json_shape_and_values ... ok
test tests::jobs_unit_tests::test_image_route_enables_and_live_route_stages ... ok
test tests::hardening_tests::test_v1_signature_still_verifies ... ok
test tests::job_fields_tests::test_progress_and_heartbeat_stamps ... ok
test tests::hardening_tests::test_verify_unknown_kid_is_bad ... ok
test tests::jobs_unit_tests::test_unit_exists ... ok
test tests::jobs_unit_tests::test_install_and_target_want_each_other ... ok
test tests::hardening_tests::test_transplanted_signature_fails ... ok
test tests::jobs_unit_tests::test_service_identity_workdir_and_oneshot ... ok
test tests::jobs_unit_tests::test_unit_ordering_target_and_secrets_gate ... ok
test tests::jobs_unit_tests::test_readme_section_and_spec_record ... ok
test tests::lease_expiry_tests::test_expired_claim_can_be_reclaimed ... ok
test tests::nick_claim_tests::test_claim_expires ... ok
test tests::nick_claim_tests::test_claim_renewed_by_heartbeat ... ok
test tests::nick_claim_tests::test_claim_ttl_matches_presence_interval ... ok
test tests::nick_claim_tests::test_conflict_clears_when_holder_leaves ... ok
test tests::lease_expiry_tests::test_requeue_after_expiry ... ok
test tests::nick_claim_tests::test_first_claim_wins ... ok
test tests::nick_claim_tests::test_nick_holder_readonly ... ok
test tests::nick_claim_tests::test_winner_sees_no_conflict ... ok
test tests::jobs_unit_tests::test_jobspy_is_the_named_process ... ok
test tests::post_tests::test_post_empty_spec_rejected ... ok
test tests::post_tests::test_post_announces_to_room ... ok
test tests::post_tests::test_post_bad_artifact_ref_posts_nothing ... ok
test tests::lease_expiry_tests::test_sweep ... ok
test tests::lease_expiry_tests::test_requeue_refuses_active_lease ... ok
test tests::post_tests::test_post_creates_job ... ok
test tests::list_show_tests::test_list_and_show ... ok
test tests::post_tests::test_post_lease_too_short_rejected ... ok
test tests::post_tests::test_post_spec_from_stdin ... ok
test tests::progress_done_tests::test_done ... ok
test tests::progress_done_tests::test_claim_blocked_fails ... ok
test tests::progress_done_tests::test_blocked_releases ... ok
test tests::progress_done_tests::test_done_by_other_fails ... ok
test tests::progress_done_tests::test_heartbeat_renews ... ok
test tests::progress_done_tests::test_progress_renews_and_notes ... ok
test tests::pure_tests::test_artifact_ref_valid_and_malformed ... ok
test tests::pure_tests::test_brief_time_eastern_conversion ... ok
test tests::pure_tests::test_canonical_v1_payload_and_signature ... ok
test tests::pure_tests::test_canonical_v2_payload_and_signature ... ok
test tests::pure_tests::test_canonical_v2_unicode_escaping_matches_python ... ok
test tests::pure_tests::test_clean_room_and_bus_key ... ok
test tests::pure_tests::test_keyring_parsing ... ok
test tests::pure_tests::test_sha256_vectors ... ok
test tests::pure_tests::test_url_quote_unquote_roundtrip ... ok
test tests::req_tests::test_post_stores_normalized_req ... ok
test tests::req_tests::test_post_without_req_stores_empty ... ok
test tests::req_tests::test_list_json_and_show_carry_req ... ok
test tests::signed_job_tests::test_post_bad_secret_file_errors ... ok
test tests::signed_job_tests::test_claim_signed_ok ... ok
test tests::signed_job_tests::test_claim_unsigned_with_secret_still_works ... ok
test tests::signed_job_tests::test_post_unsigned_has_no_sig ... ok
test tests::signed_job_tests::test_claim_refuses_tampered ... ok
test tests::sweep_dep_dead_tests::test_claimed_job_with_blocked_dep_flagged ... ok
test tests::sweep_dep_dead_tests::test_failed_final_dep_flagged ... ok
test tests::signed_job_tests::test_verify_ok ... ok
test tests::signed_job_tests::test_verify_unknown_job ... ok
test tests::signed_job_tests::test_verify_unsigned ... ok
test tests::signed_job_tests::test_post_signed_stores_sig ... ok
test tests::signed_job_tests::test_verify_tampered_spec ... ok
test tests::signed_job_tests::test_verify_wrong_secret ... ok
test tests::signed_job_tests::test_show_displays_signed_by ... ok
test tests::trust_warning_tests::test_claim_warns_on_spoofed_poster ... ok
test tests::sweep_dep_dead_tests::test_open_or_done_dep_not_flagged ... ok
test tests::sweep_dep_dead_tests::test_open_job_with_blocked_dep_flagged_no_mutation ... ok
test tests::signed_job_tests::test_verify_tampered_field ... ok

test result: ok. 101 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-b85e409718d41230)

running 6 tests
test duplicate_deps_warn_once_per_listed_dep ... ok
test maximum_input_round_trips_a_64k_spec ... ok
test duplicate_input_in_one_attach_is_stored_twice ... ok
test empty_input_omits_empty_fields_and_lists_no_jobs ... ok
test zero_attempt_budget_fails_final_on_the_first_requeue ... ok
test out_of_order_input_lists_ids_lexicographically_within_one_second ... ok

test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/error_paths.rs (target/debug/deps/error_paths-aadce5a9c3048481)

running 56 tests
test a_missing_keyring_file_is_a_read_refusal ... ok
test attach_refuses_a_malformed_ref ... ok
test attach_refuses_a_missing_job ... ok
test attach_reports_a_write_failure ... ok
test blocked_refuses_a_missing_job ... ok
test blocked_refuses_a_non_claimer ... ok
test cancel_reports_a_store_failure ... ok
test claim_does_not_read_the_secret_file_for_an_unsigned_job ... ok
test claim_refuses_a_job_that_is_not_open ... ok
test claim_refuses_a_missing_job ... ok
test claim_refuses_a_short_lease ... ok
test done_refuses_a_missing_job ... ok
test environment_lines_reports_every_missing_quarter ... ok
test claim_reports_a_mutex_write_failure ... ok
test done_reports_a_store_failure ... ok
test claim_reports_a_malformed_expiry_as_a_verify_failure ... ok
test claim_rolls_back_the_mutex_when_the_claim_record_fails ... ok
test done_refuses_a_non_claimer ... ok
test environment_lines_reports_nobody_when_the_jobs_list_is_empty ... ok
test claim_refuses_a_tampered_signature_and_announces_it ... ok
test claim_refuses_an_expired_signature ... ok
test heartbeat_refuses_a_missing_job ... ok
test heartbeat_refuses_a_non_claimer ... ok
test heartbeat_reports_a_lost_lease_on_a_store_failure ... ok
test job_get_returns_nothing_for_an_invalid_id ... ok
test job_get_swallows_a_store_failure ... ok
test keyring_refuses_a_line_with_two_colons ... ok
test keyring_refuses_empty_kid_or_secret ... ok
test keyring_refuses_multiple_legacy_secrets ... ok
test keyring_refuses_an_empty_file ... ok
test nick_claim_returns_none_when_the_store_fails ... ok
test post_bad_room_is_refused ... ok
test post_empty_spec_is_refused ... ok
test post_fails_when_the_job_hash_write_fails ... ok
test post_fails_when_the_index_write_fails ... ok
test post_fails_when_the_sequence_counter_fails ... ok
test post_fails_when_the_spec_write_fails ... ok
test post_malformed_artifact_ref_is_refused ... ok
test post_refuses_a_zero_expiry ... ok
test post_short_lease_is_refused ... ok
test progress_refuses_a_missing_job ... ok
test progress_refuses_a_non_claimer ... ok
test requeue_refuses_a_job_that_is_not_claimed ... ok
test progress_reports_a_note_write_failure ... ok
test post_with_a_missing_secret_file_reports_after_the_job_is_written ... ok
test requeue_refuses_a_missing_job ... ok
test requeue_reports_a_requeue_write_failure ... ok
test post_reports_a_signing_write_failure ... ok
test requeue_reports_an_attempts_write_failure ... ok
test sweep_reports_an_index_read_failure ... ok
test verdict_words_are_stable ... ok
test sweep_warns_when_a_requeue_fails_and_does_not_fail_the_sweep ... ok
test post_refuses_an_unknown_kid ... ok
test verify_exits_one_on_a_bad_signature ... ok
test verify_refuses_an_unknown_job ... ok
test verify_reports_a_missing_secret_file ... ok

test result: ok. 56 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s

     Running tests/gap_close.rs (target/debug/deps/gap_close-55c0e90d02c5e774)

running 13 tests
test canonical_json_sorts_keys_and_uses_compact_separators ... ok
test canonical_payload_v1_is_the_sorted_six_field_shape ... ok
test canonical_payload_v2_binds_job_and_key_id ... ok
test ct_eq_is_length_aware_and_content_aware ... ok
test hex_digest_is_lowercase_and_zero_padded ... ok
test hmac_sha256_matches_the_published_vector ... ok
test json_escape_handles_quote_backslash_and_controls ... ok
test json_escape_surrogate_pairs_beyond_the_bmp ... ok
test python_repr_escapes_quote_and_backslash ... ok
test sha256_matches_the_published_vector ... ok
test url_quote_percent_encodes_everything_but_unreserved ... ok
test url_quote_unquote_round_trips_utf8 ... ok
test url_unquote_leaves_malformed_sequences_alone ... ok

test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running unittests src/lib.rs (target/debug/deps/os_memory-49b01e276695c6b9)

running 37 tests
test tests::test_depth_non_dict_snapshot_gets_no_record ... ok
test tests::test_depth_snapshot_with_nothing_usable_gets_no_record ... ok
test tests::test_depth_hand_stated_record_wins_unchanged ... ok
test tests::test_depth_default_stamp_is_an_int_when_now_is_not_given ... ok
test tests::test_depth_memory_down_record_carries_no_item_beside_it ... ok
test tests::test_depth_fills_all_three_categories_with_one_stamp ... ok
test tests::test_depth_single_category_record_reads_other_categories_none_reported ... ok
test tests::test_format_brief_time_dst_boundaries ... ok
test tests::test_depth_filled_record_renders_memory_depth_lines ... ok
test tests::test_depth_malformed_entries_skipped_never_guessed ... ok
test tests::test_format_brief_time_known_values ... ok
test tests::test_depth_caller_snapshot_is_never_mutated ... ok
test tests::test_os078_bake_build_image_bakes_root_and_enables_unit ... ok
test tests::test_os078_bake_build_live_stages_root ... ok
test tests::test_os078_bake_hook_enables_unit_and_chowns_root ... ok
test tests::test_os078_bake_target_wants_unit ... ok
test tests::test_os078_bake_unit_shape ... ok
test tests::test_os078_bake_packer_bakes_root_and_enables_unit ... ok
test tests::test_os078_bake_docs_record_first_light_without_em_dash ... ok
test tests::test_os078_agent_validation_refuses_slash ... ok
test tests::test_os078_key_validation_refuses_escape ... ok
test tests::test_os078_ensure_root_creates_namespaces_idempotently ... ok
test tests::test_os078_cli_read_back_and_ensure_and_escape ... ok
test tests::test_os078_corrupt_journal_line_raises ... ok
test tests::test_os078_mount_paths_name_own_and_shared ... ok
test tests::test_os078_cli_write_author_and_version_flags ... ok
test tests::test_os078_identical_rewrite_is_a_noop ... ok
test tests::test_os078_list_keys_sorted_and_shared_separate ... ok
test tests::test_os078_missing_key_and_bad_version_raise_never_guess ... ok
test tests::test_os078_cli_write_list_history_and_shared ... ok
test tests::test_os078_shared_identical_rewrite_is_a_noop ... ok
test tests::test_os078_wrong_shaped_entry_text_raises ... ok
test tests::test_os078_shared_namespace_versions_independently ... ok
test tests::test_os078_write_and_read_round_trip ... ok
test tests::test_os078_versions_increment_and_versioned_read ... ok
test tests::test_os078_bake_build_scripts_bash_syntax_clean ... ok
test tests::test_os078_bake_memory_root_sweeps_clean_and_secret_value_flagged ... ok

test result: ok. 37 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.09s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-c9e6defe303ec274)

running 9 tests
test b039_duplicate_json_keys_keep_the_first_like_python_dict_order ... ok
test b039_a_blank_journal_line_is_skipped_not_refused ... ok
test b039_unicode_agent_nick_is_alphanumeric_and_accepted ... ok
test b039_duplicate_input_identical_write_appends_nothing ... ok
test b039_agent_and_shared_namespaces_do_not_leak_into_each_other ... ok
test b039_out_of_order_input_reads_journal_order_not_version_order ... ok
test b039_extra_journal_fields_round_trip_through_the_typed_entry ... ok
test b039_empty_input_empty_text_is_a_real_version_and_a_noop_after ... ok
test b039_maximum_input_large_body_and_long_key_round_trip ... ok

test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s

     Running tests/error_paths.rs (target/debug/deps/error_paths-d5eeb2dacb60201c)

running 10 tests
test b038_agent_refusals_keep_the_python_order_and_messages ... ok
test b038_shared_key_refusal_leaves_no_shared_directory ... ok
test b038_key_refusals_keep_the_python_order_and_messages ... ok
test b038_a_valid_cli_error_never_writes_to_stdout ... ok
test b038_cli_refusals_are_exit_2_with_the_documented_prefix ... ok
test b038_ensure_root_refuses_when_the_root_is_a_file ... ok
test b038_write_reads_before_appending_so_a_bad_journal_blocks_writes ... ok
test b038_unreadable_journal_refuses_with_the_io_reason ... ok
test b038_missing_key_and_bad_versions_refuse_with_exact_text ... ok
test b038_corrupt_journal_refuses_and_names_the_line ... ok

test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/gap_close.rs (target/debug/deps/gap_close-5dfe0c835c6b001d)

running 11 tests
test gap_json_big_integer_falls_back_to_float_like_the_port_says ... ok
test gap_json_leading_zero_is_accepted_by_this_parser ... ok
test gap_json_lists_and_empty_containers_round_trip ... ok
test gap_json_objects_keep_order_and_get_returns_the_first_duplicate ... ok
test gap_json_parser_refuses_empty_trailing_and_unterminated_input ... ok
test gap_json_parses_every_scalar_shape ... ok
test gap_json_render_then_parse_keeps_unicode_text ... ok
test gap_json_strings_decode_short_escapes_and_surrogate_pairs ... ok
test gap_json_writer_escapes_non_ascii_and_control_characters ... ok
test gap_json_writer_formats_floats_like_json_dumps ... ok
test gap_json_writer_preserves_insertion_order_while_sorted_sorts ... ok

test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running unittests src/lib.rs (target/debug/deps/os_misc-67c92d14a440c8ae)

running 47 tests
test b24::poll::tests::missing_seen_starts_at_zero ... ok
test b24::send::tests::duration_shapes ... ok
test b24::send::tests::basename_shapes ... ok
test b24::presence::tests::empty_means_no_one ... ok
test b24::send::tests::at_shapes ... ok
test b24::send::tests::pomodoro_shapes ... ok
test b24::presence::tests::suffix_shapes ... ok
test b24::watch::tests::interval_must_be_positive ... ok
test b24::watch_nick::tests::matches_canonical_or_display ... ok
test b24::watch_nick::tests::flag_and_render_shapes ... ok
test b25::announce::tests::filter_keeps_announcer_only ... ok
test b25::announce::tests::filter_no_announcer_keeps_all ... ok
test b25::announce::tests::gate_shapes ... ok
test b25::clipboard::tests::tool_order_matches_spec ... ok
test b25::edits::tests::length_limit ... ok
test b25::edits::tests::parse_shapes ... ok
test b25::forward::tests::fwd_parse_shapes ... ok
test b25::forward::tests::via_collapse_single_hop ... ok
test b25::paste::tests::known_vector ... ok
test b25::saved::tests::key_and_label_shapes ... ok
test b25::paste::tests::verify_round_trip ... ok
test b24::store::tests::bad_lines_skipped ... ok
test b26::admin::tests::display_shapes ... ok
test b26::admin::tests::rekey_and_envelope ... ok
test b24::poll::tests::filters_own_and_advances ... ok
test b25::saved::tests::list_filter_and_render ... ok
test b26::digest::tests::talkers_and_hours ... ok
test b26::export::tests::bad_time_is_unknown ... ok
test b26::export::tests::md_and_json_shapes ... ok
test b26::health::tests::line_shape ... ok
test b26::health::tests::uptime_shapes ... ok
test b26::timecapsule::tests::sweep_shapes ... ok
test b26::webhook::tests::resolve_shapes ... ok
test b24::store::tests::edit_only_author_and_history ... ok
test b27::par_clock::tests::alert_line_shape ... ok
test b27::par_clock::tests::grace_escalates_and_dedupes ... ok
test b27::par_clock::tests::enter_twice_refused_and_id_rules ... ok
test b27::par_clock::tests::inputs_never_mutated_and_crews_independent ... ok
test b27::par_clock::tests::quiet_before_interval_and_once_per_cycle ... ok
test b27::validate::tests::dir_match ... ok
test b27::par_clock::tests::complete_resets_and_exit_silences ... ok
test b27::validate::tests::rejects_non_object_and_missing_keys ... ok
test b27::validate::tests::privacy_crossing_rule ... ok
test b28::tests::inventory_complete ... ok
test b29::tests::inventory_complete ... ok
test b30::tests::inventory_complete ... ok
test b24::store::tests::append_ids_increment_and_survive ... ok

test result: ok. 47 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-6d3bfccc33a3046f)

running 4 tests
test empty_input ... ok
test maximum_input ... ok
test out_of_order_input ... ok
test duplicate_input ... ok

test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/error_paths.rs (target/debug/deps/error_paths-7a08a6fc2c1ce6b8)

running 17 tests
test admin_display_and_rekey_refusals ... ok
test edit_text_refuses_empty_and_over_max ... ok
test pack_validator_refuses_non_object_and_missing_keys ... ok
test pack_validator_names_unknown_serves_and_bad_severity ... ok
test clip_hash_mismatch_is_loud ... ok
test duration_refusals_name_the_accepted_shapes ... ok
test crew_id_rules_and_lifecycle_refusals ... ok
test missing_seen_file_reads_as_zero ... ok
test announce_gate_names_claim_holder_and_mods ... ok
test positive_only_intervals ... ok
test presence_render_carries_both_suffixes ... ok
test poll_surfaces_transport_failure_and_warns_on_best_effort_writes ... ok
test store_refuses_empty_nick_and_empty_text ... ok
test store_edit_refusals_are_exact ... ok
test watch_refuses_nonpositive_interval_and_bus_error ... ok
test webhook_url_resolution_refusals ... ok
test store_write_failure_is_returned_not_panicked ... ok

test result: ok. 17 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s

     Running tests/gap_close.rs (target/debug/deps/gap_close-66676027edbb09ed)

running 7 tests
test max_text_is_the_relay_common_value ... ok
test bus_key_round_trips_the_default_and_a_room ... ok
test mark_seen_default_succeeds ... ok
test own_prefixes_defaults_to_the_canonical_nick_only ... ok
test presence_beat_default_succeeds ... ok
test room_for_key_extracts_a_room_name ... ok
test room_for_key_treats_the_default_list_as_no_room ... ok

test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running unittests src/lib.rs (target/debug/deps/os_supervisor-544e8c6fde1fc3eb)

running 379 tests
test drills::kill_worker::tests::test_phase1_healthy_worker_yields_zero_alerts ... ok
test drills::kill_worker::tests::test_no_alert_without_any_timestamp ... ok
test drills::kill_worker::tests::test_kill_is_idempotent_and_leaves_job_untouched ... ok
test drills::kill_worker::tests::test_kill_when_absent_is_a_noop ... ok
test drills::kill_worker::tests::test_drill_accepts_an_injected_watchdog ... ok
test drills::kill_worker::tests::test_phase3_unexpired_lease_stays_claimed ... ok
test drills::kill_worker::tests::test_claim_sets_lease_fields_and_presence ... ok
test drills::kill_worker::tests::test_phase2_kill_yields_exactly_one_presence_stall ... ok
test drills::kill_worker::tests::test_announcements_only_for_critical_alerts ... ok
test drills::kill_worker::tests::test_heartbeat_is_idempotent_on_presence_and_scoped_to_own_jobs ... ok
test drills::kill_worker::tests::test_phase4_lease_expiry_requeues_and_alert_resolves ... ok
test drills::kill_worker::tests::test_present_worker_with_stale_progress_gets_progress_stall_not_presence ... ok
test drills::kill_worker::tests::test_progress_stamps_only_own_jobs_and_posts_message ... ok
test drills::kill_worker::tests::test_run_drill_passes_all_phases ... ok
test drills::kill_worker::tests::test_run_drill_stdout_reports_pass_and_exit_0 ... ok
test drills::kill_worker::tests::test_stall_boundary_is_strict ... ok
test drills::kill_worker::tests::test_sweep_clears_exactly_the_requeue_fields ... ok
test drills::kill_worker::tests::test_sweep_boundary_now_equals_lease_until_requeues ... ok
test drills::kill_worker::tests::test_sweep_skips_open_jobs_and_jobs_without_lease ... ok
test drills::kill_worker::tests::test_walk_on_claimer_not_in_caps_is_skipped ... ok
test drills::watchman_boot::tests::test_drill_arrival_rings ... ok
test drills::watchman_boot::tests::test_drill_corrupted_counter ... ok
test drills::kill_worker::tests::test_sweep_requeues_in_board_order ... ok
test drills::watchman_boot::tests::test_drill_malformed_records ... ok
test drills::watchman_boot::tests::test_drill_immutable_and_no_dale ... ok
test drills::watchman_boot::tests::test_drill_non_ringing_jobs ... ok
test drills::watchman_boot::tests::test_drill_no_double_ring ... ok
test drills::watchman_boot::tests::test_drill_sweep_reconciliation ... ok
test drills::watchman_bridge::tests::test_drill_passes ... ok
test drills::watchman_bridge::tests::test_drill_phase1_real_tick_wake ... ok
test drills::watchman_bridge::tests::test_drill_phase2_bridge_alive ... ok
test drills::watchman_boot::tests::test_drill_passes ... ok
test drills::watchman_bridge::tests::test_drill_phase4_no_bell_unknown ... ok
test drills::watchman_bridge::tests::test_drill_phase3_aged_crew_dark_and_recover ... ok
test drills::watchman_bridge_tick::tests::test_drill_phase1_ring_and_quiet ... ok
test drills::watchman_bridge_tick::tests::test_drill_phase2_silence_and_recovery ... ok
test drills::watchman_bridge_tick::tests::test_drill_passes ... ok
test drills::watchman_bridge_tick::tests::test_drill_phase3_second_episode_realerts ... ok
test drills::watchman_bridge_tick::tests::test_drill_phase4_malformed_contained ... ok
test drills::watchman_bridge_tick::tests::test_drill_phase5_absent_machine_unjudged ... ok
test drills::watchman_cycle::tests::test_drill_passes ... ok
test drills::watchman_cycle::tests::test_drill_phase1_well_behaved_runner ... ok
test drills::watchman_cycle::tests::test_drill_phase3_garbage_runner ... ok
test drills::watchman_cycle::tests::test_drill_phase2_raising_runner ... ok
test drills::watchman_cycle::tests::test_drill_phase4_non_callable_runner ... ok
test drills::watchman_cycle::tests::test_drill_phase5_empty_machine_list ... ok
test drills::watchman_cycle::tests::test_drill_phase6_truthy_is_not_true ... ok
test drills::watchman_loop::tests::test_drill_phase1_ring_and_quiet ... ok
test drills::watchman_loop::tests::test_drill_phase2_failed_runs_age_dark ... ok
test drills::watchman_loop::tests::test_drill_phase2b_open_episode_stays_silent ... ok
test drills::watchman_loop::tests::test_drill_phase2c_fresh_ring_recovers ... ok
test drills::watchman_loop::tests::test_drill_passes ... ok
test drills::watchman_loop::tests::test_drill_phase4_no_prior_failure_unjudged ... ok
test drills::watchman_loop::tests::test_drill_phase3_malformed_stdout_contained ... ok
test drills::watchman_loop::tests::test_drill_phase5_inputs_never_mutated ... ok
test drills::watchman_service::tests::test_drill_phase1_state_carries ... ok
test drills::watchman_service::tests::test_drill_phase2_zero_cycles ... ok
test drills::watchman_service::tests::test_drill_phase3_should_stop ... ok
test drills::watchman_runner::tests::test_drill_phase5_bad_inputs_contained ... ok
test drills::watchman_service::tests::test_drill_phase4_raising_cycle_contained ... ok
test drills::watchman_service::tests::test_drill_phase7_inputs_never_mutated ... ok
test drills::watchman_service::tests::test_drill_phase5_raising_callback_and_stop ... ok
test drills::watchman_runner::tests::test_drill_phase6_failed_run_ages ... ok
test drills::watchman_service_cli::tests::test_drill_phase2_empty_machines ... ok
test drills::watchman_runner::tests::test_drill_phase4_nonzero_discards ... ok
test drills::watchman_service_cli::tests::test_drill_phase4_bad_flag ... ok
test drills::watchman_service_cli::tests::test_drill_phase5_bare_machines ... ok
test drills::watchman_watch::tests::test_drill_passes ... ok
test drills::watchman_watch::tests::test_drill_phase_alive_and_unknown ... ok
test drills::watchman_watch::tests::test_drill_phase_kill_and_revive ... ok
test drills::watchman_watch::tests::test_drill_phase_kill_beyond_repair ... ok
test drills::watchman_watch::tests::test_drill_phase_no_dale_and_immutable ... ok
test drills::watchman_watch::tests::test_drill_phase_revive_then_die_again ... ok
test drills::watchman_watch::tests::test_drill_phase_stale_bell ... ok
test e2e_watchdog_surfaces::tests::test_build_alert_record_rejects_missing_fields ... ok
test e2e_watchdog_surfaces::tests::test_loop_passes_all_stages_mirrors_python ... ok
test e2e_watchdog_surfaces::tests::test_loop_twice_isolated_mirrors_python ... ok
test e2e_watchdog_surfaces::tests::test_presence_stall_detector_edges ... ok
test e2e_watchdog_surfaces::tests::test_watch_items_skip_idless_and_fall_back_to_explanation ... ok
test overseer::tests::dispatch_empty_spec_fails_and_no_dm_sent ... ok
test overseer::tests::dispatch_posts_and_dms_capable_workers_from_module_behavior ... ok
test overseer::tests::parse_helpers_mirror_python ... ok
test overseer::tests::tick_verifies_done_jobs_and_reports_failed ... ok
test overseer::tests::verify_done_failure_requeues_with_report_and_clears_claim ... ok
test overseer::tests::verify_done_guards_missing_not_done_already_verified ... ok
test overseer::tests::verify_done_success_marks_verified_and_announces ... ok
test overseer::tests::verify_done_worktree_failure_is_error_and_tick_records_it ... ok
test reconcile::tests::blocked_note_truncated_to_200_chars ... ok
test reconcile::tests::reconcile_clean_summary_when_nothing_to_do ... ok
test reconcile::tests::reconcile_full_flow_from_module_behavior ... ok
test reconcile::tests::reconcile_redis_down_returns_early_empty ... ok
test reconcile::tests::reconcile_sweep_and_prune_failures_tolerated ... ok
test reconcile::tests::reconcile_twice_is_idempotent_on_same_backend ... ok
test relay_watchman::tests::test_addressed_to_prefers_addressed_to_and_trims ... ok
test relay_watchman::tests::test_claim_by_nonlocal_agent_never_nudges ... ok
test relay_watchman::tests::test_counter_field_variation_changes_nothing ... ok
test relay_watchman::tests::test_fresh_or_missing_heartbeat_never_nudges ... ok
test relay_watchman::tests::test_inputs_never_mutated ... ok
test relay_watchman::tests::test_loop_cycle_skips_malformed_input ... ok
test relay_watchman::tests::test_no_wake_for_done_or_malformed_or_unknown ... ok
test relay_watchman::tests::test_no_wake_for_other_agent_awake_or_unaddressed ... ok
test relay_watchman::tests::test_normalize_agents_list_form_and_map_key_wins ... ok
test relay_watchman::tests::test_nudge_refires_only_when_heartbeat_refreshes ... ok
test relay_watchman::tests::test_once_malformed_input_exits_2_with_no_event ... ok
test relay_watchman::tests::test_once_missing_files_read_as_empty ... ok
test relay_watchman::tests::test_once_prints_event_and_second_run_is_silent ... ok
test relay_watchman::tests::test_once_reusing_state_file_is_silent ... ok
test relay_watchman::tests::test_open_job_wakes_sleeping_local_agent ... ok
test relay_watchman::tests::test_second_tick_with_merged_ledger_is_silent ... ok
test relay_watchman::tests::test_silent_and_unknown_statuses_never_ring ... ok
test relay_watchman::tests::test_stale_boundary_is_strict ... ok
test relay_watchman::tests::test_stale_heartbeat_nudges_on_same_cycle ... ok
test relay_watchman::tests::test_state_rung_non_string_entries_filtered ... ok
test relay_watchman::tests::test_unregistered_agent_is_not_local ... ok
test relay_watchman::tests::test_validate_args_rejects_bad_timing ... ok
test relay_watchman::tests::test_wake_via_legacy_to_field ... ok
test thresholds::tests::defaults_match_locked_python_values ... ok
test thresholds::tests::parse_env_int_below_minimum_falls_back_at_minimum_passes ... ok
test thresholds::tests::parse_env_int_unset_blank_unparseable_fall_back ... ok
test watchdog::tests::alert_dedupe_test_two_ticks_yield_same_dedupe_key ... ok
test watchdog::tests::alert_record_writer_test_tick_output_feeds_emit_sink ... ok
test watchdog::tests::announce_test_announcement_flattens_multiline_explanation ... ok
test watchdog::tests::announce_test_cli_announce_prints_line_only_with_flag ... ok
test watchdog::tests::announce_test_critical_fixture_yields_exactly_one_announcement ... ok
test watchdog::tests::announce_test_format_gate_rejects_warning_info_and_bad_input ... ok
test watchdog::tests::announce_test_info_record_yields_no_announcement ... ok
test watchdog::tests::announce_test_no_callback_means_held_not_posted ... ok
test watchdog::tests::announce_test_warning_fixture_yields_no_announcement ... ok
test watchdog::tests::attempt_exhaustion_test_budget_of_one_warns_at_zero_then_fails_at_one ... ok
test watchdog::tests::attempt_exhaustion_test_claimed_job_at_max_minus_one_warns ... ok
test watchdog::tests::attempt_exhaustion_test_done_job_at_max_yields_no_alert ... ok
test watchdog::tests::attempt_exhaustion_test_failed_final_job_at_max_yields_critical ... ok
test watchdog::tests::attempt_exhaustion_test_no_budget_yields_no_alert_at_any_attempt_count ... ok
test watchdog::tests::attempt_exhaustion_test_string_form_attempts_match_redis_hashes ... ok
test watchdog::tests::attempt_exhaustion_test_walk_produces_warning_at_max_minus_one_then_critical ... ok
test watchdog::tests::cli_test_loop_runs_bounded_ticks_then_exits_zero ... ok
test drills::watchman_service_cli::tests::test_drill_phase3_unit_execstart ... ok
test watchdog::tests::cli_test_neither_mode_is_an_error ... ok
test watchdog::tests::cli_test_once_on_quiet_fixture_exits_zero ... ok
test watchdog::tests::cli_test_once_with_bad_snapshot_file_exits_one ... ok
test watchdog::tests::cli_test_once_without_snapshot_uses_quiet_snapshot ... ok
test watchdog::tests::clock_skew_test_detector_ages_use_injected_clock_not_wall_clock ... ok
test watchdog::tests::clock_skew_test_malformed_server_time_falls_back_to_wall_clock ... ok
test watchdog::tests::clock_skew_test_explicit_now_beats_server_time ... ok
test watchdog::tests::clock_skew_test_resolve_tick_now_reports_its_source ... ok
test watchdog::tests::clock_skew_test_server_time_beats_skewed_wall_clock ... ok
test watchdog::tests::clock_skew_test_string_and_time_pair_server_time_forms ... ok
test watchdog::tests::clock_skew_test_wall_clock_fallback_when_no_server_time ... ok
test watchdog::tests::dead_dep_test_blocked_dep_yields_one_critical_alert ... ok
test watchdog::tests::dead_dep_test_claimed_job_with_blocked_dep_also_alerts ... ok
test watchdog::tests::dead_dep_test_done_job_with_blocked_dep_yields_no_alert ... ok
test watchdog::tests::dead_dep_test_failed_final_dep_also_dead ... ok
test watchdog::tests::dead_dep_test_job_with_no_deps_yields_no_alert ... ok
test watchdog::tests::dead_dep_test_live_dep_yields_no_alert ... ok
test watchdog::tests::dead_dep_test_missing_dep_is_not_dead_dep ... ok
test watchdog::tests::dead_dep_test_two_dead_deps_yield_one_alert_each ... ok
test watchdog::tests::dead_dep_test_unblocked_dep_stops_firing ... ok
test watchdog::tests::detector_coverage_test_attempt_exhaustion_positive_and_negative ... ok
test watchdog::tests::detector_coverage_test_dead_dep_positive_and_negative ... ok
test watchdog::tests::detector_coverage_test_budget_warning_positive_and_negative ... ok
test watchdog::tests::detector_coverage_test_file_collision_positive_and_negative ... ok
test watchdog::tests::detector_coverage_test_lease_risk_positive_and_negative ... ok
test watchdog::tests::detector_coverage_test_presence_stall_positive_and_negative ... ok
test watchdog::tests::detector_coverage_test_missing_dep_positive_and_negative ... ok
test watchdog::tests::detector_coverage_test_progress_stall_positive_and_negative ... ok
test watchdog::tests::detector_coverage_test_rejected_dispatch_positive_and_negative ... ok
test watchdog::tests::detector_coverage_test_registry_runs_all_nine_detectors ... ok
test watchdog::tests::detector_coverage_test_silent_room_positive_and_negative ... ok
test watchdog::tests::env_override_test_bad_env_values_fall_back_to_defaults ... ok
test watchdog::tests::env_override_test_defaults_unchanged_without_env ... ok
test watchdog::tests::env_override_test_env_override_changes_silent_room_behavior ... ok
test watchdog::tests::env_override_test_env_override_changes_presence_stall_behavior ... ok
test watchdog::tests::file_collision_test_claimed_overlapping_done_branch_yields_alert ... ok
test watchdog::tests::env_override_test_env_override_changes_tick_cap_behavior ... ok
test watchdog::tests::file_collision_test_claimed_overlapping_done_without_branch_yields_no_alert ... ok
test watchdog::tests::file_collision_test_disjoint_files_yield_no_alert ... ok
test watchdog::tests::file_collision_test_duplicate_path_on_one_job_counts_once ... ok
test watchdog::tests::file_collision_test_job_with_no_files_yields_no_alert ... ok
test watchdog::tests::file_collision_test_open_job_overlapping_claimed_yields_no_alert ... ok
test watchdog::tests::file_collision_test_overlapping_claimed_pair_yields_one_critical_alert ... ok
test watchdog::tests::file_collision_test_list_form_files_are_checked_too ... ok
test watchdog::tests::file_collision_test_removing_the_overlap_clears_the_alert ... ok
test watchdog::tests::journal_test_failures_group_by_unit_with_count_and_truncation ... ok
test watchdog::tests::file_collision_test_two_shared_paths_yield_one_alert_each ... ok
test watchdog::tests::journal_test_parse_skips_blank_bad_and_unitless_lines ... ok
test watchdog::tests::journal_test_relay_err_priority_is_a_failure ... ok
test watchdog::tests::journal_test_systemd_failure_phrasing_fires_at_benign_priority ... ok
test watchdog::tests::journal_test_relay_info_and_non_relay_failures_are_quiet ... ok
test watchdog::tests::journal_test_value_and_text_entry_shapes ... ok
test watchdog::tests::journal_test_watch_tick_emit_failure_does_not_hide_next_unit ... ok
test watchdog::tests::json_test_last_activity_prefers_progress_fields_in_order ... ok
test watchdog::tests::json_test_snapshot_from_json_text_and_non_object_rejected ... ok
test watchdog::tests::lease_risk_test_already_expired_lease_is_not_a_warning ... ok
test watchdog::tests::lease_risk_test_explicit_heartbeat_beats_derived_heartbeat ... ok
test watchdog::tests::lease_risk_test_job_without_lease_until_never_invents_an_expiry ... ok
test watchdog::tests::lease_risk_test_lease_far_from_expiry_is_not_a_risk ... ok
test watchdog::tests::lease_risk_test_near_expiry_with_quiet_heartbeat_yields_warning ... ok
test watchdog::tests::lease_risk_test_recent_heartbeat_with_short_lease_is_not_a_risk ... ok
test watchdog::tests::lease_risk_test_requeued_job_stops_firing ... ok
test watchdog::tests::lease_risk_test_walk_on_claimer_lease_still_warned ... ok
test watchdog::tests::locked_thresholds_test_int022_locked_threshold_table ... ok
test watchdog::tests::missing_dep_test_claimed_job_with_dangling_dep_also_alerts ... ok
test watchdog::tests::missing_dep_test_dangling_dep_yields_one_critical_alert ... ok
test watchdog::tests::missing_dep_test_dead_dep_and_missing_dep_do_not_cross_fire ... ok
test watchdog::tests::missing_dep_test_done_job_with_dangling_dep_yields_no_alert ... ok
test watchdog::tests::missing_dep_test_existing_dep_yields_no_alert ... ok
test watchdog::tests::missing_dep_test_job_with_no_deps_yields_no_alert ... ok
test watchdog::tests::missing_dep_test_list_form_deps_are_checked_too ... ok
test watchdog::tests::missing_dep_test_posting_the_missing_job_clears_the_alert ... ok
test watchdog::tests::missing_dep_test_two_dangling_deps_yield_one_alert_each ... ok
test watchdog::tests::presence_stall_test_absent_nick_with_no_claimed_job_is_not_a_stall ... ok
test watchdog::tests::presence_stall_test_explicit_progress_timestamp_beats_claim_time ... ok
test watchdog::tests::presence_stall_test_fresh_claimed_job_is_not_a_stall ... ok
test watchdog::tests::presence_stall_test_job_with_no_timestamp_never_invents_an_age ... ok
test watchdog::tests::presence_stall_test_cli_once_on_stall_fixture_reports_one_alert ... ok
test watchdog::tests::presence_stall_test_present_nick_with_idle_job_is_not_presence_stall ... ok
test watchdog::tests::presence_stall_test_stall_fixture_yields_exactly_one_alert_naming_all ... ok
test watchdog::tests::presence_stall_test_walk_on_claimer_not_in_caps_is_not_presence_stall ... ok
test watchdog::tests::progress_stall_test_absent_nick_yields_presence_stall_not_progress_stall ... ok
test watchdog::tests::progress_stall_test_fresh_progress_is_not_a_stall ... ok
test watchdog::tests::progress_stall_test_heartbeat_but_no_progress_yields_exactly_one ... ok
test watchdog::tests::progress_stall_test_job_with_no_timestamp_never_invents_an_age ... ok
test watchdog::tests::progress_stall_test_old_claim_with_no_progress_note_is_a_stall ... ok
test watchdog::tests::progress_stall_test_unclaimed_job_is_not_a_stall ... ok
test watchdog::tests::progress_stall_test_one_alert_per_job_not_per_detector ... ok
test watchdog::tests::progress_stall_test_walk_on_claimer_not_in_caps_is_not_progress_stall ... ok
test watchdog::tests::render_test_unknown_template_panics_like_python_value_error - should panic ... ok
test watchdog::tests::restart_note_test_missing_nick_or_job_is_an_error ... ok
test watchdog::tests::restart_note_test_worker_restart_is_info_not_a_stall ... ok
test watchdog::tests::self_beat_test_beat_called_once_per_tick_even_when_quiet ... ok
test watchdog::tests::self_beat_test_beat_called_once_when_alerts_fire ... ok
test watchdog::tests::self_beat_test_no_beat_callback_writes_nothing_and_raises_nothing ... ok
test watchdog::tests::self_beat_test_failing_beat_never_fails_the_tick_or_hides_alerts ... ok
test watchdog::tests::severity_mapping_test_every_detector_emits_its_table_severity ... ok
test watchdog::tests::severity_mapping_test_mapping_matches_the_lane_plan_rule ... ok
test watchdog::tests::severity_mapping_test_table_values_are_valid_severities ... ok
test watchdog::tests::silent_room_test_dashboard_severity_mapping_silent_room_is_info ... ok
test watchdog::tests::severity_mapping_test_table_covers_every_detector_kind ... ok
test watchdog::tests::silent_room_test_fresh_message_inside_threshold_yields_no_record ... ok
test watchdog::tests::silent_room_test_latest_message_sets_the_clock ... ok
test watchdog::tests::silent_room_test_message_after_tick_time_yields_no_record ... ok
test watchdog::tests::silent_room_test_multiple_claimed_jobs_yield_one_room_record ... ok
test watchdog::tests::silent_room_test_no_claimed_jobs_yields_no_record ... ok
test watchdog::tests::silent_room_test_room_name_scopes_dedupe_key ... ok
test watchdog::tests::silent_room_test_no_timestamped_messages_yields_no_record ... ok
test watchdog::tests::silent_room_test_silence_exactly_at_threshold_yields_no_record ... ok
test watchdog::tests::silent_room_test_silent_room_yields_info_record_only ... ok
test watchdog::tests::spark_polish_test_emitted_alert_carries_polished_text ... ok
test watchdog::tests::spark_polish_test_empty_spark_reply_keeps_template_text ... ok
test watchdog::tests::spark_polish_test_polish_helper_toggle_off_and_failure ... ok
test watchdog::tests::spark_polish_test_quiet_snapshot_with_polish_client_calls_nothing ... ok
test watchdog::tests::spark_polish_test_spark_failure_keeps_template_text ... ok
test watchdog::tests::spark_polish_test_toggle_off_keeps_template_text ... ok
test watchdog::tests::spark_polish_test_toggle_on_uses_polished_text ... ok
test watchdog::tests::tick_budget_test_1500_message_tick_completes_with_correct_verdict ... ok
test watchdog::tests::tick_budget_test_cap_keeps_newest_and_reports_the_drop ... ok
test watchdog::tests::tick_budget_test_cap_under_the_limit_passes_through_unchanged ... ok
test watchdog::tests::tick_budget_test_cap_with_zero_max_keeps_nothing ... ok
test watchdog::tests::tick_budget_test_cap_twice_accumulates_the_drop_count ... ok
test watchdog::tests::tick_budget_test_paginate_rejects_non_positive_page_size ... ok
test watchdog::tests::tick_budget_test_paginate_yields_page_sized_chunks_oldest_first ... ok
test watchdog::tests::tick_budget_test_tick_cap_never_hides_a_job_detector_verdict ... ok
test watchdog::tests::tick_budget_test_cli_once_on_1500_message_snapshot_exits_zero ... ok
test watchdog::tests::tick_test_a_crashing_detector_does_not_blind_the_loop ... ok
test watchdog::tests::tick_test_emit_receives_each_alert_in_order ... ok
test watchdog::tests::tick_test_healthy_busy_snapshot_also_yields_zero_for_now ... ok
test watchdog::tests::tick_test_missing_sections_are_empty_not_an_error ... ok
test watchdog::tests::tick_test_quiet_snapshot_yields_zero_alerts ... ok
test watchdog::tests::walk_on_tracking_test_malformed_sections_yield_no_crash ... ok
test watchdog::tests::walk_on_tracking_test_no_timestamp_never_invents_an_age ... ok
test watchdog::tests::walk_on_tracking_test_open_job_is_not_tracked ... ok
test watchdog::tests::walk_on_tracking_test_present_walk_on_is_still_tracked ... ok
test watchdog::tests::walk_on_tracking_test_registered_claimer_is_not_tracked ... ok
test watchdog::tests::walk_on_tracking_test_stall_detection_still_works_alongside_tracking ... ok
test watchdog::tests::walk_on_tracking_test_tracking_is_not_an_alert ... ok
test watchdog::tests::walk_on_tracking_test_unknown_claimer_yields_tracking_record ... ok
test watchdog_load_check::tests::test_check_passes_with_exact_counts_mirrors_python ... ok
test watchdog_load_check::tests::test_integration_surface_values ... ok
test watchdog_load_check::tests::test_check_twice_isolated_mirrors_python ... ok
test watchdog_load_check::tests::test_table_renders_counts_and_budgets_mirrors_python ... ok
test watchdog_load_check::tests::test_tick1_wrong_kind_split_fails ... ok
test watchdog_load_check::tests::test_tick2_created_at_moved_fails_and_tick3_alert_fails ... ok
test watchman_boot::tests::test_arrivals_ring_and_only_arrivals_ring ... ok
test watchman_boot::tests::test_duplicate_input_rings_once ... ok
test watchman_boot::tests::test_corrupted_counter_changes_nothing ... ok
test watchman_boot::tests::test_malformed_records_never_ring_and_never_crash ... ok
test watchman_boot::tests::test_mismatch_brief_lines_name_ids ... ok
test watchman_boot::tests::test_inputs_never_mutated ... ok
test watchman_boot::tests::test_note_carries_no_push_or_announcement ... ok
test watchman_boot::tests::test_pre_window_post_boot_live_lease_and_done_do_not_ring ... ok
test watchman_boot::tests::test_second_cycle_with_ledger_rings_nothing_new ... ok
test watchman_boot::tests::test_sweep_mismatch_named_never_fudged ... ok
test watchman_boot::tests::test_sweep_reconciliation_agrees ... ok
test watchman_boot::tests::test_window_boundaries ... ok
test watchman_bridge::tests::test_absent_machine_unjudged ... ok
test watchman_bridge::tests::test_bridge_record_reads_alive_then_dark ... ok
test watchman_bridge::tests::test_inputs_never_mutated ... ok
test watchman_bridge::tests::test_malformed_events_and_prior_ignored ... ok
test watchman_bridge::tests::test_malformed_input_contained_per_machine ... ok
test watchman_bridge::tests::test_no_restart_fact_escalates_once ... ok
test watchman_bridge::tests::test_nudge_is_not_a_bell ... ok
test watchman_bridge::tests::test_prior_bell_kept_without_new_wake ... ok
test watchman_bridge::tests::test_recovery_then_second_episode_realerts ... ok
test watchman_bridge::tests::test_ring_alive_quiet_unknown_no_journal ... ok
test watchman_bridge::tests::test_silence_journals_dark_and_restart_only_for_dark ... ok
test watchman_bridge::tests::test_snapshot_skips_non_dict_records ... ok
test watchman_bridge::tests::test_wake_advances_bell ... ok
test watchman_bridge::tests::test_unknown_constant_matches_watch ... ok
test watchman_cycle::tests::test_empty_machines_never_calls_runner ... ok
test watchman_cycle::tests::test_false_pair_is_failed_not_runner_error ... ok
test watchman_cycle::tests::test_garbage_string_is_bad_return_unjudged ... ok
test watchman_cycle::tests::test_list_pair_accepted_as_success ... ok
test watchman_cycle::tests::test_non_callable_fails_every_machine ... ok
test watchman_cycle::tests::test_none_machines_is_empty_cycle ... ok
test watchman_cycle::tests::test_panicking_runner_is_contained_as_panic ... ok
test watchman_cycle::tests::test_priors_and_journal_unchanged ... ok
test watchman_cycle::tests::test_ring_and_quiet_clean_diagnostics ... ok
test watchman_cycle::tests::test_raising_runner_carries_prior_and_names_error ... ok
test watchman_cycle::tests::test_short_pair_is_bad_return ... ok
test watchman_cycle::tests::test_string_machines_is_one_machine ... ok
test watchman_cycle::tests::test_truthy_one_is_not_true ... ok
test watchman_loop::tests::test_failed_run_carries_prior_and_ages_dark ... ok
test watchman_loop::tests::test_failed_run_stdout_ignored ... ok
test watchman_loop::tests::test_fresh_ring_recovers_after_failed_runs ... ok
test watchman_loop::tests::test_inputs_never_mutated ... ok
test watchman_loop::tests::test_junk_and_non_object_lines_counted ... ok
test watchman_loop::tests::test_malformed_run_reads_as_failed_run ... ok
test watchman_loop::tests::test_malformed_stdout_contained_per_machine ... ok
test watchman_loop::tests::test_no_prior_failure_unjudged ... ok
test watchman_loop::tests::test_non_string_input_is_one_malformed ... ok
test watchman_loop::tests::test_successful_ring_and_quiet ... ok
test watchman_loop::tests::test_open_episode_stays_silent_on_repeat_failure ... ok
test watchman_loop::tests::test_valid_lines_parse ... ok
test watchman_runner::tests::test_argv_distinct_per_machine ... ok
test watchman_runner::tests::test_bad_argv ... ok
test watchman_runner::tests::test_bad_machine_yields_none ... ok
test watchman_runner::tests::test_default_argv_shape ... ok
test watchman_runner::tests::test_failed_run_carries_prior_bell_stripped ... ok
test drills::watchman_runner::tests::test_drill_phase1_real_once_rings ... ok
test watchman_runner::tests::test_not_found ... ok
test drills::watchman_service::tests::test_drill_passes ... ok
test watchman_runner::tests::test_runner_never_raises ... ok
test drills::watchman_service::tests::test_drill_phase6_default_path_rings ... ok
test drills::watchman_service_cli::tests::test_drill_phase1_plain_command ... ok
test watchman_service::tests::test_bad_cycle_return_contained ... ok
test drills::watchman_runner::tests::test_drill_phase2_full_cycle ... ok
test watchman_service::tests::test_cli_parsing_bare_and_empty_machines ... ok
test watchman_service::tests::test_inputs_never_mutated ... ok
test watchman_service::tests::test_negative_interval_means_no_sleep_delay ... ok
test watchman_service::tests::test_priors_and_journal_carry_across_cycles ... ok
test watchman_service::tests::test_raising_callback_and_stop_contained ... ok
test watchman_service::tests::test_raising_clock_contained ... ok
test watchman_service::tests::test_raising_cycle_contained_and_loop_recovers ... ok
test watchman_runner::tests::test_missing_snapshots_are_quiet_not_failed ... ok
test watchman_service::tests::test_should_stop_stops_without_sleep ... ok
test watchman_service::tests::test_sleep_only_between_cycles ... ok
test watchman_service::tests::test_unit_directives_match_unit_contract ... ok
test watchman_runner::tests::test_success_returns_stdout ... ok
test watchman_service::tests::test_zero_cycles_runs_nothing ... ok
test watchman_watch::tests::test_beyond_repair_yields_exactly_one_valid_escalation ... ok
test watchman_watch::tests::test_brief_and_board_lines ... ok
test watchman_watch::tests::test_default_push_builder_gates ... ok
test watchman_watch::tests::test_escalated_this_episode_quirk_other_machine_counts ... ok
test watchman_watch::tests::test_escalation_payload_built_never_sent ... ok
test watchman_watch::tests::test_killed_watchman_flags_crew_dark_in_one_tick ... ok
test watchman_watch::tests::test_malformed_inputs_never_crash ... ok
test watchman_watch::tests::test_revival_yields_recovered_and_still_no_escalation ... ok
test watchman_watch::tests::test_second_death_after_recovery_realerts ... ok
test watchman_runner::tests::test_nonzero_discards_partial_stdout ... ok
test watchman_watch::tests::test_stale_bell_reads_dead_and_fresh_bell_reads_alive ... ok
test watchman_watch::tests::test_tick_never_mutates_inputs ... ok
test watchman_watch::tests::test_unknown_machine_yields_nothing_and_reads_unknown ... ok
test drills::watchman_service_cli::tests::test_drill_passes ... ok
test watchman_service::tests::test_service_main_runs_one_cycle_on_real_snapshots ... ok
test watchman_runner::tests::test_real_cycle_rings_and_stays_quiet ... ok
test watchman_service::tests::test_default_path_rings_on_real_snapshots ... ok
test watchman_runner::tests::test_timeout ... ok
test drills::watchman_runner::tests::test_drill_phase3_hanging_timeout ... ok
test drills::watchman_runner::tests::test_drill_passes ... ok

test result: ok. 379 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.93s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-a045f759d8da67f0)

running 16 tests
test empty_input_paginates_to_no_pages ... ok
test a_missing_events_string_counts_as_one_malformed_line ... ok
test a_stale_bell_is_dead_and_a_fresh_one_is_alive ... ok
test a_missing_record_is_unknown ... ok
test alive_without_a_bell_is_unknown ... ok
test an_older_wake_never_moves_the_prior_bell_backwards ... ok
test duplicate_wake_events_at_the_same_time_keep_the_same_bell ... ok
test an_explicit_dead_flag_wins_over_a_fresh_bell ... ok
test board_states_come_out_in_machine_name_order ... ok
test duplicate_sweep_ids_collapse_and_do_not_create_extra_mismatches ... ok
test empty_text_parses_to_zero_events_and_zero_malformed ... ok
test maximum_input_paginates_into_full_pages_then_the_remainder ... ok
test malformed_event_lines_are_counted_without_losing_the_good_ones ... ok
test out_of_order_wakes_keep_the_latest_bell ... ok
test relay_timing_boundaries_are_inclusive ... ok
test maximum_page_size_larger_than_input_is_one_page ... ok

test result: ok. 16 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/error_paths.rs (target/debug/deps/error_paths-4ca6c1b149c7b752)

running 19 tests
test an_empty_hash_map_never_produces_a_blocked_reason ... ok
test blocked_reasons_are_cut_at_200_characters ... ok
test a_clean_report_is_not_default_when_redis_answers ... ok
test env_int_range_refuses_outside_both_bounds ... ok
test env_values_below_the_minimum_fall_back ... ok
test paginate_refuses_a_zero_page_size ... ok
test paginate_refuses_a_negative_page_size ... ok
test parse_job_id_refuses_output_with_no_job_line ... ok
test parse_job_id_takes_the_first_job_line ... ok
test parse_json_refuses_a_truncated_document ... ok
test parse_json_refuses_trailing_characters ... ok
test reconcile_stops_when_the_backend_is_unreachable ... ok
test reconcile_tolerates_sweep_and_prune_failures_and_still_reads_jobs ... ok
test relay_args_refuse_a_negative_stale_window ... ok
test relay_args_refuse_a_non_positive_interval ... ok
test relay_once_exits_2_on_a_malformed_input_file ... ok
test service_args_refuse_a_missing_cycles_value ... ok
test service_args_refuse_an_unknown_flag ... ok
test unknown_explanation_template_panics - should panic ... ok

test result: ok. 19 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s

     Running tests/gap_close.rs (target/debug/deps/gap_close-9bf33bd1402b922d)

running 12 tests
test a_number_too_large_for_i64_falls_back ... ok
test a_float_is_not_an_int_and_falls_back ... ok
test bad_env_values_never_invent_a_threshold ... ok
test announcement_newlines_are_flattened_to_one_line ... ok
test env_int_range_stays_inside_the_budget_band ... ok
test every_detector_kind_has_one_canonical_severity ... ok
test watchdog_thresholds_read_overrides_and_keep_defaults_for_the_rest ... ok
test the_detector_registry_has_the_ten_registered_detectors ... ok
test whitespace_is_stripped_before_parsing ... ok
test only_critical_alerts_announce_and_the_id_prefers_the_explicit_one ... ok
test the_budget_warning_band_is_warning_at_the_edge_but_never_at_the_cap ... ok
test locked_defaults_are_the_documented_numbers ... ok

test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running unittests src/lib.rs (target/debug/deps/os_worker-f5e381dcabbdfe98)

running 96 tests
test tests::accept_parse_accept_cases ... ok
test tests::drill_kill_worker::test_sweep_leaves_unexpired_and_open_jobs_alone ... ok
test tests::drill_kill_worker::test_drill_passes_and_reports_the_stall_alert ... ok
test tests::drill_kill_worker::test_cli_main_exits_zero_and_prints_pass ... ok
test tests::driver_contract::test_c3_empty_files_rejected ... ok
test tests::driver_contract::test_c2_unparseable_accept_rejected ... ok
test tests::driver_contract::test_c1_unsigned_spec_rejected_and_nothing_spawns ... ok
test tests::driver_contract::test_docs_pin_contract_and_checklist ... ok
test tests::driver_heartbeat_bridge::test_bridge_mapping_does_not_mutate ... ok
test tests::driver_contract::test_c10_no_bus_or_redis_imports ... ok
test tests::driver_heartbeat_bridge::test_drill_and_eval_exist ... ok
test tests::driver_heartbeat_bridge::test_fresh_heartbeat_no_alert ... ok
test tests::driver_heartbeat_bridge::test_no_em_dash_in_new_files ... ok
test tests::driver_heartbeat_bridge::test_stale_absent_is_presence_stall_only ... ok
test tests::driver_heartbeat_bridge::test_stale_present_is_progress_stall_only ... ok
test tests::driver_heartbeat_bridge::test_template_joins_driver_slice ... ok
test tests::driver_heartbeat_bridge::test_tick_leaves_job_claimed ... ok
test tests::driver_heartbeat_bridge::test_watchdog_has_no_driver_special_casing ... ok
test tests::driver_muse::test_argv_shape_and_extra_args ... ok
test tests::driver_muse::test_c10_no_bus_or_redis_imports ... ok
test tests::driver_muse::test_c1_unsigned_spec_rejected_and_nothing_spawns ... ok
test tests::driver_muse::test_c2_unparseable_accept_rejected ... ok
test tests::driver_muse::test_c3_empty_files_rejected ... ok
test tests::accept_verify_from_disk_true_false_and_empty ... ok
test tests::driver_contract::test_c8_unowned_changes_visible ... ok
test tests::driver_contract::test_c4_heartbeat_shape_and_before_start ... ok
test tests::driver_contract::test_c9_stop_after_finish_safe_and_artifacts_stable ... ok
test tests::driver_contract::test_c6_changed_files_lists_new_file_not_log ... ok
test tests::driver_contract::test_start_twice_rejected_and_spec_defaults ... ok
test tests::driver_contract::test_c7_acceptance_from_disk_true_and_false ... ok
test tests::driver_muse::test_missing_binary_refused_before_spawning ... ok
test tests::driver_muse::test_prompt_carries_work_not_signature ... ok
test tests::driver_muse::test_c4_heartbeat_shape_and_before_start ... ok
test tests::driver_muse::test_c7_acceptance_from_disk_true_and_false ... ok
test tests::driver_muse::test_runner_refuses_unsigned_spec_with_exit_2 ... ok
test tests::driver_muse::test_prompt_file_lives_outside_workdir_and_is_cleaned ... ok
test tests::driver_stall::test_demo_env_sets_one_minute_window ... ok
test tests::driver_stall::test_demo_window_fires_at_61s_and_quiet_at_30s ... ok
test tests::driver_stall::test_eval_exists ... ok
test tests::driver_stall::test_drill_exists_with_all_phases ... ok
test tests::driver_stall::test_no_em_dash_in_new_files ... ok
test tests::driver_stall::test_tick_leaves_both_driver_jobs_claimed ... ok
test tests::driver_stall::test_spec_records_drill ... ok
test tests::driver_stall::test_wedged_driver_no_presence_stall ... ok
test tests::driver_stall::test_wedged_driver_progress_stall ... ok
test tests::driver_stall::test_wedged_worker_same_alert ... ok
test tests::driver_supervision::test_drill_exists_with_all_phases ... ok
test tests::driver_supervision::test_driver_presence_stall ... ok
test tests::driver_supervision::test_eval_exists ... ok
test tests::driver_supervision::test_present_driver_no_alert_and_fresh_no_alert ... ok
test tests::driver_supervision::test_no_em_dash_in_new_files ... ok
test tests::driver_supervision::test_slice_values ... ok
test tests::driver_supervision::test_tick_leaves_driver_job_claimed ... ok
test tests::hmac_sha256_matches_python_vectors ... ok
test tests::driver_supervision::test_spec_records_slice_and_values ... ok
test tests::json_parse_and_render_spec ... ok
test tests::sha256_known_vectors ... ok
test tests::test_thresholds_from_env_fallback_rules ... ok
test tests::uplink::test_backoff_sequence ... ok
test tests::uplink::test_record_failure_and_success ... ok
test tests::uplink::test_tick_crew_mode_unsigned_refused_stays_pending ... ok
test tests::uplink::test_tick_connected_intake_signed_and_unsigned ... ok
test tests::uplink::test_tick_drain_invalid_dropped_not_requeued ... ok
test tests::uplink::test_tick_duplicate_seen_and_input_untouched ... ok
test tests::uplink::test_tick_disconnected_queues_and_duplicates ... ok
test tests::uplink::test_tick_rejects_invalid_in_either_mode ... ok
test tests::uplink::test_validate_order_reasons ... ok
test tests::worker_loop::test_caps_normalization_and_matching ... ok
test tests::worker_loop::test_parse_announcement_cases ... ok
test tests::worker_loop::test_skipped_blocked_crash_and_error_paths ... ok
test tests::worker_loop::test_truncation_rules_500_200_400 ... ok
test tests::worker_loop::test_undelivered_dispatched_job_stays_open ... ok
test tests::worker_loop::test_dispatched_chain_flows_through_worker_loop ... ok
test tests::worker_loop::test_worker_heartbeat_renews_dispatched_claim ... ok
test tests::worker_units_and_slice::test_env_files_required_and_optional ... ok
test tests::worker_units_and_slice::test_build_scripts_carry_template_but_never_auto_enable ... ok
test tests::worker_units_and_slice::test_exec_runs_mos_worker_without_dm_secret ... ok
test tests::worker_units_and_slice::test_instance_name_is_the_nick ... ok
test tests::worker_units_and_slice::test_no_em_dash_in_worker_unit ... ok
test tests::worker_units_and_slice::test_no_em_dash_in_workers_slice_files ... ok
test tests::worker_units_and_slice::test_readme_section_names_both_owed_items ... ok
test tests::worker_units_and_slice::test_service_identity_slice_restart ... ok
test tests::worker_units_and_slice::test_template_exists_and_unit_ordering ... ok
test tests::worker_units_and_slice::test_workers_drill_exists_with_host_gate ... ok
test tests::worker_units_and_slice::test_workers_eval_note_exists ... ok
test tests::worker_units_and_slice::test_spec_records_template_as_landed ... ok
test tests::worker_units_and_slice::test_workers_slice_values ... ok
test tests::worker_units_and_slice::test_workers_spec_records_values ... ok
test tests::driver_heartbeat_bridge::test_driver_heartbeat_shape ... ok
test tests::driver_muse::test_c9_stop_after_finish_safe_and_artifacts_stable ... ok
test tests::driver_muse::test_runner_prints_artifacts_json ... ok
test tests::driver_muse::test_child_output_streamed_into_heartbeats ... ok
test tests::driver_muse::test_c8_unowned_changes_visible ... ok
test tests::driver_muse::test_c6_changed_files_lists_new_file_not_log ... ok
test tests::driver_contract::test_c5_stop_kills_sleeping_child ... ok
test tests::driver_muse::test_c5_stop_kills_sleeping_child ... ok

test result: ok. 96 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.34s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-26e090e2ab6887b7)

running 11 tests
test announcement_parser_requires_a_digit_id_and_a_trailing_req_clause ... ok
test announcements_only_emit_for_critical_and_flatten_newlines ... ok
test duplicate_uplink_order_is_reported_and_the_state_does_not_grow ... ok
test empty_input_accept_text_verifies_true_with_one_note ... ok
test lease_expiry_boundary_requeues_and_open_jobs_are_untouched ... ok
test duplicate_ini_keys_take_the_last_value_and_multi_keeps_all ... ok
test maximum_input_note_is_cut_to_the_limit_on_char_boundaries ... ok
test out_of_order_pending_drains_before_new_orders ... ok
test crew_mode_without_a_key_refuses_intake_but_keeps_the_order ... ok
test disconnected_orders_queue_and_the_backoff_doubles ... ok
test prompt_carries_the_work_but_never_the_signature ... ok

test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/error_paths.rs (target/debug/deps/error_paths-4f73f8e5574dabfc)

running 15 tests
test new_refuses_a_missing_workdir ... ok
test validate_spec_names_every_missing_field ... ok
test start_refuses_an_empty_command_without_a_child ... ok
test start_refuses_an_unsigned_spec_before_spawning ... ok
test parse_accept_refuses_every_bad_line_shape ... ok
test muse_refuses_a_binary_that_is_not_on_path ... ok
test run_driver_maps_bad_json_and_missing_fields_to_errors ... ok
test every_operation_before_start_is_not_started ... ok
test validate_spec_refuses_unparseable_accept_lines ... ok
test validate_spec_refuses_unsigned_and_blank_signature ... ok
test verify_accept_reports_a_parse_failure_as_one_result ... ok
test start_refuses_a_command_that_cannot_spawn ... ok
test wait_child_reports_a_signal_as_a_negative_code ... ok
test a_second_start_is_refused_even_after_the_child_exited ... ok
test wait_child_times_out_when_asked_to ... ok

test result: ok. 15 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.06s

     Running tests/gap_close.rs (target/debug/deps/gap_close-e10821a40f695649)

running 9 tests
test json_escape_covers_quotes_backslashes_and_controls ... ok
test parse_json_reads_nested_values_and_preserves_number_spelling ... ok
test empty_state_is_the_default_state ... ok
test sha256_matches_the_fips_vectors ... ok
test apply_heartbeat_truncates_toward_zero_like_python_int ... ok
test a_snapshot_never_yields_both_stall_kinds_for_one_job ... ok
test hmac_sha256_matches_rfc_4231_case_one ... ok
test artifacts_split_owned_from_unowned_changes_and_ignore_the_log ... ok
test stopped_run_wins_over_the_exit_code_in_the_artifacts_status ... ok

test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s

     Running unittests src/lib.rs (target/debug/deps/os_workspace-652853d3925fa0ec)

running 39 tests
test tests::attach_rejects_non_object ... ok
test tests::deposit_default_author_is_unknown ... ok
test tests::deposit_first_version ... ok
test tests::deposit_nested_name ... ok
test tests::attach_preserves_existing_artifacts ... ok
test tests::deposit_identical_is_noop ... ok
test tests::gitops_reject_branch ... ok
test tests::cli_full_flow_and_errors ... ok
test tests::attach_two_deposits_mirrors_caller_test ... ok
test tests::deposit_unicode_name_and_author_roundtrip ... ok
test tests::cli_read_version_flag ... ok
test tests::binary_bytes_survive_versioned_read ... ok
test tests::json_compact_serialization_is_sorted ... ok
test tests::json_parse_escapes_and_surrogate_pairs ... ok
test tests::json_parse_numbers_nesting_and_literals ... ok
test tests::json_parse_rejects_malformed_escapes_and_surrogates ... ok
test tests::json_rejects_trailing_garbage ... ok
test tests::json_roundtrip ... ok
test tests::history_without_repo_errors ... ok
test tests::manifest_malformed_and_wrong_shape_error ... ok
test tests::deposit_str_matches_bytes ... ok
test tests::deposit_changed_bumps_version_and_reads_versions ... ok
test tests::history_unknown_artifact_in_existing_store_is_empty ... ok
test tests::sha256_abc_vector ... ok
test tests::sha256_empty_vector ... ok
test tests::sha256_long_input_matches_block_boundary ... ok
test tests::validate_job_id_ok ... ok
test tests::validate_job_id_rejects ... ok
test tests::validate_name_ok ... ok
test tests::validate_name_rejects ... ok
test tests::gitops_review_guards ... ok
test tests::manifest_preserves_unknown_fields_on_redeposit ... ok
test tests::gitops_worktree_add_remove ... ok
test tests::gitops_is_repo_and_branch_and_clean ... ok
test tests::read_errors ... ok
test tests::list_sorted_and_empty_job ... ok
test tests::read_latest_missing_file_errors ... ok
test tests::gitops_review_branch_ok ... ok
test tests::gitops_approve_merge_ok_and_guards ... ok

test result: ok. 39 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.08s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-9c136ee5dcf33356)

running 9 tests
test empty_record_attaches_an_empty_artifact_list ... ok
test empty_input_deposits_a_zero_byte_artifact ... ok
test non_array_artifacts_field_is_treated_as_absent ... ok
test duplicate_attach_entries_are_appended_not_deduped ... ok
test duplicate_identical_deposit_is_one_version ... ok
test maximum_name_depth_and_long_job_id_round_trip ... ok
test out_of_order_attach_keeps_existing_order_then_appends_store_order ... ok
test maximum_input_one_mebibyte_round_trips ... ok
test out_of_order_version_reads_return_the_right_bytes ... ok

test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.59s

     Running tests/error_paths.rs (target/debug/deps/error_paths-68a17f23b18aa578)

running 17 tests
test cli_usage_refusals_exit_two ... ok
test manifest_corruption_and_shape_are_refused ... ok
test cli_missing_flag_values_are_usage_errors ... ok
test job_id_refusals_are_the_documented_messages ... ok
test deposit_validates_before_it_creates_the_store ... ok
test attach_refuses_a_non_object_record ... ok
test name_refusals_are_the_documented_messages ... ok
test reject_branch_needs_a_reason ... ok
test store_root_that_is_a_file_fails_as_an_artifact_error ... ok
test non_repo_gitops_helpers_error_or_are_false ... ok
test cli_negative_version_is_refused ... ok
test cli_missing_source_and_artifact_are_artifact_store_errors ... ok
test cli_non_integer_version_is_refused ... ok
test read_refusals_are_exact ... ok
test worktree_refusals_are_exact ... ok
test merge_refusals_are_exact ... ok
test review_refusals_are_exact ... ok

test result: ok. 17 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.40s

     Running tests/gap_close.rs (target/debug/deps/gap_close-a7733ea8b1a346e9)

running 9 tests
test run_cli_identical_deposit_reports_no_new_commit ... ok
test attach_preserves_top_level_fields_and_does_not_mutate_input ... ok
test is_repo_accepts_a_subdirectory ... ok
test clean_tree_counts_an_untracked_file_as_dirty ... ok
test branch_exists_is_false_for_a_commit_sha ... ok
test current_branch_is_empty_on_a_detached_head ... ok
test run_cli_show_lists_oldest_first ... ok
test worktree_add_detaches_and_remove_cleans_up ... ok
test approve_merge_refuses_an_unknown_base ... ok

test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.37s

     Running unittests src/lib.rs (target/debug/deps/parity_tests-687aa87537ff316b)

running 235 tests
test tests::test_boss_trigger::tests::test_canonical_payload_stable ... ok
test tests::test_boss_trigger::tests::test_canonical_matches ... ok
test support::fake_redis::tests::set_nx_and_ttl ... ok
test tests::test_boss_trigger::tests::test_bad_hex_rejected ... ok
test support::acceptance::tests::empty_and_bad ... ok
test support::fake_redis::tests::zrangebyscore_order ... ok
test support::helpers::tests::tmp_routing ... ok
test support::fake_redis::tests::lrem_semantics ... ok
test support::acceptance::tests::parse_shapes ... ok
test tests::test_boss_trigger::tests::test_bad_version_rejected ... ok
test tests::test_boss_trigger::tests::test_empty_text_canonical ... ok
test tests::test_boss_trigger::tests::test_future_ts_within_skew_ok ... ok
test tests::test_boss_trigger::tests::test_malformed_fields_rejected ... ok
test tests::test_boss_trigger::tests::test_hmac_agrees ... ok
test tests::test_boss_trigger::tests::test_null_sig_without_flag_rejected ... ok
test tests::test_boss_trigger::tests::test_hex_roundtrip ... ok
test tests::test_boss_trigger::tests::test_stale_ts_rejected ... ok
test tests::test_boss_trigger::tests::test_replay_rejected ... ok
test tests::test_boss_trigger::tests::test_unsigned_replay_rejected ... ok
test tests::test_boss_trigger::tests::test_unsigned_stale_ts_rejected ... ok
test tests::test_boss_trigger::tests::test_unicode_payload_agrees ... ok
test tests::test_boss_trigger::tests::test_unsigned_test_envelope_accepted ... ok
test tests::test_boss_trigger::tests::test_uppercase_sig_accepted ... ok
test tests::test_boss_trigger::tests::test_tampered_text_rejected ... ok
test tests::test_boss_trigger::tests::test_wrong_secret_rejected ... ok
test tests::test_bus_rename::tests::test_is_admin_case_insensitive ... ok
test tests::test_boss_trigger::tests::test_valid_envelope ... ok
test tests::test_bus_rename::tests::test_history_entry_shape ... ok
test tests::test_bus_rename::tests::test_label_for ... ok
test tests::test_bus_rename::tests::test_log_entry_is_keyless ... ok
test tests::test_bus_rename::tests::test_keyless_entry_passes_admin_verify ... ok
test tests::test_bus_rename::tests::test_log_entry_is_valid_json ... ok
test tests::test_bus_rename::tests::test_names_hash_entry_shape ... ok
test tests::test_bus_rename::tests::test_parse_names_flat_array_form ... ok
test tests::test_bus_rename::tests::test_parse_names_nullish ... ok
test tests::test_bus_rename::tests::test_nonce_shape ... ok
test tests::test_bus_rename::tests::test_parse_names_object_form ... ok
test tests::test_bus_rename::tests::test_pystr_matches_json_dumps ... ok
test tests::test_bus_rename::tests::test_qnick_encoding ... ok
test tests::test_clip::tests::test_read_falls_through_failing_tool ... ok
test tests::test_bustools_parity::tests::test_live_matches_vendored ... ok
test tests::test_clip::tests::test_read_no_tools_installed_is_loud ... ok
test tests::test_clip::tests::test_read_uses_first_working_tool ... ok
test tests::test_clip::tests::test_read_all_tools_fail_is_loud ... ok
test tests::test_clip::tests::test_write_no_tools_is_loud ... ok
test tests::test_clip::tests::test_write_returns_tool_name_and_sends_data ... ok
test tests::test_fdny_par_clock::tests::test_crew_id_rules ... ok
test tests::test_fdny_par_clock::tests::test_enter_starts_interval_from_entry ... ok
test tests::test_fdny_par_clock::tests::test_enter_twice_is_refused ... ok
test tests::test_fdny_par_clock::tests::test_due_fires_once_per_cycle ... ok
test tests::test_fdny_par_clock::tests::test_exit_removes_crew_and_cleans_ledger ... ok
test tests::test_fdny_par_clock::tests::test_completion_resets_cycle_and_clears_alarm ... ok
test tests::test_fdny_par_clock::tests::test_exit_unknown_crew_is_refused ... ok
test tests::test_fdny_par_clock::tests::test_exit_silences_overdue ... ok
test tests::test_fdny_par_clock::tests::test_grace_escalates_to_life_safety ... ok
test tests::test_fdny_par_clock::tests::test_ids_carry_no_spaces_or_explanations ... ok
test tests::test_fdny_par_clock::tests::test_inputs_never_mutated ... ok
test tests::test_fdny_par_clock::tests::test_line_matches_fnd020_shape ... ok
test tests::test_fdny_par_clock::tests::test_location_present_on_life_safety_event ... ok
test tests::test_fdny_par_clock::tests::test_quiet_before_interval ... ok
test tests::test_fdny_par_clock::tests::test_second_crew_counts_independently ... ok
test tests::test_os021_update::tests::test_readme_documents_rollback ... ok
test tests::test_os021_update::tests::test_script_defaults_to_opt_relay_and_names_hook ... ok
test tests::test_os058_gateway_unit::tests::test_header_names_bake_and_has_no_em_dash ... ok
test tests::test_os058_gateway_unit::tests::test_exec_runs_gateway_with_no_secret_on_command_line ... ok
test tests::test_os058_gateway_unit::tests::test_image_routes_enable_after_bake ... ok
test tests::test_os058_gateway_unit::tests::test_install_and_target_wiring_live_after_bake ... ok
test tests::test_os058_gateway_unit::tests::test_unit_exists ... ok
test tests::test_os058_gateway_unit::tests::test_readme_section_and_spec_record ... ok
test tests::test_os058_gateway_unit::tests::test_service_identity_workdir_and_restart ... ok
test tests::test_os058_gateway_unit::tests::test_unit_ordering_target_and_secrets_gate ... ok
test tests::test_os059_gateway_bake::tests::test_bake_block_copies_only_daemon_and_catalog ... ok
test tests::test_os059_gateway_bake::tests::test_bake_block_refuses_missing_source ... ok
test tests::test_os059_gateway_bake::tests::test_enablement_loop_names_gateway ... ok
test tests::test_os059_gateway_bake::tests::test_file_provisioners_carry_only_daemon_and_catalog ... ok
test tests::test_os059_gateway_bake::tests::test_hook_enables_gateway ... ok
test tests::test_os059_gateway_bake::tests::test_build_image_bash_syntax ... ok
test tests::test_os059_gateway_bake::tests::test_hook_shell_syntax ... ok
test tests::test_os059_gateway_bake::tests::test_allowlisted_gateway_tree_sweeps_clean ... ok
test tests::test_os059_gateway_bake::tests::test_readme_carries_os059_section_without_em_dash ... ok
test tests::test_os059_gateway_bake::tests::test_shell_installs_stamp_and_enables ... ok
test tests::test_os059_gateway_bake::tests::test_spec_records_os059_bake ... ok
test tests::test_os059_gateway_bake::tests::test_planted_env_file_is_finding ... ok
test tests::test_os059_gateway_bake::tests::test_target_wants_gateway ... ok
test tests::test_os059_gateway_bake::tests::test_sweep_script_shell_syntax ... ok
test tests::test_os059_gateway_bake::tests::test_unit_header_no_longer_defers_enablement ... ok
test tests::test_os059_gateway_bake::tests::test_wrapper_stages_gateway_and_stamp ... ok
test tests::test_os065_skills_loader::tests::test_build_image_bakes_collection_root ... ok
test tests::test_os065_skills_loader::tests::test_build_live_stages_collection_root ... ok
test tests::test_os059_gateway_bake::tests::test_wrapper_bash_syntax ... ok
test tests::test_os065_skills_loader::tests::test_live_hook_owns_collection_root ... ok
test tests::test_os065_skills_loader::tests::test_no_em_dash_in_new_files ... ok
test tests::test_os065_skills_loader::tests::test_packer_bakes_collection_root ... ok
test tests::test_os083_artifact_store::tests::test_build_image_bakes_store_root ... ok
test tests::test_os083_artifact_store::tests::test_build_live_stages_store_root ... ok
test tests::test_os065_skills_loader::tests::test_build_scripts_parse ... ok
test tests::test_os083_artifact_store::tests::test_no_em_dash_in_new_module ... ok
test tests::test_os083_artifact_store::tests::test_packer_bakes_store_root ... ok
test tests::test_os094_job_artifacts::tests::test_parse_artifact_ref_shape ... ok
test tests::test_os_base::tests::test_base_doc_carries_no_em_dash ... ok
test tests::test_os_base::tests::test_base_doc_names_the_frozen_base_and_source ... ok
test tests::test_os_base::tests::test_base_doc_states_checksum_limit_honestly ... ok
test tests::test_os_base::tests::test_build_script_pins_bookworm_suite_and_mirror ... ok
test tests::test_os083_artifact_store::tests::test_build_scripts_parse ... ok
test tests::test_os_base::tests::test_preseed_names_no_suite_or_mirror ... ok
test tests::test_os_base::tests::test_no_second_base_in_build_files ... ok
test tests::test_os_boot_harness::tests::test_bad_numbers_fail ... ok
test tests::test_os_boot_harness::tests::test_launch_contract_in_script ... ok
test tests::test_os_boot_harness::tests::test_missing_image_fails_naming_path ... ok
test tests::test_os_boot_harness::tests::test_missing_qemu_fails_naming_binary ... ok
test tests::test_os_boot_harness::tests::test_no_em_dash_in_new_content ... ok
test tests::test_os_boot_harness::tests::test_no_image_is_usage_error ... ok
test tests::test_os_boot_harness::tests::test_non_ppm_screenshot_fails ... ok
test tests::test_os_boot_harness::tests::test_readme_section_states_unproven_limit ... ok
test tests::test_os_boot_harness::tests::test_script_exists_and_bash_clean ... ok
test tests::test_os_bus_unit::tests::test_exec_runs_watchpy_with_no_secret_on_command_line ... ok
test tests::test_os_bus_unit::tests::test_image_route_enables_and_live_route_stages ... ok
test tests::test_os_bus_unit::tests::test_install_and_target_want_each_other ... ok
test tests::test_os_bus_unit::tests::test_readme_section_and_spec_record ... ok
test tests::test_os_bus_unit::tests::test_service_identity_workdir_and_restart ... ok
test tests::test_os_bus_unit::tests::test_unit_exists ... ok
test tests::test_os_bus_unit::tests::test_unit_ordering_target_and_secrets_gate ... ok
test tests::test_os_bus_unit::tests::test_watchpy_is_the_named_process ... ok
test tests::test_os_livebuild::tests::test_base_carries_fallback_divergences ... ok
test tests::test_os_livebuild::tests::test_config_exists_and_names_bookworm_amd64_iso_hybrid ... ok
test tests::test_os_livebuild::tests::test_config_shell_syntax ... ok
test tests::test_os_livebuild::tests::test_config_states_unproven_limit ... ok
test tests::test_os_livebuild::tests::test_covers_packages_txt_names ... ok
test tests::test_os_livebuild::tests::test_covers_spec_extras_as_real_package_names ... ok
test tests::test_os_livebuild::tests::test_hook_enables_exactly_the_build_image_unit_set ... ok
test tests::test_os_livebuild::tests::test_hook_enables_nothing_else_from_services ... ok
test tests::test_os_livebuild::tests::test_hook_shell_syntax ... ok
test tests::test_os_livebuild::tests::test_new_doc_sections_carry_no_em_dash ... ok
test tests::test_os_livebuild::tests::test_no_second_base_in_live_build_files ... ok
test tests::test_os_livebuild::tests::test_no_unit_copy_lives_in_live_build_tree ... ok
test tests::test_os_livebuild::tests::test_no_versions_pinned_here ... ok
test tests::test_os_livebuild::tests::test_readme_carries_os008_section_with_limit ... ok
test tests::test_os059_gateway_bake::tests::test_planted_venv_and_servers_files_are_findings ... ok
test tests::test_os_livebuild::tests::test_wrapper_bash_syntax ... ok
test tests::test_os_livebuild::tests::test_wrapper_guards ... ok
test tests::test_os_livebuild::tests::test_wrapper_build_steps_and_output_naming ... ok
test tests::test_os_livebuild::tests::test_wrapper_stages_from_repo_sources_and_cleans_up ... ok
test tests::test_os_manifest::tests::test_header_states_unpinned_and_owed_diff ... ok
test tests::test_os_manifest::tests::test_live_build_list_matches_packages_txt ... ok
test tests::test_os_manifest::tests::test_no_duplicates_and_no_version_pins ... ok
test tests::test_os_manifest::tests::test_no_em_dash_in_manifest_files ... ok
test tests::test_os_manifest::tests::test_openssh_disabled_by_default_noted ... ok
test tests::test_os_manifest::tests::test_packages_txt_is_exactly_the_frozen_set ... ok
test tests::test_os_manifest::tests::test_readme_carries_os010_section_with_limit ... ok
test tests::test_os_manifest::tests::test_spec_set_present ... ok
test tests::test_os_overseer_unit::tests::test_exec_runs_mos_tick_with_no_secret_on_command_line ... ok
test tests::test_os_overseer_unit::tests::test_install_target_and_image_routes ... ok
test tests::test_os_overseer_unit::tests::test_mospy_is_the_named_process ... ok
test tests::test_os_overseer_unit::tests::test_service_identity_workdir_and_oneshot ... ok
test tests::test_os_overseer_unit::tests::test_readme_section_and_spec_record ... ok
test tests::test_os_overseer_unit::tests::test_timer_is_the_loop ... ok
test tests::test_os_overseer_unit::tests::test_unit_exists ... ok
test tests::test_os_overseer_unit::tests::test_unit_ordering_wants_and_secrets_gate ... ok
test tests::test_os_packer::tests::test_committed_preseed_still_locked ... ok
test tests::test_os_packer::tests::test_readme_carries_os007_section_with_unproven_limit ... ok
test tests::test_os_packer::tests::test_no_literal_password_in_template_or_wrapper ... ok
test tests::test_os_packer::tests::test_template_exists_and_names_qemu_source ... ok
test tests::test_os_packer::tests::test_template_iso_checksum_is_publisher_file_not_invented_hash ... ok
test tests::test_os_packer::tests::test_template_bookworm_only_no_second_base ... ok
test tests::test_os_packer::tests::test_template_iso_url_has_no_default ... ok
test tests::test_os_packer::tests::test_template_provisioners_mirror_build_image_glue ... ok
test tests::test_os_packer::tests::test_template_raw_output_and_names ... ok
test tests::test_os_packer::tests::test_template_ssh_password_sensitive_and_undefaulted ... ok
test tests::test_os_packer::tests::test_wrapper_generates_password_with_openssl_not_a_literal ... ok
test tests::test_os_packer::tests::test_wrapper_guards ... ok
test tests::test_os_boot_harness::tests::test_embedded_python_compiles ... ok
test tests::test_os_stackbake::tests::test_dirty_guard_runs_before_any_image_write ... ok
test tests::test_os_stackbake::tests::test_no_hardcoded_commit_sha_in_script ... ok
test tests::test_os_stackbake::tests::test_no_requirements_file_exists ... ok
test tests::test_os_stackbake::tests::test_payload_still_excludes_git ... ok
test tests::test_os_packer::tests::test_wrapper_syntax_clean ... ok
test tests::test_os_stackbake::tests::test_pinned_commit_captured_from_checkout_head ... ok
test tests::test_os_stackbake::tests::test_readme_has_no_em_dash ... ok
test tests::test_os_packer::tests::test_wrapper_preseed_transform_changes_exactly_one_line ... ok
test tests::test_os_stackbake::tests::test_readme_has_os011_section_with_limits ... ok
test tests::test_os_stackbake::tests::test_readme_states_no_venv_step_and_why ... ok
test tests::test_os_stackbake::tests::test_refuses_dirty_checkout ... ok
test tests::test_os_stackbake::tests::test_stamp_written_after_git_removal ... ok
test tests::test_os_stackbake::tests::test_source_commit_stamp_file_written_from_variable ... ok
test tests::test_os_stackbake::tests::test_version_stamp_carries_source_commit_line ... ok
test tests::test_os_target_unit::tests::test_gate_documents_the_oneshot_and_timer_limits ... ok
test tests::test_os_target_unit::tests::test_gate_probes_the_gateable_set ... ok
test tests::test_os_target_unit::tests::test_marker_write_is_guarded_and_block_is_reported ... ok
test tests::test_os_target_unit::tests::test_no_secret_on_any_command_line ... ok
test tests::test_os_target_unit::tests::test_readme_carries_os016_section_with_exclusions ... ok
test tests::test_os_target_unit::tests::test_ready_does_not_wait_on_the_brief ... ok
test tests::test_os_target_unit::tests::test_ready_is_oneshot_checklist_under_relay_target ... ok
test tests::test_os_target_unit::tests::test_ready_orders_after_every_checked_unit ... ok
test tests::test_os_target_unit::tests::test_spec_carries_os016_record ... ok
test tests::test_os_target_unit::tests::test_target_keeps_preexisting_base_ordering ... ok
test tests::test_os_target_unit::tests::test_target_enabled_identically_on_all_image_routes ... ok
test tests::test_os_target_unit::tests::test_target_names_worker_template_exclusion ... ok
test tests::test_os_target_unit::tests::test_target_wants_full_os016_set ... ok
test tests::test_os_tree::tests::test_build_image_code_lines_reference_no_lane_src ... ok
test tests::test_os_tree::tests::test_build_image_referenced_inputs_exist ... ok
test tests::test_os_tree::tests::test_enabled_units_exist_in_services ... ok
test tests::test_os_tree::tests::test_new_os_docs_carry_no_em_dash ... ok
test tests::test_os_tree::tests::test_packages_list_carries_proven_set ... ok
test tests::test_os_tree::tests::test_preseed_carries_os009_answers ... ok
test tests::test_os_tree::tests::test_readme_states_honesty_limits ... ok
test tests::test_os_stackbake::tests::test_script_bash_syntax ... ok
test tests::test_os_tree::tests::test_tree_files_exist ... ok
test tests::test_os_uplink::tests::test_enabled_on_all_three_image_routes ... ok
test tests::test_os_uplink::tests::test_unit_wiring ... ok
test tests::test_pomodoro::tests::test_fmt_remaining ... ok
test tests::test_pomodoro::tests::test_parse_compound_durations ... ok
test tests::test_pomodoro::tests::test_parse_rejects_garbage ... ok
test tests::test_worlds_pack::tests::test_agent_serving_unknown_watcher_fails ... ok
test tests::test_worlds_pack::tests::test_bad_severity_fails ... ok
test tests::test_worlds_pack::tests::test_bad_status_fails ... ok
test tests::test_worlds_pack::tests::test_duplicate_urgency_rank_fails ... ok
test tests::test_worlds_pack::tests::test_local_alert_may_not_cross_bus ... ok
test tests::test_worlds_pack::tests::test_missing_key_fails ... ok
test tests::test_worlds_pack::tests::test_send_without_never_carries_fails ... ok
test tests::test_worlds_pack::tests::test_shipped_packs_are_honest_spec ... ok
test tests::test_worlds_pack::tests::test_shipped_packs_have_docs ... ok
test tests::test_worlds_pack::tests::test_shipped_packs_validate ... ok
test tests::test_worlds_pack::tests::test_summary_alert_may_cross_bus ... ok
test tests::test_worlds_pack::tests::test_unknown_urgency_class_fails ... ok
test tests::test_worlds_pack::tests::test_valid_manifest_passes ... ok
test tests::tests::index_complete ... ok
test tests::test_os_tree::tests::test_bash_scripts_syntax_clean ... ok
test tests::test_os_tree::tests::test_sh_scripts_syntax_clean ... ok
test tests::test_os021_update::tests::test_no_args_without_hook_exits_before_touching_target ... ok
test tests::test_os021_update::tests::test_non_git_target_refuses ... ok
test tests::test_os021_update::tests::test_rollback_without_previous_refuses ... ok
test tests::test_os021_update::tests::test_missing_bundle_is_usage_error ... ok
test tests::test_os021_update::tests::test_corrupt_bundle_refuses_and_leaves_target ... ok
test tests::test_os021_update::tests::test_apply_moves_tree_and_keeps_previous ... ok
test tests::test_os021_update::tests::test_rollback_swaps_and_second_rollback_swaps_back ... ok

test result: ok. 235 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.71s

     Running unittests src/lib.rs (target/debug/deps/queue_core-5a02588de0211192)

running 12 tests
test tests::base64_round_trip_and_strictness ... ok
test tests::envelope_non_jpeg_data_url_refused ... ok
test tests::envelope_tampered_byte_length_refused ... ok
test tests::envelope_tampered_sha256_refused ... ok
test tests::job_store_claim_renew_release_finish ... ok
test tests::job_store_submit_idempotent_and_round_trip ... ok
test tests::job_store_result_round_trip ... ok
test tests::key_layout_matches_python ... ok
test tests::envelope_wrong_kind_refused ... ok
test tests::envelope_validates ... ok
test tests::envelope_unknown_product_refused ... ok
test tests::sha256_known_vectors ... ok

test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.04s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-6da286d47af84dae)

running 9 tests
test claiming_an_unfiled_job_creates_claim_state ... ok
test duplicate_claim_first_caller_wins ... ok
test duplicate_submit_is_idempotent_and_indexes_once ... ok
test empty_namespace_keeps_the_same_key_shape ... ok
test product_matching_is_exact_not_case_folded ... ok
test out_of_order_submit_orders_the_index_by_created_at ... ok
test empty_frame_is_a_valid_envelope ... ok
test finish_then_claim_is_allowed_and_claim_then_finish_releases ... ok
test maximum_frame_validates ... ok

test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.19s

     Running tests/error_paths.rs (target/debug/deps/error_paths-46c2a02d14e3f6f9)

running 13 tests
test base64_errors_are_typed_strings ... ok
test base64_rejects_a_quad_with_too_much_padding ... ok
test base64_accepts_the_empty_input ... ok
test empty_id_is_refused ... ok
test empty_timestamp_is_refused ... ok
test empty_product_list_refuses_every_product ... ok
test byte_length_mismatch_is_refused ... ok
test non_jpeg_data_url_is_refused ... ok
test sha256_mismatch_is_refused ... ok
test undecodable_base64_is_refused ... ok
test unknown_product_is_refused_with_the_python_wording ... ok
test wrong_kind_is_refused ... ok
test wrong_version_is_refused ... ok

test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/gap_close.rs (target/debug/deps/gap_close-2c5f06b1c975f0cf)

running 8 tests
test memory_backend_starts_empty ... ok
test set_nx_ex_holds_while_the_key_is_live ... ok
test hset_skips_empty_values_and_counts_only_stored_fields ... ok
test zrange_orders_by_score_then_member ... ok
test delete_counts_only_live_string_keys ... ok
test set_body_and_get_round_trip ... ok
test set_xx_ex_requires_a_live_key ... ok
test delete_of_a_hash_only_key_counts_zero_but_removes_it ... ok

test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running unittests src/lib.rs (target/debug/deps/queue_store-029a2abddecb2a40)

running 5 tests
test tests::test_env_host_wins ... ok
test tests::test_env_full_url_yields_its_host ... ok
test tests::test_result_round_trip_exact_keys ... ok
test tests::test_store_full_round_trip ... ok
test tests::test_unconfigured_raises_typed_error ... ok

test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-0d183d1a4b77ff02)

running 9 tests
test result_key_ignores_the_job_namespace ... ok
test empty_hash_values_are_not_written ... ok
test out_of_order_index_scores_sort_by_score ... ok
test equal_index_scores_fall_back_to_member_order ... ok
test empty_envelope_is_idempotent_on_second_submit ... ok
test claim_lease_fields_are_internally_consistent ... ok
test empty_envelope_files_under_the_empty_job_id ... ok
test duplicate_submit_keeps_the_first_envelope ... ok
test maximum_envelope_round_trips_intact ... ok

test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.04s

     Running tests/error_paths.rs (target/debug/deps/error_paths-4f67cfeb4a362867)

running 16 tests
test key_helpers_match_the_documented_layout ... ok
test duplicate_claim_is_refused ... ok
test malformed_credential_url_is_refused ... ok
test non_object_envelope_is_none ... ok
test invalid_json_envelope_is_none ... ok
test claim_on_a_missing_job_is_not_refused ... ok
test put_result_without_job_id_writes_the_empty_key ... ok
test credential_url_supplies_the_host_when_env_is_empty ... ok
test missing_envelope_and_result_are_none ... ok
test non_object_result_is_none ... ok
test renew_without_a_claim_is_false ... ok
test unknown_job_fields_are_an_empty_map_not_an_error ... ok
test unconfigured_host_is_a_typed_refusal ... ok
test whitespace_host_falls_through_to_the_same_refusal ... ok
test sqlite_nx_and_xx_lease_refusals ... ok
test sqlite_delete_counts_only_kv_rows ... ok

test result: ok. 16 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s

     Running tests/gap_close.rs (target/debug/deps/gap_close-7764b787548dc6a9)

running 9 tests
test category_lists_carry_the_source_values ... ok
test every_key_helper_uses_the_expected_shape ... ok
test the_repo_layer_has_exactly_the_three_products ... ok
test finish_releases_the_claim ... ok
test finish_filters_the_job_out_of_open_job_ids ... ok
test ping_is_honest_on_both_backends ... ok
test sqlite_hash_write_skips_empty_values ... ok
test sqlite_index_orders_by_score ... ok
test sqlite_backend_runs_the_full_job_round_trip ... ok

test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s

     Running unittests src/lib.rs (target/debug/deps/relay-424a13ef7e9a6715)

running 29 tests
test http::tests::append_then_poll_by_watermark ... ok
test http::tests::health_names_the_memory_store ... ok
test http::tests::health_names_the_file_store ... ok
test http::tests::refusals_for_bad_json_and_oversized_bodies ... ok
test http::tests::notify_line_format_and_deterministic_id ... ok
test http::tests::rooms_are_isolated ... ok
test http::tests::since_parsing_matches_parseint ... ok
test http::tests::validation_refusals ... ok
test json::tests::escape_controls ... ok
test json::tests::parse_tolerances ... ok
test json::tests::round_trip ... ok
test notify::tests::different_basis_different_id ... ok
test notify::tests::id_format_and_determinism ... ok
test notify::tests::id_matches_node_for_js_suite_payload ... ok
test notify::tests::line_formats ... ok
test sha256::tests::abc_vector ... ok
test http::tests::viewer_is_served_at_slash ... ok
test sha256::tests::empty_input_vector ... ok
test sha256::tests::long_input_spans_blocks ... ok
test store::tests::append_indices_and_isolation ... ok
test http::tests::file_store_persists_lines_across_a_restart ... ok
test store::tests::since_semantics ... ok
test validation::tests::room_names ... ok
test validation::tests::severities ... ok
test validation::tests::utf16_length_matches_js ... ok
test validation::tests::single_line_rules ... ok
test store::tests::reload_skips_torn_records ... ok
test store::tests::file_store_persists_across_reload ... ok
test http::tests::live_http_post_then_get ... ok

test result: ok. 29 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.05s

     Running unittests src/main.rs (target/debug/deps/relay-ab7dbb41b1661ffd)

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-f241cb09b037f984)

running 7 tests
test empty_inputs_are_answered_not_crashed ... ok
test duplicate_json_keys_follow_last_one_wins ... ok
test a_get_before_any_post_is_an_honest_empty_room ... ok
test out_of_order_watermarks_are_clamped_and_first_since_wins ... ok
test duplicate_notify_payloads_keep_one_id_and_two_indices ... ok
test maximum_lengths_are_accepted_at_the_cap ... ok
test an_exactly_maximum_body_is_not_an_oversized_body ... ok

test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s

     Running tests/error_paths.rs (target/debug/deps/error_paths-2ac4a790985d2145)

running 12 tests
test a_body_that_is_not_a_json_object_is_refused ... ok
test a_malformed_percent_escape_is_a_500_not_a_400 ... ok
test a_missing_viewer_is_500_plain_text_with_the_upstream_wording ... ok
test an_oversized_body_is_refused_before_parsing ... ok
test health_on_an_empty_relay_names_zero_rooms_and_the_memory_store ... ok
test invalid_room_names_are_refused_with_the_documented_message ... ok
test an_unreadable_store_file_panics_at_boot - should panic ... ok
test room_store_reports_the_unreadable_file_as_an_error ... ok
test nick_refusals_name_the_nick_field ... ok
test notify_refuses_severity_topic_and_text_in_that_order ... ok
test text_refusals_name_the_text_field ... ok
test unknown_routes_and_wrong_methods_are_404_json ... ok

test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/gap_close.rs (target/debug/deps/gap_close-57defbec18e8abc0)

running 10 tests
test parse_decodes_unicode_escapes_and_surrogate_pairs ... ok
test escape_handles_quotes_backslashes_and_unicode ... ok
test escape_leaves_del_and_everything_above_it_alone ... ok
test escape_uses_the_named_control_sequences ... ok
test parse_duplicate_keys_last_one_wins ... ok
test parse_ignores_extra_fields_including_nested_ones ... ok
test parse_rejects_lone_surrogates ... ok
test parse_tolerates_whitespace_between_tokens ... ok
test record_line_round_trips_every_hostile_character ... ok
test parse_rejects_every_shape_that_is_not_a_room_line_object ... ok

test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running unittests src/lib.rs (target/debug/deps/stack-8ed222495a2c5a87)

running 13 tests
test tests::agent_service_matches_script ... ok
test tests::app_service_matches_script_queue_path_always_on ... ok
test tests::empty_port_values_fall_back_to_defaults ... ok
test tests::non_numeric_port_passes_through_verbatim ... ok
test tests::default_ports_and_bases ... ok
test tests::job_ns_absent_by_default_and_inherited_verbatim ... ok
test tests::port_overrides_are_honored ... ok
test tests::relay_service_matches_script ... ok
test tests::plan_order_is_script_order ... ok
test tests::queue_service_matches_script ... ok
test tests::summary_lines_match_script_echo ... ok
test tests::transport_production_when_key_present ... ok
test tests::transport_dev_helper_when_key_missing_or_empty ... ok

test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/edge_cases.rs (target/debug/deps/edge_cases-5177530cb1705b2c)

running 8 tests
test empty_input_yields_the_documented_defaults ... ok
test duplicate_input_keeps_the_first_value ... ok
test every_service_has_a_unique_name_and_a_non_empty_argv ... ok
test empty_job_namespace_is_inherited_verbatim ... ok
test out_of_order_input_is_resolved_by_key_not_position ... ok
test zero_port_is_kept_not_treated_as_unset ... ok
test unicode_port_is_kept_verbatim ... ok
test maximum_input_is_carried_without_truncation ... ok

test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests/error_paths.rs (target/debug/deps/error_paths-935fde25c42e3c65)

running 11 tests
test any_non_empty_spark_key_is_production_without_validation ... ok
test empty_spark_key_selects_dev_helper_not_an_error ... ok
test keys_are_case_sensitive_and_a_wrong_case_is_unset ... ok
test empty_port_value_is_not_an_error_it_falls_back ... ok
test duplicate_keys_take_the_first_match ... ok
test missing_spark_key_selects_dev_helper_not_an_error ... ok
test negative_port_is_kept_verbatim ... ok
test plan_survives_an_unusable_port ... ok
test unknown_keys_are_ignored_not_refused ... ok
test summary_survives_an_unusable_port ... ok
test whitespace_port_is_kept_verbatim ... ok

test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s

     Running tests/gap_close.rs (target/debug/deps/gap_close-1f54fd95e541a814)

running 8 tests
test dev_helper_warning_is_only_for_dev_helper ... ok
test from_env_reads_live_values_and_empty_falls_back ... ok
test plan_with_empty_job_namespace_is_inherited ... ok
test plan_order_and_cwd_match_the_script ... ok
test readiness_constants_are_the_script_values ... ok
test plan_without_job_namespace_has_no_namespace_env ... ok
test the_resident_agent_never_gets_an_http_gate ... ok
test summary_lines_carry_custom_bases ... ok

test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests agent_runtime

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests dashboard

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests guardrail

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests os_boot

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests os_budget

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests os_identity

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests os_jobs

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests os_memory

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests os_misc

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests os_supervisor

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests os_worker

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests os_workspace

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests parity_tests

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests queue_core

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests queue_store

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests relay

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests stack

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

exit: 0
