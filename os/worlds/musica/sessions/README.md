# Musica sessions

Each session dir holds `session.json` and `take_log.jsonl` (the
record) plus, once the keeper pass has run, a `keepers/` dir with
the keeper audio. The working `takes/` dir is NOT committed: every
take is reproducible byte-identically from its log entry, because
the loop is deterministic (same seed + params = same audio).

Replay any take:

```
python3 os/worlds/musica/runtime/compose.py --replay \
  os/worlds/musica/sessions/<session>/take_log.jsonl <take-id> out.wav
```

The replayed file's sha256 must match the log entry's sha256.

Audio policy: keeper and normalised audio is committed only for
the first catalogue (hn029), to keep the repo lean. Later
sessions (including the 100-take overnight run) keep audio as
reproducible working output: the take log plus the replay command
above reproduces any take byte-identically, and the catalogue
points at those reproducible files.
