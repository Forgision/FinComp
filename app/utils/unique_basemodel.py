from pydantic import BaseModel, model_validator, ValidationError
from collections import defaultdict
from typing import Any, ClassVar, Set


class UniqueValuesModel(BaseModel):
    """
    Base model that enforces unique values across its fields.

    Class attributes to customize behavior:
      - __unique_ignore_fields__ : Set[str] of field names to ignore.
      - __unique_allow_values__  : Set[Any] of values allowed to repeat (e.g. {None}).
    """

    # Use sets for efficient 'in' checks
    __unique_ignore_fields__: ClassVar[Set[str]] = set()
    # By default, we allow 'None' to be repeated, as this is a common use case.
    __unique_allow_values__: ClassVar[Set[Any]] = {None}

    @model_validator(mode="after")
    def ensure_unique_values(self) -> "UniqueValuesModel":
        # defaultdict makes it easy to append to a list for a new key
        seen_values = defaultdict(list)

        # Iterate through the model's dictionary representation
        for field_name, value in self.model_dump().items():
            # 1. Skip fields in the ignore list
            if field_name in self.__unique_ignore_fields__:
                continue

            # 2. Skip values in the allow list
            # We must check if the value is hashable before an 'in' check on the set
            is_hashable = getattr(value, "__hash__", None) is not None

            if is_hashable and value in self.__unique_allow_values__:
                continue

            # 3. Track the value
            # We must use a hashable key.
            # If the value itself isn't hashable (like a list),
            # this validator can't check it. We raise an error
            # to make this explicit.
            if not is_hashable:
                raise TypeError(
                    f"Field '{field_name}' has an unhashable type '{type(value).__name__}'. "
                    "This validator only supports hashable types (str, int, float, tuple, etc.). "
                    f"Please add '{field_name}' to __unique_ignore_fields__."
                )

            seen_values[value].append(field_name)

        # 4. Find and report any duplicates
        duplicates = {
            # Use repr(val) for a clear error message (e.g., shows 'foo' vs foo)
            repr(val): fields
            for val, fields in seen_values.items()
            if len(fields) > 1
        }

        if duplicates:
            # Format a clean error message
            error_msg_parts = [
                f"{val} found in fields: {fields}" for val, fields in duplicates.items()
            ]
            raise ValueError(f"Duplicate values found: {'; '.join(error_msg_parts)}")

        return self


# --- Example Usage ---


class MyData(UniqueValuesModel):
    # Let's ignore 'field_c' and allow '0' to repeat
    __unique_ignore_fields__ = {"field_c"}
    __unique_allow_values__ = {None, 0}

    field_a: str
    field_b: int
    field_c: str  # This one will be ignored
    field_d: int  # This one is allowed to repeat '0'
    field_e: int  # So is this one


# 1. Example that PASSES
try:
    data_ok = MyData(
        field_a="hello",
        field_b=123,
        field_c="hello",  # Duplicate of 'field_a', but 'field_c' is ignored
        field_d=0,  # Duplicate of 'field_e', but '0' is allowed
        field_e=0,
    )
    print("Validation PASSED (as expected):")
    # print(data_ok.model_dump_json(indent=2))
except (ValidationError, ValueError) as e:
    print(f"Validation FAILED (unexpected):\n{e}\n")


print("\n" + "---" * 10 + "\n")

# 2. Example that FAILS
try:
    data_fail = MyData(
        field_a="FAIL",
        field_b=555,
        field_c="some_other_value",
        field_d=555,  # Duplicate of 'field_b'
        field_e=999,
    )
    print(f"Validation PASSED (unexpected):\n{data_fail}\n")
except (ValidationError, ValueError) as e:
    print("Validation FAILED (as expected):")
    print(e)
