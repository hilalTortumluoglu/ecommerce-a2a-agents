#!/usr/bin/env python3
"""
E-Commerce A2A Demo Client

Tests all agents directly via A2A protocol and the REST API.
Usage:
  python scripts/test_client.py              # Run all tests
  python scripts/test_client.py --chat       # Interactive chat mode
  python scripts/test_client.py --agent product  # Test specific agent
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from a2a.client import A2AClient
from a2a.types import MessageSendParams, SendMessageRequest
from a2a.utils import new_agent_text_message
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

console = Console()

AGENTS = {
    "orchestrator": "http://localhost:8000",
    "product": "http://localhost:8006",
    "order": "http://localhost:8005",
    "search": "http://localhost:8004",
}

TEST_QUERIES = {
    "orchestrator": [
        "Merhaba! Bana iyi bir kulaklık önerir misin?",
        "ord-001 siparişim nerede?",
        "Sony WH-1000XM5 piyasa fiyatı nedir?",
    ],
    "product": [
        "Elektronik kategorisinde en iyi ürünler neler?",
        "prod-001 hakkında detaylı bilgi ver",
        "500 TL altı ürün var mı?",
    ],
    "order": [
        "ahmet.yilmaz@example.com için tüm siparişleri göster",
        "ord-001 nerede?",
        "ord-003 iptal edebilir miyim?",
    ],
    "search": [
        "Sony WH-1000XM5 Türkiye fiyatı 2025",
        "En iyi kablosuz kulaklıklar yorumları",
    ],
}


async def send_a2a_message(agent_url: str, query: str) -> str:
    """Send a message to an A2A agent and return the response."""
    async with httpx.AsyncClient(timeout=60.0) as httpx_client:
        try:
            client = A2AClient(
                httpx_client = httpx_client, 
                url = agent_url
            )
            request = SendMessageRequest(
                id=str(uuid.uuid4()), 
                params=MessageSendParams(
                    message=new_agent_text_message(query),
                )
            )
            response = await client.send_message(request)

            result_text = ""
            if hasattr(response, "root"):
                resp_root = response.root
                if hasattr(resp_root, "result"):
                    result = resp_root.result
                    if hasattr(result, "artifacts") and result.artifacts:
                        for artifact in result.artifacts:
                            if hasattr(artifact, "parts"):
                                for part in artifact.parts:
                                    if hasattr(part, "root") and hasattr(part.root, "text"):
                                        result_text += part.root.text
                    elif hasattr(result, "status") and result.status and result.status.message:
                        msg = result.status.message
                        if hasattr(msg, "parts"):
                            for part in msg.parts:
                                if hasattr(part, "root") and hasattr(part.root, "text"):
                                    result_text += part.root.text

            return result_text or "(Yanıt alınamadı)"
        except Exception as e:
            return f"❌ Hata: {e}"


async def check_health() -> None:
    """Check health of all services."""
    console.print("\n[bold blue]🏥 Servis Sağlık Kontrolü[/bold blue]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Servis")
    table.add_column("URL")
    table.add_column("Durum")

    checks = [
        ("MCP Server", "http://localhost:8090/health"),
        ("Orchestrator", "http://localhost:8000/health"),
        ("Product Agent", "http://localhost:8006/.well-known/agent.json"),
        ("Order Agent", "http://localhost:8005/.well-known/agent.json"),
        ("Search Agent", "http://localhost:8004/.well-known/agent.json"),
    ]

    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in checks:
            try:
                resp = await client.get(url)
                status = "✅ Online" if resp.status_code == 200 else f"⚠️ {resp.status_code}"
            except Exception as e:
                status = f"❌ Offline ({str(e)[:30]})"
            table.add_row(name, url, status)

    console.print(table)


async def test_rest_api() -> None:
    """Test the REST chat API."""
    console.print("\n[bold blue]🌐 REST API Testi[/bold blue]")
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                "http://localhost:8000/api/chat",
                json={"message": "Merhaba! Bana en popüler elektronik ürünü öner."},
            )
            data = resp.json()
            console.print(Panel(
                Markdown(data.get("response", "Yanıt yok")),
                title="REST API Yanıtı",
                border_style="green",
            ))
        except Exception as e:
            console.print(f"[red]REST API hatası: {e}[/red]")


async def run_agent_tests(agent_name: str) -> None:
    """Test a specific agent."""
    agent_url = AGENTS.get(agent_name)
    if not agent_url:
        console.print(f"[red]Bilinmeyen ajan: {agent_name}[/red]")
        return

    queries = TEST_QUERIES.get(agent_name, [])
    console.print(f"\n[bold blue]🤖 {agent_name.title()} Agent Testi[/bold blue]")

    for query in queries:
        console.print(f"\n[bold yellow]📤 Soru:[/bold yellow] {query}")
        response = await send_a2a_message(agent_url, query)
        console.print(Panel(
            Markdown(response[:2000] + "..." if len(response) > 2000 else response),
            title=f"{agent_name.title()} Agent Yanıtı",
            border_style="cyan",
        ))
        await asyncio.sleep(1)


async def interactive_chat() -> None:
    """Interactive chat mode with the orchestrator."""
    console.print(Panel(
        "[bold green]E-Commerce AI Asistan[/bold green]\n"
        "Orchestrator üzerinden konuşuyorsunuz.\n"
        "Çıkmak için 'exit' yazın.\n\n"
        "Örnek sorular:\n"
        "• Kulaklık önerir misin?\n"
        "• ord-001 siparişim nerede?\n"
        "• Sony WH-1000XM5 fiyatı ne kadar?",
        title="💬 Sohbet Modu",
        border_style="green",
    ))

    while True:
        try:
            user_input = input("\n[Siz]: ").strip()
            if user_input.lower() in ("exit", "quit", "q", "çık"):
                console.print("[yellow]Görüşmek üzere! 👋[/yellow]")
                break
            if not user_input:
                continue

            console.print("[dim]Düşünüyorum...[/dim]")
            response = await send_a2a_message(AGENTS["orchestrator"], user_input)
            console.print(Panel(
                Markdown(response),
                title="🤖 Asistan",
                border_style="blue",
            ))
        except KeyboardInterrupt:
            console.print("\n[yellow]Görüşmek üzere! 👋[/yellow]")
            break


async def main() -> None:
    parser = argparse.ArgumentParser(description="E-Commerce A2A Demo Client")
    parser.add_argument("--chat", action="store_true", help="Interactive chat mode")
    parser.add_argument(
        "--agent",
        choices=list(AGENTS.keys()),
        help="Test a specific agent",
    )
    parser.add_argument("--health", action="store_true", help="Check service health only")
    args = parser.parse_args()

    console.print(Panel(
        "[bold]E-Commerce A2A Multi-Agent System[/bold]\n"
        "A2A Protocol + LangGraph + MCP + Tavily Web Search",
        title="🛒 Demo Client",
        border_style="magenta",
    ))

    if args.health:
        await check_health()
        return

    await check_health()

    if args.chat:
        await interactive_chat()
    elif args.agent:
        await run_agent_tests(args.agent)
    else:
        # Run all tests
        await test_rest_api()
        for agent_name in ["product", "order", "search", "orchestrator"]:
            await run_agent_tests(agent_name)


if __name__ == "__main__":
    asyncio.run(main())
