import logging
from typing import Any, Dict, List, Optional, Type
from .base import BaseStrategy

logger = logging.getLogger(__name__)


import re


def _normalize_name(name: str) -> str:
    """Normalizes strategy name key to lowercase stripped string without version suffixes."""
    clean = name.lower().strip()
    clean = re.sub(r"\s+v\d+(\.\d+)*$", "", clean)
    clean = clean.replace(" ", "_")
    return clean



class StrategyRegistry:
    """
    Central registry for strategy discovery, registration, and instantiation.
    """

    def __init__(self):
        self._strategies: Dict[str, Type[BaseStrategy]] = {}

    def register(self, strategy_cls: Type[BaseStrategy]) -> Type[BaseStrategy]:
        """
        Registers a strategy class. Can be used directly or as a decorator.
        """
        if not issubclass(strategy_cls, BaseStrategy):
            raise TypeError(f"Class {strategy_cls} must subclass BaseStrategy")

        key = _normalize_name(strategy_cls.name)
        if key in self._strategies:
            logger.info(f"Overwriting registered strategy '{key}' with {strategy_cls.__name__}")

        self._strategies[key] = strategy_cls
        return strategy_cls

    def get_strategy(
        self, name: str, parameters: Optional[Dict[str, Any]] = None
    ) -> BaseStrategy:
        """
        Instantiates and returns a strategy instance by name.

        Raises KeyError if strategy is not registered.
        """
        key = _normalize_name(name)
        if key not in self._strategies:
            raise KeyError(
                f"Unknown strategy '{name}'. Registered strategies: {self.list_names()}"
            )

        strategy_cls = self._strategies[key]
        return strategy_cls(parameters=parameters)

    def list_strategies(self) -> List[Dict[str, Any]]:
        """
        Returns metadata for all currently registered strategies.
        """
        result = []
        for name, cls in sorted(self._strategies.items()):
            instance = cls()
            result.append(instance.get_metadata())
        return result

    def list_names(self) -> List[str]:
        """Returns list of registered strategy names."""
        return sorted(list(self._strategies.keys()))

    def clear(self) -> None:
        """Clears all registered strategies (primarily for testing isolation)."""
        self._strategies.clear()


# Global Singleton Registry Instance
_GLOBAL_REGISTRY = StrategyRegistry()


def register_strategy(strategy_cls: Type[BaseStrategy]) -> Type[BaseStrategy]:
    """Global helper to register a strategy class."""
    return _GLOBAL_REGISTRY.register(strategy_cls)


def get_strategy(
    name: str, parameters: Optional[Dict[str, Any]] = None
) -> BaseStrategy:
    """Global helper to get an instantiated strategy by name."""
    return _GLOBAL_REGISTRY.get_strategy(name, parameters=parameters)


def list_strategies() -> List[Dict[str, Any]]:
    """Global helper to list metadata for all registered strategies."""
    return _GLOBAL_REGISTRY.list_strategies()


def clear_registry() -> None:
    """Global helper to clear registry (for testing)."""
    _GLOBAL_REGISTRY.clear()
