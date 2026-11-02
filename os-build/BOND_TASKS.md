# BOND — OS CODE LAYER TASK LIST (boss order, 2026-11-02)

Bond writes the OS code layer: the Rust crates and the
Python root they port. Machine rules from the light lanes
still hold: no workspace builds, no emulator runs; verify
by reading, by text and parity tests, and by single-crate
checks with -j1 when a compile is unavoidable.
Work in order. Checkpoint on room 1 per section.
Merges go through Pax from exact commits.

## Section 1 — crates/os-boot

- [ ] B001. Read crates/os-boot end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/os-boot.md, every claim tied to a file and line range.
- [ ] B002. Error-path tests for crates/os-boot: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B003. Edge-case tests for crates/os-boot: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B004. Spec-versus-code pass on crates/os-boot: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B005. The Python original behind crates/os-boot (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B006. Ledger and record shapes in crates/os-boot: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B007. Callers of crates/os-boot: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B008. Config surface of crates/os-boot: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B009. Failure drill for crates/os-boot: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B010. Public surface inventory of crates/os-boot: every exported name, one line each, marked used or unused in the repo today.
- [ ] B011. Test-gap close for crates/os-boot: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B012. Changelog record for crates/os-boot: what changed since the port began, from git history, in os-build/records/os-boot-changes.md.

## Section 2 — crates/os-supervisor

- [ ] B013. Read crates/os-supervisor end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/os-supervisor.md, every claim tied to a file and line range.
- [ ] B014. Error-path tests for crates/os-supervisor: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B015. Edge-case tests for crates/os-supervisor: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B016. Spec-versus-code pass on crates/os-supervisor: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B017. The Python original behind crates/os-supervisor (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B018. Ledger and record shapes in crates/os-supervisor: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B019. Callers of crates/os-supervisor: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B020. Config surface of crates/os-supervisor: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B021. Failure drill for crates/os-supervisor: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B022. Public surface inventory of crates/os-supervisor: every exported name, one line each, marked used or unused in the repo today.
- [ ] B023. Test-gap close for crates/os-supervisor: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B024. Changelog record for crates/os-supervisor: what changed since the port began, from git history, in os-build/records/os-supervisor-changes.md.

## Section 3 — crates/os-jobs

- [ ] B025. Read crates/os-jobs end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/os-jobs.md, every claim tied to a file and line range.
- [ ] B026. Error-path tests for crates/os-jobs: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B027. Edge-case tests for crates/os-jobs: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B028. Spec-versus-code pass on crates/os-jobs: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B029. The Python original behind crates/os-jobs (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B030. Ledger and record shapes in crates/os-jobs: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B031. Callers of crates/os-jobs: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B032. Config surface of crates/os-jobs: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B033. Failure drill for crates/os-jobs: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B034. Public surface inventory of crates/os-jobs: every exported name, one line each, marked used or unused in the repo today.
- [ ] B035. Test-gap close for crates/os-jobs: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B036. Changelog record for crates/os-jobs: what changed since the port began, from git history, in os-build/records/os-jobs-changes.md.

## Section 4 — crates/os-memory

- [ ] B037. Read crates/os-memory end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/os-memory.md, every claim tied to a file and line range.
- [ ] B038. Error-path tests for crates/os-memory: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B039. Edge-case tests for crates/os-memory: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B040. Spec-versus-code pass on crates/os-memory: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B041. The Python original behind crates/os-memory (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B042. Ledger and record shapes in crates/os-memory: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B043. Callers of crates/os-memory: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B044. Config surface of crates/os-memory: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B045. Failure drill for crates/os-memory: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B046. Public surface inventory of crates/os-memory: every exported name, one line each, marked used or unused in the repo today.
- [ ] B047. Test-gap close for crates/os-memory: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B048. Changelog record for crates/os-memory: what changed since the port began, from git history, in os-build/records/os-memory-changes.md.

## Section 5 — crates/os-identity

- [ ] B049. Read crates/os-identity end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/os-identity.md, every claim tied to a file and line range.
- [ ] B050. Error-path tests for crates/os-identity: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B051. Edge-case tests for crates/os-identity: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B052. Spec-versus-code pass on crates/os-identity: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B053. The Python original behind crates/os-identity (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B054. Ledger and record shapes in crates/os-identity: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B055. Callers of crates/os-identity: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B056. Config surface of crates/os-identity: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B057. Failure drill for crates/os-identity: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B058. Public surface inventory of crates/os-identity: every exported name, one line each, marked used or unused in the repo today.
- [ ] B059. Test-gap close for crates/os-identity: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B060. Changelog record for crates/os-identity: what changed since the port began, from git history, in os-build/records/os-identity-changes.md.

## Section 6 — crates/os-budget

- [ ] B061. Read crates/os-budget end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/os-budget.md, every claim tied to a file and line range.
- [ ] B062. Error-path tests for crates/os-budget: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B063. Edge-case tests for crates/os-budget: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B064. Spec-versus-code pass on crates/os-budget: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B065. The Python original behind crates/os-budget (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B066. Ledger and record shapes in crates/os-budget: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B067. Callers of crates/os-budget: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B068. Config surface of crates/os-budget: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B069. Failure drill for crates/os-budget: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B070. Public surface inventory of crates/os-budget: every exported name, one line each, marked used or unused in the repo today.
- [ ] B071. Test-gap close for crates/os-budget: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B072. Changelog record for crates/os-budget: what changed since the port began, from git history, in os-build/records/os-budget-changes.md.

## Section 7 — crates/os-worker

- [ ] B073. Read crates/os-worker end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/os-worker.md, every claim tied to a file and line range.
- [ ] B074. Error-path tests for crates/os-worker: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B075. Edge-case tests for crates/os-worker: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B076. Spec-versus-code pass on crates/os-worker: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B077. The Python original behind crates/os-worker (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B078. Ledger and record shapes in crates/os-worker: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B079. Callers of crates/os-worker: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B080. Config surface of crates/os-worker: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B081. Failure drill for crates/os-worker: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B082. Public surface inventory of crates/os-worker: every exported name, one line each, marked used or unused in the repo today.
- [ ] B083. Test-gap close for crates/os-worker: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B084. Changelog record for crates/os-worker: what changed since the port began, from git history, in os-build/records/os-worker-changes.md.

## Section 8 — crates/os-workspace

- [ ] B085. Read crates/os-workspace end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/os-workspace.md, every claim tied to a file and line range.
- [ ] B086. Error-path tests for crates/os-workspace: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B087. Edge-case tests for crates/os-workspace: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B088. Spec-versus-code pass on crates/os-workspace: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B089. The Python original behind crates/os-workspace (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B090. Ledger and record shapes in crates/os-workspace: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B091. Callers of crates/os-workspace: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B092. Config surface of crates/os-workspace: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B093. Failure drill for crates/os-workspace: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B094. Public surface inventory of crates/os-workspace: every exported name, one line each, marked used or unused in the repo today.
- [ ] B095. Test-gap close for crates/os-workspace: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B096. Changelog record for crates/os-workspace: what changed since the port began, from git history, in os-build/records/os-workspace-changes.md.

## Section 9 — crates/agent-runtime

- [ ] B097. Read crates/agent-runtime end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/agent-runtime.md, every claim tied to a file and line range.
- [ ] B098. Error-path tests for crates/agent-runtime: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B099. Edge-case tests for crates/agent-runtime: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B100. Spec-versus-code pass on crates/agent-runtime: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B101. The Python original behind crates/agent-runtime (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B102. Ledger and record shapes in crates/agent-runtime: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B103. Callers of crates/agent-runtime: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B104. Config surface of crates/agent-runtime: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B105. Failure drill for crates/agent-runtime: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B106. Public surface inventory of crates/agent-runtime: every exported name, one line each, marked used or unused in the repo today.
- [ ] B107. Test-gap close for crates/agent-runtime: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B108. Changelog record for crates/agent-runtime: what changed since the port began, from git history, in os-build/records/agent-runtime-changes.md.

## Section 10 — crates/queue-core

- [ ] B109. Read crates/queue-core end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/queue-core.md, every claim tied to a file and line range.
- [ ] B110. Error-path tests for crates/queue-core: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B111. Edge-case tests for crates/queue-core: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B112. Spec-versus-code pass on crates/queue-core: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B113. The Python original behind crates/queue-core (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B114. Ledger and record shapes in crates/queue-core: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B115. Callers of crates/queue-core: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B116. Config surface of crates/queue-core: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B117. Failure drill for crates/queue-core: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B118. Public surface inventory of crates/queue-core: every exported name, one line each, marked used or unused in the repo today.
- [ ] B119. Test-gap close for crates/queue-core: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B120. Changelog record for crates/queue-core: what changed since the port began, from git history, in os-build/records/queue-core-changes.md.

## Section 11 — crates/queue-store

- [ ] B121. Read crates/queue-store end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/queue-store.md, every claim tied to a file and line range.
- [ ] B122. Error-path tests for crates/queue-store: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B123. Edge-case tests for crates/queue-store: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B124. Spec-versus-code pass on crates/queue-store: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B125. The Python original behind crates/queue-store (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B126. Ledger and record shapes in crates/queue-store: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B127. Callers of crates/queue-store: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B128. Config surface of crates/queue-store: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B129. Failure drill for crates/queue-store: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B130. Public surface inventory of crates/queue-store: every exported name, one line each, marked used or unused in the repo today.
- [ ] B131. Test-gap close for crates/queue-store: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B132. Changelog record for crates/queue-store: what changed since the port began, from git history, in os-build/records/queue-store-changes.md.

## Section 12 — crates/assess-server

- [ ] B133. Read crates/assess-server end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/assess-server.md, every claim tied to a file and line range.
- [ ] B134. Error-path tests for crates/assess-server: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B135. Edge-case tests for crates/assess-server: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B136. Spec-versus-code pass on crates/assess-server: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B137. The Python original behind crates/assess-server (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B138. Ledger and record shapes in crates/assess-server: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B139. Callers of crates/assess-server: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B140. Config surface of crates/assess-server: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B141. Failure drill for crates/assess-server: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B142. Public surface inventory of crates/assess-server: every exported name, one line each, marked used or unused in the repo today.
- [ ] B143. Test-gap close for crates/assess-server: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B144. Changelog record for crates/assess-server: what changed since the port began, from git history, in os-build/records/assess-server-changes.md.

## Section 13 — crates/dashboard

- [ ] B145. Read crates/dashboard end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/dashboard.md, every claim tied to a file and line range.
- [ ] B146. Error-path tests for crates/dashboard: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B147. Edge-case tests for crates/dashboard: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B148. Spec-versus-code pass on crates/dashboard: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B149. The Python original behind crates/dashboard (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B150. Ledger and record shapes in crates/dashboard: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B151. Callers of crates/dashboard: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B152. Config surface of crates/dashboard: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B153. Failure drill for crates/dashboard: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B154. Public surface inventory of crates/dashboard: every exported name, one line each, marked used or unused in the repo today.
- [ ] B155. Test-gap close for crates/dashboard: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B156. Changelog record for crates/dashboard: what changed since the port began, from git history, in os-build/records/dashboard-changes.md.

## Section 14 — crates/guardrail

- [ ] B157. Read crates/guardrail end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/guardrail.md, every claim tied to a file and line range.
- [ ] B158. Error-path tests for crates/guardrail: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B159. Edge-case tests for crates/guardrail: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B160. Spec-versus-code pass on crates/guardrail: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B161. The Python original behind crates/guardrail (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B162. Ledger and record shapes in crates/guardrail: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B163. Callers of crates/guardrail: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B164. Config surface of crates/guardrail: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B165. Failure drill for crates/guardrail: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B166. Public surface inventory of crates/guardrail: every exported name, one line each, marked used or unused in the repo today.
- [ ] B167. Test-gap close for crates/guardrail: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B168. Changelog record for crates/guardrail: what changed since the port began, from git history, in os-build/records/guardrail-changes.md.

## Section 15 — crates/intel

- [ ] B169. Read crates/intel end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/intel.md, every claim tied to a file and line range.
- [ ] B170. Error-path tests for crates/intel: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B171. Edge-case tests for crates/intel: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B172. Spec-versus-code pass on crates/intel: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B173. The Python original behind crates/intel (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B174. Ledger and record shapes in crates/intel: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B175. Callers of crates/intel: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B176. Config surface of crates/intel: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B177. Failure drill for crates/intel: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B178. Public surface inventory of crates/intel: every exported name, one line each, marked used or unused in the repo today.
- [ ] B179. Test-gap close for crates/intel: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B180. Changelog record for crates/intel: what changed since the port began, from git history, in os-build/records/intel-changes.md.

## Section 16 — crates/relay

- [ ] B181. Read crates/relay end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/relay.md, every claim tied to a file and line range.
- [ ] B182. Error-path tests for crates/relay: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B183. Edge-case tests for crates/relay: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B184. Spec-versus-code pass on crates/relay: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B185. The Python original behind crates/relay (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B186. Ledger and record shapes in crates/relay: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B187. Callers of crates/relay: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B188. Config surface of crates/relay: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B189. Failure drill for crates/relay: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B190. Public surface inventory of crates/relay: every exported name, one line each, marked used or unused in the repo today.
- [ ] B191. Test-gap close for crates/relay: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B192. Changelog record for crates/relay: what changed since the port began, from git history, in os-build/records/relay-changes.md.

## Section 17 — crates/stack

- [ ] B193. Read crates/stack end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/stack.md, every claim tied to a file and line range.
- [ ] B194. Error-path tests for crates/stack: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B195. Edge-case tests for crates/stack: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B196. Spec-versus-code pass on crates/stack: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B197. The Python original behind crates/stack (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B198. Ledger and record shapes in crates/stack: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B199. Callers of crates/stack: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B200. Config surface of crates/stack: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B201. Failure drill for crates/stack: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B202. Public surface inventory of crates/stack: every exported name, one line each, marked used or unused in the repo today.
- [ ] B203. Test-gap close for crates/stack: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B204. Changelog record for crates/stack: what changed since the port began, from git history, in os-build/records/stack-changes.md.

## Section 18 — crates/os-misc

- [ ] B205. Read crates/os-misc end to end and write its behaviour record: what it does, what it refuses, what it writes down. File under os-build/records/os-misc.md, every claim tied to a file and line range.
- [ ] B206. Error-path tests for crates/os-misc: every refusal and failure branch gets a test that proves it refuses the way the code says. Text/parity style where a compile is too heavy; single-crate check -j1 only.
- [ ] B207. Edge-case tests for crates/os-misc: empty input, maximum input, duplicate input, out-of-order input — one test each, named for the case.
- [ ] B208. Spec-versus-code pass on crates/os-misc: the docs and comments against the code as written; every disagreement is a finding filed on room 1, and the doc fixed where the code is right.
- [ ] B209. The Python original behind crates/os-misc (os/ tree): list the behaviours the Rust port does not carry yet, as tasks with the source lines named — do not port them yourself, the list is the deliverable.
- [ ] B210. Ledger and record shapes in crates/os-misc: write the worked examples — one real record of each kind the crate writes, annotated field by field.
- [ ] B211. Callers of crates/os-misc: find every caller in the repo, record what each one expects, and flag any caller expecting something the crate does not do.
- [ ] B212. Config surface of crates/os-misc: every environment variable, flag, and file it reads, in one table, with the default and the refusal when it is wrong.
- [ ] B213. Failure drill for crates/os-misc: what breaks first when its inputs stop arriving — written from the code, as a drill another agent can run.
- [ ] B214. Public surface inventory of crates/os-misc: every exported name, one line each, marked used or unused in the repo today.
- [ ] B215. Test-gap close for crates/os-misc: the module with the fewest tests in the crate gets its missing cases written until it matches the crate's best-covered module.
- [ ] B216. Changelog record for crates/os-misc: what changed since the port began, from git history, in os-build/records/os-misc-changes.md.

## Section 19 — the Python root (os/)

- [ ] B217. Behaviour record for the Python watchman: inputs, outputs, refusals — under os-build/records/, tied to files and lines.
- [ ] B218. Missing-case tests for the Python watchman: the refusal and boundary cases its current tests do not cover, written and run.
- [ ] B219. Behaviour record for the Python uplink: inputs, outputs, refusals — under os-build/records/, tied to files and lines.
- [ ] B220. Missing-case tests for the Python uplink: the refusal and boundary cases its current tests do not cover, written and run.
- [ ] B221. Behaviour record for the Python dashboard: inputs, outputs, refusals — under os-build/records/, tied to files and lines.
- [ ] B222. Missing-case tests for the Python dashboard: the refusal and boundary cases its current tests do not cover, written and run.
- [ ] B223. Behaviour record for the Python queue service: inputs, outputs, refusals — under os-build/records/, tied to files and lines.
- [ ] B224. Missing-case tests for the Python queue service: the refusal and boundary cases its current tests do not cover, written and run.
- [ ] B225. Behaviour record for the Python trio store: inputs, outputs, refusals — under os-build/records/, tied to files and lines.
- [ ] B226. Missing-case tests for the Python trio store: the refusal and boundary cases its current tests do not cover, written and run.
- [ ] B227. Behaviour record for the Python evidence store: inputs, outputs, refusals — under os-build/records/, tied to files and lines.
- [ ] B228. Missing-case tests for the Python evidence store: the refusal and boundary cases its current tests do not cover, written and run.
- [ ] B229. Behaviour record for the Python crew seam: inputs, outputs, refusals — under os-build/records/, tied to files and lines.
- [ ] B230. Missing-case tests for the Python crew seam: the refusal and boundary cases its current tests do not cover, written and run.
- [ ] B231. Behaviour record for the Python orchestrator: inputs, outputs, refusals — under os-build/records/, tied to files and lines.
- [ ] B232. Missing-case tests for the Python orchestrator: the refusal and boundary cases its current tests do not cover, written and run.
- [ ] B233. Behaviour record for the Python judge: inputs, outputs, refusals — under os-build/records/, tied to files and lines.
- [ ] B234. Missing-case tests for the Python judge: the refusal and boundary cases its current tests do not cover, written and run.
- [ ] B235. Behaviour record for the Python budget governor: inputs, outputs, refusals — under os-build/records/, tied to files and lines.
- [ ] B236. Missing-case tests for the Python budget governor: the refusal and boundary cases its current tests do not cover, written and run.
- [ ] B237. Behaviour record for the Python records writer: inputs, outputs, refusals — under os-build/records/, tied to files and lines.
- [ ] B238. Missing-case tests for the Python records writer: the refusal and boundary cases its current tests do not cover, written and run.
- [ ] B239. Behaviour record for the Python model caller: inputs, outputs, refusals — under os-build/records/, tied to files and lines.
- [ ] B240. Missing-case tests for the Python model caller: the refusal and boundary cases its current tests do not cover, written and run.

## Section 20 — kernel-adjacent (reading only — kernel/src is Rowan's pen)

- [ ] B241. Write the memory.rs allocator record.
- [ ] B242. Write the tasks.rs lifecycle record.
- [ ] B243. Write the sched.rs policy record.
- [ ] B244. Write the user.rs dispatch record.
- [ ] B245. Write the interrupts.rs + traps.rs fault-path record.
- [ ] B246. Write the vga.rs + logo_frames.rs display record.
- [ ] B247. Write the gdt.rs + main.rs boot-sequence record.
- [ ] B248. Write the framebuffer.rs unwired-surface inventory.
- [ ] B249. Write the syscalls.rs frozen-file inventory (read only, never edited).
- [ ] B250. Write the the boot log index: every committed log, its build, its claims.
- [ ] B251. Write the the claim audit support pack: each claim sentence mapped to its log.
- [ ] B252. Write the the ABI spec's worked examples, one per syscall.

Total tasks: 252. When a section closes, the count is
recounted on room 1 — lines written are reported per
section, from the files, never estimated.
