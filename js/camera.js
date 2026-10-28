// Camera control over getUserMedia. Browser-only module (not imported by the
// node tests, except for the pure facing-mode helpers, which the node
// camera tests do import). All getUserMedia errors are rethrown untouched
// so the UI can show the honest state (permission denied, no camera
// found, and so on) instead of a generic failure.

export function cameraSupported() {
  return typeof navigator !== "undefined" &&
    !!navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === "function";
}

// The two facings the UI offers. "user" is the front camera (selfie view),
// "environment" is the rear camera — the one a phone demo points at the
// scene being assessed. Both are passed as plain preferences, never as
// exact requirements, so a device with only one camera still gets that
// camera instead of failing.
export const CAMERA_FACINGS = ["user", "environment"];

export function isFacingMode(value) {
  return CAMERA_FACINGS.includes(value);
}

export function facingConstraints(facingMode) {
  if (!isFacingMode(facingMode)) {
    throw new Error(`Unknown camera facing: ${String(facingMode)}`);
  }
  return { video: { facingMode }, audio: false };
}

// The native camera downscales frames so the longest side is at most
// this many pixels before JPEG encoding, keeping request bodies
// reasonable; the web capture must do the same, or a phone camera's
// full-resolution frame (several megabytes as a base64 data URL) risks
// the server's request-body cap while the native app sails under it.
export const MAX_FRAME_DIMENSION = 1280;

export class Camera {
  constructor(videoEl) {
    this.videoEl = videoEl;
    this.stream = null;
    this.facingMode = "user";
  }

  get active() {
    return this.stream !== null && this.stream.getVideoTracks().some((t) => t.readyState === "live");
  }

  // Throws the original DOMException on failure (err.name is e.g.
  // "NotAllowedError" or "NotFoundError").
  async start(facingMode = this.facingMode) {
    if (!isFacingMode(facingMode)) {
      throw new Error(`Unknown camera facing: ${String(facingMode)}`);
    }
    if (!cameraSupported()) {
      const err = new Error("getUserMedia is not supported in this browser or context (a secure context, HTTPS or localhost, is required).");
      err.name = "NotSupportedError";
      throw err;
    }
    if (this.stream) return;
    this.facingMode = facingMode;
    this.stream = await navigator.mediaDevices.getUserMedia(facingConstraints(facingMode));
    this.videoEl.srcObject = this.stream;
    await this.videoEl.play();
  }

  // Switches the facing. While the camera is off this only records the
  // choice, so the next Start uses it. While the camera is live it
  // restarts the stream on the new facing; if that start fails, the
  // error propagates and the camera is left off with no stream, exactly
  // like a failed Start — the UI reports it honestly and Start retries
  // with the newly chosen facing.
  async switchFacing(facingMode) {
    if (!isFacingMode(facingMode)) {
      throw new Error(`Unknown camera facing: ${String(facingMode)}`);
    }
    if (!this.active) {
      this.facingMode = facingMode;
      return;
    }
    this.stop();
    await this.start(facingMode);
  }

  stop() {
    if (this.stream) {
      for (const track of this.stream.getTracks()) {
        track.stop();
      }
      this.stream = null;
    }
    this.videoEl.srcObject = null;
  }

  // Draws the current video frame to the given canvas and returns a JPEG
  // data URL. Frames are encoded in memory and only ever sent to the
  // configured assessment endpoint; they are not stored by this app.
  // Native parity: the native camera downscales so the longest side is
  // at most MAX_FRAME_DIMENSION pixels before encoding, and the web
  // capture did not — it sent the sensor's full resolution, so a phone
  // frame could be several megabytes as a base64 data URL and risk the
  // server's request-body cap. Downscale here with the same cap and the
  // same 0.8 quality, keeping the aspect ratio; frames already under
  // the cap pass through at their own size, unchanged.
  captureFrame(canvas, quality = 0.8) {
    if (!this.active) {
      throw new Error("Camera is not active.");
    }
    const width = this.videoEl.videoWidth;
    const height = this.videoEl.videoHeight;
    if (!width || !height) {
      throw new Error("Camera frame is not ready yet (no dimensions).");
    }
    const longestSide = Math.max(width, height);
    const scale = longestSide > MAX_FRAME_DIMENSION ? MAX_FRAME_DIMENSION / longestSide : 1;
    const scaledWidth = Math.max(1, Math.round(width * scale));
    const scaledHeight = Math.max(1, Math.round(height * scale));
    canvas.width = scaledWidth;
    canvas.height = scaledHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(this.videoEl, 0, 0, scaledWidth, scaledHeight);
    return canvas.toDataURL("image/jpeg", quality);
  }
}
