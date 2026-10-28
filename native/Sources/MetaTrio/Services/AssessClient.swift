import Foundation

// Assessment client: POSTs one sampled frame to the configured endpoint
// and validates the reply against the v2 contract. Every failure mode
// (invalid endpoint, network, HTTP status, server error body, unparseable
// body, contract violation) throws an AssessError with a kind, so the UI
// can show the real error and never render a fabricated assessment.
//
// The client measures the actual round-trip time with Date() around the
// request — including on failure paths — and attaches it to the result or
// the error. It is nil only when no request was attempted (invalid URL).

struct AssessError: Error {
    enum Kind: String {
        case network
        case http
        case invalid
    }

    let kind: Kind
    let message: String
    let latencyMs: Int?
}

final class AssessClient {
    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    /// Sends {product, timestamp, image} and returns the validated response
    /// plus the client-measured round-trip latency in milliseconds.
    func assess(
        endpoint: String,
        product: ProductID,
        timestamp: String,
        imageDataURL: String
    ) async throws -> (response: AssessmentResponse, latencyMs: Int) {
        guard let url = URL(string: endpoint),
              let scheme = url.scheme?.lowercased(),
              scheme == "http" || scheme == "https"
        else {
            throw AssessError(kind: .network, message: "Endpoint is not a valid http(s) URL: \(endpoint)", latencyMs: nil)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let payload: [String: Any] = [
            "product": product.rawValue,
            "timestamp": timestamp,
            "image": imageDataURL,
        ]
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: payload)
        } catch {
            throw AssessError(kind: .invalid, message: "Could not encode the request body: \(error.localizedDescription)", latencyMs: nil)
        }

        let start = Date()
        let data: Data
        let httpResponse: HTTPURLResponse
        do {
            let (responseData, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                throw AssessError(
                    kind: .network,
                    message: "Endpoint returned a non-HTTP response",
                    latencyMs: Self.elapsedMs(since: start)
                )
            }
            data = responseData
            httpResponse = http
        } catch let error as AssessError {
            throw error
        } catch {
            throw AssessError(
                kind: .network,
                message: "Request to \(endpoint) failed: \(error.localizedDescription)",
                latencyMs: Self.elapsedMs(since: start)
            )
        }
        let latencyMs = Self.elapsedMs(since: start)

        if !(200...299).contains(httpResponse.statusCode) {
            var message = "Endpoint returned HTTP \(httpResponse.statusCode)"
            if let serverError = Self.serverErrorMessage(in: data) {
                message += ": \(serverError)"
            }
            throw AssessError(kind: .http, message: message, latencyMs: latencyMs)
        }

        // The contract's error shape: HTTP 200 with an {"error": "..."} body.
        if let serverError = Self.serverErrorMessage(in: data) {
            throw AssessError(kind: .invalid, message: "Endpoint returned an error: \(serverError)", latencyMs: latencyMs)
        }

        switch ContractValidator.validate(data, expectedProduct: product) {
        case .success(let response):
            return (response, latencyMs)
        case .failure(let validationError):
            throw AssessError(
                kind: .invalid,
                message: "Endpoint response failed contract validation: \(validationError.problems.joined(separator: "; "))",
                latencyMs: latencyMs
            )
        }
    }

    private static func serverErrorMessage(in data: Data) -> String? {
        guard let object = try? JSONSerialization.jsonObject(with: data),
              let dict = object as? [String: Any],
              let error = dict["error"] as? String,
              !error.isEmpty
        else {
            return nil
        }
        return error
    }

    private static func elapsedMs(since start: Date) -> Int {
        Int(Date().timeIntervalSince(start) * 1000)
    }
}
