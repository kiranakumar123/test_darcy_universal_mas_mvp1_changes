from universal_framework.llm.providers import LLMConfig
from universal_framework.workflow.builder import WorkflowBuilder


def test_builder_injects_provider():
    class MockProvider:
        def __init__(self) -> None:
            self.config = LLMConfig(
                openai_api_key="test", model_name="gpt-mock", temperature=0.0
            )

        def create_agent_llm(self) -> object:
            return object()

    provider = MockProvider()
    builder = WorkflowBuilder(llm_provider=provider)
    agent = builder.create_requirements_agent()
    assert agent.llm_provider is provider
