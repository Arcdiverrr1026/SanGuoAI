import os
import re
import shutil
from llama_index.core import (
    StorageContext,
    load_index_from_storage,
    SimpleDirectoryReader,
    VectorStoreIndex,
    PromptTemplate
)
from llama_index.core.node_parser import SentenceSplitter

from final.config import config_manager
from final.core.models import CustomLLM, CustomEmbeddings

def get_safe_dir_name(model_name: str) -> str:
    """Sanitize the model name to be a safe directory name."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', model_name)

def get_vector_store_dir() -> str:
    """Get the persistent directory for the current configuration."""
    base_storage_path = config_manager.get_config("system.storage_path", "/Users/lucent/AIGC_project/final/vector_store")
    embed_model_name = config_manager.get_config("embedding.model", "embedding-3")
    chunk_size = config_manager.get_config("rag.chunk_size", 500)
    chunk_overlap = config_manager.get_config("rag.chunk_overlap", 50)
    
    safe_model_name = get_safe_dir_name(embed_model_name)
    dir_name = f"{safe_model_name}_cs{chunk_size}_co{chunk_overlap}"
    return os.path.join(base_storage_path, dir_name)

def get_embedding_model() -> CustomEmbeddings:
    """Instantiate the CustomEmbeddings based on current config."""
    provider = config_manager.get_config("embedding.provider", "zhipu")
    model_name = config_manager.get_config("embedding.model", "embedding-3")
    api_key = config_manager.get_config("embedding.api_key", "")
    api_base = config_manager.get_config("embedding.api_base", "")
    
    return CustomEmbeddings(
        model=model_name,
        api_key=api_key,
        base_url=api_base if api_base else None
    )

def get_llm_model() -> CustomLLM:
    """Instantiate the CustomLLM based on current config."""
    model_name = config_manager.get_config("llm.model", "glm-4")
    api_key = config_manager.get_config("llm.api_key", "")
    api_base = config_manager.get_config("llm.api_base", "")
    temperature = config_manager.get_config("llm.temperature", 0.7)
    top_p = config_manager.get_config("llm.top_p", 0.7)
    max_tokens = config_manager.get_config("llm.max_tokens", 2048)
    
    return CustomLLM(
        model=model_name,
        api_key=api_key,
        base_url=api_base if api_base else None,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens
    )

def get_query_engine(force_rebuild: bool = False):
    """
    Get or create the Q&A query engine.
    If force_rebuild is True, delete the current configuration's vector store and rebuild.
    """
    vector_dir = get_vector_store_dir()
    docs_path = config_manager.get_config("system.docs_path", "/Users/lucent/AIGC_project/final/data")
    
    # 1. Instantiate the embedding model
    embed_model = get_embedding_model()
    
    # 2. Check if vector storage exists and force_rebuild is False
    if force_rebuild and os.path.exists(vector_dir):
        shutil.rmtree(vector_dir)
        print(f"Force rebuild: deleted existing vector store at {vector_dir}")
        
    os.makedirs(vector_dir, exist_ok=True)
    
    # Check if vector directory is empty
    is_empty = not os.listdir(vector_dir)
    
    if is_empty:
        print(f"Vector store at {vector_dir} is empty. Building index...")
        if not os.path.exists(docs_path) or not os.listdir(docs_path):
            raise FileNotFoundError(f"Knowledge base documents directory '{docs_path}' is empty or does not exist.")
            
        # Load documents
        exts = ['.pdf', '.docx', '.doc', '.txt']
        reader = SimpleDirectoryReader(input_dir=docs_path, required_exts=exts)
        documents = reader.load_data()
        
        # Build node splitter
        chunk_size = config_manager.get_config("rag.chunk_size", 500)
        chunk_overlap = config_manager.get_config("rag.chunk_overlap", 50)
        
        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator='\n'
        )
        
        nodes = splitter.get_nodes_from_documents(documents)
        
        # Build vector store index
        index = VectorStoreIndex(nodes, embed_model=embed_model)
        
        # Persist
        index.storage_context.persist(persist_dir=vector_dir)
        print(f"Index built and persisted to {vector_dir}")
    else:
        print(f"Loading index from storage: {vector_dir}")
        # Load from storage
        storage_context = StorageContext.from_defaults(persist_dir=vector_dir)
        index = load_index_from_storage(storage_context, embed_model=embed_model)
        
    # 3. Instantiate the LLM
    llm = get_llm_model()
    
    # 4. Formulate the prompt template
    system_prompt = config_manager.get_config(
        "rag.system_prompt",
        "你是一个三国知识库问答助手。根据下面的知识库内容回答问题：\n\n{context_str}\n\n问题：\n{query_str}\n\n如果知识库没有相关信息，请说明不知道。"
    )
    prompt_template = PromptTemplate(system_prompt)
    
    # 5. Build and return the query engine
    similarity_top_k = config_manager.get_config("rag.similarity_top_k", 3)
    
    query_engine = index.as_query_engine(
        llm=llm,
        similarity_top_k=similarity_top_k,
        text_qa_template=prompt_template
    )
    
    return query_engine
