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
                Text(response.assessment.summary)
            }
            observationsSection
            uncertaintySection
            Divider()
            processingLine
        }
        .frame(maxWidth: .infinity, alignment: .leading)
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
                    Label("REQUIRES HUMAN REVIEW", systemImage: "exclamationmark.triangle.fill")
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundStyle(.orange)
                }
                Spacer()
            }
            Text("\(response.timestamp) · \(productDisplayName)")
                .font(.caption)
                .foregroundStyle(.secondary)
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
                            Text(observation.category)
                                .fontWeight(.semibold)
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
                    // One VoiceOver item per observation, so category,
                    // confidence, description, and evidence are read together.
                    .accessibilityElement(children: .combine)
                }
            }
        }
    }

    private var uncertaintySection: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Uncertainty")
                .font(.headline)
                .accessibilityAddTraits(.isHeader)
            if response.assessment.uncertainty.isEmpty {
                Text("The model reported no uncertainty items.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(Array(response.assessment.uncertainty.enumerated()), id: \.offset) { _, item in
                    HStack(alignment: .top, spacing: 6) {
                        Text("•")
                        Text(item)
                    }
                }
            }
        }
    }

    private var processingLine: some View {
        Text("Model: \(response.processing.model) · Server-reported latency: \(serverLatencyText)")
            .font(.caption)
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
