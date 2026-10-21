"""What tax items refuse: missing fields, old years, negative amounts, unknown kinds, backwards periods."""

import pytest
from tax_helpers import TAX_ITEMS, create


@pytest.mark.parametrize("missing", ["tax_year", "tax_type"])
def test_a_tax_item_needs_a_year_and_a_type(client, owner, missing):
    body = {"tax_year": 2026, "tax_type": "vat"}
    del body[missing]
    response = client.post(TAX_ITEMS, headers=owner, json=body)
    assert response.status_code == 422, response.text


def test_tax_year_cannot_be_before_2000(client, owner):
    assert create(client, owner, tax_year=1999).status_code == 422
    assert create(client, owner, tax_year=2000).status_code == 201


def test_tax_year_must_be_a_whole_number(client, owner):
    assert create(client, owner, tax_year="this year").status_code == 422
    assert create(client, owner, tax_year=2026.5).status_code == 422


def test_tax_type_must_be_a_known_kind(client, owner):
    assert create(client, owner, tax_type="customs").status_code == 422
    for kind in (
        "income",
        "vat",
        "withholding",
        "property",
        "social_security",
        "other",
    ):
        response = create(client, owner, tax_type=kind)
        assert response.status_code == 201, response.text


def test_status_must_be_a_known_state(client, owner):
    assert create(client, owner, status="forgotten").status_code == 422
    for state in ("estimated", "open", "filed", "paid", "waived", "overdue"):
        response = create(client, owner, status=state)
        assert response.status_code == 201, response.text


def test_amount_due_cannot_be_negative(client, owner):
    assert create(client, owner, amount_due=-1).status_code == 422
    assert create(client, owner, amount_due=0).status_code == 201


def test_amount_paid_cannot_be_negative(client, owner):
    assert create(client, owner, amount_paid=-0.5).status_code == 422
    assert create(client, owner, amount_paid=0).status_code == 201


def test_jurisdiction_and_currency_are_at_most_12_characters(client, owner):
    assert create(client, owner, jurisdiction="J" * 13).status_code == 422
    assert create(client, owner, currency="C" * 13).status_code == 422
    assert (
        create(client, owner, jurisdiction="J" * 12, currency="C" * 12).status_code
        == 201
    )


def test_metadata_must_be_an_object(client, owner):
    assert create(client, owner, metadata=["not", "an", "object"]).status_code == 422
    assert create(client, owner, metadata={"form": "PND90"}).status_code == 201


def test_dates_must_be_real_dates(client, owner):
    assert create(client, owner, due_date="2026-02-30").status_code == 422
    assert create(client, owner, period_start="January").status_code == 422


def test_a_tax_item_cannot_carry_fields_the_cell_does_not_know(client, owner):
    assert create(client, owner, rate=0.07).status_code == 422


def test_a_period_cannot_end_before_it_starts(client, owner):
    backwards = create(
        client, owner, period_start="2026-03-31", period_end="2026-03-01"
    )
    assert backwards.status_code == 422, backwards.text
    assert backwards.json()["detail"] == {
        "error": "invalid_value",
        "fields": ["period_end", "period_start"],
    }
    one_day = create(client, owner, period_start="2026-03-31", period_end="2026-03-31")
    assert one_day.status_code == 201, one_day.text


def test_a_period_may_have_only_one_end(client, owner):
    assert create(client, owner, period_start="2026-03-31").status_code == 201
    assert create(client, owner, period_end="2026-03-01").status_code == 201


def test_moving_the_period_end_before_its_start_is_refused_on_update(client, owner):
    item = create(
        client, owner, period_start="2026-01-01", period_end="2026-03-31"
    ).json()
    path = f"{TAX_ITEMS}/{item['id']}"
    refused = client.patch(path, headers=owner, json={"period_end": "2025-12-31"})
    assert refused.status_code == 422, refused.text
    assert refused.json()["detail"]["fields"] == ["period_end", "period_start"]
    stored = client.get(path, headers=owner).json()
    assert stored["period_end"] == "2026-03-31"
    assert stored["version"] == 1
    # A patch that touches neither date still works.
    paid = client.patch(path, headers=owner, json={"status": "paid"})
    assert paid.status_code == 200, paid.text


def test_moving_the_period_start_after_its_end_is_refused_on_update(client, owner):
    item = create(
        client, owner, period_start="2026-01-01", period_end="2026-03-31"
    ).json()
    path = f"{TAX_ITEMS}/{item['id']}"
    refused = client.patch(path, headers=owner, json={"period_start": "2026-04-01"})
    assert refused.status_code == 422, refused.text
    assert client.get(path, headers=owner).json()["period_start"] == "2026-01-01"


def test_update_refuses_the_same_bad_values(client, owner):
    item = create(client, owner).json()
    path = f"{TAX_ITEMS}/{item['id']}"
    assert client.patch(path, headers=owner, json={"tax_year": 1990}).status_code == 422
    assert client.patch(path, headers=owner, json={"amount_due": -3}).status_code == 422
    assert client.patch(path, headers=owner, json={"status": "lost"}).status_code == 422
    assert client.get(path, headers=owner).json()["version"] == 1


def test_a_required_field_cannot_be_cleared(client, owner):
    item = create(client, owner).json()
    path = f"{TAX_ITEMS}/{item['id']}"
    cleared = client.patch(path, headers=owner, json={"tax_year": None})
    assert cleared.status_code == 422, cleared.text
    assert client.get(path, headers=owner).json()["tax_year"] == 2026
