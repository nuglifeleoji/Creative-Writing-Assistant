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
    """GraphRAG引擎，将检索和LLM调用分离，支持多书本"""
    
    def __init__(self, input_dir: str = "./rag/output"):
        """
        初始化RAG引擎
        
        Args:
            input_dir: 输入目录路径，包含GraphRAG处理后的数据文件
        """
        self.input_dir = input_dir
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


        
        # self.embedding_config = LanguageModelConfig(
        #     api_key=self.embedding_key,
        #     type=ModelType.OpenAIEmbedding,
        #     api_base="https://open.bigmodel.cn/api/paas/v4",
        #     model="embedding-3",
        #     deployment_name="embedding-3",
        #     auth_type="api_key",
        #     max_retries=20,
        #     tokens_per_minute=120000000,
        #     requests_per_minute=100,
        #     encoding_model="cl100k_base",
        # )

        self.embedding_config = LanguageModelConfig(
                        type=ModelType.AzureOpenAIChat,
            api_base="https://tcamp.openai.azure.com/",
            api_version="2023-05-15",
            auth_type="api_key",
            api_key=self.api_key,
            model="text-embedding-ada-002",
            deployment_name="text-embedding-ada-002",
            model_supports_json=True,
            concurrent_requests=25,
            async_mode="threaded",
            retry_strategy="native",
            max_retries=20,
            tokens_per_minute=120000000,
            requests_per_minute=100,
            encoding_model="cl100k_base",
        )
        
        self.token_encoder = tiktoken.get_encoding("cl100k_base")
        
    def _init_data(self):
        """初始化数据"""
        COMMUNITY_LEVEL = 2
        
        # 检查输入目录是否存在
        if not os.path.exists(self.input_dir):
            raise ValueError(f"输入目录不存在: {self.input_dir}")
        
        print(f"📚 正在加载书本数据: {self.input_dir}")
        
        # 读取数据文件
        self.community_df = pd.read_parquet(f"{self.input_dir}/communities.parquet")
        self.entity_df = pd.read_parquet(f"{self.input_dir}/entities.parquet")
        self.report_df = pd.read_parquet(f"{self.input_dir}/community_reports.parquet")
        self.relationship_df = pd.read_parquet(f"{self.input_dir}/relationships.parquet")
        self.text_unit_df = pd.read_parquet(f"{self.input_dir}/text_units.parquet")
        
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
        self.description_embedding_store.connect(db_uri=f"{self.input_dir}/lancedb")
        
        print(f"✅ 书本数据加载完成: {self.input_dir}")
        
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
        
        # 大幅减少max_tokens以避免上下文超限，优化API调用效率
        self.global_context_params = {
            "use_community_summary": False,
            "shuffle_data": True,
            "include_community_rank": True,
            "min_community_rank": 0,
            "community_rank_name": "rank",
            "include_community_weight": True,
            "community_weight_name": "occurrence weight",
            "normalize_community_weight": True,
            "max_tokens": 4000,  # 再次收缩，降低超长上下文概率
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
            max_data_tokens=6000,  # 从10000减少到6000以减少检索内容
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

        # 大幅减少max_tokens以避免上下文超限，优化API调用效率
        self.local_context_params = {
            "text_unit_prop": 0.4,  # 从0.5减少到0.4
            "community_prop": 0.05,  # 从0.1减少到0.05
            "conversation_history_max_turns": 2,  # 从3减少到2
            "conversation_history_user_turns_only": True,
            "top_k_mapped_entities": 3,  # 从5减少到3
            "top_k_relationships": 3,  # 从5减少到3
            "include_entity_rank": True,
            "include_relationship_weight": True,
            "include_community_rank": False,
            "return_candidate_context": False,
            "embedding_vectorstore_key": EntityVectorStoreKey.ID,
            "max_tokens": 3500,  # 再次收缩
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
        """截断文本以避免token超限 - 已弃用，保留向后兼容"""
        if not text:
            return text
        
        tokens = self.token_encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        # 截断到指定token数
        truncated_tokens = tokens[:max_tokens]
        return self.token_encoder.decode(truncated_tokens)
    
    def _chunk_text(self, text: str, max_tokens_per_chunk: int = 6000, overlap_tokens: int = 300) -> List[Dict[str, Any]]:
        """
        将长文本分块，用于并行处理（智能分块版本，确保每个分块都在LLM处理范围内）
        
        Args:
            text: 要分块的文本
            max_tokens_per_chunk: 每个分块的最大token数（8000，为提示词留出空间）
            overlap_tokens: 分块之间的重叠token数
            
        Returns:
            分块列表，每个分块包含文本、位置信息等
        """
        if not text:
            return []
        
        tokens = self.token_encoder.encode(text)
        total_tokens = len(tokens)
        
        # 如果文本不太长，直接返回单个分块
        if total_tokens <= max_tokens_per_chunk:
            return [{
                "chunk_id": 0,
                "text": text,
                "start_token": 0,
                "end_token": total_tokens,
                "total_tokens": total_tokens,
                "chunk_tokens": total_tokens,
                "is_complete": True,
                "safe_for_llm": True
            }]
        
        chunks = []
        chunk_id = 0
        start = 0
        
        # 智能分块：确保每个分块都能被LLM处理
        # 考虑提示词开销（约2000-3000 tokens）+ 分块内容（6000 tokens）≈ 8000-9000 tokens
        # 更保守，降低超限概率
        
        while start < total_tokens:
            end = min(start + max_tokens_per_chunk, total_tokens)
            
            # 提取当前分块的token
            chunk_tokens = tokens[start:end]
            chunk_text = self.token_encoder.decode(chunk_tokens)
            
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "start_token": start,
                "end_token": end,
                "total_tokens": total_tokens,
                "chunk_tokens": len(chunk_tokens),
                "is_complete": (len(chunks) == 1 and end >= total_tokens),
                "safe_for_llm": True  # 标记这个分块是LLM安全的
            })
            
            chunk_id += 1
            
            # 下一个分块的起始位置，考虑重叠
            if end >= total_tokens:
                break
            start = end - overlap_tokens
        
        print(f"📊 [智能分块] 原始 {total_tokens} tokens 分为 {len(chunks)} 个安全分块（每块最多 {max_tokens_per_chunk} tokens，确保LLM可处理）")
        return chunks
    
    async def naive_retrieve(self, query: str) -> Dict[str, Any]:
        try:
            print(f"🔍 [RAG检索] 正在进行朴素检索: {query}")
            # 直接使用文本检索
            context = await self.global_context_builder.build_context(
                query=query,
                **self.global_context_params
            )
            return {
                "method": "naive_retrieve",
                "query": query,
                "retrieved_context": context,
                "context_ready": True,
                "success": True,
                "note": "朴素检索完成"
            }
        except Exception as e:
            print(f"❌ [RAG检索] 朴素检索失败: {e}")
            return {
                "method": "naive_retrieve",
                "query": query,
                "error": str(e),
                "success": False
            }

    async def global_search_retrieve(self, query: str) -> Dict[str, Any]:
        """全局搜索 - 仅检索阶段，返回完整召回内容用于分块处理"""
        try:
            print(f"🔍 [RAG检索] 正在检索全局信息: {query}")
            
            # 获取检索结果（通过上下文构建器）
            # build_context 是异步方法，需要 await
            context = await self.global_context_builder.build_context(
                query=query,
                **self.global_context_params
            )
            
            # 处理context对象，获取原始文本
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
            
            # 计算原始长度
            original_tokens = len(self.token_encoder.encode(context_text))
            
            # 大分块处理（大幅减少分块数量以减少API调用次数）
            chunks = self._chunk_text(context_text, max_tokens_per_chunk=100000, overlap_tokens=20000)
            
            print(f"✅ [RAG检索] 全局检索完成，原始内容 {original_tokens} tokens，分为 {len(chunks)} 个大分块")
            
            return {
                "method": "global_retrieve",
                "query": query,
                "retrieved_context": {
                    "full_text": context_text,
                    "original_length": len(context_text),
                    "original_tokens": original_tokens,
                    "chunks": chunks,
                    "total_chunks": len(chunks),
                    "context_summary": f"GraphRAG全局搜索检索到的社区报告和实体信息（完整内容，{len(chunks)}个大分块，减少API调用）"
                },
                "context_ready": True,
                "success": True,
                "note": "检索完成"
            }
        except Exception as e:
            print(f"❌ [RAG检索] 全局检索失败: {e}")
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
        """全局搜索 - 完整流程（检索+分块并行分析+综合）"""
        return await self.naive_retrieve(query)
        # try:
        #     print(f"🚀 [完整流程] 开始全局搜索: {query}")
            
        #     # 1. 先检索
        #     retrieve_result = await self.naive_retrieve(query)
        #     if not retrieve_result['success']:
        #         return retrieve_result
            
