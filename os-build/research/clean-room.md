# Clean-room rule card (OS-101)

Study, describe, write fresh. Never paste.

1. Read the original (Debian behavior, other systems' docs).
2. Close it. Describe the BEHAVIOR in plain words in our own
   research files (that description is the spec).
3. Write OUR code from the description only — no original text,
   identifiers, or comments cross over.
4. The grep gate (OS-219): search our kernel for comments or
   identifiers that only make sense copied from Linux source;
   every hit is explained or removed.
5. GPL is red (OS-117): an idea may inspire; GPL code never
   enters `kernel/`, `services/`, or `lobster/`. Dual-license
   fonts/data are allowed only with the license file carried
   (the Terminus table precedent: FONT_TABLE_LICENSE.md).
6. Vendored code keeps its license file beside it, named.
7. When in doubt, the cautious reading wins and the doubt is
   written down (this file grows; it never shrinks silently).
