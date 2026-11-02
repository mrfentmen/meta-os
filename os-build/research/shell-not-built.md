# NOT BUILT in the shell (OS-215) — named, in these words

- Line editing: no backspace, no arrows, no history. A typo
  means retyping the line.
- Tab completion: NOT BUILT. `help` lists two commands; that is
  the whole discovery surface.
- Colors beyond banner/status: the log body is monochrome;
  errors are text, not color.
- Scrollback/search, multi-line input, scripting: NOT BUILT.
- Prompt string: there is none (no `>` prefix); the echo plus
  uptime lines ARE the prompt for now.
- None of the above blocks the milestones: status/help/unknown/
  truncated/empty all behave, proven in O-shell.txt + O-shell2.txt.
