MetaOS vendored font licences — skeleton (R2-T1, 2026-11-04).

No binaries are vendored yet: this host is offline for font fetching per lane
orders (no downloads performed), so there is nothing to attach licence texts
to. At vendoring time, drop each family's OFL-1.1 text here as:

  LICENSES/OFL-Inter.txt            <- https://github.com/rsms/inter/blob/master/LICENSE.txt
  LICENSES/OFL-SourceSans3.txt      <- https://github.com/adobe-fonts/source-sans/blob/release/LICENSE.md
  LICENSES/OFL-JetBrainsMono.txt   <- https://github.com/JetBrains/JetBrainsMono/blob/master/OFL.txt
  LICENSES/OFL-SpaceGrotesk.txt     <- https://github.com/floriankarsten/space-grotesk/blob/master/OFL.txt
  LICENSES/OFL-Archivo.txt          <- https://github.com/Omnibus-Type/Archivo/blob/master/OFL.txt
  LICENSES/OFL-IBMPlexSans.txt      <- https://github.com/IBM/plex/blob/master/LICENSE.txt

All six families are declared SIL Open Font License 1.1 (see MANIFEST.txt for
the per-file record). install.sh --check does not gate on this directory, but
the image must not ship without these six texts present.
