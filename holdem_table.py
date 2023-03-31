from dataclasses import dataclass, field

from holdem_round import (
    HoldemRound,
    HoldemRoundConfig,
    HoldemRoundPlayer,
    HoldemRoundStage,
)


@dataclass
class HoldemTable:
    table_name: str
    pass

