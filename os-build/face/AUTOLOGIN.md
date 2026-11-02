# Demo autologin switch (face task 21)

Two boot modes, one flag: which page the kiosk opens.

- SHIPPED image (default, in the image bake): kiosk opens
  `login.html`. The user sees the glass card and signs in.
  No password is checked against the system yet (demo build:
  any non-empty password enters; documented on the card).
- AUTOLOGIN (development/demo shortcut, OFF in the shipped
  image): kiosk opens `shell.html` directly, skipping login.
  Enable ONLY for unattended demos: start chromium with
  `http://127.0.0.1:18900/shell.html` instead of `/login.html`.
  The getty-level OS autologin (console `relay`) is independent
  of this and stays ON — the machine boots to a logged-in
  console either way.

Do NOT ship autologin-to-desktop: the login screen is the
product's front door until the boss orders otherwise.
