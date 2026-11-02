# Proposals — work that belongs to another lane

Each file here is a change someone else owns, written so they can apply it without
re-deriving it. A proposal is not a merge request: it is a specification with line numbers,
an owner, and an acceptance test.

| Proposal | Owner | Status | Acceptance |
|---|---|---|---|
| `quitter-badcall-wiring.md` | Rowan (`kernel/src` lane) | filed 2026-11-02, not applied | the expected lines in the proposal appear in a boot log |

## Rules

1. **No edits in the owner's files.** The proposal names the file and line; the owner makes
   the change. The one exception is disclosed, not hidden: `ROWAN_PROPOSALS.md` lists the
   kernel edits that landed before the lane fence arrived, with their proof logs.
2. **An acceptance test, not a patch that applies.** A proposal is done when the behaviour
   shows up in a log, not when the diff is clean.
3. **Blocked work is still work.** `hog` and `talker`/`listener` cannot be written honestly
   yet; that is recorded in `../USERSPACE_PROGRAMS.md`, not worked around.
