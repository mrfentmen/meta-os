# Brief eval rubric — BRF-015

Score a brief against a fixture manifest. Every check below is
answered yes or no, from the brief text plus the manifest only.
No check needs a judgement call about style. A brief that fails
any check is not a good brief, even if it reads well.

How to score: for each check, write yes or no, then the brief id
and the manifest fact that proves it. Log the result in
`intel/evals/log.md` (see BRF-016/017/018).

## The 8 checks

1. **All blocked named.** Every job with status "blocked" in the
   jobs dump appears in the brief's Blocked section, by id.
   Yes only if the count matches the manifest exactly — no
   blocked job missing, no extra job listed as blocked.

2. **Owners right.** Every claimed job's owner in the brief
   matches the jobs dump claim field, and every claimed job
   appears under its owner. Yes only if the owner table matches
   the manifest owner table exactly.

3. **No invented facts.** Every job id, job title, nick, decision,
   and alert id in the brief appears in the snapshot or the
   manifest. Yes only if a check against the manifest finds zero
   invented names, jobs, or facts.

4. **Within budget.** The brief's word count is at or under its
   kind budget: morning 220 words, on-join 150 words, on-demand
   300 words. Count every word in the brief, including headings.
   Yes only if the count is at or under budget.

5. **Plain English.** The brief contains no term from the
   jargon blocklist (BRF-037, Buffy lane — pending in this repo;
   until it lands, use this plain test: no acronym is used
   without an explanation in the same sentence, and no sentence
   needs a technical dictionary to understand). Yes only if it
   passes that test.

6. **Window stated.** The brief's first lines state the window
   it actually covers, including its start point when history
   was trimmed. Yes only if a reader can say, from the brief
   alone, what time span the brief covers.

7. **Decisions real.** Every decision in the brief traces to a
   decision marker (DONE:/BLOCKED:/DECISION:) in the snapshot
   messages, or to a done/blocked job record. Yes only if every
   listed decision is found in the snapshot; a decision with no
   source is a no.

8. **Alerts linked.** Every open watchdog alert in the snapshot
   is named in the brief's Watch items by alert id, with a
   one-line summary. Yes only if the alert ids match the
   manifest exactly — no alert missing, no invented alert id.

## What a score means

- 8 yes: the brief passes. It may still be improved, but it is
  honest, complete, and within budget.
- 7 or fewer yes: the brief fails. Log which checks failed, fix
  the top failure first (BRF-017 rule), then score again. Do not
  average scores across briefs into a pass rate without listing
  the per-brief, per-check results.

## OS-050 cold-start honesty check (boot briefs only)

This check sits beside the 8 checks above; it does not renumber
them. Score it yes or no, from the brief text plus the manifest
only, the same way as the 8 checks. A boot brief passes it only
when every part that applies to it holds:

1. Empty history says it is empty. A brief over a manifest with
   no messages, no jobs, and no alerts, and no stated window,
   has a window line reading "Window: empty". A brief over a
   capped window that kept 0 messages says "The window is
   empty." on its window line. Either way the brief names no
   job, nick, decision, or alert.
2. No shutdown story without a shutdown record. A brief whose
   manifest holds no previous shutdown time states no shutdown
   time and describes no job as carried over from shutdown.
3. No previous session without a previous-session record. A
   brief whose manifest holds no previous-session record says
   nothing about a previous session — no digest, no summary,
   no "last time" claim. With a record, the brief carries
   exactly the OS-051 digest line (see the OS-051 check
   below) and nothing more about the previous session.
4. A stated window bounds the brief. A brief with content but
   no stated window keeps a "not stated" window line; it never
   presents a claimed shutdown-to-boot span the manifest does
   not hold, and no listed fact comes from outside the stated
   window.

A boot brief that fails this check fails the cold-start rule
even if it passes all 8 checks above.

## OS-051 previous-session digest check (boot briefs only)

