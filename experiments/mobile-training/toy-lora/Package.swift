// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "ToyLoRA",
    platforms: [.iOS(.v16), .macOS(.v13)],
    products: [.executable(name: "ToyLoRA", targets: ["ToyLoRA"]), .library(name: "ToyLoRAEngine", targets: ["ToyLoRAEngine"])],
    targets: [
        .target(name: "ToyLoRAEngine"),
        .executableTarget(name: "ToyLoRA", dependencies: ["ToyLoRAEngine"]),
        .testTarget(name: "ToyLoRAEngineTests", dependencies: ["ToyLoRAEngine"])
    ]
)
