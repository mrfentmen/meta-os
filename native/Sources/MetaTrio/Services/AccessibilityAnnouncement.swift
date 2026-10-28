import AppKit

// VoiceOver announcements for new results, the native match for the web
// frontend's polite live regions (the backend-status line and the
// latest-assessment panel). A new validated assessment or a backend
// failure is announced without stealing focus, so a VoiceOver user
// learns about it as it arrives instead of having to poll the timeline.
// Re-inspecting a past timeline row deliberately does NOT announce:
// the web history is not a live region either, so a redisplayed past
// result can never sound like a new one.
//
// Posting an announcement when VoiceOver is not running is harmless:
// the notification simply has no listener. Nothing here invents a
// result — both call sites announce only what the app already
// displayed from a real server response or a real error.
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
}
