"""Listing, grouping and the lifecycle of a tax item."""

from tax_helpers import TAX_ITEMS, create


def ids(response):
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def test_list_filters_by_tax_year(client, owner):
    this_year = create(client, owner, tax_year=2026).json()
    create(client, owner, tax_year=2025)
    listed = client.get(TAX_ITEMS, headers=owner, params={"tax_year": 2026})
    assert ids(listed) == [this_year["id"]]


def test_list_filters_by_tax_type_and_status(client, owner):
    wanted = create(client, owner, tax_type="vat", status="open").json()
    create(client, owner, tax_type="vat", status="paid")
    create(client, owner, tax_type="property", status="open")
    listed = client.get(
        TAX_ITEMS, headers=owner, params={"tax_type": "vat", "status": "open"}
    )
    assert ids(listed) == [wanted["id"]]


def test_a_filter_can_list_several_values(client, owner):
    open_item = create(client, owner, status="open").json()
    overdue = create(client, owner, status="overdue").json()
    create(client, owner, status="paid")
    listed = client.get(
        TAX_ITEMS,
        headers=owner,
        params=[("status", "open"), ("status", "overdue")],
    )
    assert sorted(ids(listed)) == sorted([open_item["id"], overdue["id"]])


def test_an_unknown_filter_is_refused(client, owner):
    listed = client.get(TAX_ITEMS, headers=owner, params={"jurisdiction": "TH"})
    assert listed.status_code == 422


def test_list_is_ordered_by_id(client, owner):
    first = create(client, owner, tax_year=2026).json()
    second = create(client, owner, tax_year=2020).json()
    assert ids(client.get(TAX_ITEMS, headers=owner)) == [first["id"], second["id"]]
    newest_first = client.get(TAX_ITEMS, headers=owner, params={"order": "desc"})
    assert ids(newest_first) == [second["id"], first["id"]]


def test_stats_count_tax_items_per_status(client, owner):
    create(client, owner, status="open")
    create(client, owner, status="open")
    create(client, owner)
    stats = client.get(
        f"{TAX_ITEMS}/stats", headers=owner, params={"group_by": "status"}
    )
    assert stats.status_code == 200, stats.text
    assert stats.json()["groups"] == {"open": 2, "estimated": 1}


def test_stats_count_tax_items_per_year_and_type(client, owner):
    create(client, owner, tax_year=2025, tax_type="income")
    create(client, owner, tax_year=2026, tax_type="vat")
    create(client, owner, tax_year=2026, tax_type="vat")
    by_year = client.get(
        f"{TAX_ITEMS}/stats", headers=owner, params={"group_by": "tax_year"}
    )
    assert by_year.json()["groups"] == {"2025": 1, "2026": 2}
    by_type = client.get(
        f"{TAX_ITEMS}/stats",
        headers=owner,
        params={"group_by": "tax_type", "tax_year": 2026},
    )
    assert by_type.json()["groups"] == {"vat": 2}


def test_stats_refuse_a_field_that_is_not_a_filter(client, owner):
    for field in ("amount_due", "jurisdiction", "due_date", "evidence_ref"):
        stats = client.get(
            f"{TAX_ITEMS}/stats", headers=owner, params={"group_by": field}
        )
        assert stats.status_code == 422, field


def test_filing_and_paying_an_item_bumps_its_version(client, owner):
    item = create(client, owner, amount_due=1000, status="open").json()
    path = f"{TAX_ITEMS}/{item['id']}"
    filed = client.patch(path, headers=owner, json={"status": "filed"})
    assert filed.json()["version"] == 2
    paid = client.patch(
        path, headers=owner, json={"status": "paid", "amount_paid": 1000}
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"
    assert paid.json()["amount_paid"] == 1000
    assert paid.json()["version"] == 3


def test_a_patch_that_changes_nothing_keeps_the_version(client, owner):
    item = create(client, owner, status="open", amount_due=500).json()
    path = f"{TAX_ITEMS}/{item['id']}"
    same = client.patch(path, headers=owner, json={"status": "open", "amount_due": 500})
    assert same.status_code == 200, same.text
    assert same.json()["version"] == 1


def test_a_stale_expected_version_is_refused(client, owner):
    item = create(client, owner).json()
    path = f"{TAX_ITEMS}/{item['id']}"
    client.patch(path, headers=owner, json={"status": "open"})
    stale = client.patch(
        path, headers=owner, json={"status": "paid", "expected_version": 1}
    )
    assert stale.status_code == 409, stale.text
    assert client.get(path, headers=owner).json()["status"] == "open"


def test_deleting_a_tax_item_removes_it(client, owner):
    item = create(client, owner).json()
    path = f"{TAX_ITEMS}/{item['id']}"
    assert client.delete(path, headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404
    assert ids(client.get(TAX_ITEMS, headers=owner)) == []


def test_a_tax_item_that_does_not_exist_is_404(client, owner):
    assert client.get(f"{TAX_ITEMS}/999999999", headers=owner).status_code == 404
    patched = client.patch(
        f"{TAX_ITEMS}/999999999", headers=owner, json={"status": "paid"}
    )
    assert patched.status_code == 404
    assert client.delete(f"{TAX_ITEMS}/999999999", headers=owner).status_code == 404
