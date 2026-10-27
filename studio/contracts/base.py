from pydantic import BaseModel, ConfigDict


class Contract(BaseModel):
    """Base for all contracts: strict, no unknown fields."""

    model_config = ConfigDict(extra="forbid")

    def dump(self) -> dict:
        """JSON-safe dict (enums as strings) suitable for LangGraph state."""
        return self.model_dump(mode="json")
