import ToyLoRAEngine

let result = try ToyLoRATrainer().train()
print("Toy adapter training (synthetic)")
print("loss: \(result.initialLoss) -> \(result.finalLoss)")
print("base frozen: \(result.frozenBaseWeight)")
print("A=\(result.adapterA), B=\(result.adapterB), effective=\(result.frozenBaseWeight + result.adapterA * result.adapterB)")
