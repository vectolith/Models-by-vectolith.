import Foundation

public enum ToyTrainingError: Error, Equatable {
    case invalidLearningRate
}

public struct TrainingResult: Equatable {
    public let initialLoss: Double
    public let finalLoss: Double
    public let frozenBaseWeight: Double
    public let adapterA: Double
    public let adapterB: Double
    public let steps: Int
}

public struct ToyLoRATrainer {
    public init() {}

    public func train(steps: Int = 500, learningRate: Double = 0.02) throws -> TrainingResult {
        guard learningRate.isFinite, learningRate > 0, learningRate <= 0.1 else {
            throw ToyTrainingError.invalidLearningRate
        }
        let w = 1.0
        let target = 3.0
        let samples = [-2.0, -1.0, 0.5, 1.0, 2.0]
        var a = 0.5
        var b = 0.0

        func loss(_ a: Double, _ b: Double) -> Double {
            samples.reduce(0.0) { sum, x in
                let error = (w + a * b - target) * x
                return sum + error * error
            } / Double(samples.count)
        }

        let initial = loss(a, b)
        let boundedSteps = max(0, steps)
        for _ in 0..<boundedSteps {
            var gradientA = 0.0
            var gradientB = 0.0
            for x in samples {
                let error = (w + a * b - target) * x
                gradientA += 2 * error * x * b
                gradientB += 2 * error * x * a
            }
            gradientA /= Double(samples.count)
            gradientB /= Double(samples.count)
            a -= learningRate * gradientA
            b -= learningRate * gradientB
        }
        return TrainingResult(
            initialLoss: initial,
            finalLoss: loss(a, b),
            frozenBaseWeight: w,
            adapterA: a,
            adapterB: b,
            steps: boundedSteps
        )
    }
}
