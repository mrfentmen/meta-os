import AppKit
import AVKit
import SwiftUI

// ContentView — the Meta Imperium web app as the native window.
// The web UI (index.html + js/ served by server/server.mjs) is the
// single interface now: one UI to maintain instead of a native
// re-implementation shadowing it. Camera capture, assessment, relay,
// and the queue keep working through the page: the backend is the
// same local server the native assess path already used.
// Camera access in the page triggers the normal macOS TCC prompt;
// Info.plist already carries NSCameraUsageDescription for it.

struct ContentView: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        CommandWebView(rootURL: CommandWebView.root(forAssessEndpoint: model.trimmedEndpoint))
            .frame(minWidth: 1020, minHeight: 660)
    }
}


struct PanelHeading: View {
    let title: String
    let isIgnis: Bool
    let isVigiles: Bool
    let isMedicus: Bool

    var body: some View {
        if isIgnis {
            HStack(alignment: .top, spacing: 10) {
                Rectangle()
                    .fill(Color(red: 217 / 255, green: 43 / 255, blue: 43 / 255))
                    .frame(width: 3)
                Text(title.uppercased())
                    .font(.system(size: 15, weight: .bold, design: .monospaced))
                    .tracking(1.8)
            }
            .accessibilityLabel(title)
        } else if isVigiles {
            // OPS-CONSOLE-7: Vigiles renders the web OPS-CONSOLE-6
            // console treatment — uppercased monospaced 15pt bold
            // with 1.8pt tracking (0.12em of 15pt) and a 3pt
            // Vigiles-blue (#4f7ec2) leading tick with 10pt of room
            // before the text — the Ignis branch's shape in Vigiles
            // blue. Medicus takes its own OPS-CONSOLE-10 branch below,
            // and the Vigiles branch keeps the original title as its
            // accessibility label, as the Ignis branch does.
            HStack(alignment: .top, spacing: 10) {
                Rectangle()
                    .fill(Color(red: 79 / 255, green: 126 / 255, blue: 194 / 255))
                    .frame(width: 3)
                Text(title.uppercased())
                    .font(.system(size: 15, weight: .bold, design: .monospaced))
                    .tracking(1.8)
            }
            .accessibilityLabel(title)
        } else if isMedicus {
            // OPS-CONSOLE-10: Medicus renders the web Medicus
            // ops-console rule — uppercased plain 15pt bold with
            // 1.2pt tracking (0.08em of 15pt). The web rule sets no
            // mono face and no left border, so this branch carries
            // neither: no mono face, no tick shape, and no
            // green restyle of anything else. Size and weight stay
            // 15pt bold, and the original title stays the
            // accessibility label, as the Ignis and Vigiles branches
            // do. Body, status, and button treatments are later
            // slices; this slice is headings only.
            Text(title.uppercased())
                .font(.system(size: 15, weight: .bold))
                .tracking(1.2)
                .accessibilityLabel(title)
        } else {
            Text(title)
                .font(.system(size: 15, weight: .bold))
        }
    }
}
