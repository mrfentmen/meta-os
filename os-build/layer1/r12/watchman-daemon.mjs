// Round 12 watchman daemon for process-death drills. Unlike the CLI it takes an explicit root,
// so a drill can kill and restart it against the same on-disk state.
import fs from "node:fs";
import path from "node:path";
import { createWatchman } from "../../../agents/watchman.mjs";

const [, , root, registryFile, jobsDir] = process.argv;
if (!root || !registryFile || !jobsDir) {
  console.error("usage: watchman-daemon.mjs <root> <registry> <jobs>");
  process.exit(2);
}
const w = createWatchman({ registryFile, root, jobsDir });
fs.writeFileSync(path.join(root, "watchman.pid"), String(process.pid));
let stopping = false;
const stop = () => {
  if (stopping) return;
  stopping = true;
  fs.writeFileSync(path.join(root, "watchman.stopped"), String(Date.now()));
  process.exit(0);
};
process.on("SIGTERM", stop);
process.on("SIGINT", stop);
console.log("watchman-drill: pid " + process.pid);
await w.pollOnce();
if (process.argv.includes("--once")) process.exit(0);
setInterval(() => { w.pollOnce(); }, 50);
