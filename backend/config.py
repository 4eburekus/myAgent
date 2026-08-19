# базовые настройки
import os
from dataclasses import dataclass, field
from typing import List
from pydantic_ai import Agent

# Настройка окружения
os.environ["OPENAI_BASE_URL"] = "http://10.45.0.75:8000/v1"

@dataclass
class AssistantDeps:
    notes: List[str] = field(default_factory=list)

# Создаем объект агента здесь, чтобы его могли импортировать инструменты
agent = Agent(
    model='openai:RedHatAi/Qwen3.6-35B-A3B-NVFP4',
    deps_type=AssistantDeps,
    system_prompt=(
        "Ты — консольный ассистент. Правила:\n"
        "- Общайся с пользователем на русском языке.\n"
        "- Используй инструмент 'calculate' для всех вычислений.\n"
        "- Сохраняй ключевую информацию в 'agent_notes'.\n"
        "- Перед вызовом инструмента кратко опиши, что ты собираешься сделать и почему.\n"
        "- Стиль: краткий и четкий."
    ),
    retries=2
)