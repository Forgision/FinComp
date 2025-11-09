# app_registry.py
from app.utils.unique_dict import UniqueEnumDict


# Single registry instance (you could import this anywhere)
ENDPOINTS = UniqueEnumDict(
    DASHBOARD="dashboard",
    allow_new_keys=False,
    allow_value_mutation=False,
)

ENDPOINTS.freeze()
