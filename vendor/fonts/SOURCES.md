# Vendored fonts

Every file here is served from the same origin as the apps. No page makes a
network request for type. All families are licensed under the SIL Open Font
License 1.1; each directory carries the upstream `OFL.txt` verbatim.

| Directory | Family | Files | Used by |
|---|---|---|---|
| `Archivo/` | Archivo (variable) | `Archivo-var.woff2` | Vigiles |
| `InstrumentSans/` | Instrument Sans (variable) | `InstrumentSans-var.woff2` | Ignis |
| `SourceSans3/` | Source Sans 3 (variable) | `SourceSans3-var.woff2` | Medicus |
| `Outfit/` | Outfit (variable) | `Outfit-var.woff2` | Musica |
| `SplineSans/` | Spline Sans (variable) | `SplineSans-var.woff2` | Science Lab |
| `SplineSansMono/` | Spline Sans Mono (variable) | `SplineSansMono-var.woff2` | Science Lab data |
| `SpaceGrotesk/` | Space Grotesk (variable) | `SpaceGrotesk-var.woff2` | Officina |
| `IBMPlexSans/` | IBM Plex Sans (variable) | `IBMPlexSans-var.woff2` | Aegis |
| `Manrope/` | Manrope (variable) | `Manrope-var.woff2` | Nuntius |
| `JetBrainsMono/` | JetBrains Mono (variable) | `JetBrainsMono-var.woff2` | Vigiles data |
| `AzeretMono/` | Azeret Mono (variable) | `AzeretMono-var.woff2` | Ignis data |
| `SourceCodePro/` | Source Code Pro (variable) | `SourceCodePro-var.woff2` | Medicus data |
| `DMMono/` | DM Mono | `DMMono-400.woff2`, `DMMono-500.woff2` | Musica data |
| `SpaceMono/` | Space Mono | `SpaceMono-400.woff2` | Officina data |
| `IBMPlexMono/` | IBM Plex Mono | `IBMPlexMono-400/500/600.woff2` | Aegis data |
| `FragmentMono/` | Fragment Mono | `FragmentMono-400.woff2` | Nuntius data |

## Provenance

The woff2 files were fetched from the Fontsource CDN. The upstream project is
the Google Fonts repository, where each family lives under `ofl/<family>/` with
its OFL. The OFL files here are the exact upstream copies.

The old Latin-only `woff2` files are used instead of full TTF/OTF so an offline
image adds well under 1 MB. Latin-only is sufficient because every UI string in
this repo is English.

## Why these families

All eight primaries are modern neo-grotesque or geometric sans faces, chosen
for legibility at 11-13 px, wide weight coverage, and distinct silhouettes:

- Archivo: sturdy civic grotesque, reads as an operational console.
- Instrument Sans: neutral contemporary sans with a slightly narrow fit.
- Source Sans 3: humanist, clinical, excellent at small sizes.
- Outfit: geometric with a clean music/creative feel.
- Spline Sans: technical but soft, suits a lab tool.
- Space Grotesk: engineering character without becoming decorative.
- IBM Plex Sans: institutional and precise, right for a security record.
- Manrope: open, conversational, right for messages.

No serif, script, or decorative display face is part of the interface.
