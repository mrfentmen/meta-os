import AppKit
import AVFoundation
import CoreImage
import CoreMedia
import Foundation

// Camera control over AVFoundation. The capture session feeds the preview
// layer in the UI, and a video-data output keeps the most recent frame so
// the sampler can grab a JPEG on demand. All failures land in an honest
// State (permission denied, no camera, failed with the real message) —
// the UI shows that state and nothing else.
//
// Frames are encoded in memory and only ever sent to the configured
// assessment endpoint; they are not stored by this app.

enum CameraError: LocalizedError {
    case notRunning
    case frameNotReady
    case frameConversionFailed

    var errorDescription: String? {
        switch self {
        case .notRunning:
            return "Camera is not running."
        case .frameNotReady:
            return "Camera frame is not ready yet."
        case .frameConversionFailed:
            return "Could not encode the captured frame as JPEG."
        }
    }
}

final class CameraService: NSObject, ObservableObject {
    /// Which camera the user wants. Front is the built-in Mac camera;
    /// rear is the camera a phone demo points at the scene. On a Mac
    /// this is a preference, never a requirement, exactly like the web
    /// frontend's facingMode: if no device sits at the chosen position,
    /// device(for:) falls back to the default camera instead of failing,
    /// so a single-camera Mac still gets its camera either way.
    enum Facing: String, CaseIterable {
        case front
        case rear

        var avPosition: AVCaptureDevice.Position {
            switch self {
            case .front: return .front
            case .rear: return .back
            }
        }

        /// The web frontend's picker labels, word for word.
        var label: String {
            switch self {
            case .front: return "Front-facing (selfie view)"
            case .rear: return "Rear-facing (point the phone at the scene)"
            }
        }
    }

    enum State: Equatable {
        case idle
        case requestingPermission
        case running
        case stopped
        case denied
        case noCamera
        case failed(String)
    }

    @Published private(set) var state: State = .idle

    /// The facing the next start uses. Changed only through setFacing,
    /// so a change while live restarts the capture on the new facing
    /// instead of silently applying to a later start.
    @Published private(set) var facing: Facing = .front

    /// The session the preview layer renders. Identity is stable for the
    /// lifetime of the app; it simply has no input until start() succeeds.
    let session = AVCaptureSession()

    private let sessionQueue = DispatchQueue(label: "com.metatrio.camera.session")
    private let frameQueue = DispatchQueue(label: "com.metatrio.camera.frames")
    private let videoOutput = AVCaptureVideoDataOutput()
    private var configured = false

    private let frameLock = NSLock()
    private var latestSampleBuffer: CMSampleBuffer?
    private let ciContext = CIContext()

    /// Frames are downscaled so the longest side is at most this many
    /// pixels before JPEG encoding, keeping request bodies reasonable.
    private let maxFrameDimension: CGFloat = 1280
    private let jpegQuality: CGFloat = 0.8

    var isRunning: Bool { state == .running }

