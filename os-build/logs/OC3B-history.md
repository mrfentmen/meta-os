# OC3B-016 — history policy

Default: no history retention configured by this lane and none of its
files enable sync, sign-in, or cloud history. Chromium's local
History SQLite still records visits unless the profile disables it;
this lane does NOT claim otherwise. Two honest options for the ISO
lane (decision: theirs, recorded here as pending):
(a) seed Preferences with history-expire at session end, or
(b) document "local history kept, never synced" as policy.
OC1 boot check confirms which landed. No silent default is asserted.
