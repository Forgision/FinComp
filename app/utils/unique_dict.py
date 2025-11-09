import json
from typing import Any, Iterable, Mapping


class UniqueEnumDict(dict):
    """
    dict subclass with:
      - dot access (d.key)
      - uniqueness of values (no two keys may share the same value)
      - serialization helpers
      - enum-like reverse lookup (get_key)
      - optional restrictions on adding keys / mutating values
    """

    def __init__(
        self,
        *args,
        allow_new_keys: bool = False,
        allow_value_mutation: bool = True,
        **kwargs,
    ):
        # Internal control flags (protected by leading underscore)
        object.__setattr__(self, "_allow_new_keys", bool(allow_new_keys))
        object.__setattr__(self, "_allow_value_mutation", bool(allow_value_mutation))
        # _initialized marks end of __init__ phase (no accidental new-key allowance)
        object.__setattr__(self, "_initialized", False)

        super().__init__()  # start empty
        # funnel all initializer data through update() (which enforces uniqueness)
        if args or kwargs:
            self.update(*args, **kwargs)

        # initialization complete
        object.__setattr__(self, "_initialized", True)

    # ---------- Helper ----------
    def _check_value(self, value: Any, for_key: str | None = None) -> None:
        """
        O(n) check: ensure `value` is not already present under a different key.
        """
        for k, v in self.items():
            if v == value and k != for_key:
                raise ValueError(
                    f"Duplicate value {value!r} would conflict with existing key {k!r}"
                )

    # ---------- Core overrides ----------
    def __setitem__(self, key: str, value: Any) -> None:
        # If updating existing key:
        if key in self:
            if not self._allow_value_mutation:
                raise TypeError(
                    f"Mutation of existing value for key {key!r} is disallowed."
                )
            # Check uniqueness excluding the same key
            self._check_value(value, for_key=key)
        else:
            # Adding a new key
            if getattr(self, "_initialized", True) and not self._allow_new_keys:
                raise TypeError(
                    f"Adding new key {key!r} is disallowed (allow_new_keys=False)."
                )
            # Ensure value uniqueness
            self._check_value(value, for_key=key)

        super().__setitem__(key, value)
        # Provide dot-access attribute for convenience (only for non-internal names)
        if not key.startswith("_"):
            # set attribute on instance (avoid recursion by using object.__setattr__)
            object.__setattr__(self, key, value)

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)
        # remove attribute if present (and not an internal attr)
        if hasattr(self, key):
            try:
                object.__delattr__(self, key)
            except AttributeError:
                # safe-guard: ignore if attr removal fails for some reason
                pass

    # Route attribute access to dict keys unless name is internal or real attribute
    def __getattr__(self, name: str) -> Any:
        # Called only if normal attribute lookup failed.
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")

    def __setattr__(self, name: str, value: Any) -> None:
        # Protect internal attributes and real class attributes
        if name.startswith("_") or name in self.__class__.__dict__:
            object.__setattr__(self, name, value)
        else:
            # route setting d.name = value to dict assignment (enforces uniqueness)
            self.__setitem__(name, value)

    def __delattr__(self, name: str) -> None:
        if name.startswith("_") or name in self.__class__.__dict__:
            object.__delattr__(self, name)
        else:
            try:
                del self[name]
            except KeyError:
                raise AttributeError(
                    f"{type(self).__name__!s} has no attribute {name!r}"
                )

    # ---------- Update and setdefault to funnel through uniqueness checks ----------
    def update(self, *args, **kwargs) -> None:
        """
        Override update to ensure all entries are validated through __setitem__.
        Accepts:
          - mapping: d.update({'A':1})
          - iterable of pairs: d.update([('A',1), ('B',2)])
          - kwargs: d.update(A=1)
        """
        if args:
            if len(args) > 1:
                raise TypeError("update expected at most 1 positional argument")
            other = args[0]  # type: ignore
            if isinstance(other, Mapping):
                for k, v in other.items():
                    self[k] = v
            elif isinstance(other, Iterable):
                for pair in other:
                    if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                        raise TypeError("update iterable must yield (key, value) pairs")
                    k, v = pair
                    self[k] = v
            else:
                raise TypeError("update argument must be mapping or iterable of pairs")

        for k, v in kwargs.items():
            self[k] = v

    def setdefault(self, key: str, default: Any = None) -> Any:
        """
        Only set (and check uniqueness) if key is absent.
        """
        # If key exists, just return its value
        if key in self:
            return self[key]

        # If key is new, assign the default value.
        # This routes through __setitem__, which handles ALL logic:
        # 1. _allow_new_keys check
        # 2. _check_value (uniqueness) check
        # 3. super().__setitem__() call
        # 4. object.__setattr__() call (to add dot-access)
        self[key] = default
        return default

    # ---------- Enum-like & Serialization helpers ----------
    def get_key(self, value: Any) -> str:
        """Reverse lookup: return key for a given value. Raises ValueError if not found."""
        for k, v in self.items():
            if v == value:
                return k
        raise ValueError(f"Value {value!r} not present in {type(self).__name__}")

    def to_dict(self) -> dict:
        """Return a shallow copy as a plain dict."""
        return dict(self)

    def to_json(self, **json_kwargs) -> str:
        """Serialize to JSON. Pass kwargs to json.dumps (e.g., indent=2)."""
        return json.dumps(self.to_dict(), **json_kwargs)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], **constructor_kwargs):
        """Construct from a mapping. Pass constructor flags like allow_new_keys here."""
        if not isinstance(data, Mapping):
            raise TypeError("from_dict expects a mapping")
        return cls(data, **constructor_kwargs)

    def freeze(self) -> None:
        """Convenience: disallow adding keys and disallow mutation of existing values."""
        object.__setattr__(self, "_allow_new_keys", False)
        object.__setattr__(self, "_allow_value_mutation", False)

    # ---------- Nice repr / membership ----------
    def __repr__(self) -> str:
        pairs = ", ".join(f"{k}={v!r}" for k, v in self.items())
        return f"<{type(self).__name__} {pairs}>"

    def __contains__(self, item: Any) -> bool:
        """
        Membership checks both keys and values...
        """
        if dict.__contains__(self, item):
            return True
        # fall back to checking values
        for v in self.values():
            if v == item:
                return True
        return False
