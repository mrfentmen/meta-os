import Foundation

// Backend health client: GETs the server's /api/health and validates
// the reply, mirroring the web frontend's checkHealth in js/client.js
// exactly (same URL derivation, same validation, same error kinds).
// The check contacts the health route only: it never sends a frame and
// never returns an assessment. A reachable server is NOT the same as
// a server ready to assess — the model state in the reply says whether
// live calls are on or held, and the UI must say so plainly.

struct HealthStatus {
    let service: String
    let products: [String]
    let modelConfigured: Bool
    let modelLiveEnabled: Bool
}

final class HealthClient {
    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    /// The health URL for an assessment endpoint: the same origin and
    /// prefix, with /api/assess swapped for /api/health. A bare base URL
    /// just gains the /api/health path. This keeps the check pointed at
    /// the server the user actually configured, never at a guessed host.
    static func healthUrlFor(endpoint: String) -> String {
        var trimmed = endpoint.trimmingCharacters(in: .whitespacesAndNewlines)
        while trimmed.hasSuffix("/") {
            trimmed.removeLast()
        }
        if trimmed.hasSuffix("/api/assess") {
            return String(trimmed.dropLast("/api/assess".count)) + "/api/health"
        }
        return trimmed + "/api/health"
    }

    func checkHealth(endpoint: String) async throws -> HealthStatus {
        let urlString = Self.healthUrlFor(endpoint: endpoint)
        guard let url = URL(string: urlString),
              let scheme = url.scheme?.lowercased(),
              scheme == "http" || scheme == "https"
        else {
            throw AssessError(kind: .network, message: "Endpoint is not a valid http(s) URL: \(endpoint)", latencyMs: nil)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        let data: Data
        let httpResponse: HTTPURLResponse
        do {
            let (responseData, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                throw AssessError(kind: .network, message: "Health endpoint returned a non-HTTP response", latencyMs: nil)
            }
            data = responseData
            httpResponse = http
        } catch let error as AssessError {
            throw error
        } catch {
            throw AssessError(
                kind: .network,
                message: "Health check to \(urlString) failed: \(error.localizedDescription)",
                latencyMs: nil
            )
        }

        if !(200...299).contains(httpResponse.statusCode) {
            var message = "Health endpoint returned HTTP \(httpResponse.statusCode)"
            if let serverError = Self.serverErrorMessage(in: data) {
                message += ": \(serverError)"
            }
            throw AssessError(kind: .http, message: message, latencyMs: nil)
        }

        guard let object = try? JSONSerialization.jsonObject(with: data),
              let body = object as? [String: Any]
        else {
            throw AssessError(kind: .invalid, message: "Health response was not valid JSON", latencyMs: nil)
        }

        if let serverError = Self.serverErrorMessage(in: body) {
            throw AssessError(kind: .invalid, message: "Health endpoint returned an error: \(serverError)", latencyMs: nil)
        }

        if let problem = Self.validateHealth(body) {
            throw AssessError(kind: .invalid, message: "Health response failed validation: \(problem)", latencyMs: nil)
        }

        // validateHealth has already proven every field's shape.
        let model = body["model"] as! [String: Any]
        return HealthStatus(
            service: body["service"] as! String,
            products: body["products"] as! [String],
            modelConfigured: model["configured"] as! Bool,
            modelLiveEnabled: model["live_enabled"] as! Bool
        )
    }

    private static func serverErrorMessage(in data: Data) -> String? {
        guard let object = try? JSONSerialization.jsonObject(with: data),
              let body = object as? [String: Any]
        else {
            return nil
        }
        return serverErrorMessage(in: body)
    }

    private static func serverErrorMessage(in body: [String: Any]) -> String? {
        guard let error = body["error"] as? String, !error.isEmpty else {
            return nil
        }
        return error
    }

    private static func validateHealth(_ body: [String: Any]) -> String? {
        guard body["ok"] is Bool else {
            return "health response has no boolean ok field"
        }
        guard let service = body["service"] as? String, !service.isEmpty else {
            return "health response has no service name"
        }
        guard let products = body["products"] as? [Any],
              products.allSatisfy({ $0 is String })
        else {
            return "health response has no products list"
        }
        guard let model = body["model"] as? [String: Any] else {
            return "health response has no model status"
        }
        guard model["configured"] is Bool, model["live_enabled"] is Bool else {
            return "health response model status is incomplete"
        }
        return nil
    }
}