#             # 2. 获取检索到的内容和分块
#             retrieved_context = retrieve_result['retrieved_context']
#             full_text = retrieved_context['full_text']
#             chunks = retrieved_context['chunks']
            
#             print(f"📊 [分块处理] 开始对 {len(chunks)} 个分块进行并行LLM分析")
            
#             # 3. 对每个分块并行调用LLM进行分析
#             async def analyze_chunk(chunk_info):
#                 chunk_id = chunk_info['chunk_id']
#                 chunk_text = chunk_info['text']
#                 chunk_tokens = chunk_info.get('chunk_tokens', 0)
                
#                 print(f"  📝 [分块 {chunk_id}] 正在分析 ({chunk_tokens} tokens)")
                
#                 # 构建分析提示（优化：更简洁聚焦）
#                 analysis_prompt = f"""你是一个文本分析助手，请基于输入的文本提取与用户问题相关的信息：{query}。输入内容是一个数据表格，它代表了某本书的一部分数据信息且是分条对内容进行表述，你可以通过这个数据表格获取有用内容。

# 内容片段 [{chunk_id + 1}]:
# {chunk_text}

# 要求：
# # 文本分析要求
# - 根据上面的文本片段回答用户问题，尽可能详细，逻辑严密。例如：用户问题有关“总结书中主要信息、主题”，那么就对于输入的文本信息进行总结，提取其中的关键部分；如果问题有关“书中的人物A”，那么就提取与人物A相关的信息，等等。
# # 输出格式
# 严格按照中文输出，可以考虑分条叙述。
# """
                
