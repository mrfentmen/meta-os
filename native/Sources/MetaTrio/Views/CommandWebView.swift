import SwiftUI
import WebKit

// CommandWebView — the Meta Imperium web app as the native window's
// content. The web UI (index.html + js/ served by server/server.mjs)
// is the single interface: one UI to maintain instead of a native
// re-implementation shadowing it. The backend stays the same local
// server the native assess path already used (default
// http://127.0.0.1:8080), so camera capture, assessment, relay, and
// the queue keep working through the page's own transports.
// Camera access in the page triggers the normal macOS TCC prompt;
// Info.plist already carries NSCameraUsageDescription for it.

struct CommandWebView: NSViewRepresentable {
    /// Server root, e.g. http://127.0.0.1:8080 (no trailing path).
    let rootURL: URL

    /// The web root for an assess endpoint: the same host the native
    /// assess path already uses, with any trailing `/api/assess`
    /// removed (mirrors HealthClient's prefix rule).
    static func root(forAssessEndpoint endpoint: String) -> URL {
        let trimmed = endpoint.trimmingCharacters(in: .whitespacesAndNewlines)
        let base = trimmed.isEmpty ? "http://127.0.0.1:8080" : trimmed
        let dropped = base.hasSuffix("/api/assess")
            ? String(base.dropLast("/api/assess".count))
            : base
        return URL(string: dropped) ?? URL(string: "http://127.0.0.1:8080")!
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.preferences.javaScriptEnabled = true
        config.mediaTypesRequiringUserActionForPlayback = []
        let view = WKWebView(frame: .zero, configuration: config)
        view.navigationDelegate = context.coordinator
        view.load(URLRequest(url: rootURL, cachePolicy: .reloadIgnoringLocalCacheData))
        context.coordinator.lastLoaded = rootURL
        return view
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {
        // Follow endpoint changes (e.g. the user points the app at a
        // different backend in Settings): reload only when the root
        // actually changed, never on every SwiftUI pass.
        if context.coordinator.lastLoaded != rootURL {
            nsView.load(URLRequest(url: rootURL, cachePolicy: .reloadIgnoringLocalCacheData))
            context.coordinator.lastLoaded = rootURL
        }
    }

    final class Coordinator: NSObject, WKNavigationDelegate {
        var lastLoaded: URL?
    }
}
