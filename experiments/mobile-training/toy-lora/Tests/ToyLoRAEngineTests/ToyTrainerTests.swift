import XCTest
@testable import ToyLoRAEngine

final class ToyTrainerTests: XCTestCase {
    func testLossFallsAndBaseIsFrozen() {
        let result = ToyLoRATrainer().train(steps: 500, learningRate: 0.02)
        XCTAssertLessThan(result.finalLoss, result.initialLoss)
        XCTAssertEqual(result.frozenBaseWeight, 1.0, accuracy: 1e-12)
        XCTAssertNotEqual(result.adapterA * result.adapterB, 0.0)
    }

    func testTrainingIsBoundedAndRepeatable() {
        let trainer = ToyLoRATrainer()
        XCTAssertEqual(trainer.train(steps: 50), trainer.train(steps: 50))
        XCTAssertEqual(trainer.train(steps: -5).steps, 0)
    }
}
