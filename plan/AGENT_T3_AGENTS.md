# Agent T3 lane: the agent pipeline inside the OS

Read this whole file before touching anything. Work on branch `agent-t3`.
Commit there. Do not merge. Do not push.

## Mission

The OS advertises agents. Right now a submitted job can fail in 82 ms on an
image-side bug, the key file is root-only, and no run has ever produced a
receipt a judge could open. Your lane makes submit, queue, run, and receipt a
real path on this machine, with proof for each step.

## Owned paths (only these)

- `agents/`
- `agent-layer/`
- `server/queue/`
- `server/crew-start.mjs` and the other `server/crew-*` files
- `os-build/iso/payload-agent/`
- `iso/apps/agent-status/` (when present)
- `os-build/lanes/T3_REPORT.md` (yours to write)

Do not edit `os-build/face/`, `trio/`, `os-build/identity/`, or
`os-build/iso/payload-theme/`. Those have owners.

## Rules

- No QEMU. No paid API calls. If a task would spend money, build the dry path
  and say what you did not run.
- Never print a key. Check the environment and the files by presence and
  permissions, not by value.
- Every run you claim must have its record file path in the report.
- Use subagents. Split the sections across at least three. A subagent may only
  touch the section it was given. Have one subagent read the whole diff against
  this file at the end and hunt for invented claims.

## Section A. What exists today (1-18)

1. Read `agent-layer/README.md` and list the seven units plus their start conditions.
2. Read `agents/runtime.mjs` and describe one job's life in five sentences.
3. Read `agents/submit.mjs` and list every refusal it can produce.
4. Read `agents/watchman.mjs` and say what it watches and what it writes.
5. Read `server/queue/patrol.py` and the spark generator. Name where a key is required.
6. Run `meta-ask --list` if present. Paste the output.
7. Submit one job with a real agent name and paste the result, including failures.
8. Follow that job to its record on disk. Paste the path and the first lines.
9. Find every place a run can fail and never write a record. List them.
10. Find every place a failure is swallowed with a bare `|| true`. List them.
11. Confirm whether a run ever emits a receipt. If not, say what a receipt would be.
12. Check the registry for agents marked draft. List them and what is missing.
13. Check the key file's path, owner, and mode. Do not print the value.
14. Check whether any process reads the key from the environment. Name the file and line.
15. Write a short current-state page at the top of your report, with dates.
16. Name the single bug that blocks a full run end to end.
17. Name the second one.
18. Fix the first bug. Paste before and after.

## Section B. Submit path (19-40)

19. Make `meta-ask` refuse an unknown agent with the list of known agents. Paste it.
20. Make it refuse an empty request with a reason the user can act on.
21. Make it refuse a duplicate of a queued job, and say which job it duplicates.
22. Make it refuse a job over the budget, and name the budget.
23. Make it print the queue id it created, or say the queue is not answering.
24. Make it exit non-zero on every refusal. Paste a table of exit codes.
25. Make it accept a request from a file as well as an argument.
26. Make it show a job's status by id.
27. Make it list recent jobs with their state and age.
28. Make it never print a key or a token, even in verbose mode. Prove with a grep.
29. Add `--json` output for the status and list commands, and validate it parses.
30. Make the refusal messages match the desktop's voice, not a stack trace.
31. Make the queue's address configurable in one place.
32. Make a submit to a dead queue fail in under two seconds.
33. Prove that timeout with a closed port. Paste the timing.
34. Make the board accept the same job shape the CLI sends. Prove with one payload.
35. Add a schema file for a job, and validate both callers against it.
36. Reject a job whose fields do not match the schema, by name.
37. Make the CLI and the board share the schema, not two copies.
38. Add a test that submits a valid job and a malformed one, and checks both outcomes.
39. Run it and paste the output.
40. Document the three ways to submit a job, with examples.

## Section C. Queue and runner (41-66)

41. Trace one job from submit to runner. Write the file names in order.
42. Fix the permissions bug that made the payload jobs directory unwritable. Paste the mode before and after.
43. Make the runner create its work directory if it is missing, with the right owner.
44. Make the runner fail with a named error when a world file is missing, and name the file.
45. Make the runner never leave a half-written record. Write to a temp file and rename.
46. Make the runner write a start line and an end line with timestamps.
47. Make the runner cap concurrency and prove the cap with four jobs.
48. Make the runner stop cleanly on SIGTERM without orphaning children.
49. Make the runner enforce a per-job wall clock and kill the child on timeout.
50. Make the timeout produce a record with the reason, not silence.
51. Make the patrol loop's paused state visible in a status file.
52. Make a paused patrol log one line per cycle, not one per second.
53. Make the queue survive a restart with jobs still queued.
54. Prove persistence: queue a job, restart the service, find the job.
55. Make duplicate job ids impossible. Prove with a burst of submits.
56. Make the queue reject a job older than a configured age.
57. Make the queue expose counts by state on a status endpoint.
58. Make the status endpoint answer even while a job is running.
59. Make the runner log which agent ran, which model was asked, and what it cost.
60. Make the cost field come from the provider's response, not an estimate.
61. Record the model name and the prompt hash per run.
62. Make the run record link to its input and its output by path.
63. Confirm no run writes outside the runs directory.
64. Confirm no run reads the key from a world file or a prompt.
65. Add a test that runs the queue with a stub provider and checks the record shape.
66. Paste that test's output.

