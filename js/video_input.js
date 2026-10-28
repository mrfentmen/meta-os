// Prerecorded-video input helpers for the web frontend. A chosen video
// file is played in the page; tapping "Assess this frame" sends only the
// frame showing at that moment — one JPEG, through the same endpoint,
// validation, history entry, and session-log entry as a live camera
// frame. The whole video is never sent, and nothing is stored by this
// app: the object URL lives in memory and is revoked by Reset (and when
// a different file is chosen). Only the validation and frame-capture
// helpers are pure enough for the node tests; object URLs need the
// browser.

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
export function captureVideoFrame(videoEl, canvas, quality = 0.8) {
  const width = videoEl.videoWidth;
  const height = videoEl.videoHeight;
  if (!width || !height) {
    throw new Error("Video frame is not ready yet (no dimensions).");
  }
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(videoEl, 0, 0, width, height);
  return canvas.toDataURL("image/jpeg", quality);
}
