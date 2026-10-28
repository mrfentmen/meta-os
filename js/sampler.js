// Frame sampler: fires onSample() on a fixed interval, but never overlaps
// requests. If the previous sample has not settled when a tick fires, the
// tick is skipped and counted. This is the "no unbounded polling" guard from
// BRIEF.md section 6. Timers are injectable so the logic is testable in node
// without a camera or a real clock.

export class FrameSampler {
  constructor({
    intervalMs = 3000,
    onSample,
    onError = null,
    onTick = null,
    setIntervalFn = (fn, ms) => setInterval(fn, ms),
    clearIntervalFn = (id) => clearInterval(id),
  } = {}) {
    if (typeof onSample !== "function") {
      throw new TypeError("FrameSampler requires an onSample function");
    }
    if (!(intervalMs > 0)) {
      throw new RangeError("intervalMs must be > 0");
    }
    this.intervalMs = intervalMs;
    this.onSample = onSample;
    this.onError = onError;
    this.onTick = onTick;
    this._setIntervalFn = setIntervalFn;
    this._clearIntervalFn = clearIntervalFn;
    this._timerId = null;
    this.inFlight = false;
    this.tickCount = 0;
    this.sampledCount = 0;
    this.skippedCount = 0;
    this.errorCount = 0;
  }

  get running() {
    return this._timerId !== null;
  }

  start() {
    if (this.running) return;
    this._timerId = this._setIntervalFn(() => {
      // tick() never rejects (errors go to onError), so no unhandled rejection.
      void this.tick();
    }, this.intervalMs);
  }

  stop() {
    if (!this.running) return;
    this._clearIntervalFn(this._timerId);
    this._timerId = null;
  }

  setIntervalMs(ms) {
    if (!(ms > 0)) {
      throw new RangeError("intervalMs must be > 0");
    }
    this.intervalMs = ms;
    if (this.running) {
      this.stop();
      this.start();
    }
  }

  _finish(status) {
    if (this.onTick) {
      try {
        this.onTick(status);
      } catch {
        // A stats observer must never break the sampler loop.
      }
    }
    return status;
  }

  // One sampling attempt. Returns "sampled", "skipped", or "error".
  async tick() {
    this.tickCount += 1;
    if (this.inFlight) {
      this.skippedCount += 1;
      return this._finish("skipped");
    }
    this.inFlight = true;
    try {
      await this.onSample();
      this.sampledCount += 1;
      return this._finish("sampled");
    } catch (err) {
      this.errorCount += 1;
      if (this.onError) {
        try {
          this.onError(err);
        } catch {
          // An error handler must never break the sampler loop.
        }
      }
      return this._finish("error");
    } finally {
      this.inFlight = false;
    }
  }
}
