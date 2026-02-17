import pytest
import httpx
import uuid
import asyncio
from a2a.client import A2AClient
from a2a.types import MessageSendParams, SendMessageRequest
from a2a.utils import new_agent_text_message

# Configuration
ORCHESTRATOR_URL = "http://localhost:8000"
PRODUCT_AGENT_URL = "http://localhost:8006"
ORDER_AGENT_URL = "http://localhost:8005"
SEARCH_AGENT_URL = "http://localhost:8004"
MCP_SERVER_URL = "http://localhost:8090"

@pytest.fixture
async def http_client():
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client

async def get_a2a_response(client: httpx.AsyncClient, agent_url: str, query: str):
    """Helper to send A2A message and extract text response."""
    a2a_client = A2AClient(httpx_client=client, url=agent_url)
    request = SendMessageRequest(
        id=str(uuid.uuid4()),
        params=MessageSendParams(
            message=new_agent_text_message(query),
        )
    )
    response = await a2a_client.send_message(request)
    
    result_text = ""
    if hasattr(response, "root") and hasattr(response.root, "result"):
        result = response.root.result
        if hasattr(result, "artifacts") and result.artifacts:
            for artifact in result.artifacts:
                for part in artifact.parts:
                    if hasattr(part.root, "text"):
                        result_text += part.root.text
        elif hasattr(result, "status") and result.status and result.status.message:
            for part in result.status.message.parts:
                if hasattr(part.root, "text"):
                    result_text += part.root.text
    return result_text

@pytest.mark.asyncio
async def test_all_services_health(http_client):
    """Test 1: Check if all services are online and responding."""
    endpoints = [
        (ORCHESTRATOR_URL + "/health", 200),
        (MCP_SERVER_URL + "/health", 200),
        (PRODUCT_AGENT_URL + "/.well-known/agent.json", 200),
        (ORDER_AGENT_URL + "/.well-known/agent.json", 200),
        (SEARCH_AGENT_URL + "/.well-known/agent.json", 200),
    ]
    
    for url, expected_status in endpoints:
        response = await http_client.get(url)
        assert response.status_code == expected_status, f"Service at {url} is down"

@pytest.mark.asyncio
async def test_search_agent_integration(http_client):
    """Test 2: Verify Search Agent can perform web searches."""
    query = "Sony WH-1000XM5 current price in Turkey 2024"
    response_text = await get_a2a_response(http_client, SEARCH_AGENT_URL, query)
    
    assert len(response_text) > 20, "Search agent response too short"
    assert any(keyword in response_text.lower() for keyword in ["sony", "price", "tl", "fiyat"]), \
        "Search agent response doesn't contain expected keywords"

@pytest.mark.asyncio
async def test_orchestrator_product_flow(http_client):
    """Test 3: Verify Orchestrator can handle product recommendation queries."""
    query = "En iyi gürültü engelleyici kulaklıkları listeler misin?"
    response_text = await get_a2a_response(http_client, ORCHESTRATOR_URL, query)
    
    assert len(response_text) > 50, "Orchestrator response too short"
    # Orchestrator usually routes this to product or search agent
    assert any(keyword in response_text.lower() for keyword in ["kulaklık", "öneri", "ürün", "model"]), \
        "Orchestrator response doesn't seem relevant to the query"

@pytest.mark.asyncio
async def test_error_handling_invalid_input(http_client):
    """Test 4: Verify agent behavior with empty or invalid input."""
    # Note: A2A SDK might catch empty messages, but let's test a very vague one
    query = "???" 
    response_text = await get_a2a_response(http_client, PRODUCT_AGENT_URL, query)
    
    # We expect some form of graceful handling or request for clarification
    assert len(response_text) > 0, "Agent should return a response even for vague queries"

@pytest.mark.asyncio
async def test_rest_api_integration(http_client):
    """Test 5: Verify the FastAPI REST endpoint on the orchestrator."""
    payload = {"message": "Sipariş durumumu kontrol etmek istiyorum."}
    response = await http_client.post(f"{ORCHESTRATOR_URL}/api/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0