This check sits beside the OS-050 check; it does not renumber
the 8 checks. Score it yes or no, from the brief text plus the
manifest only. A boot brief passes it only when every part
that applies to it holds:

1. With a previous-session record, the brief opens with the
   digest line: one line reading "Previous session: last
   brief <time>, N jobs completed, M open threads", placed
   right after the window line and before Decisions, with the
   time, the completed titles, and the open thread titles all
   matching the manifest exactly.
2. Without a previous-session record, the brief says nothing
   about a previous session at all.
3. A non-boot brief carries no digest line, even when its
   snapshot holds a previous-session record.
4. The digest line is one line, never more, and its counts
   match its titles: a list with no titles is counted as 0
   and carries no parentheses.

## OS-062 drivers + tools + apps check (boot briefs only)

This check sits beside the OS-050 and OS-051 checks; it
does not renumber the 8 checks. Score it yes or no, from
the brief text plus the manifest only. A boot brief passes
it only when every part that applies to it holds:

1. Three lines, in order, after the digest (when one
   exists) and before Decisions: a Drivers line, a Tools
   line, and a Skill apps line, each on one line.
2. The Drivers line names exactly the drivers in the
   manifest's system_state record, in order, or says no
   drivers reported when the list is empty, or says not
   reported when the record carries no drivers field.
3. The Tools line says the MCP gateway is healthy when
   the manifest says so, says it is down when the
   manifest says it is down (never omitted), or says its
   health is not reported when the manifest says nothing
   about it.
4. The Skill apps line names exactly the skill apps in
   the manifest's system_state record, in order, or says
   no skill apps mounted when the list is empty, or says
   not reported when the record carries no skill_apps
   field.
5. A non-boot brief carries none of the three lines, even
   when its snapshot holds a system_state record.

## OS-103 environment lines check (boot briefs only)

This check sits beside the OS-050, OS-051, and OS-062
checks; it does not renumber the 8 checks. Score it yes
or no, from the brief text plus the manifest only. A boot
brief passes it only when every part that applies to it
holds:

1. Four lines, in order, after the system lines (when
   they exist) and before Decisions: a Repo line, a Bus
   line, a Working now line, and a Budget line, each on
   one line.
2. The Repo line names exactly the manifest's repo
   branch and short commit, plus "clean" or the
   uncommitted-file count from the manifest, or says
   the repo state is not reported when the manifest
   carries no usable repo record.
3. The Bus line names exactly the manifest's message
   count and rooms, or says the bus state is not
   reported when the manifest carries no usable bus
   record.
4. The Working now line names exactly the manifest's
   claimed jobs, nick and title each, in order, or says
   nobody holds a claimed job when the manifest's job
   list holds none, or says it is not reported when the
   manifest carries no jobs record. An open, unclaimed
   job is never presented as work in progress.
5. The Budget line shows exactly the manifest's lane
   budget remaining, with the cap when the manifest
   gives one, or says the budget is not reported when
   the manifest carries no usable budget record.
6. Every valued line carries its age: the manifest's
   as_of time, or the snapshot-time-not-reported label
   when the manifest gives no time. No valued line is
   presented without an age label.
7. A non-boot brief carries none of the four lines,
   even when its snapshot holds an environment record,
   and a boot brief whose snapshot holds no environment
   record carries none either.

## OS-127 recovery line check (boot briefs only)

This check sits beside the OS-050, OS-051, OS-062,
and OS-103 checks; it does not renumber the 8 checks.
Score it yes or no, from the brief text plus the
manifest only. A boot brief passes it only when every
part that applies to it holds:

1. One line, after the environment lines (when they
   exist) and before Decisions: the in-flight-jobs-
   recovered line, on one line.
2. A reconciled record names exactly the manifest's
   recovered count, and for each recovered job its id
   and title plus the baton step it resumed from, or
   step not reported when the manifest gives no step.
3. A reconciled record with no recovered jobs reads
   0 recovered, plainly.
