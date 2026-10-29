import AppKit

// VoiceOver announcements for new results, the native match for the web
// frontend's polite live regions (the backend-status line and the
// latest-assessment panel, and the backend-health line). A new validated
// assessment, a backend failure, or a settled backend-health result is
// announced without stealing focus, so a VoiceOver user
// learns about it as it arrives instead of having to poll the timeline.
// A frame-capture failure is announced too, with its own message: the
// web frontend's live backend-status line reads a capture failure aloud
// the moment it is set, and the native app used to set the same error
// status silently, so a VoiceOver user never heard that a tick had
// failed. A capture failure is not a backend failure — no request was
// made — so it is announced verbatim, never prefixed with "Model backend
// not connected". A session-log export failure is announced the same
// way: it sets the status bar to an error, and it used to do so
// silently, so a VoiceOver user never heard that the export they just
// asked for had failed — and the backend may be perfectly fine, so
// prefixing it as a backend failure would mislead. Re-inspecting a past timeline row deliberately does
// NOT announce: the web history is not a live region either, so a
// redisplayed past result can never sound like a new one.
//
// Posting an announcement when VoiceOver is not running is harmless:
// the notification simply has no listener. Nothing here invents a
// result — both call sites announce only what the app already
// displayed from a real server response or a real error. A
// still-image read failure is announced the same way as an export
// failure: it sets only the panel's error text, it involves no
// backend and no frame capture, so it is posted verbatim, never
// through backendFailure or captureFailure, either of which would
// misdescribe what went wrong. A successfully chosen input is
// announced the same way, in the panel's own ready words: the web
// frontend's image-state and video-state lines are polite live
// regions, so choosing a file reads its "ready" line aloud there, but
// the native panels used to set the same ready text silently — a
// VoiceOver user who had just picked a file heard nothing confirming
// the Assess button was now enabled, while only the failure case was
// announced. Clearing an input stays silent: the user tapped Clear
// themselves, and nothing new becomes possible.
enum AccessibilityAnnouncement {
    static func post(_ message: String) {
        guard !message.isEmpty else { return }
        let element: Any = NSApp.keyWindow ?? NSApp
        NSAccessibility.post(
            element: element,
            notification: .announcementRequested,
            userInfo: [.announcement: message]
        )
    }

    /// Announcement for a newly arrived validated assessment.
    static func newAssessment(productDisplayName: String, response: AssessmentResponse) {
        var message = "New assessment from \(productDisplayName): " +
            "\(response.assessment.category). \(response.assessment.summary)"
        if response.assessment.requiresHumanReview {
            message += " Requires human review."
        }
        post(message)
    }

    /// Announcement for a backend failure, using the same words as the
    /// status line the web frontend's live region reads.
    static func backendFailure(message: String) {
        post("Model backend not connected: \(message)")
    }

    /// Announcement for a frame-capture failure (live sample or video
    /// frame extraction). The message is already the status line's own
    /// wording ("Frame capture failed: …" / "Video frame capture
    /// failed: …"), so it is posted verbatim: calling backendFailure
    /// here would wrongly tell the listener the backend was not
    /// connected, when no request was ever made.
    static func captureFailure(message: String) {
        post(message)
    }

    /// Announcement for a session-log export failure, in the status
    /// line's own words. The export touches no backend and sends no
    /// frame, so it is posted verbatim, never through backendFailure:
    /// calling that here would wrongly tell the listener the backend
    /// was not connected, when the failure was writing the file.
    static func exportFailure(_ message: String) {
        post(message)
    }

    /// Announcement for a still-image read failure, in the panel's own
    /// words. Reading the chosen file touches no backend and captures
    /// no frame, so it is posted verbatim, never through
    /// backendFailure or captureFailure: either would misdescribe a
    /// file the app could not decode as a backend or camera problem.
    static func inputError(_ message: String) {
        post(message)
    }

    /// Announcement for a successfully chosen still image or video, in
    /// the panel's own ready words. Choosing the file touches no
    /// backend and captures no frame, so it is posted verbatim, never
    /// through backendFailure or captureFailure: either would
    /// misdescribe a file the app just accepted as a backend or
    /// camera problem.
    static func inputReady(_ message: String) {
        post(message)
    }

    /// Announcement for a settled backend-health result, success or
    /// failure, in the health line's own words. Web parity: the web
    /// frontend's health line is a polite live region, so a VoiceOver
    /// user hears the result there; the native app used to set the
    /// same line silently, so the result never reached a VoiceOver
    /// user at all. The interim "Checking …" text is deliberately
    /// not announced — only the settled result is — and the call site
    /// posts it only inside the view-generation guard, so a result
    /// from before a Reset Session is never announced as current.
    static func healthResult(_ message: String) {
        post(message)
    }
}
