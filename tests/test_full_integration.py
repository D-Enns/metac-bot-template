"""
Test full GPR integration workflow
Simulates 4 LLM calls with 3 scenarios each, verifies GPR aggregation
"""
import sys
sys.path.insert(0, '/mnt/c/Users/Donni/projects/metac_bot_Spring_2026')

from main import SpringTemplateBot2026, ThreeScenarioPrediction

def test_scenario_storage_and_aggregation():
    """Test that scenarios are stored correctly across multiple calls"""

    # Create bot instance
    bot = SpringTemplateBot2026(
        research_reports_per_question=1,
        predictions_per_research_report=4,  # 4 calls expected
    )

    print("Testing scenario storage across 4 simulated LLM calls...")
    print(f"predictions_per_research_report = {bot.predictions_per_research_report}")

    # Simulate 4 calls with different scenario values
    test_scenarios_by_call = [
        [0.35, 0.45, 0.60],  # Call 1: low, mid, high
        [0.40, 0.50, 0.65],  # Call 2
        [0.38, 0.48, 0.62],  # Call 3
        [0.42, 0.52, 0.67],  # Call 4
    ]

    # Simulate storing scenarios like the bot would do
    bot._binary_scenarios = []
    bot._current_question_id = "test_question_123"
    bot._current_call_number = 0

    for call_num, scenarios in enumerate(test_scenarios_by_call, 1):
        bot._current_call_number = call_num
        bot._binary_scenarios.extend(scenarios)

        print(f"\nCall {call_num}:")
        print(f"  Added scenarios: {scenarios}")
        print(f"  Total stored: {len(bot._binary_scenarios)} scenarios")

        # On final call, should trigger GPR
        if call_num == bot.predictions_per_research_report:
            print(f"\n  → Final call detected ({call_num}/{bot.predictions_per_research_report})")
            print(f"  → Applying GPR aggregation...")

            gpr_result = bot._gpr_aggregate_binary(bot._binary_scenarios)
            print(f"  → GPR p50: {gpr_result:.4f}")

            # Validate
            assert len(bot._binary_scenarios) == 12, f"Expected 12 scenarios, got {len(bot._binary_scenarios)}"
            assert 0.40 <= gpr_result <= 0.60, f"GPR result {gpr_result} seems unreasonable"

            print(f"\n✓ Integration test passed!")
            print(f"  - Stored {len(bot._binary_scenarios)} scenarios correctly")
            print(f"  - GPR aggregation triggered on call {call_num}")
            print(f"  - Final forecast: {gpr_result:.4f}")

            return gpr_result

if __name__ == "__main__":
    test_scenario_storage_and_aggregation()
