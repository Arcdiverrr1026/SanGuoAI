from openai import OpenAI
from typing import Optional, List, Mapping, Any, Sequence, Dict
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from llama_index.core.constants import DEFAULT_CONTEXT_WINDOW, DEFAULT_NUM_OUTPUTS
from llama_index.core.llms import (
    CustomLLM,
    CompletionResponse,
    CompletionResponseGen,
    LLMMetadata,
    ChatMessage,
    ChatResponse,
    ChatResponseGen,
    MessageRole
)
from llama_index.core.llms.callbacks import llm_completion_callback, llm_chat_callback
from llama_index.core.embeddings import BaseEmbedding

def to_message_dicts(messages: Sequence[ChatMessage]) -> List[Dict[str, Any]]:
    return [
        {"role": message.role.value, "content": message.content}
        for message in messages
    ]

def get_additional_kwargs(response) -> Dict[str, Any]:
    usage = getattr(response, 'usage', None)
    if usage:
        return {
            "token_counts": getattr(usage, 'total_tokens', 0),
            "prompt_tokens": getattr(usage, 'prompt_tokens', 0),
            "completion_tokens": getattr(usage, 'completion_tokens', 0),
        }
    return {}

class CustomLLM(CustomLLM):
    num_output: int = DEFAULT_NUM_OUTPUTS
    context_window: int = Field(default=DEFAULT_CONTEXT_WINDOW, description="The maximum number of context tokens for the model.", gt=0)
    model: str = Field(default=None, description="The LLM model name")
    api_key: str = Field(default=None, description="The LLM API key.")
    base_url: str = Field(default=None, description="The LLM Base Url")
    top_p: float = Field(default=0.7, description="Top P parameter")
    temperature: float = Field(default=0.7, description="Temperature parameter")
    reuse_client: bool = Field(default=True, description="Reuse the client between requests.")

    _client: Optional[OpenAI] = PrivateAttr()

    def __init__(
        self,
        model: str = None,
        reuse_client: bool = True,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        top_p: float = 0.7,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            reuse_client=reuse_client,
            top_p=top_p,
            temperature=temperature,
            **kwargs,
        )
        self._client = None
        self.top_p = top_p
        self.temperature = temperature

    def _get_client(self) -> OpenAI:
        if not self.reuse_client:
            return OpenAI(api_key=self.api_key, base_url=self.base_url)
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    @classmethod
    def class_name(cls) -> str:
        return "custom_openai_llm"

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=self.context_window,
            num_output=self.num_output,
            model_name=self.model,
        )

    def _chat_call(self, messages: List[Dict[str, Any]], stream: bool = False) -> Any:
        # Standardize parameters: exclude None values
        params = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if self.temperature is not None:
            params["temperature"] = self.temperature
        if self.top_p is not None:
            params["top_p"] = self.top_p
            
        return self._get_client().chat.completions.create(**params)

    @llm_chat_callback()
    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        message_dicts = to_message_dicts(messages)
        response = self._chat_call(message_dicts, stream=False)
        
        role_str = getattr(response.choices[0].message, 'role', 'assistant')
        if role_str == 'user':
            role = MessageRole.USER
        elif role_str == 'system':
            role = MessageRole.SYSTEM
        else:
            role = MessageRole.ASSISTANT

        return ChatResponse(
            message=ChatMessage(
                content=response.choices[0].message.content,
                role=role,
                additional_kwargs={}
            ),
            raw=response,
            additional_kwargs=get_additional_kwargs(response),
        )

    @llm_chat_callback()
    def stream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponseGen:
        message_dicts = to_message_dicts(messages)
        response = self._chat_call(message_dicts, stream=True)
        
        response_txt = ""
        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            token = getattr(delta, 'content', None) or ""
            response_txt += token
            
            role_str = getattr(delta, 'role', 'assistant') or 'assistant'
            if role_str == 'user':
                role = MessageRole.USER
            elif role_str == 'system':
                role = MessageRole.SYSTEM
            else:
                role = MessageRole.ASSISTANT
                
            yield ChatResponse(
                message=ChatMessage(content=response_txt, role=role, additional_kwargs={}),
                delta=token,
                raw=chunk,
            )

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        messages = [{"role": "user", "content": prompt}]
        response = self._chat_call(messages, stream=False)
        return CompletionResponse(
            text=str(response.choices[0].message.content),
            raw=response,
            additional_kwargs=get_additional_kwargs(response),
        )

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        messages = [{"role": "user", "content": prompt}]
        response = self._chat_call(messages, stream=True)
        response_txt = ""
        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            token = getattr(delta, 'content', None) or ""
            response_txt += token
            yield CompletionResponse(text=response_txt, delta=token, raw=chunk)


class CustomEmbeddings(BaseEmbedding):
    model: str = Field(default='embedding-3', description="The embedding model to use.")
    api_key: str = Field(default=None, description="The embedding API key.")
    base_url: str = Field(default=None, description="The embedding Base Url")
    reuse_client: bool = Field(default=True, description="Reuse the client between requests.")

    _client: Optional[OpenAI] = PrivateAttr()

    def __init__(
        self,
        model: str = 'embedding-3',
        reuse_client: bool = True,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            reuse_client=reuse_client,
            **kwargs,
        )
        self._client = None

    def _get_client(self) -> OpenAI:
        if not self.reuse_client:
            return OpenAI(api_key=self.api_key, base_url=self.base_url)
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    @classmethod
    def class_name(cls) -> str:
        return "custom_openai_embedding"

    def get_general_text_embedding(self, prompt: str) -> List[float]:
        response = self._get_client().embeddings.create(
            model=self.model,
            input=prompt,
        )
        return response.data[0].embedding

    def _get_query_embedding(self, query: str) -> List[float]:
        return self.get_general_text_embedding(query)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self.get_general_text_embedding(query)

    def _get_text_embedding(self, text: str) -> List[float]:
        return self.get_general_text_embedding(text)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self.get_general_text_embedding(text)

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        embeddings_list: List[List[float]] = []
        for text in texts:
            embeddings = self.get_general_text_embedding(text)
            embeddings_list.append(embeddings)
        return embeddings_list

    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self._get_text_embeddings(texts)
