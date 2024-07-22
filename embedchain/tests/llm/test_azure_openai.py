from unittest.mock import MagicMock, patch

import pytest
from langchain.schema import HumanMessage, SystemMessage

from embedchain.config import BaseLlmConfig
from embedchain.llm.azure_openai import AzureOpenAILlm


@pytest.fixture
def azure_openai_llm():
    config = BaseLlmConfig(
        deployment_name="azure_deployment",
        temperature=0.7,
        model="gpt-4o-mini",
        max_tokens=50,
        system_prompt="System Prompt",
    )
    return AzureOpenAILlm(config)


def test_get_llm_model_answer(azure_openai_llm):
    with patch.object(AzureOpenAILlm, "_get_answer", return_value="Test Response") as mock_method:
        prompt = "Test Prompt"
        response = azure_openai_llm.get_llm_model_answer(prompt)
        assert response == "Test Response"
        mock_method.assert_called_once_with(prompt=prompt, config=azure_openai_llm.config)


def test_get_answer(azure_openai_llm):
    with patch("langchain_openai.AzureChatOpenAI") as mock_chat:
        mock_chat_instance = mock_chat.return_value
        mock_chat_instance.invoke.return_value = MagicMock(content="Test Response")

        prompt = "Test Prompt"
        response = azure_openai_llm._get_answer(prompt, azure_openai_llm.config)

        assert response == "Test Response"
        mock_chat.assert_called_once_with(
            deployment_name=azure_openai_llm.config.deployment_name,
            openai_api_version="2024-02-01",
            model_name=azure_openai_llm.config.model or "gpt-4o-mini",
            temperature=azure_openai_llm.config.temperature,
            max_tokens=azure_openai_llm.config.max_tokens,
            streaming=azure_openai_llm.config.stream,
        )


def test_get_messages(azure_openai_llm):
    prompt = "Test Prompt"
    system_prompt = "Test System Prompt"
    messages = azure_openai_llm._get_messages(prompt, system_prompt)
    assert messages == [
        SystemMessage(content="Test System Prompt", additional_kwargs={}),
        HumanMessage(content="Test Prompt", additional_kwargs={}, example=False),
    ]


def test_when_no_deployment_name_provided():
    config = BaseLlmConfig(temperature=0.7, model="gpt-4o-mini", max_tokens=50, system_prompt="System Prompt")
    with pytest.raises(ValueError):
        llm = AzureOpenAILlm(config)
        llm.get_llm_model_answer("Test Prompt")


def test_with_api_version():
    config = BaseLlmConfig(
        deployment_name="azure_deployment",
        temperature=0.7,
        model="gpt-4o-mini",
        max_tokens=50,
        system_prompt="System Prompt",
        api_version="2024-02-01",
    )

    with patch("langchain_openai.AzureChatOpenAI") as mock_chat:
        llm = AzureOpenAILlm(config)
        llm.get_llm_model_answer("Test Prompt")

        mock_chat.assert_called_once_with(
            deployment_name="azure_deployment",
            openai_api_version="2024-02-01",
            model_name="gpt-4o-mini",
            temperature=0.7,
            max_tokens=50,
            streaming=False,
        )
