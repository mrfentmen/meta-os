import SwiftUI

// MetaTrio — one app, three products (Meta Sentinel / Meta Ember /
// Meta Sanitas) on one shared foundation, per MASTER_DIRECTIVE_V2.md.

@main
struct MetaTrioApp: App {
    @StateObject private var model = AppModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(model)
        }
    }
}
