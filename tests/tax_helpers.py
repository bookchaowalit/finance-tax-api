"""Shared helpers for the tax domain tests."""

from typing import Any

TAX_ITEMS = "/v1/tax-items"


def create(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    body = {"tax_year": 2026, "tax_type": "income", **fields}
    return client.post(TAX_ITEMS, headers=owner, json=body)
