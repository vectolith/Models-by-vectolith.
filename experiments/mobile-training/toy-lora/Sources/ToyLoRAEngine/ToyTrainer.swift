import Foundation
public struct TrainingResult: Equatable { public let initialLoss: Double; public let finalLoss: Double; public let frozenBaseWeight: Double; public let adapterA: Double; public let adapterB: Double; public let steps: Int }
public struct ToyLoRATrainer { public init() {}
 public func train(steps: Int = 500, learningRate: Double = 0.02) -> TrainingResult {
  let w = 1.0, target = 3.0, samples = [-2.0,-1.0,0.5,1.0,2.0]; var a = 0.5, b = 0.0
  func loss(_ a:Double,_ b:Double)->Double { samples.reduce(0.0){s,x in let e=(w+a*b-target)*x; return s+e*e}/Double(samples.count) }
  let initial=loss(a,b); for _ in 0..<max(0,steps) { var ga=0.0,gb=0.0; for x in samples {let e=(w+a*b-target)*x; ga += 2*e*x*b; gb += 2*e*x*a}; ga /= Double(samples.count);gb /= Double(samples.count);a -= learningRate*ga;b -= learningRate*gb }
  return TrainingResult(initialLoss:initial,finalLoss:loss(a,b),frozenBaseWeight:w,adapterA:a,adapterB:b,steps:max(0,steps))
 }
}
