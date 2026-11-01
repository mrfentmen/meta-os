# Debian users and permissions (OS-093)

- Model: numeric uids, `/etc/passwd` (identity), `/etc/shadow`
  (hashes), `/etc/group`; discretionary file bits + optional ACLs.
- Our image: single `relay` user (created in-chroot, password
  locked `!`, autologin on console+serial). Payload and stores
  chowned `relay:relay`; `/etc/metaos` is root-only (700).
- Failure modes that matter for an agent OS: everything the crew
  runs shares ONE uid — a misbehaving agent can read every other
  agent's memory, tools, and records (no isolation primitive is
  used). `sudo` membership for `relay` (preseed) widens this to
  root on a compromised agent. This is rough edge #1 and the
  direct reason for the sandboxing design note (OS-127).
