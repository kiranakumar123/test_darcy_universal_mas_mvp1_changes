from datetime import datetime
from fnmatch import fnmatch

import pytest

from universal_framework.contracts.exceptions import TemplateValidationError
from universal_framework.contracts.templates import StoredTemplate
from universal_framework.templates import TemplateStore


class FakeRedisAdapter:
    def __init__(self) -> None:
        self.store = {}

    async def execute_command(self, command: str, *args, **kwargs):
        if command == "KEYS":
            pattern = args[0]
            return [k for k in self.store if fnmatch(k, pattern)]
        if command == "GET":
            return self.store.get(args[0])
        if command == "SET":
            key, value = args[0], args[1]
            self.store[key] = value
            return True
        raise NotImplementedError(command)


@pytest.mark.asyncio
async def test_store_and_retrieve_template():
    adapter = FakeRedisAdapter()
    store = TemplateStore(adapter)

    template = StoredTemplate(
        template_id="tmp1",
        template_type="policy_communication",
        subject_template="Policy {name}",
        body_template="<p>{name}</p>",
        variables=["name"],
        metadata={},
        created_date=datetime.now(),
        last_used=datetime.now(),
        usage_count=0,
    )

    result = await store.store_template(template)
    assert result is True

    found = await store.find_template_by_type("policy_communication")
    assert found is not None
    assert found.template_id == "tmp1"
    assert found.usage_count == 1


@pytest.mark.asyncio
async def test_missing_template_returns_none():
    adapter = FakeRedisAdapter()
    store = TemplateStore(adapter)
    result = await store.find_template_by_type("unknown")
    assert result is None


@pytest.mark.asyncio
async def test_template_validation_error():
    adapter = FakeRedisAdapter()
    store = TemplateStore(adapter)

    bad_template = StoredTemplate(
        template_id="tmp2",
        template_type="marketing_promotion",
        subject_template="Attack",
        body_template="<script>alert('x')</script>",
        variables=[],
        metadata={},
        created_date=datetime.now(),
        last_used=datetime.now(),
        usage_count=0,
    )

    with pytest.raises(TemplateValidationError):
        await store.store_template(bad_template)


@pytest.mark.asyncio
async def test_lookup_records_metrics():
    adapter = FakeRedisAdapter()
    store = TemplateStore(adapter)

    template = StoredTemplate(
        template_id="tmp3",
        template_type="team_notification",
        subject_template="Hi",
        body_template="<p>Body</p>",
        variables=[],
        metadata={},
        created_date=datetime.now(),
        last_used=datetime.now(),
        usage_count=0,
    )
    await store.store_template(template)
    await store.find_template_by_type("team_notification")
    assert any(key.startswith("template_lookup_ms") for key in store.metrics.histograms)
