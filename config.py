import yaml
import os
import threading

class ConfigManager:
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
    _config = {}
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config_file=CONFIG_FILE):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.load_config(config_file)
            return cls._instance

    def load_config(self, config_file=CONFIG_FILE):
        if not os.path.exists(config_file):
            # Fallback default values
            self._config = {
                "embedding": {
                    "api_base": "https://open.bigmodel.cn/api/paas/v4/",
                    "api_key": "79a00282369a40d2a074b7ea31184f81.DXLwpmyfguXugwYn",
                    "model": "embedding-3",
                    "provider": "zhipu"
                },
                "llm": {
                    "api_base": "https://open.bigmodel.cn/api/paas/v4/",
                    "api_key": "79a00282369a40d2a074b7ea31184f81.DXLwpmyfguXugwYn",
                    "max_tokens": 2048,
                    "model": "glm-4",
                    "provider": "zhipu",
                    "temperature": 0.7,
                    "top_p": 0.7
                },
                "rag": {
                    "chunk_overlap": 50,
                    "chunk_size": 500,
                    "similarity_top_k": 3,
                    "system_prompt": "你是一个三国知识库问答助手。根据下面的知识库内容回答问题：\n\n{context_str}\n\n问题：\n{query_str}\n\n如果知识库没有相关信息，请说明不知道。"
                },
                "system": {
                    "docs_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"),
                    "storage_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "vector_store")
                }
            }
            # Save the default fallback
            self.save_config()
        else:
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}

    def get_config(self, key, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def save_config(self):
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False, indent=2)

    def set_config(self, key, value):
        keys = key.split(".")
        d = self._config
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        
        # Coerce standard data types where necessary
        if keys[-1] in ['chunk_size', 'chunk_overlap', 'similarity_top_k', 'max_tokens']:
            try:
                value = int(value)
            except (ValueError, TypeError):
                pass
        elif keys[-1] in ['temperature', 'top_p']:
            try:
                value = float(value)
            except (ValueError, TypeError):
                pass
                
        d[keys[-1]] = value

# Global singleton instance
config_manager = ConfigManager()
