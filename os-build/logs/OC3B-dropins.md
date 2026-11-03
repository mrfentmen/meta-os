# OC3 ISO-1 — OC2 drop-ins copied + verified (no waiting)

Source: `origin/main @8923da87`, `git archive origin/main agent-layer`.
Staged byte-copies (OC2-owned source, read-only here):
`os-build/logs/oc3b-dropins/desktop-entries/` (9 files) +
`os-build/logs/oc3b-dropins/MANIFEST-8923da87.md` (basis).

Verification vs `agent-layer/MANIFEST.md`: 19/19 manifest-listed
paths sha256-match (order said 16; manifest actually lists 19 —
all 19 checked, all match, count reported as-run, not as-told).

- `agent-layer/README.md` `50f478ca095acc5f7c6ff036ad0f123d3d3317c386f0659c993c264192c72806`
- `agent-layer/desktop-entries/INSTALL-OC1.md` `a0a69fa48edfecd027db2a18dadf846b4d7dfc5eb3a2035fe9f739088b06dbe9`
- `agent-layer/desktop-entries/README.md` `8e91e2954aba06650883237d2d25eb67facbf8ff32ffb01128219f45039096d6`
- `agent-layer/desktop-entries/atril.desktop` `0990716ef614ae6b3b1c1db37fd468af4a89cef28a7b165a8c038524bf711f92`
- `agent-layer/desktop-entries/evince.desktop` `a7ae673c8cd39800017922ecb4ddc8068a94d396f7234a0c1c0e43eac39fcb69`
- `agent-layer/desktop-entries/meta-agent-status.desktop` `68a373a01a804fc54ae831c4784fa5763592de280b8dae1104f6cc1cd17a3d1c`
- `agent-layer/desktop-entries/mimeapps.list` `2d35dc7560dee71e02e9f48b16df5b7660afa8b9632b098d3a52af581f5369a6`
- `agent-layer/desktop-entries/mousepad.desktop` `11e146a72825a357cc7e13207da0e58d031b64f7bb5b6b5f5a44a3652b025fd0`
- `agent-layer/desktop-entries/ristretto.desktop` `95b85d2a13093d51b7bac7c396c0e40737fa4719440bac49895`
- `agent-layer/desktop-entries/thunar.desktop` `2ae2d8c3ceba18a687077385f392be51f164bb84931a6dd6001572f8a85e262c`
- `agent-layer/env.example` `9d541b7139e7d085c192020ffcc1c8f7f864bb5fc614e069b8b88c75f5238a22`
- `agent-layer/install.sh` `ec8bd4d718b60bb0cabb9f2364e239885d7fd3c565caa09f460273a771283dd1`
- `agent-layer/units/oc2-health.service` `245d8a6c06add6e423f16ee2645b828b814577542db0c3064b054feef353825f`
- `agent-layer/units/oc2-health.timer` `c486b2af2fbe6bc22a81241ff31020bdc723f7a36b7c951d58b712dbf8957a7d`
- `agent-layer/units/oc2-patrol.service` `23c4e7e3fb8fdbce875e2291589d07bb309ce9d08dc9a0e42211c641b7a32aa6`
- `agent-layer/units/oc2-patrol.timer` `3cc61523deaabecffaf980bf736683073e8ef85cd148576fff3072ee4f02dcbc`
- `agent-layer/units/oc2-queue.service` `d20f9672794a163715650f5d0ab864dd16e26ed1f9c80c4a3678650b820cd22e`
- `agent-layer/units/oc2-trio.service` `b066f74e0932a9bd3bb510ac0c028ff4d935ea2dbba402c668e6d40c079dca76`
- `agent-layer/units/oc2-watchman.service` `854cdb40a07a63c6a298722d4bc226203cb62b0332dfc8f822505b36c07027e4`

Staged copies re-hashed after copy: 9/9 match the rows above.
OC1 pulls by these shas; nothing here is edited, installed, or run.
