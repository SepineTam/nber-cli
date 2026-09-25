#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : topic-related.py

import os
import sys
import math

# We use python 3.11+ as runtime,
# we have known that python 3.7 does not support tomllib
import tomllib

from pathlib import Path

import requests


# 加载 skill 目录下的 config.toml
_SKILL_DIR = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _SKILL_DIR / "config.toml"


def _load_config() -> dict:
    """Load local config.toml from the skill directory."""
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"config.toml not found at {_CONFIG_PATH}. "
            "Copy config.example.toml to config.toml first."
        )
    with _CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)


def _get_api_key(cfg: dict) -> str:
    """Return API key from config file or environment variable."""
    key = cfg.get("embedding", {}).get("api_key", "")
    if key:
        return key

    env_var = cfg.get("embedding", {}).get("api_env", "OPENAI_API_KEY")
    key = os.environ.get(env_var, "")
    if key:
        return key

    raise ValueError(
        f"API key not found. Set it in config.toml or export {env_var}."
    )


def _get_embeddings(texts: list[str], cfg: dict) -> list[list[float]]:
    """Fetch embedding vectors for a batch of texts via OpenAI-compatible API."""
    base_url = cfg.get("embedding", {}).get("base_url", "https://api.openai.com/v1")
    model = cfg.get("embedding", {}).get("model", "text-embedding-3-small")
    api_key = _get_api_key(cfg)

    url = f"{base_url.rstrip('/')}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": texts,
        "encoding_format": "float",
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Embedding request failed: {exc}") from exc

    data = response.json()
    embeddings = sorted(data["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in embeddings]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def related(
    topic: str,
    abstract: str,
    method: str = "cosine"
) -> float:
    """Compute cosine similarity between a topic and a paper abstract.

    Args:
        topic: The research topic or keyword phrase.
        abstract: The paper abstract.
        method: Only "cosine" is supported at the moment.

    Returns:
        A cosine similarity score in the range [-1, 1].
    """
    if method != "cosine":
        raise ValueError(f"Unsupported similarity method: {method}")

    cfg = _load_config()
    vectors = _get_embeddings([topic, abstract], cfg)
    return _cosine_similarity(vectors[0], vectors[1])


def main() -> int:
    """CLI entry point for quick manual testing."""
    if len(sys.argv) not in (3, 4):
        print("Usage: uv run scripts/topic-related.py <topic> <abstract> [method]")
        return 1

    topic, abstract = sys.argv[1], sys.argv[2]
    method = sys.argv[3] if len(sys.argv) == 4 else "cosine"
    score = related(topic, abstract, method=method)
    print(f"similarity: {score:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
