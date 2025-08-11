from universal_framework.compliance.classification import DataClassificationManager
from universal_framework.contracts.session.interfaces import DataClassification


def test_ttl_mapping() -> None:
    manager = DataClassificationManager()
    assert manager.get_ttl_for_classification(DataClassification.PUBLIC) == 3600
    assert (
        manager.get_ttl_for_classification(DataClassification.HIGHLY_SENSITIVE) == 900
    )


def test_classify_session_data() -> None:
    manager = DataClassificationManager()
    result = manager.classify_session_data({"ssn": "123-45-6789"})
    assert result is DataClassification.HIGHLY_SENSITIVE
