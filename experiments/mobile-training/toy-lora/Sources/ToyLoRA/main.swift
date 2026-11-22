import Foundation
import ToyLoRAEngine

let result = ToyLoRATrainer().train()
print("Toy local adapter-training demonstration (synthetic data)")
print("steps: \(result.steps)")
print("loss: \(result.initialLoss) -> \(result.finalLoss)")
print("frozen base weight: \(result.frozenBaseWeight)")
print("adapter A: \(result.adapterA)")
print("adapter B: \(result.adapterB)")
print("effective weight: \(result.frozenBaseWeight + result.adapterA * result.adapterB)")
