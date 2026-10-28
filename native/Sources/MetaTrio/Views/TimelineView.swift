import SwiftUI

// Event timeline for the current session, newest first. Assessment rows
// are selectable and redisplay that assessment; failure rows show the real
// error and are not selectable (there is no assessment to display).

struct TimelineView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Event timeline")
                .font(.headline)
                .accessibilityAddTraits(.isHeader)
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
}
