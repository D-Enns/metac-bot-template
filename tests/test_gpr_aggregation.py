"""
Test GPR aggregation with dummy data
"""
import sys
sys.path.insert(0, '/mnt/c/Users/Donni/projects/metac_bot_Spring_2026')

from main import SpringTemplateBot2026

def test_gpr_aggregation():
    """Test GPR aggregation with sample scenario data"""

    # Create bot instance (minimal config)
    bot = SpringTemplateBot2026(
        research_reports_per_question=1,
        predictions_per_research_report=4,
    )

    # Test data: 4 runs × 3 scenarios = 12 values
    # Simulating: [low, mid, high] for each of 4 runs
    test_scenarios = [
        0.35, 0.45, 0.60,  # Run 1
        0.40, 0.50, 0.65,  # Run 2
        0.38, 0.48, 0.62,  # Run 3
        0.42, 0.52, 0.67,  # Run 4
    ]

    print(f"Testing GPR with {len(test_scenarios)} scenarios...")
    print(f"Input scenarios (decimal): {test_scenarios}")
    print(f"Sorted: {sorted(test_scenarios)}")

    # Run GPR aggregation
    result = bot._gpr_aggregate_binary(test_scenarios)

    print(f"\n✓ GPR p50 result: {result:.4f}")
    print(f"  (Median would be: {sorted(test_scenarios)[5]:.4f})")

    # Validate result
    assert 0.01 <= result <= 0.99, f"Result {result} out of valid range"
    assert 0.40 <= result <= 0.60, f"Result {result} seems unreasonable for this data"

    print("\n✓ All tests passed!")
    return result

if __name__ == "__main__":
    test_gpr_aggregation()