    func start() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            configureAndStart()
        case .notDetermined:
            setState(.requestingPermission)
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                guard let self = self else { return }
                if granted {
                    self.configureAndStart()
                } else {
                    self.setState(.denied)
                }
            }
        case .denied, .restricted:
            setState(.denied)
        @unknown default:
            setState(.failed("Unknown camera authorization status."))
        }
    }

    func stop() {
        sessionQueue.async { [weak self] in
            guard let self = self else { return }
            if self.session.isRunning {
                self.session.stopRunning()
            }
        }
        frameLock.lock()
        latestSampleBuffer = nil
        frameLock.unlock()
        setState(.stopped)
    }

    /// Records a new facing. While the camera is off this only records
    /// the choice, which the next start uses. While live it restarts
    /// the capture on the new facing, mirroring the web frontend's
    /// switchFacing (which restarts the stream): the session is stopped,
    /// the old input is removed, and configureAndStart rebuilds the
    /// input for the new facing. A failed restart lands in .failed with
    /// the real message, exactly like a failed start — it never falls
    /// back silently to the old facing while claiming the new one.
    /// Called from the UI, so on the main thread.
    func setFacing(_ newFacing: Facing) {
        facing = newFacing
        guard isRunning else { return }
        sessionQueue.async { [weak self] in
            guard let self = self else { return }
            if self.session.isRunning {
                self.session.stopRunning()
            }
            self.session.beginConfiguration()
            for input in self.session.inputs {
                self.session.removeInput(input)
            }
            self.session.commitConfiguration()
            self.configured = false
            self.frameLock.lock()
            self.latestSampleBuffer = nil
            self.frameLock.unlock()
            DispatchQueue.main.async { [weak self] in
                self?.start()
            }
        }
    }

    /// The device at the chosen position, or the default camera when
    /// none sits there. The fallback is what makes the facing a
    /// preference: a rear pick on a single-camera Mac still opens the
    /// front camera instead of reporting no camera.
    private func device(for facing: Facing) -> AVCaptureDevice? {
        let discovery = AVCaptureDevice.DiscoverySession(
            deviceTypes: [.builtInWideAngleCamera],
            mediaType: .video,
            position: facing.avPosition
        )
        return discovery.devices.first ?? AVCaptureDevice.default(for: .video)
    }

    /// Encodes the most recent frame as a JPEG data URL
    /// ("data:image/jpeg;base64,..."), the image format of the client ->
    /// server contract. Throws CameraError when no frame is available.
    func captureFrameDataURL() throws -> String {
        guard isRunning else {
            throw CameraError.notRunning
        }
        frameLock.lock()
        let sampleBuffer = latestSampleBuffer
        frameLock.unlock()
        guard let sampleBuffer = sampleBuffer,
              let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer)
        else {
            throw CameraError.frameNotReady
        }

        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        let extent = ciImage.extent
        let longestSide = max(extent.width, extent.height)
        let scale = longestSide > maxFrameDimension ? maxFrameDimension / longestSide : 1
        let image = scale < 1
            ? ciImage.transformed(by: CGAffineTransform(scaleX: scale, y: scale))
            : ciImage
        guard let cgImage = ciContext.createCGImage(image, from: image.extent) else {
            throw CameraError.frameConversionFailed
        }
        let bitmap = NSBitmapImageRep(cgImage: cgImage)
        guard let jpeg = bitmap.representation(using: .jpeg, properties: [.compressionFactor: jpegQuality]) else {
            throw CameraError.frameConversionFailed
        }
        return "data:image/jpeg;base64,\(jpeg.base64EncodedString())"
    }

    // MARK: - Session setup

    private func configureAndStart() {
        sessionQueue.async { [weak self] in
            guard let self = self else { return }
            if !self.configured {
                guard let device = self.device(for: self.facing) else {
                    self.setState(.noCamera)
                    return
                }
                self.session.beginConfiguration()
                self.session.sessionPreset = .high
                do {
                    let input = try AVCaptureDeviceInput(device: device)
                    if self.session.canAddInput(input) {
                        self.session.addInput(input)
                    }
                } catch {
                    self.session.commitConfiguration()
                    self.setState(.failed("Could not open the camera: \(error.localizedDescription)"))
                    return
                }
                self.videoOutput.videoSettings = [
                    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
                ]
                self.videoOutput.alwaysDiscardsLateVideoFrames = true
                self.videoOutput.setSampleBufferDelegate(self, queue: self.frameQueue)
                if self.session.canAddOutput(self.videoOutput) {
                    self.session.addOutput(self.videoOutput)
                }
                self.session.commitConfiguration()
                self.configured = true
            }
            if !self.session.isRunning {
                self.session.startRunning()
            }
            self.setState(self.session.isRunning ? .running : .failed("Capture session did not start."))
        }
    }

    private func setState(_ newState: State) {
        if Thread.isMainThread {
            state = newState
        } else {
            DispatchQueue.main.async { [weak self] in
                self?.state = newState
            }
        }
    }
}

extension CameraService: AVCaptureVideoDataOutputSampleBufferDelegate {
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        frameLock.lock()
        latestSampleBuffer = sampleBuffer
        frameLock.unlock()
    }
}
