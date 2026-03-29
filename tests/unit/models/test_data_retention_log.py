# tests/unit/models/test_data_retention_log.py
from datetime import UTC, datetime
from src.models.data_retention_log import DataRetentionLog

def test_warning_sent_instantiation():
    log = DataRetentionLog(
        user_id="user_abc",
        event_type="warning_sent",
        days_inactive=155,
    )
    assert log.event_type == "warning_sent"
    assert log.days_inactive == 155
    assert log.sources_deleted == 0
    assert log.id is None
    assert isinstance(log.created_at, datetime)

def test_data_purged_with_counts():
    log = DataRetentionLog(
        user_id="user_xyz",
        event_type="data_purged",
        days_inactive=183,
        sources_deleted=7,
    )
    assert log.sources_deleted == 7
    assert log.event_type == "data_purged"