4. A record whose sweep count disagrees with its
   recovered job count, a record with no sweep count,
   or a record with a corrupted job says recovery is
   incomplete and prints no clean count; the corrupted
   case names the corrupted job.
5. A non-boot brief carries no recovery line, even
   when its snapshot holds a recovery record, and a
   boot brief whose snapshot holds no recovery record
   carries none either, so no brief claims zero
   recovered without a sweep record.

## OS-079 settled decisions + spend vs budget check

This check sits beside the OS-050, OS-051, OS-062,
OS-103, and OS-127 checks; it does not renumber the
8 checks. Score it yes or no, from the brief text
plus the manifest only. A brief passes it only when
every part that applies to it holds:

1. A brief whose snapshot carries a memory_budget
   record opens with the settled-decisions line
   right after the window line and before the digest
   and the sections, followed by one spend-vs-budget
   line per lane, each on one line, in record order.
2. The settled-decisions line names exactly the
   manifest's settled decisions, verbatim, or reads
   none reported when the manifest's decision list
   holds none, or says the memory service is down
   when the manifest says the service did not
   answer, showing no decision at all in that case.
   A decision the manifest does not name is never
   listed.
3. Each spend line shows exactly the manifest's lane
   figure: spent of cap budget with the remaining
   figure, or remaining of cap, or remaining alone,
   matching the manifest's entry for that lane. A
   lane the manifest does not describe is never
   given a figure; a record with no usable budget
   entry reads spend vs budget not reported.
4. Every line carries its age: the manifest's as_of
   time, or the snapshot-time-not-reported label
   when the manifest gives no time. No valued line
   is presented without an age label.
5. A brief whose snapshot carries no memory_budget
   record carries none of the lines, so older briefs
   keep their exact shape; a brief over an empty
   window carries the lines before "no activity
   yet".

## OS-097 two pushes check

This check sits beside the OS-050, OS-051, OS-062, OS-103,
and OS-127 checks; it does not renumber the 8 checks. It
scores the push payloads in `intel/push.py`, not a brief
text, from the job record plus the verification record
only. A push set passes it only when every part that
applies to it holds:

1. A verified close — job status "done", overseer verified
   stamp, verification with every check passed — yields
   exactly one done push whose body starts "All done",
   names the job title, names exactly the artifact
   record's files, and names exactly the passed checks.
   With no artifacts recorded it says so; with no checks
   recorded it says no acceptance criteria were recorded.
2. A job closed without passing its checks — status
   "done" but no verified stamp, a failed check, or no
   verification — yields no done push at all.
3. A parked job — status "blocked" with a question, the
   caller's question or the job's stored note — yields
   exactly one blocked push naming the job title and the
   question verbatim. A blocked job with no question and
   no note yields no push.
4. A second close or park for the same job and kind, run
   through the same ledger, yields no second push.
5. No push of any other type exists: a third kind is
   refused at build time, and a push of another type
   fails validation.

## OS-117 federation section check

This check sits beside the OS-050, OS-051, OS-062,
OS-103, OS-127, and OS-079 checks; it does not
renumber the 8 checks. Score it yes or no, from the
brief text plus the manifest only. A morning brief
passes it only when every part that applies to it
holds:

1. A brief whose snapshot carries a federation
   record naming at least two machines carries a
   Federation section after Watch items, naming
   each machine in record order with its completed
   titles verbatim and its cross-machine jobs with
   id, title, and status.
2. A brief whose snapshot carries a federation
   record naming one machine carries no Federation
   section at all, and a brief whose snapshot
   carries no federation record carries none
   either, so no single-machine brief is padded
   into a crew of crews.
3. A machine with no completions reads no
   completions reported, never a padded title; a
   trust refusal names the machine and the detail
   verbatim, or reads reason not reported when the
   manifest gives no detail; a join names the
   machine that joined.
4. A brief over an empty window carries the section
   before "no activity yet" when its snapshot
   carries a qualifying federation record.

## OS-092 long-term memory check

