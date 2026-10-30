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
            // OPS-CONSOLE-2: panel heading (see PanelHeading in
            // ContentView) — Ignis and Vigiles render their console
            // treatments, Sanitas the plain 15pt bold title as before.
            PanelHeading(title: "Event timeline", isIgnis: model.selectedProduct == .ignis, isVigiles: model.selectedProduct == .vigiles)
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
                // IGNIS-UI-47: empty-state notes at 13pt, the native
                // counterparts to the web #history-empty note (class
                // .note at 13px, muted). Until now both notes were
                // plain Texts at the default body size, so they read
                // four points larger than the web note while the
                // timeline intro note just above them (UI-34) already
                // matched its own 13px web rule. The size is the only
                // change: the muted color and the wording — which
                // match the web strings exactly — are untouched.
                if model.analysisRunning {
                    Text("Analysis is running — assessments and errors will appear here as they arrive.")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                } else {
                    Text("No events yet. Assessments and errors will appear here.")
                        .font(.system(size: 13))
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
            // IGNIS-UI-37: timeline row product name and timestamp at
            // 12.5pt, the native counterparts to the web assessment
            // head's 12.5px rules (.assessment-product for the product
            // name, .assessment-time for the timestamp). Until now
            // both used .caption (12pt), so they read a half point
            // smaller than the web head's product and time while the
            // timeline title (UI-34) already matched its own 15px web
            // rule. The size is the only change: both keep their
            // muted color, the title keeps its semibold weight, and
            // the row detail below kept its callout size until UI-43.
            HStack(alignment: .firstTextBaseline, spacing: 6) {
                // IGNIS-UI-53: timeline row title at 15pt, the
                // native counterpart to the web history head (js/
                // app.js renders the title as a strong element in a
                // .history-head paragraph, and styles.css gives that
                // head no font-size of its own, so the title inherits
                // the 15px body size). Until now the native title
                // carried no font at all, so it read at the default
                // 17pt body size, two points larger than the web
                // title, while the row product name and timestamp
                // (UI-37) already matched their own 12.5px web rules
                // and the row detail (UI-43) already matched its own
                // 15px web rule. The size is the only change: the
                // semibold weight, the assessment-primary and
                // failure-red colors, and the row layout are
                // untouched.
                // IGNIS-UI-55: timeline row title at bold weight, the
                // native counterpart to the web history title, which
                // js/app.js renders as a strong element (weight 700).
                // Until now the native title used semibold (600), so
                // it read one step lighter than the web title while
                // the observation category (UI-17) already matched
                // its own web strong at bold and the row title size
                // (UI-53) already matched at 15pt. The weight is the
                // only change: the 15pt size, the assessment-primary
                // and failure-red colors, the firstTextBaseline row,
                // and the 10pt leading rule gap are untouched.
                Text(item.title)
                    .font(.system(size: 15))
                    .fontWeight(.bold)
                    .foregroundStyle(titleColor(for: item))
                Text(item.product.config.displayName)
                    .font(.system(size: 12.5))
                    .foregroundStyle(.secondary)
                Spacer()
                Text(item.timestamp)
                    .font(.system(size: 12.5))
                    .foregroundStyle(.secondary)
            }
            if !item.detail.isEmpty {
                // IGNIS-UI-43: timeline row detail at 15pt, the native
                // counterpart to the web history body (a plain <p> in
                // a .history-item, inheriting the 15px body size).
                // Until now the detail used .callout (16pt), so it
                // read one point larger than the web body line while
                // the row product name and timestamp (UI-37) already
                // matched their own 12.5px web rules. The size is the
                // only change: the three-line limit, the wording
                // (the assessment summary or the failure message),
                // and the row's product-accent edge are untouched.
                Text(item.detail)
                    .font(.system(size: 15))
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
