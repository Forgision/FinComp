from typing import Set


class SubscriptionRegistry:
    def __init__(self):
        self._subscriptions: Set[str] = set()

    def add(self, symbol: str) -> bool:
        """
        Add a symbol to the registry.
        Returns True if the symbol was newly added, False if it was already present.
        """
        if symbol not in self._subscriptions:
            self._subscriptions.add(symbol)
            return True
        return False

    def remove(self, symbol: str) -> bool:
        """
        Remove a symbol from the registry.
        Returns True if the symbol was removed, False if it was not present.
        """
        if symbol in self._subscriptions:
            self._subscriptions.remove(symbol)
            return True
        return False

    def get_active_symbols(self) -> Set[str]:
        return self._subscriptions.copy()
