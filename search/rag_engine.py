import os
import asyncio
import pandas as pd
import tiktoken
from typing import Dict, Any, List, Optional

from graphrag.config.enums import ModelType
from graphrag.config.models.language_model_config import LanguageModelConfig
from graphrag.language_model.manager import ModelManager
from graphrag.query.indexer_adapters import (
    read_indexer_communities,
    read_indexer_entities,
    read_indexer_reports,
    read_indexer_relationships,
    read_indexer_text_units,
    read_indexer_covariates,
)
from graphrag.query.structured_search.global_search.community_context import (
    GlobalCommunityContext,
)
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.structured_search.local_search.mixed_context import (
    LocalSearchMixedContext,
)
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.vector_stores.lancedb import LanceDBVectorStore
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from dotenv import load_dotenv

load_dotenv()

class RAGEngine:
    """GraphRAG引擎，将检索和LLM调用分离"""
    
    def __init__(self):
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.embedding_key = os.getenv("Embedding_key")
        
        # 初始化配置
        self._init_configs()
        self._init_data()
        self._init_engines()
        
    def _init_configs(self):
        """初始化LLM配置"""
        self.chat_config = LanguageModelConfig(
            type=ModelType.AzureOpenAIChat,
            api_base="https://tcamp.openai.azure.com/",
            api_version="2025-01-01-preview",
            auth_type="api_key",
            api_key=self.api_key,
            model="gpt-4o",
            deployment_name="gpt-4o",
            model_supports_json=True,
            concurrent_requests=25,
            async_mode="threaded",
            retry_strategy="native",
            max_retries=10,
            tokens_per_minute=120000,
            requests_per_minute=100,
            encoding_model="cl100k_base",
        )
        
        self.embedding_config = LanguageModelConfig(
            api_key=self.embedding_key,
            type=ModelType.OpenAIEmbedding,
            api_base="https://open.bigmodel.cn/api/paas/v4",
            model="embedding-3",
            deployment_name="embedding-3",
            auth_type="api_key",
            max_retries=20,
            tokens_per_minute=120000000,
            requests_per_minute=100,
            encoding_model="cl100k_base",
        )
        
        self.token_encoder = tiktoken.get_encoding("cl100k_base")
        
    def _init_data(self):
        """初始化数据"""
        INPUT_DIR = "./rag/output"
        COMMUNITY_LEVEL = 2
        
        # 读取数据文件
        self.community_df = pd.read_parquet(f"{INPUT_DIR}/communities.parquet")
        self.entity_df = pd.read_parquet(f"{INPUT_DIR}/entities.parquet")
        self.report_df = pd.read_parquet(f"{INPUT_DIR}/community_reports.parquet")
        self.relationship_df = pd.read_parquet(f"{INPUT_DIR}/relationships.parquet")
        self.text_unit_df = pd.read_parquet(f"{INPUT_DIR}/text_units.parquet")
        
        # 初始化GraphRAG数据结构
        self.communities = read_indexer_communities(self.community_df, self.report_df)
        self.reports = read_indexer_reports(self.report_df, self.community_df, COMMUNITY_LEVEL)
        self.entities = read_indexer_entities(self.entity_df, self.community_df, COMMUNITY_LEVEL)
        self.relationships = read_indexer_relationships(self.relationship_df)
        self.text_units = read_indexer_text_units(self.text_unit_df)
        
        # 初始化向量存储
        self.description_embedding_store = LanceDBVectorStore(
            collection_name="default-entity-description",
        )
        self.description_embedding_store.connect(db_uri=f"{INPUT_DIR}/lancedb")
        
    def _init_engines(self):
        """初始化搜索引擎"""
        # 初始化模型管理器
        self.model_manager = ModelManager()
        self.chat_model = self.model_manager.get_or_create_chat_model(
            name="rag_engine",
            model_type=ModelType.AzureOpenAIChat,
            config=self.chat_config,
        )
        self.text_embedder = self.model_manager.get_or_create_embedding_model(
            name="rag_engine_embedding",
            model_type=ModelType.OpenAIEmbedding,
            config=self.embedding_config,
        )
        
        # 初始化上下文构建器
        self._init_global_context()
        self._init_local_context()
        
    def _init_global_context(self):
        """初始化全局搜索上下文"""
        self.global_context_builder = GlobalCommunityContext(
            community_reports=self.reports,
            communities=self.communities,
            entities=self.entities,
            token_encoder=self.token_encoder,
        )
        
        # 大幅减少max_tokens以避免上下文超限
        self.global_context_params = {
            "use_community_summary": False,
            "shuffle_data": True,
            "include_community_rank": True,
            "min_community_rank": 0,
            "community_rank_name": "rank",
            "include_community_weight": True,
            "community_weight_name": "occurrence weight",
            "normalize_community_weight": True,
            "max_tokens": 10000,  # 从4000增加到10000
            "context_name": "Reports",
        }
        
        self.map_llm_params = {
            "max_tokens": 1200,  # 从800增加到1200
            "temperature": 0.0,
            # 移除 "response_format": {"type": "json_object"},
        }
        
        self.reduce_llm_params = {
            "max_tokens": 1500,  # 从2500减少到1500
            "temperature": 0.0,
        }
        
        self.global_search_engine = GlobalSearch(
            model=self.chat_model,
            context_builder=self.global_context_builder,
            token_encoder=self.token_encoder,
            max_data_tokens=10000,  # 从4000增加到10000
            map_llm_params=self.map_llm_params,
            reduce_llm_params=self.reduce_llm_params,
            allow_general_knowledge=False,
            json_mode=False,  # 关闭JSON模式，避免JSON解析错误
            context_builder_params=self.global_context_params,
            concurrent_coroutines=128,
            response_type="multiple paragraphs",
        )
        
    def _init_local_context(self):
        """初始化局部搜索上下文"""
        self.local_context_builder = LocalSearchMixedContext(
            community_reports=self.reports,
            text_units=self.text_units,
            entities=self.entities,
            relationships=self.relationships,
            covariates=None,
            entity_text_embeddings=self.description_embedding_store,
            embedding_vectorstore_key=EntityVectorStoreKey.ID,
            text_embedder=self.text_embedder,
            token_encoder=self.token_encoder,
        )

        # 大幅减少max_tokens以避免上下文超限
        self.local_context_params = {
            "text_unit_prop": 0.5,
            "community_prop": 0.1,
            "conversation_history_max_turns": 3,  # 从5减少到3
            "conversation_history_user_turns_only": True,
            "top_k_mapped_entities": 5,  # 从10减少到5
            "top_k_relationships": 5,  # 从10减少到5
            "include_entity_rank": True,
            "include_relationship_weight": True,
            "include_community_rank": False,
            "return_candidate_context": False,
            "embedding_vectorstore_key": EntityVectorStoreKey.ID,
            "max_tokens": 10000,  # 从4000增加到10000
        }
        
        self.local_model_params = {
            "max_tokens": 1500,  # 从2500减少到1500
            "temperature": 0.0,
        }
        
        self.local_search_engine = LocalSearch(
            model=self.chat_model,
            context_builder=self.local_context_builder,
            token_encoder=self.token_encoder,
            model_params=self.local_model_params,
            context_builder_params=self.local_context_params,
            response_type="multiple paragraphs",
        )
    
    def _truncate_text(self, text: str, max_tokens: int = 2000) -> str:
        """截断文本以避免token超限"""
        if not text:
            return text
        
        tokens = self.token_encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        # 截断到指定token数
        truncated_tokens = tokens[:max_tokens]
        return self.token_encoder.decode(truncated_tokens)
    
    async def global_search_retrieve(self, query: str) -> Dict[str, Any]:
        """全局搜索 - 仅检索阶段，展示RAG召回内容"""
        try:
            print(f"🔍 [RAG检索] 正在检索全局信息: {query}")
            
            # 获取检索结果（通过上下文构建器）
            # build_context 是异步方法，需要 await
            context = await self.global_context_builder.build_context(
                query=query,
                **self.global_context_params
            )
            
            # 截断上下文以避免token超限
            # 更安全地处理context对象
            if hasattr(context, 'context_text'):
                context_text = context.context_text
            elif hasattr(context, 'text'):
                context_text = context.text
            elif hasattr(context, 'content'):
                context_text = context.content
            elif hasattr(context, 'response'):
                context_text = context.response
            else:
                # 如果都没有，尝试转换为字符串
                context_text = str(context)
            
            truncated_context = self._truncate_text(context_text, max_tokens=8000)  # 从3000增加到8000
            
            print(f" [RAG检索] 全局检索完成，获得 {len(truncated_context)} 字符的上下文")
            print(f"🤖 [Agent调用] 正在使用Agent调用LLM生成回答...")
            
            return {
                "method": "global_retrieve",
                "query": query,
                "retrieved_context": {
                    "context_text": truncated_context,
                    "context_length": len(truncated_context),
                    "context_summary": "GraphRAG全局搜索检索到的社区报告和实体信息（已截断）"
                },
                "success": True
            }
        except Exception as e:
            print(f"[RAG检索] 全局检索失败: {e}")
            return {
                "method": "global_retrieve", 
                "query": query,
                "error": str(e),
                "success": False
            }
    
    async def global_search_generate(self, query: str, retrieved_context: Any) -> Dict[str, Any]:
        """全局搜索 - 仅生成阶段，使用预检索的上下文"""
        try:
            print(f" [LLM生成] 正在调用大模型生成全局搜索回答: {query}")
            
            # 不直接调用GraphRAG的search方法，而是返回检索到的上下文
            # 让agent通过独立LLM工具来处理生成
            context_text = retrieved_context.get('context_text', '') if isinstance(retrieved_context, dict) else str(retrieved_context)
            
            print(f"[LLM生成] 准备上下文，长度: {len(context_text)} 字符")
            
            return {
                "method": "global_generate",
                "query": query,
                "retrieved_context": retrieved_context,
                "context_ready": True,
                "success": True,
                "note": "请使用llm_generate_tool来处理生成"
            }
        except Exception as e:
            print(f" [LLM生成] 全局搜索生成失败: {e}")
            return {
                "method": "global_generate",
                "query": query,
                "error": str(e),
                "success": False
            }
    
    async def global_search_full(self, query: str) -> Dict[str, Any]:
        """全局搜索 - 完整流程（检索+生成）"""
        try:
            print(f"🚀 [完整流程] 开始全局搜索: {query}")
            
            # 1. 先检索
            retrieve_result = await self.global_search_retrieve(query)
            if not retrieve_result['success']:
                return retrieve_result
            
            # 2. 返回检索结果，让agent决定如何处理
            print(f"✅ [完整流程] 全局检索完成，等待agent处理")
            print(f"🤖 [Agent调用] 正在使用Agent调用LLM生成回答...")
            
            return {
                "method": "global_full",
                "query": query,
                "retrieved_context": retrieve_result['retrieved_context'],
                "context_ready": True,
                "success": True,
                "note": "检索完成，请使用llm_generate_tool进行生成"
            }
        except Exception as e:
            print(f"❌ [完整流程] 全局搜索失败: {e}")
            return {
                "method": "global_full",
                "query": query,
                "error": str(e),
                "success": False
            }
    
    async def local_search_retrieve(self, query: str) -> Dict[str, Any]:
        """局部搜索 - 仅检索阶段，展示RAG召回内容"""
        try:
            print(f"🔍 [RAG检索] 正在检索局部信息: {query}")
            
            # 获取检索结果（通过上下文构建器）
            # LocalSearchMixedContext.build_context 是同步方法，不需要 await
            context = self.local_context_builder.build_context(
                query=query,
                **self.local_context_params
            )
            
            # 截断上下文以避免token超限
            # 更安全地处理context对象
            if hasattr(context, 'context_text'):
                context_text = context.context_text
            elif hasattr(context, 'text'):
                context_text = context.text
            elif hasattr(context, 'content'):
                context_text = context.content
            elif hasattr(context, 'response'):
                context_text = context.response
            else:
                # 如果都没有，尝试转换为字符串
                context_text = str(context)
            
            truncated_context = self._truncate_text(context_text, max_tokens=8000)  # 从3000增加到8000
            
            print(f" [RAG检索] 局部检索完成，获得 {len(truncated_context)} 字符的上下文")
            print(f"🤖 [Agent调用] 正在使用Agent调用LLM生成回答...")
            
            return {
                "method": "local_retrieve",
                "query": query,
                "retrieved_context": {
                    "context_text": truncated_context,
                    "context_length": len(truncated_context),
                    "context_summary": "GraphRAG局部搜索检索到的文本单元、实体和关系信息（已截断）"
                },
                "success": True
            }
        except Exception as e:
            print(f"❌ [RAG检索] 局部检索失败: {e}")
            return {
                "method": "local_retrieve",
                "query": query,
                "error": str(e),
                "success": False
            }
    
    async def local_search_generate(self, query: str, retrieved_context: Any) -> Dict[str, Any]:
        """局部搜索 - 仅生成阶段，使用预检索的上下文"""
        try:
            print(f"🤖 [LLM生成] 正在调用大模型生成局部搜索回答: {query}")
            
            # 不直接调用GraphRAG的search方法，而是返回检索到的上下文
            # 让agent通过独立LLM工具来处理生成
            context_text = retrieved_context.get('context_text', '') if isinstance(retrieved_context, dict) else str(retrieved_context)
            
            print(f"✅ [LLM生成] 准备上下文，长度: {len(context_text)} 字符")
            
            return {
                "method": "local_generate",
                "query": query,
                "retrieved_context": retrieved_context,
                "context_ready": True,
                "success": True,
                "note": "请使用llm_generate_tool来处理生成"
            }
        except Exception as e:
            print(f"❌ [LLM生成] 局部搜索生成失败: {e}")
            return {
                "method": "local_generate",
                "query": query,
                "error": str(e),
                "success": False
            }
    
    async def local_search_full(self, query: str) -> Dict[str, Any]:
        """局部搜索 - 完整流程（检索+生成）"""
        try:
            print(f"🚀 [完整流程] 开始局部搜索: {query}")
            
            # 1. 先检索
            retrieve_result = await self.local_search_retrieve(query)
            if not retrieve_result['success']:
                return retrieve_result
            
            # 2. 返回检索结果，让agent决定如何处理
            print(f"✅ [完整流程] 局部检索完成，等待agent处理")
            print(f"🤖 [Agent调用] 正在使用Agent调用LLM生成回答...")
            
            return {
                "method": "local_full",
                "query": query,
                "retrieved_context": retrieve_result['retrieved_context'],
                "context_ready": True,
                "success": True,
                "note": "检索完成，请使用llm_generate_tool进行生成"
            }
        except Exception as e:
            print(f"❌ [完整流程] 局部搜索失败: {e}")
            return {
                "method": "local_full",
                "query": query,
                "error": str(e),
                "success": False
            }

# 全局实例
rag_engine = RAGEngine()