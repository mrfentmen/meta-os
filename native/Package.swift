// swift-tools-version: 5.9
import PackageDescription

// MetaTrio — one native macOS app hosting Meta Vigiles, Meta Ignis, and
// Meta Medicus behind a product switcher, on one shared foundation.
// Open this file in Xcode to build/run, or use Scripts/make-app.sh to
// assemble an ad-hoc signed MetaTrio.app bundle (see README.md).
let package = Package(
    name: "MetaTrio",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "MetaTrio", targets: ["MetaTrio"])
    ],
    targets: [
        .executableTarget(
            name: "MetaTrio",
            path: "Sources/MetaTrio"
        )
    ]
)
