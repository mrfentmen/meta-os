import AVFoundation
import SwiftUI

// Live camera preview: an AVCaptureVideoPreviewLayer hosted in an NSView.
// The layer renders the session directly, so the preview is live whenever
// the session is running, independent of SwiftUI state updates.

final class PreviewContainerView: NSView {
    override func layout() {
        super.layout()
        layer?.frame = bounds
    }
}

struct CameraPreviewView: NSViewRepresentable {
    let session: AVCaptureSession

    func makeNSView(context: Context) -> PreviewContainerView {
        let view = PreviewContainerView()
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.videoGravity = .resizeAspectFill
        view.wantsLayer = true
        view.layer = previewLayer
        return view
    }

    func updateNSView(_ nsView: PreviewContainerView, context: Context) {
        if let previewLayer = nsView.layer as? AVCaptureVideoPreviewLayer,
           previewLayer.session !== session {
            previewLayer.session = session
        }
        nsView.needsLayout = true
    }
}
