import os

import pytest

import emily_ai_bot as emily


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    monkeypatch.setattr(emily, "DB_FILE", str(tmp_path / "emily-test.db"))
    monkeypatch.setattr(emily, "FREE_DAILY", 2)
    monkeypatch.setattr(emily, "PREMIUM_DAILY", 4)
    emily.init_db()
    yield


def add_user(user_id=1, plan="free", credits=0):
    emily.ensure_user(user_id, f"user{user_id}")
    with emily.closing(emily.db()) as conn:
        conn.execute("UPDATE users SET plan=?, credits=? WHERE user_id=?", (plan, credits, user_id))
        conn.commit()


def test_quota_is_50_style_and_credits_are_one_generation(test_db):
    add_user(1, credits=1)
    assert emily.consume_generation(1) == "free"
    assert emily.consume_generation(1) == "free"
    assert emily.consume_generation(1) == "credit"
    assert emily.consume_generation(1) is None


def test_new_day_resets_quota_without_manual_command(test_db):
    add_user(1)
    with emily.closing(emily.db()) as conn:
        conn.execute("UPDATE users SET daily_messages=2, quota_date=? WHERE user_id=1", ("2000-01-01",))
        conn.commit()
    assert emily.consume_generation(1) == "free"


def test_failed_generation_can_be_refunded(test_db):
    add_user(1)
    kind = emily.consume_generation(1)
    assert kind == "free"
    emily.refund_generation(1, kind)
    assert emily.get_user(1)["daily_messages"] == 0
    assert emily.get_user(1)["total_messages"] == 0


def test_credit_refund_returns_credit(test_db):
    add_user(1, credits=1)
    emily.consume_generation(1)
    emily.consume_generation(1)
    kind = emily.consume_generation(1)
    assert kind == "credit"
    emily.refund_generation(1, kind)
    assert emily.get_user(1)["credits"] == 1


def test_memory_extracts_common_user_facts():
    found = dict(emily.extract_simple_memories("My name is Raj and I study BCA. I like cricket!"))
    assert found["name"] == "Raj"
    assert found["study"].lower() == "bca"
    assert found["likes"].lower() == "cricket"


def test_memory_crud(test_db):
    add_user(1)
    emily.save_memory(1, "favorite_food", "biryani")
    assert emily.get_memories(1)[0]["memory_value"] == "biryani"
    assert emily.delete_memory(1, "favorite_food") is True
    assert emily.get_memories(1) == []


def test_admin_env_is_checked(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_ID", "123")
    assert emily.is_admin(123) is True
    assert emily.is_admin(456) is False


def test_invalid_admin_id_is_rejected(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_ID", "abc")
    with pytest.raises(RuntimeError):
        emily.admin_id()
