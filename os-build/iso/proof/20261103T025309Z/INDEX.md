# MetaOS 1.0 install proof — 20261103T025309Z

Mode: DRY (harness plumbing, not an install)
Host: Darwin arm64, qemu 11.1.3
ISO: none
Accel: -accel tcg,thread=multi -cpu max

Every frame below is QEMU's framebuffer via QMP screendump — a real VM,
not a mock. Interpret them in order; a stage with no frame did not happen.

| frame | expected |
|---|---|
| 00-harness-dry.png | DRY: firmware screen; proves QMP screendump works, not a Meta boot |