A morning-format brief passes it only when every
part that applies to it holds:

1. A brief whose snapshot carries a memory_depth
   record carries a Long-term memory section after
   Watch items, naming each aged decision with its
   original date, each due commitment with its due
   date, and each fresh-agent context item, all
   verbatim from the record and in record order.
2. A brief whose snapshot carries no memory_depth
   record carries no Long-term memory section at
   all, so no older brief gains a padded section.
3. An aged decision with no original date reads
   original date not reported, and a due commitment
   with no due date reads due date not reported;
   a record with no usable entry in a category
   reads none reported for that category, never a
   padded item.
4. A brief whose snapshot carries a memory_depth
   record with memory_down true carries the memory
   service down line and shows no aged decision, due
   commitment, or fresh-agent context beside it.
5. A brief over an empty window carries the section
   before "no activity yet" when its snapshot
   carries a memory_depth record, and a brief over
   budget keeps its memory lines after the BRF-007
   trim drops bullet lines.

## OS-075 daily brief check

A morning-format brief passes it only when every
part that applies to it holds:

1. A brief whose snapshot carries a daily record
   carries a Daily brief section after Watch items
   and before Long-term memory, naming each
   overnight result, each queued job with its id
   and title, and each question waiting on Dale's
   word verbatim from the record and in record
   order, with the job tag only when the record
   gives a job.
2. A brief whose snapshot carries no daily record
   carries no Daily brief section at all, so no
   older brief gains a padded section.
3. A queue job without both an id and a title is
   skipped, and a needs-word entry without a
   question is skipped, never padded; a record
   with no usable entry in a category reads none
   reported for that category, never a padded
   item.
4. A brief over an empty window carries the
   section before "no activity yet" when its
   snapshot carries a daily record, and a brief
   over budget keeps its daily lines after the
   BRF-007 trim drops bullet lines.
5. Every daily line carries its as_of age label,
   or the snapshot-time-not-reported label when
   the record gives no time, so a stale daily
   section is never silently presented as current.

## INT-027 gaps 3/4 held decisions + sources check

A morning-format brief passes it only when every
part that applies to it holds:

1. A brief whose snapshot carries a held_decisions
   record carries a Held decisions section after
   Watch items (and Federation, when one renders),
   naming each question verbatim from the record
   and in record order, with the decider nick when
   the record gives one, or decider not reported
   when it gives none.
2. A brief whose snapshot carries no held_decisions
   record carries no Held decisions section at all,
   so no older brief gains a padded section; a
   record with no usable entry reads none reported,
   never a padded decision, and an entry without a
   question is skipped.
3. A brief whose snapshot carries a source_pointers
   list carries a Sources section after Held
   decisions, naming each pointer verbatim and in
   list order; a brief whose snapshot carries no
   list, or an empty one, carries no Sources
   section at all, and a non-string entry is skipped.
4. A brief over an empty window carries both
   sections before "no activity yet" when its
   snapshot carries the records, and a brief over
   budget keeps its held and source lines after the
   BRF-007 trim drops bullet lines, because both
   are plain lines, not bullets.
5. Every held line carries its as_of age label, or
   the snapshot-time-not-reported label when the
   record gives no time, so a stale held list is
   never silently presented as current. Source
   lines carry no age label: they name locations,
   not dated facts.

INT-027 follow-up, 2026-10-28: the morning path now
fills `held_decisions` first (`intel/brief.py`
`with_held_decisions`, called by `intel.py brief`
for boot and morning briefs, ondemand left alone), so
a snapshot that only carries a stated
held_decision_entries list still carries the Held
decisions section, with one stamp; a snapshot that
hand-states a record keeps it, and a snapshot that
states no usable question keeps its exact old shape.
No question is read from the jobs list: a blocked
reason or a job title is not a question waiting on
Dale's word, so the question comes only from the
stated entries, never guessed. The Sources section
needs no filler of its own: the renderer already
reads the snapshot's plain source_pointers list
directly, so a snapshot that states pointers already
carries that section.

