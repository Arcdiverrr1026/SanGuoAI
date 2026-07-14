import os
import uvicorn
import time
import json
import uuid
import numpy as np
from typing import Any, List
from fastapi import FastAPI, HTTPException, Body, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from llama_index.core import StorageContext

from final.config import config_manager
from final.core.engine import get_query_engine, get_vector_store_dir, get_embedding_model

app = FastAPI(title="三国知识库问答助手", description="基于 LlamaIndex 的三国演义问答系统")

# Allow CORS for development ease
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic schemas for request validation
class QueryRequest(BaseModel):
    question: str = Field(..., description="用户输入的提问问题")

class ConfigUpdateRequest(BaseModel):
    settings: dict = Field(..., description="Key-value pairs to update in config")

class FavoriteRequest(BaseModel):
    question: str = Field(..., description="要收藏的问题")
    answer: str = Field(..., description="要收藏的回答")

# Favorites storage constants and helpers
FAVORITES_FILE = "/Users/lucent/AIGC_project/final/data/favorites.json"

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    dot_val = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot_val / (norm_a * norm_b))

def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        try:
            with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_favorites(favs):
    os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        json.dump(favs, f, ensure_ascii=False, indent=2)

@app.get("/api/config")
def get_config():
    """Retrieve the current system configuration."""
    return {
        "llm": {
            "provider": config_manager.get_config("llm.provider", "zhipu"),
            "model": config_manager.get_config("llm.model", "glm-4"),
            "api_key": config_manager.get_config("llm.api_key", ""),
            "api_base": config_manager.get_config("llm.api_base", ""),
            "temperature": config_manager.get_config("llm.temperature", 0.7),
            "top_p": config_manager.get_config("llm.top_p", 0.7),
            "max_tokens": config_manager.get_config("llm.max_tokens", 2048),
        },
        "embedding": {
            "provider": config_manager.get_config("embedding.provider", "zhipu"),
            "model": config_manager.get_config("embedding.model", "embedding-3"),
            "api_key": config_manager.get_config("embedding.api_key", ""),
            "api_base": config_manager.get_config("embedding.api_base", ""),
        },
        "rag": {
            "chunk_size": config_manager.get_config("rag.chunk_size", 500),
            "chunk_overlap": config_manager.get_config("rag.chunk_overlap", 50),
            "similarity_top_k": config_manager.get_config("rag.similarity_top_k", 3),
            "system_prompt": config_manager.get_config("rag.system_prompt", ""),
        }
    }

