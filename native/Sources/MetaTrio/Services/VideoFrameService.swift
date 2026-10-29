import AppKit
import AVFoundation

// VideoFrameService: prerecorded-video input for the native app (web
// parity with js/video_input.js). It extracts exactly one frame — the
// frame at the playback position the user paused on — as a JPEG data
// URL, so the shared submit path can send it like a live frame. The
// whole video is never sent, never copied, and never stored by this
// app: the AVAsset reads the user's file in place, and only the single
// extracted JPEG leaves the machine, inside the assessment request.
// Live-capture parity: the extracted frame is downscaled so its
// longest side is at most 1280 px and encoded at JPEG 0.8, exactly
// like the live camera, the native still-image path, and the web
// video path — a 4K clip's frame used to go out at full size with the
// default JPEG quality, several megabytes as a base64 data URL, while
// every other frame path sailed under the server's request-body cap.
//
// Throws VideoFrameError with a plain message for every failure mode
// (no video track, unplayable file, frame generation failure), so the
// caller can log and display the honest state instead of inventing a
// frame. Requires macOS 13+ (the package's platform floor) for the
// async AVAsset load API.

enum VideoFrameError: Error, LocalizedError {
    case noVideoTrack
    case frameGenerationFailed(String)
    case jpegEncodingFailed

    var errorDescription: String? {
        switch self {
        case .noVideoTrack:
            return "That file has no video track to assess."
        case .frameGenerationFailed(let detail):
            return "Could not extract a frame from that video: \(detail)"
        case .jpegEncodingFailed:
            return "Could not encode the extracted video frame as a JPEG."
        }
    }
}

enum VideoFrameService {
    /// Frames are downscaled so the longest side is at most this many
    /// pixels before JPEG encoding, keeping request bodies reasonable —
    /// the same cap the live camera, the still-image path, and the web
    /// video path use, at the same 0.8 quality.
    private static let maxFrameDimension: CGFloat = 1280
    private static let jpegQuality: CGFloat = 0.8

    /// Extracts the frame at `seconds` into the video as a JPEG data
    /// URL. Exact-frame tolerances (.zero) are requested so the frame
    /// assessed is the one showing at the paused playback position,
    /// not a nearby keyframe.
    static func jpegDataURL(for url: URL, at seconds: Double) async throws -> String {
        let asset = AVAsset(url: url)
        let videoTracks = try await asset.loadTracks(withMediaType: .video)
        guard !videoTracks.isEmpty else {
            throw VideoFrameError.noVideoTrack
        }
        let generator = AVAssetImageGenerator(asset: asset)
        generator.appliesPreferredTrackTransform = true
        generator.requestedTimeToleranceBefore = .zero
        generator.requestedTimeToleranceAfter = .zero
        let time = CMTime(seconds: seconds, preferredTimescale: 600)
        let cgImage: CGImage
        do {
            cgImage = try generator.copyCGImage(at: time, actualTime: nil)
        } catch {
            throw VideoFrameError.frameGenerationFailed(error.localizedDescription)
        }
        let image = NSImage(
            cgImage: cgImage,
            size: NSSize(width: cgImage.width, height: cgImage.height)
        )
        // Downscale only when the cap actually bites; a frame already
        // under it keeps its size, exactly like the still-image path.
        var source = image
        let longestSide = max(image.size.width, image.size.height)
        if longestSide > maxFrameDimension {
            let scale = maxFrameDimension / longestSide
            let newSize = NSSize(width: image.size.width * scale, height: image.size.height * scale)
            let resized = NSImage(size: newSize)
            resized.lockFocus()
            image.draw(
                in: NSRect(origin: .zero, size: newSize),
                from: NSRect(origin: .zero, size: image.size),
                operation: .copy,
                fraction: 1.0
            )
            resized.unlockFocus()
            source = resized
        }
        guard let tiff = source.tiffRepresentation,
              let rep = NSBitmapImageRep(data: tiff),
              let jpeg = rep.representation(using: .jpeg, properties: [.compressionFactor: jpegQuality])
        else {
            throw VideoFrameError.jpegEncodingFailed
        }
        return "data:image/jpeg;base64,\(jpeg.base64EncodedString())"
    }
}
