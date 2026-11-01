// Demo-mode detection for HN-022. Pure: the caller supplies the
// query string, so node tests run without a browser. Only the
// exact flag ?demo=1 counts — ?demo, ?demo=0, and anything else
// stay live, so demo data can never leak into the live view by
// a sloppy flag.

export function isDemoMode(search) {
  try {
    return new URLSearchParams(search).get("demo") === "1";
  } catch {
    return false;
  }
}