@app.post("/api/config")
def update_config(request: ConfigUpdateRequest):
    """Update settings dynamically and save to yaml."""
    try:
        for key, val in request.settings.items():
            config_manager.set_config(key, val)
        config_manager.save_config()
        return {"status": "success", "message": "Settings updated and saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

@app.get("/api/index/status")
def get_index_status():
    """Check if the vector store index is built for the current config."""
    vector_dir = get_vector_store_dir()
    exists = os.path.exists(vector_dir) and len(os.listdir(vector_dir)) > 0
    return {
        "exists": exists,
        "path": vector_dir,
    }

@app.post("/api/index/rebuild")
def rebuild_index():
    """Force rebuild the vector index for the current config."""
    try:
        get_query_engine(force_rebuild=True)
        return {"status": "success", "message": "Vector index rebuilt successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebuild index: {str(e)}")

@app.get("/api/kb/status")
def get_kb_status():
    """Retrieve detailed status of the knowledge base files and vector stores."""
    docs_path = config_manager.get_config("system.docs_path", "/Users/lucent/AIGC_project/final/data")
    vector_dir = get_vector_store_dir()
    
    # 1. Get knowledge base files list
    files = []
    if os.path.exists(docs_path):
        for f in os.listdir(docs_path):
            fpath = os.path.join(docs_path, f)
            if os.path.isfile(fpath) and not f.startswith('.'):
                stat = os.stat(fpath)
                files.append({
                    "name": f,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "modified": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
                })
                
    # 2. Get vector store details
    vector_count = 0
    index_exists = False
    if os.path.exists(vector_dir) and os.listdir(vector_dir):
        index_exists = True
        try:
            storage_context = StorageContext.from_defaults(persist_dir=vector_dir)
            vector_count = len(storage_context.docstore.docs)
        except Exception as e:
            print(f"Error counting vectors: {e}")
            
    return {
        "docs_path": docs_path,
        "files": files,
        "active_index": {
            "exists": index_exists,
            "path": vector_dir,
            "vector_count": vector_count
        }
    }

# Favorites REST APIs
@app.get("/api/favorites")
def get_favorites():
    """Retrieve the list of bookmarked Q&As."""
    favs = load_favorites()
    result = []
    for f in favs:
        result.append({
            "id": f["id"],
            "question": f["question"],
            "answer": f["answer"],
            "created_at": f.get("created_at", "")
        })
    return result

@app.post("/api/favorites")
def add_favorite(request: FavoriteRequest):
    """Add a new Q&A pair to favorites and pre-compute embedding for direct retrieval."""
    try:
        favs = load_favorites()
        
        # Calculate embedding of the question for quick semantic search
        embed_model = get_embedding_model()
        question_embedding = embed_model.get_general_text_embedding(request.question)
        
        entry = {
            "id": str(uuid.uuid4()),
            "question": request.question,
            "answer": request.answer,
            "embedding": question_embedding,
            "created_at": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        favs.append(entry)
        save_favorites(favs)
        return {"status": "success", "id": entry["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add favorite: {str(e)}")

@app.delete("/api/favorites/{fav_id}")
def delete_favorite(fav_id: str):
    """Delete a favorite Q&A pair by ID."""
    favs = load_favorites()
    new_favs = [f for f in favs if f["id"] != fav_id]
    if len(new_favs) == len(favs):
        raise HTTPException(status_code=404, detail="Favorite Q&A not found.")
    save_favorites(new_favs)
    return {"status": "success"}

# KB Document Upload API
@app.post("/api/kb/upload")
def upload_file(file: UploadFile = File(...)):
    """Upload a new .txt document to the knowledge base and trigger a rebuild of the index."""
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Only .txt files are allowed.")
        
    docs_path = config_manager.get_config("system.docs_path", "/Users/lucent/AIGC_project/final/data")
    os.makedirs(docs_path, exist_ok=True)
    
    target_path = os.path.join(docs_path, file.filename)
    try:
        # Read uploaded content and save to file
        content = file.file.read()
        with open(target_path, "wb") as f:
            f.write(content)
            
        # Force rebuild index to ingest the new document
        get_query_engine(force_rebuild=True)
        return {"status": "success", "filename": file.filename}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save and index document: {str(e)}")

# Query / Chat API
@app.post("/api/chat")
def chat(request: QueryRequest):
    """Query the RAG engine, checking the favorites library first for semantic matches."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    
    # 1. Semantic search in Favorites library first
    favs = load_favorites()
    if favs:
        try:
            embed_model = get_embedding_model()
            curr_embed = embed_model.get_general_text_embedding(request.question)
            
            best_score = -1.0
            best_fav = None
            
            for f in favs:
                if "embedding" in f:
                    score = cosine_similarity(curr_embed, f["embedding"])
                    if score > best_score:
                        best_score = score
                        best_fav = f
            
            # If the current question matches a bookmarked question with > 0.82 similarity
            if best_score > 0.82 and best_fav:
                print(f"Direct Match: retrieved from favorites (Score: {best_score})")
                return {
                    "answer": best_fav["answer"],
                    "from_favorites": True,
                    "favorites_score": best_score,
                    "sources": [
                        {
                            "text": f"[收藏原题]: {best_fav['question']}\n\n[收藏解答]:\n{best_fav['answer']}",
                            "score": best_score,
                            "file_name": "favorites.json"
                        }
                    ]
                }
        except Exception as e:
            print(f"Error checking favorites cache: {e}")
            
    # 2. Fallback to LlamaIndex query engine
    try:
        engine = get_query_engine(force_rebuild=False)
        response = engine.query(request.question)
        
        # Format source nodes
        sources = []
        if hasattr(response, 'source_nodes'):
            for node_post in response.source_nodes:
                node = node_post.node
                score = getattr(node_post, 'score', None)
                file_name = node.metadata.get("file_name", "sanguo.txt")
                sources.append({
                    "text": node.get_content(),
                    "score": float(score) if score is not None else None,
                    "file_name": file_name
                })
                
        return {
            "answer": response.response,
            "sources": sources
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"RAG query execution failed: {str(e)}")

# Mount static files at the end to serve index.html at root "/"
static_dir = "/Users/lucent/AIGC_project/final/static"
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    port = int(config_manager.get_config("system.server_port", 8088))
    print(f"Starting server on port {port}...")
    uvicorn.run("final.app:app", host="0.0.0.0", port=port, reload=True)
