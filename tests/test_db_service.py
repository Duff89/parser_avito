import sqlite3
from types import SimpleNamespace

from db_service import SQLiteDBHandler


def make_ad(ad_id, price):
    return SimpleNamespace(
        id=ad_id,
        priceDetailed=SimpleNamespace(value=price),
    )


def make_db(tmp_path):
    SQLiteDBHandler._instance = None
    return SQLiteDBHandler(str(tmp_path / "database.db"))


def count_rows(db_name):
    with sqlite3.connect(db_name) as conn:
        return conn.execute("SELECT COUNT(*) FROM viewed").fetchone()[0]


def test_duplicate_id_and_price_is_stored_once(tmp_path):
    db = make_db(tmp_path)
    ad = make_ad(1, 100)

    db.add_record_from_page([ad, ad])
    db.add_record(ad)

    assert count_rows(db.db_name) == 1


def test_same_id_with_new_price_is_new_record(tmp_path):
    db = make_db(tmp_path)

    db.add_record_from_page([make_ad(1, 100), make_ad(1, 200)])

    assert count_rows(db.db_name) == 2
    assert db.record_exists(1, 100)
    assert db.record_exists(1, 200)
