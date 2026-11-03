# OC3B-076 — settings panels inventory (from shipped config, not memory)

Xfce settings are xfconf channels; the image ships these (theme lane,
on main): xsettings (theme/fonts), xfce4-panel, light-locker,
xfce4-power-manager, xfce4-desktop (backdrop channel). The manager
itself (`xfce4-settings-manager`, my §9 entry) enumerates at runtime:
Appearance, Display, Keyboard, Mouse, Window Manager, Desktop,
Panel, Power Manager, Notifications, Accessibility (upstream default
set — see a11y note), plus any installed extras.
Panels with NO shipped config on main: keyboard, mouse, notifications
— upstream defaults apply. Nothing here invents a panel.
