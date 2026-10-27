"""Cost estimation and budget guard. Mock providers always cost 0."""
from studio.config import Settings
from studio.contracts import ProviderKind


class BudgetExceeded(RuntimeError):
    pass


class CostEstimator:
    def __init__(self, settings: Settings):
        self.pricing = settings.pricing
        self.budget_usd = settings.budget_usd

    def estimate(self, kind: ProviderKind, units: float, *, mock: bool) -> tuple[float, str]:
        """Return (usd, unit_name). Mock calls are free by definition."""
        price = self.pricing.get(kind.value)
        unit = price.unit if price else "call"
        if mock or price is None:
            return 0.0, unit
        return round(units * price.usd_per_unit, 6), unit

    def check_budget(self, spent_usd: float, next_usd: float) -> None:
        if spent_usd + next_usd > self.budget_usd:
            raise BudgetExceeded(
                f"budget {self.budget_usd:.2f} USD would be exceeded "
                f"(spent {spent_usd:.4f} + next {next_usd:.4f})"
            )
