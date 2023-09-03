from typing import Iterable, Optional, Union

from embedchain.config import BaseLlmConfig
from embedchain.llm.base_llm import BaseLlm


class GPT4ALLLlm(BaseLlm):
    def __init__(self, config: Optional[BaseLlmConfig] = None):
        super().__init__(config=config)
        self.instance = GPT4ALLLlm._get_instance(config.model)

    def get_llm_model_answer(self, prompt, config: BaseLlmConfig):
        return self._get_gpt4all_answer(prompt=prompt, config=config)

    @staticmethod
    def _get_instance(model):
        try:
            from gpt4all import GPT4All
        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "The GPT4All python package is not installed. Please install it with `pip install embedchain[opensource]`"  # noqa E501
            ) from None

        return GPT4All(model)

    def _get_gpt4all_answer(self, prompt: str, config: BaseLlmConfig) -> Union[str, Iterable]:
        if config.model and config.model != self.config.model:
            raise RuntimeError(
                "OpenSourceApp does not support switching models at runtime. Please create a new app instance."
            )

        if config.system_prompt:
            raise ValueError("OpenSourceApp does not support `system_prompt`")

        response = self.instance.generate(
            prompt=prompt,
            streaming=config.stream,
            top_p=config.top_p,
            max_tokens=config.max_tokens,
            temp=config.temperature,
        )
        return response
