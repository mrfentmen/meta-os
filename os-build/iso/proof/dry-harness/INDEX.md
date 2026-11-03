# MetaOS 1.0 install proof — 20261103T025602Z

Mode: DRY (harness plumbing, not an install)
Host: Darwin arm64, qemu 11.1.3
ISO: none
Accel: -accel tcg,thread=multi -cpu max

Every frame below is QEMU's framebuffer via QMP screendump — a real VM,
not a mock. Interpret them in order; a stage with no frame did not happen.

The at column is wall-clock T+seconds from harness start, including QEMU
launch. Under TCG it is an upper bound on boot time, not hardware speed;
say so if you quote it. The H+2 box asks for "login under 60s" — only a
frame whose stage is the login screen and whose at value is under 60
answers it. (No backticks in this block: the heredoc is unquoted so the
shell would execute them; that bug mangled the first INDEX.md.)

| frame | at | expected |
|---|---|---|
| 00-harness-dry.png | T+5s | DRY: firmware screen; proves QMP screendump works, not a Meta boot |
