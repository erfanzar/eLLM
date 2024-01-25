import warnings
from typing import Literal, List, Optional
from sentence_transformers import SentenceTransformer
import faiss

from ..gradio.gradio_interface import LLMServe


def search(
        query: str,
        index: faiss.IndexFlatL2,
        embedding: SentenceTransformer,
        text_snippets: list[str],
        k: int,
):
    dists, ind = index.search(
        embedding.encode([query]),
        k=k
    )
    ind = ind[0].tolist()
    return [text_snippets[i] for i in ind]


class RAGLLMServe(LLMServe):
    index: Optional[faiss.IndexFlatL2] = None
    embedding: Optional[SentenceTransformer] = None
    text_snippets: Optional[list[str]] = None
    rag_top_k: Optional[int] = 3
    rag_qa_base_question: Optional[str] = None

    def add_rag(
            self,
            index: faiss.IndexFlatL2,
            embedding: SentenceTransformer,
            text_snippets: list[str],
            rag_top_k: int,
            rag_qa_base_question: Optional[str] = None
    ):
        self.index = index
        self.embedding = embedding
        self.text_snippets = text_snippets
        self.rag_top_k = rag_top_k
        self.rag_qa_base_question = rag_qa_base_question

    def sample(
            self,
            prompt: str,
            history: List[List[str]],
            system_prompt: str,
            mode: Literal["Chat", "Instruction"] = "Instruction",
            max_tokens: int = 4096,
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
        :param mode: str: represent the mode that model inference be used in (e.g chat or instruction)
        :param max_tokens: int: Limit the number of tokens in a response
        :param temperature: float: Control the randomness of the generated text
        :param top_p: float: Control the probability of sampling from the top k tokens
        :param top_k: int: Control the number of candidates that are considered for each token
        :return: A generator that yields the next token in the sequence
        """

        assert mode in ["Chat", "Instruction"], "Requested Mode is not in Available Modes"
        if mode == "Instruction":
            history = []
        if self.inference_session is not None:

            history.append([prompt, ""])
            index: faiss.IndexFlatL2 = self.index
            embedding: SentenceTransformer = self.embedding
            text_snippets: list[str] = self.text_snippets
            if index is not None and embedding is not None and embedding is not None:
                contexts = search(
                    query=prompt,
                    embedding=embedding,
                    text_snippets=text_snippets,
                    k=self.rag_top_k,
                    index=index
                )

                prompt = self.interactor.retrival_qa_template(
                    question=prompt,
                    contexts=contexts,
                    base_question=self.rag_qa_base_question
                )

                print(
                    prompt
                )
            else:
                warnings.warn("You are not Using rag correctly you have to add rag via `add_rag` function")
            string = self.interactor.format_message(
                prompt=prompt,
                history=history,
                system_message=None if system_prompt == "" else system_prompt,
                prefix=self.interactor.get_prefix_prompt() if self.use_prefix_for_interactor else None,
            )

            total_response = ""
            for response in self.inference_session.generate(
                    prompt=string,
                    top_k=top_k,
                    top_p=top_p,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
            ):
                total_response += response.predictions.text
                history[-1][-1] = total_response
                yield '', history
        else:
            return [
                [prompt, "Model is not loaded !"]
            ]