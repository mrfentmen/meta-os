// Still-image input helpers for the web frontend. A chosen image file is
// read in memory and sent once to the same assessment endpoint as a live
// camera frame; it is never stored by this app. Only the validation and
// downscale helpers are pure; readFileAsDataURL needs the browser's
// FileReader, and decoding a chosen file needs the browser's Image.

import { MAX_FRAME_DIMENSION } from "./camera.js";

export function isSupportedImageFile(file) {
  return (
    !!file &&
    typeof file.type === "string" &&
    file.type.toLowerCase().startsWith("image/")
  );
}

// Draws a decoded image element to the given canvas and returns a JPEG
// data URL. Throws when the image has no dimensions yet (not decoded),
// so the caller can report the honest state instead of sending a blank
// frame. Live-capture parity: the live camera and the prerecorded-video
// path both downscale frames so the longest side is at most
// MAX_FRAME_DIMENSION pixels before encoding, and the still-image path
// did not — it sent the chosen file's original bytes, so a phone photo
// could be several megabytes as a data URL and risk the server's
// request-body cap while a live frame sails under it. Downscale here
// with the same cap and the same 0.8 quality, keeping the aspect ratio;
// images already under the cap pass through at their own size, and the
// caller only re-encodes when the cap actually bites, so a small image
// keeps its original bytes and format.
export function downscaleImageToDataURL(imageEl, canvas, quality = 0.8) {
  const width = imageEl.naturalWidth;
  const height = imageEl.naturalHeight;
  if (!width || !height) {
    throw new Error("Still image is not ready yet (no dimensions).");
  }
  const longestSide = Math.max(width, height);
  const scale = longestSide > MAX_FRAME_DIMENSION ? MAX_FRAME_DIMENSION / longestSide : 1;
  const scaledWidth = Math.max(1, Math.round(width * scale));
  const scaledHeight = Math.max(1, Math.round(height * scale));
  canvas.width = scaledWidth;
  canvas.height = scaledHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(imageEl, 0, 0, scaledWidth, scaledHeight);
  return canvas.toDataURL("image/jpeg", quality);
}

export function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    if (typeof FileReader === "undefined") {
      reject(new Error("This browser does not support reading files."));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () =>
      reject(new Error(reader.error ? reader.error.message : "Could not read the file."));
    reader.onabort = () => reject(new Error("Reading the file was cancelled."));
    reader.readAsDataURL(file);
  });
}
