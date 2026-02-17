"""A2A AgentExecutor for the Orchestrator."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InvalidParamsError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_task
from a2a.utils.errors import ServerError
from langchain_core.messages import AIMessage, HumanMessage
from typing_extensions import override

from agents.orchestrator.agent import build_orchestrator
from utils.logging import get_logger

logger = get_logger(__name__)


class OrchestratorExecutor(AgentExecutor):
    """Wraps the LangGraph Orchestrator as an A2A-compliant executor."""

    def __init__(self) -> None:
        self.agent = build_orchestrator()
        logger.info("orchestrator_executor_initialized")

    @override
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if not context.message:
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        logger.info("orchestrator_execute", query=query[:100])

        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.submit()
        await updater.start_work()

        try:
            await updater.update_status(
                TaskState.working,
                message=updater.new_agent_message(
                    parts=[TextPart(text="İsteğinizi analiz ediyorum ve uygun uzman ajana yönlendiriyorum...")]
                ),
            )

            messages = [HumanMessage(content=query)]
            final_response = ""

            async for chunk in self.agent.astream(
                {"messages": messages, "session_id": task.context_id, "delegated_to": None},
                stream_mode="values",
            ):
                msgs = chunk.get("messages", [])
                if msgs:
                    last_msg = msgs[-1]
                    if isinstance(last_msg, AIMessage) and last_msg.content:
                        content = last_msg.content
                        if isinstance(content, list):
                            text_parts = [
                                c["text"]
                                for c in content
                                if isinstance(c, dict) and c.get("type") == "text"
                            ]
                            final_response = " ".join(text_parts)
                        elif isinstance(content, str):
                            final_response = content

            if not final_response:
                final_response = "Üzgünüm, isteğinizi işleyemedim. Lütfen tekrar deneyin."

            await updater.add_artifact(
                parts=[Part(root=TextPart(text=final_response))],
                artifact_id=f"orchestrator-response-{task.id}",
                name="Shopping Assistant Response",
            )
            await updater.complete()
            logger.info("orchestrator_complete", task_id=task.id)

        except Exception as e:
            logger.error("orchestrator_error", error=str(e), task_id=task.id)
            await updater.failed(
                message=updater.new_agent_message(
                    parts=[TextPart(text=f"Sistem hatası: {str(e)}. Lütfen tekrar deneyin.")]
                )
            )

    @override
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise ServerError(error=UnsupportedOperationError())
