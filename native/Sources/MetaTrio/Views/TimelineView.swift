import SwiftUI

// Event timeline for the current session, newest first. Assessment rows
// are selectable and redisplay that assessment; failure rows show the real
// error and are not selectable (there is no assessment to display).

struct TimelineView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            // IGNIS-UI-34: timeline panel title at 15pt bold, the
            // native counterpart to the web .panel h2 rule (15px
            // weight 700). Until now the title used .headline (17pt
            // semibold), so it read larger and one step lighter than
            // the web history title while the Latest panel title
            // (UI-23) already matched its own 15px web rule. The
            // size and weight are the only changes: the wording and
            // the header trait are untouched.
            Text("Event timeline")
                .font(.system(size: 15, weight: .bold))
                .accessibilityAddTraits(.isHeader)
            // Web parity: the web history panel carries this note, and
            // without it nothing in the native panel says the rows can
            // be tapped. Failure rows stay plain text — they have no
            // assessment to show.
            // IGNIS-UI-34: timeline intro note at 13pt, the native
            // counterpart to the web .note rule (13px, muted).
            // Until now the note used .caption (12pt), so it read
            // one point smaller than the web panel's notes while the
            // still-image, video, header, camera-facing, and Settings
            // notes (UI-25 through UI-33) already matched their own
            // 13px web rules. The size is the only change: the muted
            // color, the wrapping, and the wording are untouched.
            Text("Tap an assessment row to view that assessment again in the Latest assessment panel. Failure rows have no assessment to show.")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            if model.timeline.isEmpty {
                if model.analysisRunning {
                    Text("Analysis is running — assessments and errors will appear here as they arrive.")
                        .foregroundStyle(.secondary)
                } else {
                    Text("No events yet. Assessments and errors will appear here.")
                        .foregroundStyle(.secondary)
                }
            } else {
                List(model.timeline) { item in
                    row(for: item)
                }
                .listStyle(.plain)
            }
        }
    }

    @ViewBuilder
    private func row(for item: TimelineItem) -> some View {
        let content = VStack(alignment: .leading, spacing: 2) {
            HStack(alignment: .firstTextBaseline, spacing: 6) {
                Text(item.title)
                    .fontWeight(.semibold)
                    .foregroundStyle(titleColor(for: item))
                Text(item.product.config.displayName)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                Text(item.timestamp)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            if !item.detail.isEmpty {
                Text(item.detail)
                    .font(.callout)
                    .lineLimit(3)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        // UI-4: product-accent leading rule, the native counterpart to
        // the web history edge (border-left in the entry's product
        // accent, not its status color). The rule color comes from the
        // row's own product, so rows keep their product under any
        // selection, and it sits on `content` so both assessment and
        // failure rows carry it, exactly like the web history items.
        .padding(.leading, 10)
        .overlay(alignment: .leading) {
            Rectangle()
                .fill(accentColor(for: item.product))
                .frame(width: 3)
        }
        // One VoiceOver item per row: title, product, timestamp, detail.
        // Assessment rows stay buttons; failure rows stay plain text.
        .accessibilityElement(children: .combine)

        switch item.kind {
        case .assessment:
            Button {
                model.display(item)
            } label: {
                content
            }
            .buttonStyle(.plain)
        case .failure:
            content
        }
    }

    private func titleColor(for item: TimelineItem) -> Color {
        switch item.kind {
        case .assessment:
            return .primary
        case .failure:
            return .red
        }
    }

    // Row accent from the row's own product, mirroring ContentView's
    // selected-product accent mapping — the timeline keeps each row's
    // product, it never re-tints to the current selection.
    private func accentColor(for product: ProductID) -> Color {
        switch product.config.accentColorName {
        case "blue": return .blue
        case "red": return .red
        case "green": return .green
        default: return .accentColor
        }
    }
}
