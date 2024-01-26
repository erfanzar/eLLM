from threading import Thread

from ..serve import LLMServe, CHAT_MODE, RAGLLMServe
from typing import Literal, List
from transformers import GenerationConfig, PreTrainedModel, TextIteratorStreamer, AutoTokenizer, PreTrainedTokenizerBase


class PyTorchLLMServe(LLMServe):
    def __init__(
            self,
            model: PreTrainedModel,
            tokenizer: AutoTokenizer | PreTrainedTokenizerBase,
            **kwargs
    ):
        self.model = model
        self.tokenizer = tokenizer
        super().__init__(**kwargs)

    def sample(
            self,
            prompt: str,
            history: List[List[str]],
            system_prompt: str,
            mode: CHAT_MODE = CHAT_MODE[-1],
            max_length: int = 8192,
            max_new_tokens: int = 4096,
            temperature: float = 0.8,
            top_p: float = 0.9,
            top_k: int = 50
    ):
        """
        The sample function is the main entry point for a user to interact with the model.
        It takes in a prompt, which can be any string, and returns an iterator over
        strings that are generated by the model.
        The sample function also takes in some optional arguments:

        :param self: Refer to the current object
        :param prompt: str: Pass in the text that you want to generate a response for
        :param history: List[List[str]]: Keep track of the conversation history
        :param system_prompt: str: the model system prompt.
        :param mode: str: represent the mode that model inference be used in (e.g. chat or instruction)
        :param max_length: int: Maximum Length for model
        :param max_new_tokens: int: Limit the number of tokens in a response
        :param temperature: float: Control the randomness of the generated text
        :param top_p: float: Control the probability of sampling from the top k tokens
        :param top_k: int: Control the number of candidates that are considered for each token
        :return: A generator that yields the next token in the sequence
        """
        assert mode in CHAT_MODE, "Requested Mode is not in Available Modes"
        if mode == "Instruction":
            history = []
        string = self.interactor.format_message(
            prompt=prompt,
            history=history,
            system_message=None if system_prompt == "" else system_prompt,
            prefix=self.interactor.get_prefix_prompt() if self.use_prefix_for_interactor else None,
        )
        history.append([prompt, ""])
        total_response = ""
        streamer = TextIteratorStreamer(
            skip_prompt=True,
            tokenizer=self.tokenizer,
        )

        inputs = dict(
            **self.tokenizer(string, return_tensors="pt").to(self.model.device),
            generation_config=GenerationConfig(
                top_k=top_k,
                top_p=top_p,
                max_length=max_length,
                max_new_tokens=max_new_tokens,
                pad_token_id=self.sample_config.pad_token_id,
                eos_token_id=self.sample_config.eos_token_id,
                do_sample=self.sample_config.do_sample,
            ),
            streamer=streamer,
            max_length=max_length
        )
        thread = Thread(target=self.model.generate, kwargs=inputs)
        thread.start()
        for char in streamer:
            total_response += char
            history[-1][-1] = total_response
            yield "", history
        thread.join()


class PyTorchRAGLLMServe(RAGLLMServe):
    def __init__(
            self,
            model: PreTrainedModel,
            tokenizer: AutoTokenizer | PreTrainedTokenizerBase,
            **kwargs
    ):
        self.model = model
        self.tokenizer = tokenizer
        super().__init__(**kwargs)

    def sample(
            self,
            prompt: str,
            history: List[List[str]],
            system_prompt: str,
            mode: CHAT_MODE = CHAT_MODE[-1],
            max_length: int = 8192,
            max_new_tokens: int = 4096,
            temperature: float = 0.8,
            top_p: float = 0.9,
            top_k: int = 50
    ):
        """
        The sample function is the main entry point for a user to interact with the model.
        It takes in a prompt, which can be any string, and returns an iterator over
        strings that are generated by the model.
        The sample function also takes in some optional arguments:

        :param self: Refer to the current object
        :param prompt: str: Pass in the text that you want to generate a response for
        :param history: List[List[str]]: Keep track of the conversation history
        :param system_prompt: str: the model system prompt.
        :param mode: str: represent the mode that model inference be used in (e.g. chat or instruction)
        :param max_length: int: Maximum Length for model
        :param max_new_tokens: int: Limit the number of tokens in a response
        :param temperature: float: Control the randomness of the generated text
        :param top_p: float: Control the probability of sampling from the top k tokens
        :param top_k: int: Control the number of candidates that are considered for each token
        :return: A generator that yields the next token in the sequence
        """

        assert mode in CHAT_MODE, "Requested Mode is not in Available Modes"
        if mode == "Instruction":
            history = []
        prompt = self.rag_search(
            query=prompt
        )
        string = self.interactor.format_message(
            prompt=prompt,
            history=history,
            system_message=None if system_prompt == "" else system_prompt,
            prefix=self.interactor.get_prefix_prompt() if self.use_prefix_for_interactor else None,
        )
        history.append([prompt, ""])
        total_response = ""
        streamer = TextIteratorStreamer(
            skip_prompt=True,
            tokenizer=self.tokenizer,
        )

        inputs = dict(
            **self.tokenizer(string, return_tensors="pt").to(self.model.device),
            generation_config=GenerationConfig(
                top_k=top_k,
                top_p=top_p,
                max_length=max_length,
                max_new_tokens=max_new_tokens,
                pad_token_id=self.sample_config.pad_token_id,
                eos_token_id=self.sample_config.eos_token_id,
                do_sample=self.sample_config.do_sample,
            ),
            streamer=streamer,
            max_length=max_length
        )
        thread = Thread(target=self.model.generate, kwargs=inputs)
        thread.start()
        for char in streamer:
            total_response += char
            history[-1][-1] = total_response
            yield "", history
        thread.join()
