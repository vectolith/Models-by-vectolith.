import XCTest
@testable import ToyLoRAEngine
final class ToyTrainerTests:XCTestCase { func testLossFallsAndBaseFrozen(){let r=ToyLoRATrainer().train();XCTAssertLessThan(r.finalLoss,r.initialLoss);XCTAssertEqual(r.frozenBaseWeight,1.0,accuracy:1e-12);XCTAssertNotEqual(r.adapterA*r.adapterB,0)};func testDeterministicAndBounds(){let t=ToyLoRATrainer();XCTAssertEqual(t.train(steps:40),t.train(steps:40));XCTAssertEqual(t.train(steps:-1).steps,0)} }
