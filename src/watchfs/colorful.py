from __future__ import annotations

from colored import Back, Fore, Style  # type: ignore


class Badge:
    def __init__(self, name: str, fore: Fore, back: Back) -> None:
        self.name = name
        self.fore = fore
        self.back = back

    def __str__(self) -> str:
        return f"{self.back}{self.fore}{Style.bold} {self.name} {Style.reset}"
