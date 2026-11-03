# MetaOS recolored icon set — exact file list

No binaries ship here. The ISO build host clones upstream Papirus and runs
`recolor-papirus.sh`, which recolors **only** the files below, in place, then
installs the tree as `/usr/share/icons/MetaOS`.

Regenerate: `./recolor-papirus.sh /tmp/papirus/Papirus /usr/share/icons/MetaOS`

## Scope rule

`SIZE/places/{folder-blue*.svg,user-blue-*.svg}` regular files only.
Upstream: `PapirusDevelopmentTeam/papirus-icon-theme` (shallow clone at build
time; names below are upstream identifiers, shipped unchanged).

## Tone map

| source (Papirus folder-blue) | MetaOS | role |
|---|---|---|
| `#5294e2` | `#1877F2` | folder front (Meta blue) |
| `#4877b1` | `#1360C4` | folder back flap (Meta blue darkened by the 0.81 luminance ratio) |

Neutrals pass through: `#e4e4e4`, `#ffffff`, `#607d8b`, `#4d646f`, `#222c31`, `#1d344f`.

## Sizes

Identical 78-name set verified (per-size md5 `b3de97c6…`) at
`22x22 24x24 32x32 48x48 64x64 96x96 128x128/places/`.
At `16x16/places/` (symbolic set) only `folder-blue.svg` carries folder-blue
tones (single flat `#5294e2`, no back flap) and is recolored; the remaining
symbolic folder icons contain no mapped tones and pass through unchanged.

86 alias symlinks per size dir (e.g. `folder.svg -> folder-blue.svg`,
`folder-open.svg -> folder-blue-open.svg`, `folder-activities.svg ->
folder-blue-activities.svg`) are preserved by `cp -a` and resolve to the
recolored targets automatically — they are NOT separate recolor entries.

## The 78 recolored basenames

folder-blue-activities.svg
folder-blue-android.svg
folder-blue-apple.svg
folder-blue-applications.svg
folder-blue-arduino.svg
folder-blue-backup.svg
folder-blue-books.svg
folder-blue-cd.svg
folder-blue-code.svg
folder-blue-development.svg
folder-blue-docker.svg
folder-blue-documents-open.svg
folder-blue-documents.svg
folder-blue-download-open.svg
folder-blue-download.svg
folder-blue-drag-accept.svg
folder-blue-dropbox.svg
folder-blue-favorites.svg
folder-blue-games.svg
folder-blue-git.svg
folder-blue-github.svg
folder-blue-gitlab.svg
folder-blue-gnome.svg
folder-blue-google-drive.svg
folder-blue-image-people.svg
folder-blue-important.svg
folder-blue-java.svg
folder-blue-kde.svg
folder-blue-linux.svg
folder-blue-locked.svg
folder-blue-mail-cloud.svg
folder-blue-mail.svg
folder-blue-mega.svg
folder-blue-meocloud.svg
folder-blue-music-open.svg
folder-blue-music.svg
folder-blue-network.svg
folder-blue-nextcloud.svg
folder-blue-notes.svg
folder-blue-obsidian.svg
folder-blue-onedrive.svg
folder-blue-open.svg
folder-blue-owncloud.svg
folder-blue-pcloud.svg
folder-blue-photo.svg
folder-blue-pictures-open.svg
folder-blue-pictures.svg
folder-blue-print.svg
folder-blue-private.svg
folder-blue-projects-open.svg
folder-blue-projects.svg
folder-blue-publicshare-open.svg
folder-blue-recent.svg
folder-blue-remote-open.svg
folder-blue-remote.svg
folder-blue-script.svg
folder-blue-snap.svg
folder-blue-steam.svg
folder-blue-sync.svg
folder-blue-syncthing.svg
folder-blue-systemd.svg
folder-blue-tar.svg
folder-blue-templates-open.svg
folder-blue-templates.svg
folder-blue-torrent.svg
folder-blue-unlocked.svg
folder-blue-vbox.svg
folder-blue-video.svg
folder-blue-videos-open.svg
folder-blue-visiting.svg
folder-blue-vmware.svg
folder-blue-wifi.svg
folder-blue-wine.svg
folder-blue-yandex-disk.svg
folder-blue.svg
user-blue-desktop.svg
user-blue-home-open.svg
user-blue-home.svg

## Explicitly OUT of scope (incidentally contain `#5294e2`, never recolored)

12 app-icon basenames across `apps/` (all sizes), verified untouched by the
scoped script:

applications-interfacedesign.svg
caja-actions.svg
com.github.zren.alphablackcontrol.svg
com.yuenhoe.filedrawer.svg
distributor-logo-solus.svg
emily-is-away-too.svg
emily-is-away.svg
fokus.svg
kfoldersync.svg
papirus-folders-gui.svg
system-file-manager.svg
winefile.svg

(A blanket find/replace across the whole tree would corrupt these
third-party marks — that is why the script is scoped to `places/`.)