#                 try:
#                     # 检查提示长度，避免token超限
#                     prompt_tokens = len(self.token_encoder.encode(analysis_prompt))
#                     if prompt_tokens > 1000000:  # 降低限制到10K，为响应留空间
#                         print(f"    ⚠️ [分块 {chunk_id}] 内容过长 ({prompt_tokens} tokens)，进行压缩")
#                         max_chunk_chars = 600000
#                         if len(chunk_text) > max_chunk_chars:
#                             compressed_text = chunk_text[:max_chunk_chars] + "\\n\\n[内容已压缩以适配LLM限制]"
#                             analysis_prompt = f"""请基于以下内容回答用户问题，提取关键信息：

# 用户问题：{query}

# 内容片段 [{chunk_id + 1}] (已压缩):
# {compressed_text}

# 要求：
# - 直接回答用户问题的相关部分
# - 如果内容不相关，说明"此片段无相关信息"  
# - 简洁准确，突出重点"""
                    
#                     # 调用GraphRAG的chat_model进行分析
#                     response = await self.chat_model.achat(analysis_prompt)
                    
#                     # 统计response的token数
#                     response_tokens = len(self.token_encoder.encode(str(response.output)))
#                     print(f"    ✅ [分块 {chunk_id}] 分析完成，生成回答 {response_tokens} tokens")
#                     # print(response.output)
                    
