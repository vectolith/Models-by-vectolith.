import Foundation

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

    // W remains frozen. Train only scalar adapter factors a and b in W + (a*b).
    public func train(steps: Int = 500, learningRate: Double = 0.02) -> TrainingResult {
        let frozenW = 1.0
        let targetW = 3.0
        let samples: [Double] = [-2, -1, 0.5, 1, 2]
        var a = 0.5
        var b = 0.0

        func loss(_ a: Double, _ b: Double) -> Double {
            samples.reduce(0.0) { sum, x in
                let prediction = (frozenW + a * b) * x
                let target = targetW * x
                return sum + (prediction - target) * (prediction - target)
            } / Double(samples.count)
        }

        let initial = loss(a, b)
        for _ in 0..<max(0, steps) {
            var gradA = 0.0
            var gradB = 0.0
            for x in samples {
                let error = (frozenW + a * b) * x - targetW * x
                gradA += 2.0 * error * x * b
                gradB += 2.0 * error * x * a
            }
            gradA /= Double(samples.count)
            gradB /= Double(samples.count)
            let nextA = a - learningRate * gradA
            let nextB = b - learningRate * gradB
            a = nextA
            b = nextB
        }

        return TrainingResult(initialLoss: initial, finalLoss: loss(a, b),
                             frozenBaseWeight: frozenW, adapterA: a,
                             adapterB: b, steps: max(0, steps))
    }
}
