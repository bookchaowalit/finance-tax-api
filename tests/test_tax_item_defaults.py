"""Defaults and duplicates of a tax item."""

from datetime import UTC, datetime

from tax_helpers import TAX_ITEMS, create


def test_new_tax_item_defaults_to_estimated_thai_baht_with_nothing_paid(client, owner):
    response = create(client, owner)
    assert response.status_code == 201, response.text
    item = response.json()
    assert item["status"] == "estimated"
    assert item["jurisdiction"] == "TH"
    assert item["currency"] == "THB"
    assert item["amount_paid"] == 0
    assert item["amount_due"] is None
    assert item["version"] == 1


def test_defaults_can_be_overridden(client, owner):
    item = create(
        client,
        owner,
        status="open",
        jurisdiction="SG",
        currency="SGD",
        amount_due=1200,
        amount_paid=300.25,
    ).json()
    assert item["status"] == "open"
    assert item["jurisdiction"] == "SG"
    assert item["currency"] == "SGD"
    assert item["amount_due"] == 1200
    assert item["amount_paid"] == 300.25


def test_amounts_keep_their_decimal_value(client, owner):
    item = create(client, owner, amount_due=15432.75).json()
    assert item["amount_due"] == 15432.75


def test_the_same_year_and_type_can_have_several_items(client, owner):
    first = create(client, owner, tax_year=2026, tax_type="vat")
    second = create(client, owner, tax_year=2026, tax_type="vat")
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] != second.json()["id"]


def test_an_import_keeps_the_old_id(client, owner):
    imported = create(client, owner, legacy_id=3141, evidence_ref="PND90-2025")
    assert imported.status_code == 201, imported.text
    assert imported.json()["id"] == 3141
    found = client.get(f"{TAX_ITEMS}/legacy/3141", headers=owner)
    assert found.status_code == 200, found.text
    assert found.json()["evidence_ref"] == "PND90-2025"
    assert create(client, owner, legacy_id=3141).status_code == 409


def test_an_import_may_carry_its_original_timestamps(client, owner):
    imported = create(
        client,
        owner,
        legacy_id=3142,
        created_at="2021-04-05T06:07:08+00:00",
        updated_at="2021-05-06T07:08:09+00:00",
    )
    assert imported.status_code == 201, imported.text
    created = datetime.fromisoformat(imported.json()["created_at"])
    assert created == datetime(2021, 4, 5, 6, 7, 8, tzinfo=UTC)
    refused = create(client, owner, created_at="2021-04-05T06:07:08+00:00")
    assert refused.status_code == 422, refused.text
