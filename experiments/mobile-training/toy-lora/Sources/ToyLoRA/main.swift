import ToyLoRAEngine
let r=ToyLoRATrainer().train(); print("Toy adapter training (synthetic)"); print("loss: \(r.initialLoss) -> \(r.finalLoss)"); print("base frozen: \(r.frozenBaseWeight)"); print("A=\(r.adapterA), B=\(r.adapterB), effective=\(r.frozenBaseWeight+r.adapterA*r.adapterB)")
