"""
Q - question
A - answer: generated_text from RAG pipeline
C - contexts: context used for generation
G - ground_truths: ground truth answer
"""
from __future__ import annotations

import asyncio
import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from ragas.callbacks import new_group
from ragas.run_config import RunConfig

if t.TYPE_CHECKING:
    from langchain_core.callbacks import Callbacks

    from ragas.embeddings import BaseRagasEmbeddings
    from ragas.llms import BaseRagasLLM


EvaluationMode = Enum("EvaluationMode", "qac qa qc gc ga qga qcg")


@dataclass
class Metric(ABC):
    batch_size: int

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def evaluation_mode(self) -> EvaluationMode:
        ...

    @abstractmethod
    def init(self, run_config: RunConfig):
        """
        This method will lazy initialize the model.
        """
        ...

    def adapt(self, language: str, cache_dir: t.Optional[str] = None) -> None:
        """
        Adapt the metric to a different language.
        """
        raise NotImplementedError(
            "adapt() is not implemented for {} metric".format(self.name)
        )

    def save(self, cache_dir: t.Optional[str] = None) -> None:
        """
        Save the metric to a path.
        """
        raise NotImplementedError(
            "adapt() is not implemented for {} metric".format(self.name)
        )

    def score(self: t.Self, row: t.Dict, callbacks: Callbacks = []) -> float:
        rm, group_cm = new_group(
            self.name, inputs=row, callbacks=callbacks, is_async=False
        )
        try:
            score = asyncio.run(
                self._ascore(row=row, callbacks=group_cm, is_async=False)
            )
        except Exception as e:
            if not group_cm.ended:
                rm.on_chain_error(e)
            raise e
        else:
            if not group_cm.ended:
                rm.on_chain_end({"output": score})
        return score

    async def ascore(
        self: t.Self, row: t.Dict, callbacks: Callbacks = [], is_async: bool = True
    ) -> float:
        rm, group_cm = new_group(
            self.name, inputs=row, callbacks=callbacks, is_async=True
        )
        try:
            score = await self._ascore(row=row, callbacks=group_cm, is_async=is_async)
        except Exception as e:
            if not group_cm.ended:
                rm.on_chain_error(e)
            raise e
        else:
            if not group_cm.ended:
                rm.on_chain_end({"output": score})
        return score

    @abstractmethod
    async def _ascore(self, row: t.Dict, callbacks: Callbacks, is_async: bool) -> float:
        ...


@dataclass
class MetricWithLLM(Metric):
    llm: t.Optional[BaseRagasLLM] = None

    def init(self, run_config: RunConfig):
        """
        Init any models in the metric, this is invoked before evaluate()
        to load all the models
        Also check if the api key is valid for OpenAI and AzureOpenAI
        """
        if self.llm is None:
            raise ValueError(
                f"Metric '{self.name}' has no valid LLM provided (self.llm is None). Please initantiate a the metric with an LLM to run."  # noqa
            )
        self.llm.set_run_config(run_config)


@dataclass
class MetricWithEmbeddings(Metric):
    embeddings: t.Optional[BaseRagasEmbeddings] = None

    def init(self, run_config: RunConfig):
        """
        Init any models in the metric, this is invoked before evaluate()
        to load all the models
        Also check if the api key is valid for OpenAI and AzureOpenAI
        """
        if self.embeddings is None:
            raise ValueError(
                f"Metric '{self.name}' has no valid embeddings provided (self.embeddings is None). Please initantiate a the metric with an embeddings to run."  # noqa
            )
        self.embeddings.set_run_config(run_config)
