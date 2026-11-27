"""Bedrock 모델 생성과 호출 안정성(패턴 8 미들웨어의 재시도 부분). 검색기·에이전트 공용.

호출마다 타임아웃 60초, 실패 시 1·2·4초 간격 3회 재시도, run() 한 번당 150초 상한.
import만으로 Bedrock을 호출하지 않는다.
"""
from __future__ import annotations

import contextvars
import time
from pathlib import Path

CLAUDE_MODEL_ID = "us.anthropic.claude-sonnet-4-6"  # 기본 ID는 과정 IAM에서 거부, us. 추론 프로필만 가능
EMBED_MODEL_ID = "amazon.titan-embed-text-v2:0"     # Cohere 임베딩·리랭크는 과정 IAM에서 AccessDenied
REGION = "us-east-1"
TIMEOUT_S = 60
RETRY_DELAYS_S = (1, 2, 4)
RUN_BUDGET_S = 150

_deadline: contextvars.ContextVar[float | None] = contextvars.ContextVar("deadline", default=None)


class LLMUnavailable(RuntimeError):
    pass


def load_env() -> None:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # 과정 공용 ../.env


def start_budget(seconds: float = RUN_BUDGET_S) -> None:
    """run()/resume() 시작 시 호출. 이후 call_bedrock은 상한을 넘으면 새 호출을 시작하지 않는다."""
    _deadline.set(time.monotonic() + seconds)


def call_bedrock(fn, *args, **kwargs):
    last = None
    for delay in (*RETRY_DELAYS_S, None):
        deadline = _deadline.get()
        if deadline is not None and time.monotonic() >= deadline:
            raise LLMUnavailable("run time budget exceeded")
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001 — 스로틀링·타임아웃·파싱 실패 모두 재시도 대상
            last = e
        if delay is None:
            break
        time.sleep(delay)
    raise LLMUnavailable(str(last)) from last


def chat(temperature: float = 0):
    from botocore.config import Config
    from langchain_aws import ChatBedrockConverse
    load_env()
    return ChatBedrockConverse(
        model=CLAUDE_MODEL_ID, region_name=REGION, temperature=temperature,
        config=Config(read_timeout=TIMEOUT_S, retries={"max_attempts": 1}),  # 재시도는 call_bedrock이 담당
    )


def embeddings():
    from langchain_aws import BedrockEmbeddings
    load_env()
    return BedrockEmbeddings(model_id=EMBED_MODEL_ID, region_name=REGION)
