# ffmpeg in the Meta OS image

The Trio server takes one frame from an RTSP camera through ffmpeg and serves
it as a JPEG (`server/ipcam.mjs`, `/api/ipcam/:id/snapshot`). Without ffmpeg
those routes answer 502 and the boards only show NYCTMC cameras.

## What changed

- `os-build/iso/provision.sh` installs `ffmpeg` in the chroot with the same
  `apt-get` path it already used for calamares and plymouth, skipping the
  install when `command -v ffmpeg` already answers. The skip and the warning
  both print, so a bake that skips packages cannot silently lose it.
- `os-build/face/provision.sh` copies `server/cams.json` into
  `/usr/share/metaos/server` only when the destination is absent, and prints a
  named warning when the host has no ffmpeg.

## The image on this machine (`/tmp/metaos.ext4`, 16 GiB)

Installed with the image mounted through docker, chroot into the mounted
filesystem, `apt-get install -y --no-install-recommends ffmpeg`, then
unmounted. A copy of the image before the install still exists:
`/tmp/metaos.pre-ffmpeg.ext4` (APFS clone, byte-identical to the original).

Read back afterwards with debugfs, no mount:

```
$ debugfs -R "ls -l /usr/bin" /tmp/metaos.ext4 | grep -E "ffmpeg|ffprobe"
 865095  100755 (0)  0  0  330120  5-Apr-2024 17:28 ffmpeg
 865097  100755 (0)  0  0  204064  5-Apr-2024 17:28 ffprobe

$ debugfs -R "cat /var/lib/dpkg/status" /tmp/metaos.ext4 | grep -A2 "^Package: ffmpeg"
Package: ffmpeg
Status: install ok installed
```

`chroot ffmpeg -version` inside the container printed
`ffmpeg version 6.1.1-3ubuntu5`.

`e2fsck -fn` still reports the pre-existing `filetype set` warnings on package
doc directories (`libdecor-0-0`, `libsdl2-2.0-0`, `libavdevice60`, now also
`ffmpeg`). Those entries are created by the package tooling, not by this
install, and no block or inode check failed.

## Not done here

- No boot. The image change was verified by reading the filesystem back, not by
  starting the guest and running ffmpeg.
- No live RTSP camera exists on this machine, so the RTSP socket path of the
  snapshot route is unproven end to end. The ffmpeg JPEG path is proven with a
  file input (see the commit for the Trio snapshot route).
