# Error registry — final audit (B-L1-137)

Run: `python3 os-build/layer1/error_audit.py --unused`
Result: **exit 0, one finding, zero undeclared codes.**

```
error registry audit
  declared: 34   used: 34   files: 94
```

## What the audit does

Three directions, because a registry can rot in three ways:

| Direction | Hurt | Rule |
|---|---|---|
| UNDECLARED | high | A code a service returns that `services/common/err/err.goose` does not define. Compiles today if the service declares its own `let`, then becomes a second vocabulary the audit can never see. |
| UNUSED | none | A code nothing returns. Informational: spare words mean the taxonomy was designed, not accreted. |
| NUMERIC | medium | A bare `return 42` where a code belongs. The registry cannot audit a number. |

## The one finding, and why it was fixed in the auditor

`E_STOPPED` was reported as undeclared and used in `services/supervisor/deps.goose`.
It was not used. The only occurrence is prose in a comment:

```
// id 0 with E_STOPPED-ish CODE_OK when the whole order is done -- callers distinguish
```

The first version of the auditor scanned raw text, so a code *named* in a comment counted as a
*use*. That is a false positive in the safe direction, which is the dangerous direction: an
auditor that credits comments will also credit a locally-defined code's mention in a doc comment
and quietly stop reporting a real second vocabulary.

Fix, in `os-build/layer1/error_audit.py`: `strip_comments()` removes `//` to end-of-line while
respecting double-quoted strings (so a URL inside a string does not truncate the line), and all
three scans read the stripped body. `CODE_OK` was also folded into the use pattern — it is a real
code, and reporting the most-used code in the tree as "unused" is noise that trains people to
ignore the tool.

No source change was needed: nothing in `services/` declares a local error code, and no service
returns a bare number where a registry code exists. The 37 services listed under NUMERIC RETURNS
return counts and lengths (`return n`, `return 0` for "the else branch has nothing"), which is a
different job from a status code and is why the audit prints that list without failing on it.

## Registry shape as it stands

34 codes, five bands, and the band boundary is the first digit of the number:

```
0        CODE_OK
1xxx     general        INVAL NOROOM NOTFOUND BUSY TIMEOUT IO CORRUPT UNSUPPORTED DENIED STATE RATE NOKEY
2xxx     storage        NO_SPACE NO_DEVICE BAD_BLOCK READ_ONLY
3xxx     network        NO_LINK NO_ADDRESS NO_MASK RESOLVE REFUSED UNREACHABLE
4xxx     agent          NO_AGENT NO_CAPABILITY QUOTA AUDIT_FULL
5xxx     updater        BAD_MANIFEST BAD_SIGNATURE VERIFY ROLLBACK
6xxx     session        NO_SESSION AUTH SYNTAX
```

Every code is used by at least one service; every code a service returns exists in the registry.
