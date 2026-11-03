// Prerecorded-video input helpers for the web frontend. A chosen video
// file is played in the page; tapping "Assess this frame" sends only the
// frame showing at that moment — one JPEG, through the same endpoint,
// validation, history entry, and session-log entry as a live camera
// frame. The whole video is never sent, and nothing is stored by this
// app: the object URL lives in memory and is revoked by Reset (and when
// a different file is chosen). Only the validation and frame-capture
// helpers are pure enough for the node tests; object URLs need the
// browser.

import { MAX_FRAME_DIMENSION } from "./camera.js";

export function isSupportedVideoFile(file) {
  return (
    !!file &&
    typeof file.type === "string" &&
    file.type.toLowerCase().startsWith("video/")
  );
}

// Draws the video element's current frame to the given canvas and
// returns a JPEG data URL. Throws when the video has no dimensions yet
// (metadata not loaded, or nothing playable), so the caller can report
// the honest state instead of sending a blank frame.
// Live-capture parity: the live camera downscales frames so the
// longest side is at most MAX_FRAME_DIMENSION pixels before encoding,
// and this path did not — it sent the recorded clip's full resolution,
// so a 4K clip's frame could be several megabytes as a base64 data URL
// and risk the server's request-body cap while a live frame sails
// under it. Downscale here with the same cap and the same 0.8 quality,
// keeping the aspect ratio; frames already under the cap pass through
// at their own size, unchanged.
export function captureVideoFrame(videoEl, canvas, quality = 0.8) {
  const width = videoEl.videoWidth;
  const height = videoEl.videoHeight;
  if (!width || !height) {
    throw new Error("Video frame is not ready yet (no dimensions).");
  }
  const longestSide = Math.max(width, height);
  const scale = longestSide > MAX_FRAME_DIMENSION ? MAX_FRAME_DIMENSION / longestSide : 1;
  const scaledWidth = Math.max(1, Math.round(width * scale));
  const scaledHeight = Math.max(1, Math.round(height * scale));
  canvas.width = scaledWidth;
  canvas.height = scaledHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(videoEl, 0, 0, scaledWidth, scaledHeight);
  return canvas.toDataURL("image/jpeg", quality);
}
