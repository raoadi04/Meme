import pytest
from unittest.mock import Mock, patch
from mem0.llms.openai import OpenAILLM

@pytest.fixture
def mock_openai_client():
    with patch('mem0.llms.openai.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_openai.return_value = mock_client
        yield mock_client


def test_generate_response_without_tools(mock_openai_client):
    llm = OpenAILLM()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]
    
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="I'm doing well, thank you for asking!"))]
    mock_openai_client.chat.completions.create.return_value = mock_response

    response = llm.generate_response(messages)

    mock_openai_client.chat.completions.create.assert_called_once_with(
        model="gpt-4o",
        messages=messages
    )
    assert response.choices[0].message.content == "I'm doing well, thank you for asking!"
    

def test_generate_response_with_tools(mock_openai_client):
    llm = OpenAILLM()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Add a new memory: Today is a sunny day."}
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "add_memory",
                "description": "Add a memory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {"type": "string", "description": "Data to add to memory"}
                    },
                    "required": ["data"],
                },
            },
        }
    ]
    
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Memory added successfully."))]
    mock_openai_client.chat.completions.create.return_value = mock_response

    response = llm.generate_response(messages, tools=tools)

    mock_openai_client.chat.completions.create.assert_called_once_with(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    assert response.choices[0].message.content == "Memory added successfully."
    