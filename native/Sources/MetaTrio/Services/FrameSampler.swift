import Foundation

// Frame sampler: fires onSample on a fixed interval, but never overlaps
// requests. If the previous sample has not settled when a tick fires, the
// tick is skipped and counted. This is the "no unbounded polling" guard:
// the sampling cadence can never outrun the endpoint. Ticks, samples,
// skips, and errors are counted and mirrored to the UI via onTick.

@MainActor
final class FrameSampler {
    var onSample: (() async throws -> Void)?
    var onTick: (() -> Void)?

    private(set) var tickCount = 0
    private(set) var sampledCount = 0
    private(set) var skippedCount = 0
    private(set) var errorCount = 0

    private(set) var intervalSeconds: TimeInterval
    private var timer: Timer?
    private var inFlight = false

    init(intervalSeconds: TimeInterval = 3) {
        self.intervalSeconds = intervalSeconds
    }

    var isRunning: Bool { timer != nil }

    func start() {
        guard timer == nil else { return }
        timer = Timer.scheduledTimer(withTimeInterval: intervalSeconds, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            Task { @MainActor in
                await self.tick()
            }
        }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
    }

    func setInterval(_ seconds: TimeInterval) {
        guard seconds > 0 else { return }
        intervalSeconds = seconds
        if isRunning {
            stop()
            start()
        }
    }

    /// One sampling attempt. Errors thrown by onSample are counted, never
    /// swallowed silently: onSample itself is responsible for surfacing
    /// and logging the failure (AppModel does both) before rethrowing.
    func tick() async {
        tickCount += 1
        if inFlight {
            skippedCount += 1
            onTick?()
            return
        }
        guard let onSample = onSample else {
            onTick?()
            return
        }
        inFlight = true
        do {
            try await onSample()
            sampledCount += 1
        } catch {
            errorCount += 1
        }
        inFlight = false
        onTick?()
    }
}
