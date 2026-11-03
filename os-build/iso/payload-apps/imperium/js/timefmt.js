// Timezone-honest formatting for HN-024. Every timestamp renders
// in the viewer's timezone WITH the zone named — no bare clock
// that could be read as another zone's time. The caller may pass
// an explicit timeZone (tests use it for deterministic checks);
// without one, Intl uses the viewer's own zone.

export function formatTimeWithZone(date, options = {}) {
  const d = date instanceof Date ? date : new Date(date);
  if (Number.isNaN(d.getTime())) return typeof date === "string" ? date : "";
  return new Intl.DateTimeFormat([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    ...(options.timeZone ? { timeZone: options.timeZone } : {}),
    timeZoneName: "short",
  }).format(d);
}

export function zoneName(options = {}) {
  try {
    const parts = new Intl.DateTimeFormat([], {
      timeZone: options.timeZone,
      timeZoneName: "short",
    }).formatToParts(new Date());
    return parts.find((p) => p.type === "timeZoneName")?.value ?? "";
  } catch {
    return "";
  }
}