## BRF-019 gap 2 since-last-brief check

A morning-format brief passes it only when every
part that applies to it holds:

1. A brief whose snapshot carries a previous_brief
   record carries a Since your last brief section
   right after the window line and before Decisions,
   naming each changed job with its old status and
   its new status, and each new job as new, in
   current-window order; a job whose status is
   unchanged is not listed at all.
2. A brief whose snapshot carries no previous_brief
   record carries no Since your last brief section
   at all, so no older brief gains a padded section
   and no job is ever marked as new without a record
   to compare against; a malformed record yields no
   section, never a false diff, and a comparison
   that finds nothing changed reads nothing changed,
   never a padded change.
3. A brief over budget keeps its since-last-brief
   lines after the BRF-007 trim drops bullet lines,
   because they are plain lines, not bullets.
4. Every since-last-brief line carries its as_of age
   label, or the snapshot-time-not-reported label
   when the record gives no time, so a stale diff is
   never silently presented as current.

BRF-019 follow-up, 2026-10-28: the morning path now
fills `previous_brief` first (`intel/brief.py`
`with_previous_brief`, called by `intel.py brief`
for boot and morning briefs, ondemand left alone), so
a snapshot that only carries a stated
previous_brief_entries list still carries the Since
your last brief section, with one stamp; a snapshot
that hand-states a record keeps it, and a snapshot
that states no usable id keeps its exact old shape.
No previous status is read from the current jobs
list: comparing the window against itself would
report nothing changed, always, so the previous
statuses come only from the stated entries, never
guessed.

## INT-027 gaps 1/5 priority order + blocked contacts check

A morning-format brief passes it only when every
part that applies to it holds:

1. A brief whose snapshot carries a priority_order
   record carries a Priority order section after
   Sources, naming each listed job id with its
   snapshot title, numbered from 1, in record
   order; an id with no matching job is skipped,
   a duplicate id is listed once, and a job the
   record does not list is not listed at all, never
   guessed into an order.
2. A brief whose snapshot carries no priority_order
   record carries no Priority order section at all,
   so no older brief gains a padded section; a
   malformed record yields no section, never a
   false order, and an order list with no usable
   entry reads none reported, never a padded order.
3. A brief whose snapshot carries a blocked_contacts
   record carries a Blocked contacts section after
   Priority order, naming every blocked job in
   snapshot order: a job with a contact entry reads
   Ask <nick> about <id> <title>, and a job with
   no usable entry reads <id> <title>: owner not
   reported in this window, never a guessed nick;
   a contact entry for a job that is not blocked
   in this snapshot is ignored.
4. A brief whose snapshot carries no blocked_contacts
   record carries no Blocked contacts section at
   all, so no older brief gains a padded section; a
   malformed record yields no section, never a
   false contact, and a record over a window with
   no blocked jobs reads none reported.
5. The In flight and Blocked and why lines keep
   their pinned shape: these two sections are
   additive, and neither rewrites a pinned line
   in place. A brief over budget keeps its priority
   and contact lines after the BRF-007 trim drops
   bullet lines, because both are plain lines, not
   bullets.
6. Every priority and contact line carries its as_of
   age label, or the snapshot-time-not-reported
   label when the record gives no time, so a stale
   order or contact is never silently presented as
   current.

INT-027 follow-up, 2026-10-28: the morning path now
fills `priority_order` first (`intel/brief.py`
`with_priority_order`, called by `intel.py brief`
for boot and morning briefs, ondemand left alone), so
a snapshot that only carries a priority_ids list
still carries the Priority order section, with one
stamp; a snapshot that hand-states a record keeps it,
and a snapshot that states no usable id keeps its
exact old shape. The morning path now also fills
`blocked_contacts` (`intel/brief.py`
`with_blocked_contacts`, called by `intel.py brief`
for boot and morning briefs, ondemand left alone),
so a snapshot that only carries a stated
blocked_contact_entries list still carries the
Blocked contacts section, with one stamp; a snapshot
that hand-states a record keeps it, and a snapshot
that states no usable entry keeps its exact old
shape. No nick is read from the jobs list: a blocked
job carries no owner field (jobs.py deletes the claim
on block), so the ask nick comes only from the stated
entries, never guessed.