#                     return {
#                         "chunk_id": chunk_id,
#                         "analysis": response.output,
#                         "success": True,
#                         "chunk_tokens": chunk_tokens
#                     }
                    
#                 except Exception as e:
#                     print(f"    ❌ [分块 {chunk_id}] 分析失败: {e}")
#                     return {
#                         "chunk_id": chunk_id,
#                         "analysis": f"分析失败: {str(e)}",
#                         "success": False,
#                         "error": str(e),
#                         "chunk_tokens": chunk_tokens
#                     }
            
#             # 4. 并行处理所有分块（限制并发数避免API限制）
#             import asyncio
#             semaphore = asyncio.Semaphore(15)  # 限制最多3个并发
            
#             async def limited_analyze(chunk):
#                 async with semaphore:
#                     result = await analyze_chunk(chunk)
#                     # 添加小延迟避免速率限制
#                     return result
            
#             chunk_results = await asyncio.gather(*[limited_analyze(chunk) for chunk in chunks])
            
#             # 5. 统计和整理结果
#             successful_chunks = [r for r in chunk_results if r.get("success", False)]
#             failed_chunks = [r for r in chunk_results if not r.get("success", False)]
            
#             print(f"📊 [分块分析] 完成：{len(successful_chunks)}/{len(chunks)} 个分块成功")
            
#             # 6. 将所有成功的分析结果综合成一个完整的上下文
#             comprehensive_analysis = []
#             for result in successful_chunks:
#                 chunk_id = result['chunk_id']
#                 analysis = result['analysis']
#                 comprehensive_analysis.append(f"=== 分块 {chunk_id} 分析结果 ===\\n{analysis}\\n")
            
            # 7. 创建综合上下文
#             final_context = f"""基于GraphRAG全局搜索和分块分析，以下是关于"{query}"的综合信息：

# {"".join(retrieve_result)}
# """
            
#             print(f"✅ [完整流程] 全局搜索和分块分析完成，生成综合上下文")
            
#             return {
#                 "method": "global_full_with_parallel_analysis",
#                 "query": query,
#                 "comprehensive_context": final_context,
#                 "context_ready": True,
#                 "success": True,
#                 "note": f"已完成分块并行分析，{len(successful_chunks)}/{len(chunks)} 个分块成功。Agent可直接使用comprehensive_context进行最终回答。"
#             }
            
