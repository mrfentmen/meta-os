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
                }
            }
        }
    }

    private var uncertaintySection: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Uncertainty")
                .font(.headline)
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
