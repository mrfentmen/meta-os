# Gap records — R13-024 notify

No gaps filed.

The facet grep for `deprecat|legacy|old|remove|sunset|todo|fixme|compat` returns no matches in
`services/notify/*.goose`, and all 27 public `nt_*` functions are present in the current source.
There is no deprecated symbol, alias or removal marker to audit.

This is a deliberate zero, not a skipped check. A later rename should add a marker and a line
here; until then the correct gap count is 0.
