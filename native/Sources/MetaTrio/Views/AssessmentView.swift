import SwiftUI

// Renders one validated v2 assessment. Uncertainty gets its own plainly
// labeled section and is never softened or hidden. Values the server did
// not report are shown as "not reported" — confidence and server latency
// stay visibly absent rather than being filled in.

struct AssessmentView: View {
    let response: AssessmentResponse

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            header
            if !response.assessment.summary.isEmpty {
                // UI-20: summary at 15pt, the native counterpart to
                // the web panel rendering the summary as a plain <p>
                // at the 15px body size (styles.css body rule; js/app.js
                // gives the paragraph no class). Until now the native
                // summary was a plain Text at the default body size,
                // so it read smaller than the web paragraph while the
                // category (title3, UI-13's web counterpart), subline
                // (12.5pt, UI-19), and processing line (12.5pt mono,
                // UI-15) already matched their own web rules. The size
                // is the only change: the non-empty guard, the wording,
                // and every other section are untouched, and the
                // observation description keeps its own default size —
                // it is a stacked native row, not the web's inline
                // line, so it is not this item's counterpart.
                Text(response.assessment.summary)
                    .font(.system(size: 15))
            }
            observationsSection
            uncertaintySection
            Divider()
            processingLine
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        // UI-11: panel inner padding, the native counterpart to the
        // web .panel padding of 14px 16px. Until now the native card
        // carried no inner inset at all — only the UI-5 leading gap
        // — so its text sat flush against the top, bottom, and
        // trailing card edges while the web panel breathed inside
        // its border. The inset sits before the UI-5 leading padding
        // so the rule overlay still lands on the card's outer edge
        // and the wash, clip, border, and shadow still cover the
        // whole card; the leading total is therefore 16pt panel inset
        // plus the 10pt rule gap (26pt), while top, bottom, and
        // trailing map directly from the CSS pixels. It changes no
        // color, rule, content, or spacing between sections.
        .padding(EdgeInsets(top: 14, leading: 16, bottom: 14, trailing: 16))
        // UI-5: product-accent leading rule, the native counterpart to
        // the web panel gradient and the UI-4 timeline rule. The rule
        // color comes from the assessment's own product, so a
        // redisplayed Ignis assessment keeps its red rule under any
        // selection, and it sits on the outer stack so the whole panel
        // carries it, not just one section.
        .padding(.leading, 10)
        .overlay(alignment: .leading) {
            Rectangle()
                .fill(accentColor)
                .frame(width: 3)
        }
        // UI-6: product-accent panel wash, the native counterpart to
        // the web panel gradient (R2/UI-3: 0.09 red at the top on
        // Ignis). The wash uses the same assessment-own accent as
        // the UI-5 rule, so a redisplayed panel keeps its product
        // tint under any selection. It is a flat 0.09 wash, matching
        // the web gradient's top strength, rather than a gradient:
        // the UI-5 rule already marks the edge, and a fade would add
        // a second accent treatment to the same panel.
        .background(accentColor.opacity(0.09))
        // UI-7: rounded panel corners, the native counterpart to the
        // web .panel border-radius of 8px. The clip sits after the
        // wash so the wash and the UI-5 rule are cut to the same
        // rounded card edge instead of running square to the panel
        // boundary; it changes no color, rule, or content.
        .clipShape(RoundedRectangle(cornerRadius: 8))
        // UI-9: product-accent panel border, the native counterpart
        // to the web theme panels' border-color of rgba(accent, 0.5)
        // — Ignis red and Sanitas green in their theme blocks. The
        // stroke sits after the clip so the full 1pt line follows
        // the rounded edge instead of being cut to a half line by
        // it, and it uses the same assessment-own accent as the
        // UI-5 rule and UI-6 wash. Note the generalization: the web
        // Vigiles panel carries only the neutral panel-border, not
        // an accent border, but the native panel already tints
        // Vigiles by its own accent in rule and wash, so the border
        // follows the panel's own accent for all three products
        // rather than adding a second, neutral edge rule.
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(accentColor.opacity(0.5), lineWidth: 1)
        )
        // UI-10: panel drop shadow, the native counterpart to the
        // web theme panels' box-shadow of
        // 0 0 0 1px rgba(accent, 0.15), 0 8px 24px rgba(0, 0, 0, 0.35).
        // The 1px 0.15 ring is deliberately NOT mirrored: the UI-9
        // stroke already draws a stronger 1pt accent edge at 0.5, so
        // a second faint ring would double the edge. Only the drop
        // shadow is new: black at 0.35, offset 8pt down, radius 12.
        // The radius is an approximation, stated plainly: a CSS blur
        // of 24px spreads roughly twice as far as a SwiftUI shadow
        // radius unit, so 12 approximates the web spread while the
        // 8pt offset and 0.35 strength map directly. The shadow is
        // product-neutral black, exactly like the web shadow — it
        // tracks no accent, so it needs no assessment-own-accent
        // treatment. It sits last, after the border overlay, so the
        // whole bordered card casts it.
        .shadow(color: .black.opacity(0.35), radius: 12, x: 0, y: 8)
    }

    /// Panel accent from the assessment's own product, mirroring the
    /// TimelineView row-accent mapping. An unknown product key falls
    /// back to the system accent rather than guessing a product.
    private var accentColor: Color {
        switch ProductID(rawValue: response.product)?.config.accentColorName {
        case "blue": return .blue
        case "red": return .red
        case "green": return .green
        default: return .accentColor
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(response.assessment.category)
                    .font(.title3)
                    .fontWeight(.bold)
                if response.assessment.requiresHumanReview {
                    // UI-16: review flag carries 0.6pt tracking, the
                    // native counterpart to the web .review-flag rule
                    // (12px, weight 700, warn, letter-spacing 0.05em =
                    // 0.6pt at 12pt). The native Label already matched
                    // size (.caption = 12pt), weight, and warn color
                    // (.orange), but had no tracking, so the flag read
                    // tighter than the web's letterspaced flag. Text
                    // stays the uppercase literal, icon and color
                    // unchanged; the tracking follows the flag's own
                    // 12pt size, not any product accent.
                    Label("REQUIRES HUMAN REVIEW", systemImage: "exclamationmark.triangle.fill")
                        .font(.caption)
                        .fontWeight(.bold)
                        .tracking(0.6)
                        .foregroundStyle(.orange)
                }
                Spacer()
            }
            // UI-13: product name in the web .assessment-product style,
            // the native counterpart to the web Latest panel rendering
            // the product name bold (weight 700) in the assessment's
            // own product accent, with the timestamp muted. Until now
            // the native subline was one secondary caption, so a
            // redisplayed Ignis assessment's product name read in the
            // same gray as its timestamp while the web name read red
            // and bold. The subline keeps its timestamp-first order;
            // its size is 12.5pt per UI-19, not the caption size it
            // kept under UI-13. Only the product segment changes,
            // tinted by the same assessment-own accentColor the UI-5
            // rule, UI-6 wash, and UI-9 border already use, so an
            // unknown product key falls back to the system accent,
            // exactly like the web base rule falling back to the
            // selected product's accent. Text concatenation keeps the
            // subline one VoiceOver item under the header's combine.
            (
                Text("\(response.timestamp) · ")
                    .foregroundStyle(.secondary)
                + Text(productDisplayName)
                    .fontWeight(.bold)
                    .foregroundStyle(accentColor)
            )
            // UI-19: subline at 12.5pt, the native counterpart to the
            // web .assessment-product and .assessment-time rules
            // (both 12.5px). Until now the concatenated subline used
            // .caption (12pt), so both segments read a half point
            // smaller than the web's product name and timestamp while
            // the review flag (UI-16) already matched its own web
            // rule at 12pt and the processing line (UI-15) already
            // matched at 12.5pt. The size is the only change: the
            // timestamp-first order, the secondary timestamp, the
            // bold own-accent product segment, and the header's
            // single VoiceOver item are untouched, and the flag
            // keeps its caption size.
            .font(.system(size: 12.5))
        }
        // One VoiceOver item: category, human-review flag, and the
        // timestamp/product line, in reading order.
        .accessibilityElement(children: .combine)
    }

    /// Display name for the product key the server returned, falling back
    /// to the raw key if it is not one of the three known products.
    private var productDisplayName: String {
        ProductID(rawValue: response.product)?.config.displayName ?? response.product
    }

    @ViewBuilder
    private var observationsSection: some View {
        if !response.observations.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Text("Observations")
                    .font(.headline)
                    .accessibilityAddTraits(.isHeader)
                ForEach(Array(response.observations.enumerated()), id: \.offset) { _, observation in
                    VStack(alignment: .leading, spacing: 2) {
                        HStack(alignment: .firstTextBaseline) {
                            // UI-17: observation category in the web
                            // <strong> weight, the native counterpart
                            // to js/app.js rendering the web
                            // observation category with a strong
                            // element (weight 700). Until now the
                            // native category used semibold (600),
                            // so it read one step lighter than the
                            // web category while the header category
                            // already matched at bold. Only the
                            // category weight changes: the confidence
                            // caption, description, and evidence
                            // lines keep their own styles, and the
                            // single-line web layout versus the
                            // native stacked rows is unchanged.
                            Text(observation.category)
                                .fontWeight(.bold)
                            Spacer()
                            Text(confidenceText(observation.confidence))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Text(observation.description)
                        if !observation.evidence.isEmpty {
                            Text("Evidence: \(observation.evidence)")
                                .font(.callout)
                                .foregroundStyle(.secondary)
                        }
                    }
                    // UI-18: observation list bullet and 18pt inset, the
                    // native counterpart to the web .observations rule
                    // (a <ul> with padding-left 18px and default disc
                    // markers). Until now the native rows sat flush
                    // left with no marker, so a populated list read as
                    // loose stacked blocks while the web list read as
                    // an indented bulleted list. The 18pt leading
                    // padding puts the row text where the web text
                    // sits, and the bullet sits in that padding box
                    // via a topLeading overlay — the same outside
                    // position the web disc occupies — instead of
                    // pushing the text further right, as a leading
                    // HStack glyph would. The bullet is a visual
                    // marker only (accessibilityHidden, like a web
                    // list marker, which VoiceOver does not read), so
                    // the row's combined VoiceOver item is unchanged.
                    // The heading, category weight (UI-17), confidence
                    // caption, description, and evidence lines are
                    // untouched.
                    .padding(.leading, 18)
                    .overlay(alignment: .topLeading) {
                        Text("•")
                            .accessibilityHidden(true)
                    }
                    // One VoiceOver item per observation, so category,
                    // confidence, description, and evidence are read together.
                    .accessibilityElement(children: .combine)
                }
            }
        }
    }

    private var uncertaintySection: some View {
        VStack(alignment: .leading, spacing: 4) {
            // UI-12: uncertainty heading in the web .subhead style, the
            // native counterpart to js/app.js rendering the web
            // Uncertainty heading with class "subhead" (13px, weight
            // 700, uppercase, letter-spacing 0.05em, muted). Until now
            // the native heading used .headline — 17pt semibold, no
            // case or tracking, default color — so it read as a body
            // section title while the web heading read as a small
            // muted label above the uncertainty items. The mapping is
            // direct except for the color, stated plainly: .secondary
            // approximates the web --muted #9aa0a8 with the system
            // secondary gray rather than a fixed hex, and the tracking
            // is 0.05em of the 13pt size (0.65pt). The header trait is
            // kept, and the Observations heading is deliberately
            // untouched: the web panel renders observations as a bare
            // list with no heading at all, so there is no web
            // counterpart to mirror there.
            Text("Uncertainty")
                .font(.system(size: 13, weight: .bold))
                .textCase(.uppercase)
                .tracking(0.65)
                .foregroundStyle(.secondary)
                .accessibilityAddTraits(.isHeader)
            if response.assessment.uncertainty.isEmpty {
                // Uncertainty empty note at 15pt, the native counterpart
                // to the web panel rendering the empty note with class
                // "uncertainty" at the 15px body size. Until now the
                // note was a plain Text at the default size, so it read
                // smaller than the web note and smaller than the
                // populated list below once it takes the same 15pt
                // size — the same default-size gap UI-20 closed for
                // the summary. The size is the only change: the
                // wording, the muted color, and the populated-list
                // rendering are untouched.
                Text("The model reported no uncertainty items.")
                    .foregroundStyle(.secondary)
                    .font(.system(size: 15))
            } else {
                ForEach(Array(response.assessment.uncertainty.enumerated()), id: \.offset) { _, item in
                    // UI-14: uncertainty items in the web .uncertainty
                    // style, the native counterpart to styles.css
                    // rendering the web uncertainty list in --muted.
                    // Until now the items used the default text color
                    // while the heading (UI-12) and the empty note
                    // below both read muted, so a populated list read
                    // bolder than the web list and inconsistent with
                    // its own section. The muted style sits on the
                    // row so bullet and item share it, exactly like
                    // the web list items inheriting the list color.
                    // It tracks no accent: uncertainty is muted for
                    // every product, like the web rule.
                    // Uncertainty items at 15pt, the native counterpart
                    // to the web .uncertainty list, which sets only the
                    // muted color and inherits the 15px body size.
                    // Until now the row was plain Text at the default
                    // size, so a populated list read smaller than the
                    // web list while the heading (UI-12) already
                    // matched its own web rule. The size sits on the row so bullet and
                    // item share it, exactly like the UI-14 muted
                    // color they already share; the bullet, wording,
                    // and muted color are untouched.
                    HStack(alignment: .top, spacing: 6) {
                        Text("•")
                        Text(item)
                    }
                    .foregroundStyle(.secondary)
                    .font(.system(size: 15))
                }
            }
        }
    }

    private var processingLine: some View {
        // UI-15: processing line in the web "note mono" style, the
        // native counterpart to js/app.js rendering the web
        // processing line with class "note mono" (muted, 12.5px,
        // ui-monospace stack). Until now the native line used
        // .caption — 12pt proportional system text — so it read as
        // ordinary body copy while the web line read as a small
        // monospace status line. The size maps directly (12.5pt);
        // the design is stated plainly as a stand-in: SwiftUI's
        // .monospaced design is the system monospace face, not the
        // web's ui-monospace stack verbatim. The muted color is
        // unchanged (.secondary, the established stand-in for
        // --muted), and the wording is untouched — only the face
        // and size change, so no other section gains a mono face.
        Text("Model: \(response.processing.model) · Server-reported latency: \(serverLatencyText)")
            .font(.system(size: 12.5, design: .monospaced))
            .foregroundStyle(.secondary)
    }

    private var serverLatencyText: String {
        guard let latency = response.processing.latencyMs else {
            return "not reported"
        }
        if latency == latency.rounded() {
            return "\(Int(latency)) ms"
        }
        return String(format: "%.1f ms", latency)
    }

    private func confidenceText(_ confidence: Double?) -> String {
        guard let confidence = confidence else {
            return "confidence: not reported"
        }
        return String(format: "confidence: %.2f", confidence)
    }
}
