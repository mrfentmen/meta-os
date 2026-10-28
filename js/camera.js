// Camera control over getUserMedia. Browser-only module (not imported by the
// node tests). All getUserMedia errors are rethrown untouched so the UI can
// show the honest state (permission denied, no camera found, and so on)
// instead of a generic failure.

export function cameraSupported() {
  return typeof navigator !== "undefined" &&
    !!navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === "function";
}

export class Camera {
  constructor(videoEl) {
    this.videoEl = videoEl;
    this.stream = null;
  }

  get active() {
    return this.stream !== null && this.stream.getVideoTracks().some((t) => t.readyState === "live");
  }

  // Throws the original DOMException on failure (err.name is e.g.
  // "NotAllowedError" or "NotFoundError").
  async start() {
    if (!cameraSupported()) {
      const err = new Error("getUserMedia is not supported in this browser or context (a secure context, HTTPS or localhost, is required).");
      err.name = "NotSupportedError";
      throw err;
    }
    if (this.stream) return;
    this.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user" },
      audio: false,
    });
    this.videoEl.srcObject = this.stream;
    await this.videoEl.play();
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
  captureFrame(canvas, quality = 0.8) {
    if (!this.active) {
      throw new Error("Camera is not active.");
    }
    const width = this.videoEl.videoWidth;
    const height = this.videoEl.videoHeight;
    if (!width || !height) {
      throw new Error("Camera frame is not ready yet (no dimensions).");
    }
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(this.videoEl, 0, 0, width, height);
    return canvas.toDataURL("image/jpeg", quality);
  }
}