## Section D. Receipts (67-88)

67. Define what a receipt contains: job id, agent, model, start, end, result, cost, hash.
68. Write the receipt as a separate file next to the run record.
69. Make the receipt hash cover the input and the output, not just the id.
70. Make the receipt verifiable with one command. Write that command.
71. Prove tampering is caught: change one byte of the output, run the check, paste the failure.
72. Make the receipt readable by the desktop's Agents page without a new endpoint.
73. Make a failed run still produce a receipt marked failed, with the reason.
74. Make the receipt include the ports and binaries it depended on, if any.
75. Make the receipt include how long the queue waited before the run started.
76. Make the receipt path predictable from the job id.
77. Make every receipt written so far discoverable by one command. Count them.
78. Make the count readable from the Agents page.
79. Make a receipt link open the run's record, not just the JSON.
80. Add a receipt selftest that writes, verifies, tamper-checks, and cleans up.
81. Run it and paste the output.
82. Make the receipt format versioned, with the version in the file.
83. Make an old receipt still verifiable after a format change, or say it is not.
84. Document the receipt format in one page with an example.
85. Confirm no receipt contains a key, a token, or a full prompt body if the prompt is private.
86. Make the receipt include the OS build identity, so a judge can see which image ran it.
87. Make the receipt generation run even when the agent crashes, if the wrapper survives.
88. Prove the wrapper survives a child that exits 137. Paste it.

## Section E. Key handling (89-106)

89. Read every file that reads the key. List them with line numbers.
90. Make one reader: a shared module that loads the key or returns a clear error.
91. Make every caller use it.
92. Keep the file at its current restrictive mode. Prove the mode after install.
93. Make the key load fail with "no key configured" and the exact path, never a stack trace.
94. Make the key never appear in a log line, a record, or a receipt. Prove with a scan of the runs directory.
95. Add a scan script that greps runs and receipts for the key's first and last four characters.
96. Run it and paste the clean result.
97. Make the key optional: without it, jobs fail loudly and the page says so.
98. Make the desktop's Agents page show whether a key is configured, not its value.
99. Make the queue refuse a thinking job when no key is set, before it starts.
100. Make a dry run mode that builds the prompt and stops before the call.
101. Prove dry run spends nothing: run it, show the receipt says dry.
102. Make the staging script set the file mode and owner correctly, or say it cannot as non-root.
103. Check the staged mode on a scratch tree. Paste `ls -l`.
104. Make the key path overridable by an environment variable, for tests.
105. Make the tests use a fake key file, never a real one.
106. Confirm the fake key never reaches a real endpoint. Explain how.

## Section F. Agent status page and board (107-128)

107. Read the Agents page and list every value it shows.
108. Make each value traceable to a file or an endpoint. Write the mapping.
109. Remove any value the page invents. List what you removed.
110. Make the page show live agents from the registry, with drafts marked.
111. Make the page show queued and running jobs with their age.
112. Make the page show the last three receipts with their verify state.
113. Make the page survive a dead queue with a named message.
114. Make the board show a job's full life: submitted, queued, running, done, failed.
115. Make a job's detail view show the receipt and the cost.
116. Make the board's submit form validate before sending.
117. Make the board's submit form show the queue's refusal text verbatim.
118. Make the board link a run to the world it read.
119. Make the board filter by agent and by state.
120. Make the board's empty states say what to do next.
121. Add a screenshot of the page with one live job to your captures.
122. Add a screenshot of the page with the queue down.
123. Confirm the page makes no external request. Paste the sweep.
124. Confirm the page works at 1366x768.
125. Add a selftest for the page's data mapping, run it, paste it.
126. Make the page's refresh interval honest, and say what it is.
127. Make the page show the OS build and the queue's uptime.
128. Document the page's data sources in one table.

## Section G. Proof and reporting (129-150)

129. Write `os-build/lanes/T3_REPORT.md` with one section per letter above.
130. Every claim gets the command and its output, including the failures.
131. Run one job end to end with the stub provider and paste every artifact path.
132. Run one job with a real provider only if the user has authorised spend. Otherwise say so.
133. List every file you changed with `git diff --stat`.
134. Confirm no changed file is outside your owned paths.
135. Confirm no QEMU process is running. Paste the check.
136. Confirm no paid call was made. Paste the evidence.
137. Confirm no key value appears in your report. Grep your own report and paste the clean result.
138. Name the three ways the pipeline can still fail on stage.
139. Fix the cheapest one.
140. Say what the other two need, and who owns them.
141. Confirm your commits are on `agent-t3` only. Paste the branch and the log.
142. Confirm `main` is untouched by you.
143. Write the paragraph a judge would read: what the agents actually did on this machine.
144. Check that paragraph against your artifacts, line by line, and cut anything unproven.
145. Record the total cost of every run you made, with the source of the number.
146. Record how long a typical run takes, from three runs.
147. Make the report's summary table: capability, state, evidence.
148. List the cross-lane requests with file, line, and what you need.
149. Do not fix cross-lane files.
150. End with the next three tasks you would do with another session.
