import XCTest
@testable import ToyLoRAEngine

final class ToyTrainerTests: XCTestCase {
    func testLossFallsAndBaseFrozen() throws {
        let result = try ToyLoRATrainer().train()
        XCTAssertLessThan(result.finalLoss, result.initialLoss)
        XCTAssertEqual(result.frozenBaseWeight, 1.0, accuracy: 1e-12)
        XCTAssertNotEqual(result.adapterA * result.adapterB, 0)
        XCTAssertTrue(result.finalLoss.isFinite)
    }

    func testDeterministicAndStepBounds() throws {
        let trainer = ToyLoRATrainer()
        XCTAssertEqual(try trainer.train(steps: 40), try trainer.train(steps: 40))
        XCTAssertEqual(try trainer.train(steps: -1).steps, 0)
        XCTAssertEqual(try trainer.train(steps: 0).initialLoss, try trainer.train(steps: 0).finalLoss)
    }

    func testInvalidLearningRatesRejected() {
        let trainer = ToyLoRATrainer()
        XCTAssertThrowsError(try trainer.train(learningRate: 0))
        XCTAssertThrowsError(try trainer.train(learningRate: -0.1))
        XCTAssertThrowsError(try trainer.train(learningRate: .nan))
        XCTAssertThrowsError(try trainer.train(learningRate: 0.2))
    }
}
