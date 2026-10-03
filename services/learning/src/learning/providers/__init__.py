"""Small provider boundary shared by deterministic fixtures and remote models."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderRequest:
    operation: str
    system: str
    data: dict
    schema: dict
    max_output_tokens: int


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    model_version: str
    input_tokens: int
    output_tokens: int


class Provider(Protocol):
    @property
    def identity(self) -> str: ...

    def complete(self, request: ProviderRequest) -> ProviderResponse: ...