## BRF-018 follow-up on-join template sections check

A template brief of kind="onjoin" passes it only when
every part that applies to it holds:

1. The brief opens with TEMPLATE and the window line,
   then the four BRF-002 sections in prompt order:
   What this crew is building, Your likely lane,
   What is blocked, Who to ask. It carries none of
   the morning sections Decisions, In flight, or
   Owners.
2. What this crew is building carries the snapshot's
   stated crew_building sentence verbatim when the
   caller states one, else the prompt's own sentence
   that the room's current work is not stated in
   this window, never a guessed project name.
3. Your likely lane names an open job's lane field
   in the v2 rule 9 form "The open job <title>
   belongs to the <lane> lane" when the record
   carries one, and names a newcomer's capability
   record verbatim when one is stated for a
   newcomer; when neither a lane field nor a
   capability record is stated it says so and
   points to the first owner to ask for a first
   job, or says plainly that no owner is recorded.
   A lane is never guessed from a job title.
4. What is blocked names every blocked job with
   its reason verbatim, or reads "Nothing blocked
   in this window" when nothing is blocked.
5. Who to ask names the claimed-job owners, marking
   one "not online in this window" only when the
   snapshot carries a presence list that does not
   name them, plus the blocked-contact ask nick
   when the snapshot carries a blocked_contacts
   record; with no owner and no contact it says
   plainly that no owner is recorded.
6. After Who to ask, and only when they have
   content, the brief carries the additive INT-004
   sections Blocked and why and Watch items, in
   the morning bullet form, so the e2e3 loop's
   section checks keep passing; a brief with no
   blocked job carries no additive Blocked section,
   and one with no alerts carries no additive Watch
   section.
7. The default kind, an unknown kind, and a boot
   brief keep the morning shape exactly: this check
   applies to kind="onjoin" only, and an on-join
   brief over an empty room still says no activity
   yet under BRF-012, not four empty sections.

BRF-018 follow-up, 2026-10-28: the template composer
now renders the four sections for kind="onjoin"
(`intel/brief.py` `onjoin_template_lines`, called by
`compose_template_brief` with kind="onjoin", and by
`compose_brief`'s template fallback paths, which now
pass kind through); every other kind keeps the
morning shape, and the stored record's five section
keys are unchanged. The four section lines are plain
lines, so the BRF-007 trim cannot drop a blocked job
or an ask-nick ahead of any other line; the additive
bullet sections drop first under trim, the same order
the morning brief trims in.

## Status

BRF-015 v1, 2026-10-26, plus OS-050 cold-start honesty check,
2026-10-27, plus OS-051 previous-session digest check,
2026-10-27, plus OS-062 drivers + tools + apps check,
2026-10-27, plus OS-103 environment lines check,
2026-10-27, plus OS-127 recovery line check,
2026-10-27, plus OS-079 settled decisions + spend vs
budget check, 2026-10-27, plus OS-097 two pushes check,
2026-10-27, plus OS-117 federation section check,
2026-10-27, plus OS-092 long-term memory check,
2026-10-27, plus OS-075 daily brief check,
2026-10-27, plus INT-027 gaps 3/4 held decisions +
sources check, 2026-10-28, plus BRF-019 gap 2
since-last-brief check, 2026-10-28, plus INT-027 gaps 1/5
priority order + blocked contacts check, 2026-10-28, plus
BRF-018 follow-up on-join template sections check,
2026-10-28. The jargon blocklist check (check 5)
is provisional until Buffy's BRF-037 blocklist lands; the
provisional test above is stated so a scorer never has to guess.
No bus post was made for this file.