#         except Exception as e:
#             print(f"❌ [完整流程] 全局搜索失败: {e}")
#             return {
#                 "method": "global_full_with_parallel_analysis",
#                 "query": query,
#                 "error": str(e),
#                 "success": False
#             }
    
    async def local_search_retrieve(self, query: str) -> Dict[str, Any]:
        """局部搜索 - 仅检索阶段，返回完整召回内容用于分块处理"""
        try:
            print(f"🔍 [RAG检索] 正在检索局部信息: {query}")
            
            # 获取检索结果（通过上下文构建器）
            # LocalSearchMixedContext.build_context 是同步方法，不需要 await
            context = self.local_context_builder.build_context(
                query=query,
                **self.local_context_params
            )
            
            # 处理context对象，获取原始文本
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
            
            # 计算原始长度
            original_tokens = len(self.token_encoder.encode(context_text))
            
            # 大分块处理（大幅减少分块数量以减少API调用次数）
            chunks = self._chunk_text(context_text, max_tokens_per_chunk=20000, overlap_tokens=1500)
            
            print(f"✅ [RAG检索] 局部检索完成，原始内容 {original_tokens} tokens，分为 {len(chunks)} 个大分块")
            
            return {
                "method": "local_retrieve",
                "query": query,
                "retrieved_context": {
                    "full_text": context_text,
                    "original_length": len(context_text),
                    "original_tokens": original_tokens,
                    "chunks": chunks,
                    "total_chunks": len(chunks),
                    "context_summary": f"GraphRAG局部搜索检索到的文本单元、实体和关系信息（完整内容，{len(chunks)}个大分块，减少API调用）"
                },
                "context_ready": True,
                "success": True,
                "note": "检索完成，请使用parallel_chunk_analysis_tool进行分析"
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
        """局部搜索 - 完整流程（检索+分块并行分析+综合）"""
        try:
            print(f"🚀 [完整流程] 开始局部搜索: {query}")
            
            # 1. 先检索
            retrieve_result = await self.local_search_retrieve(query)
            if not retrieve_result['success']:
                return retrieve_result
            
            # 2. 获取检索到的内容和分块
            retrieved_context = retrieve_result['retrieved_context']
            full_text = retrieved_context['full_text']
            chunks = retrieved_context['chunks']
            
            print(f"📊 [分块处理] 开始对 {len(chunks)} 个分块进行并行LLM分析")
            
            # 3. 对每个分块并行调用LLM进行分析
            async def analyze_chunk(chunk_info):
                chunk_id = chunk_info['chunk_id']
                chunk_text = chunk_info['text']
                chunk_tokens = chunk_info.get('chunk_tokens', 0)
                
                print(f"  📝 [分块 {chunk_id}] 正在分析 ({chunk_tokens} tokens)")
                
                # 构建分析提示（局部搜索：聚焦具体细节）
                analysis_prompt = f"""请基于以下内容回答用户问题，专注于具体细节：

用户问题：{query}

内容片段 [{chunk_id + 1}]:
{chunk_text}

要求：
- 重点提取具体事实、数据、人物关系
- 引用关键文本段落作为证据
- 如果内容不相关，说明"此片段无相关信息"
- 简洁准确，突出关键细节"""
                
                try:
                    # 检查提示长度，避免token超限
                    prompt_tokens = len(self.token_encoder.encode(analysis_prompt))
                    if prompt_tokens > 10000:  # 降低限制到10K，为响应留空间
                        print(f"    ⚠️ [分块 {chunk_id}] 内容过长 ({prompt_tokens} tokens)，进行压缩")
                        max_chunk_chars = 6000
                        if len(chunk_text) > max_chunk_chars:
                            compressed_text = chunk_text[:max_chunk_chars] + "\\n\\n[内容已压缩以适配LLM限制]"
                            analysis_prompt = f"""请基于以下内容回答用户问题，专注于具体细节：

用户问题：{query}

内容片段 [{chunk_id + 1}] (已压缩):
{compressed_text}

要求：
- 重点提取具体事实、数据、人物关系
- 引用关键文本段落作为证据
- 如果内容不相关，说明"此片段无相关信息"
- 简洁准确，突出关键细节"""
                    
                    # 调用GraphRAG的chat_model进行分析
                    response = await self.chat_model.achat(analysis_prompt)
                    
                    print(f"    ✅ [分块 {chunk_id}] 分析完成")
                    
                    return {
                        "chunk_id": chunk_id,
                        "analysis": response,
                        "success": True,
                        "chunk_tokens": chunk_tokens
                    }
                    
                except Exception as e:
                    print(f"    ❌ [分块 {chunk_id}] 分析失败: {e}")
                    return {
                        "chunk_id": chunk_id,
                        "analysis": f"分析失败: {str(e)}",
                        "success": False,
                        "error": str(e),
                        "chunk_tokens": chunk_tokens
                    }
            
            # 4. 并行处理所有分块（限制并发数避免API限制）
            import asyncio
            semaphore = asyncio.Semaphore(3)  # 限制最多3个并发
            
            async def limited_analyze(chunk):
                async with semaphore:
                    result = await analyze_chunk(chunk)
                    # 添加小延迟避免速率限制
                    await asyncio.sleep(0.1)
                    return result
            
            chunk_results = await asyncio.gather(*[limited_analyze(chunk) for chunk in chunks])
            
            # 5. 统计和整理结果
            successful_chunks = [r for r in chunk_results if r.get("success", False)]
            failed_chunks = [r for r in chunk_results if not r.get("success", False)]
            
            print(f"📊 [分块分析] 完成：{len(successful_chunks)}/{len(chunks)} 个分块成功")
            
            # 6. 将所有成功的分析结果综合成一个完整的上下文
            comprehensive_analysis = []
            for result in successful_chunks:
                chunk_id = result['chunk_id']
                analysis = result['analysis']
                comprehensive_analysis.append(f"=== 分块 {chunk_id} 分析结果 ===\\n{analysis}\\n")
            
            # 7. 创建综合上下文
            final_context = f"""基于GraphRAG局部搜索和分块分析，以下是关于"{query}"的综合信息：

{"".join(comprehensive_analysis)}

=== 综合信息总结 ===
以上是基于 {len(successful_chunks)} 个数据分块的详细局部分析结果。每个分块都经过了独立的LLM分析，重点关注具体细节和精确信息。

原始检索信息：
- 总token数：{retrieved_context['original_tokens']}
- 分块数量：{len(chunks)}
- 成功分析：{len(successful_chunks)}个分块
- 失败分析：{len(failed_chunks)}个分块"""
            
            print(f"✅ [完整流程] 局部搜索和分块分析完成，生成综合上下文")
            
            return {
                "method": "local_full_with_parallel_analysis",
                "query": query,
                "comprehensive_context": final_context,
                "total_chunks": len(chunks),
                "successful_chunks": len(successful_chunks),
                "failed_chunks": len(failed_chunks),
                "chunk_details": chunk_results,
                "context_ready": True,
                "success": True,
                "note": f"已完成分块并行分析，{len(successful_chunks)}/{len(chunks)} 个分块成功。Agent可直接使用comprehensive_context进行最终回答。"
            }
            
        except Exception as e:
            print(f"❌ [完整流程] 局部搜索失败: {e}")
            return {
                "method": "local_full_with_parallel_analysis",
                "query": query,
                "error": str(e),
                "success": False
            }


# 全局实例 - 默认使用 ./rag/output
rag_engine = RAGEngine()

# 多书本管理器
class MultiBookManager:
    """多书本管理器，用于管理多个RAG引擎实例"""
    
    def __init__(self):
        self.engines = {}  # 缓存引擎实例
        self.current_book = None
    
    def add_book(self, book_name: str, book_folder: str):
        """添加新书本"""
        if not os.path.exists(book_folder):
            raise ValueError(f"书本文件夹不存在: {book_folder}")
        
        # 创建新的RAG引擎实例
        self.engines[book_name] = RAGEngine(input_dir=book_folder)
        print(f"✅ 添加书本: {book_name} -> {book_folder}")
        
        # 如果是第一本书，自动设置为当前书本
        if self.current_book is None:
            self.current_book = book_name
    
    def switch_book(self, book_name: str):
        """切换到指定书本"""
        if book_name not in self.engines:
            raise ValueError(f"书本不存在: {book_name}")
        
        if self.current_book == book_name:
            print(f"ℹ️ 已经在书本: {book_name}")
            return
        
        print(f"🔄 切换到书本: {book_name}")
        self.current_book = book_name
    
    def get_current_engine(self) -> RAGEngine:
        """获取当前书本的引擎"""
        if self.current_book is None:
            raise ValueError("没有选择任何书本，请先使用 add_book() 添加书本")
        
        return self.engines[self.current_book]
    
    def list_books(self) -> List[str]:
        """列出所有可用的书本"""
        return list(self.engines.keys())
    
    def get_current_book(self) -> Optional[str]:
        """获取当前书本名称"""
        return self.current_book
    
    def remove_book(self, book_name: str):
        """移除书本"""
        if book_name in self.engines:
            del self.engines[book_name]
            print(f"✅ 移除书本: {book_name}")
            
            # 如果移除的是当前书本，切换到其他书本
            if self.current_book == book_name:
                if self.engines:
                    first_book = list(self.engines.keys())[0]
                    self.current_book = first_book
                else:
                    self.current_book = None


# 全局多书本管理器实例
multi_book_manager = MultiBookManager()