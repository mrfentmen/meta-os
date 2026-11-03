# OC3B-118/123/124 — codec coverage, honestly

Shipped expectation: Xubuntu base decodes open codecs (Theora,
Vorbis, VP9, Opus, H.264 via openh264 where present) out of the box.
NOT covered: proprietary codecs (H.265/HEVC in some containers,
AAC edge cases, DRM streams of any kind).
Gap filler, named exactly once: the `ubuntu-restricted-extras`
metapackage from the Ubuntu archive. Installing it is a policy
decision (patents + phone-home-adjacent fetching at install time),
NOT taken here and NOT recommended silently — owner: Pax/Del.
No test file on this machine can prove decode ability; the honest
proof is OC1 playing the demo film at boot (OC3B-104/119) and
reporting which seconds stutter.
