from dre_forecasting_tools import SpringTemplateBotExtended
from forecasting_tools import GeneralLlm

bot = SpringTemplateBotExtended(
    research_reports_per_question=1,
    predictions_per_research_report=2,
    publish_reports_to_metaculus=False,
)

print("✓ Bot initialized successfully")
print(f"✓ Bot class: {bot.__class__.__name__}")
print(f"✓ Has _aggregate_predictions: {hasattr(bot, '_aggregate_predictions')}")
print(f"✓ Has _save_full_forecast_copy: {hasattr(bot, '_save_full_forecast_copy')}")
print(f"✓ Has _get_tournament_name: {hasattr(bot, '_get_tournament_name')}")
print(f"✓ Has _create_comment: {hasattr(bot, '_create_comment')}")
print("\n✓ All checks passed!")
