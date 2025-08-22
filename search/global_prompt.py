import os
import pandas as pd
import tiktoken
import asyncio
import openai

from graphrag.config.enums import ModelType
from graphrag.config.models.language_model_config import LanguageModelConfig
from graphrag.language_model.manager import ModelManager
from graphrag.query.indexer_adapters import (
    read_indexer_communities,
    read_indexer_entities,
    read_indexer_reports,
)
from graphrag.query.structured_search.global_search.community_context import (
    GlobalCommunityContext,
)

# -----------------------------------------------------------------------------
# 你的 LLM 和資料來源配置
# -----------------------------------------------------------------------------
api_key = "cegVziITiNPb7wEZVLSB1GBXr3okwWwreE2h5ijICRTNjMLMGhmkJQQJ99BHACHYHv6XJ3w3AAABACOG3fBh"
llm_model = "gpt-4o"
azure_api_base = "https://tcamp.openai.azure.com/"
azure_api_version = "2025-01-01-preview"

config = LanguageModelConfig(
    type=ModelType.AzureOpenAIChat,
    api_base=azure_api_base,
    api_version=azure_api_version,
    auth_type="api_key",
    api_key=api_key,
    model=llm_model,
    deployment_name=llm_model,
    model_supports_json=True,
    concurrent_requests=25,
    async_mode="threaded",
    retry_strategy="native",
    max_retries=10,
    tokens_per_minute=120000,
    requests_per_minute=100,
    encoding_model="cl100k_base",
)
model = ModelManager().get_or_create_chat_model(
    name="global_search",
    model_type=ModelType.AzureOpenAIChat,
    config=config,
)

token_encoder = tiktoken.get_encoding("cl100k_base")

INPUT_DIR = "./book_data/suspect_x/output"
COMMUNITY_TABLE = "communities"
COMMUNITY_REPORT_TABLE = "community_reports"
ENTITY_TABLE = "entities"
COMMUNITY_LEVEL = 2

# -----------------------------------------------------------------------------
# 資料載入和 GraphRAG 元件初始化
# -----------------------------------------------------------------------------
try:
    community_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_TABLE}.parquet")
    entity_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_TABLE}.parquet")
    report_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_REPORT_TABLE}.parquet")
except FileNotFoundError:
    print(f"錯誤：未能找到 {INPUT_DIR} 目錄下的 .parquet 文件。請確保你已運行 GraphRAG 的索引管道。")
    exit()

communities = read_indexer_communities(community_df, report_df)
reports = read_indexer_reports(report_df, community_df, COMMUNITY_LEVEL)
entities = read_indexer_entities(entity_df, community_df, COMMUNITY_LEVEL)

context_builder = GlobalCommunityContext(
    community_reports=reports,
    communities=communities,
    entities=entities,
    token_encoder=token_encoder,
)

# -----------------------------------------------------------------------------
# 核心功能：生成 LLM 提示詞的公開接口
# -----------------------------------------------------------------------------
async def get_llm_prompt_and_context(query: str) -> dict:
    """
    根據查詢，使用 GraphRAG 的能力生成 LLM 所需的完整提示詞和上下文。
    
    Args:
        query: 用户的原始查詢。

    Returns:
        一個字典，包含完整的 LLM 提示詞、系統指令和原始上下文。
    """
    print("使用 GraphRAG 的上下文構建器檢索上下文...")
    
    context_result = await context_builder.build_context(
        query=query, conversation_history=None, max_context_tokens=12_000
    )

    if hasattr(context_result, 'context_text'):
        context_text = context_result.context_text
    elif hasattr(context_result, 'context_chunks'):
        context_text = "\n\n---\n\n".join(context_result.context_chunks)
    else:
        raise AttributeError("ContextBuilderResult 物件沒有 'context_text' 或 'context_chunks' 屬性。")
    
    print(f"上下文檢索完成。長度: {len(context_text)} 字符。")

    system_prompt = "你是一個專業的助手，請根據提供的上下文信息回答問題。如果上下文沒有相關信息，請回答'沒有足夠的信息。'"
    user_prompt = f"上下文信息:\n{context_text}\n\n問題: {query}"

    return {
        "final_prompt": user_prompt,
        "system_prompt": system_prompt,
        "context": context_text,
    }

# -----------------------------------------------------------------------------
# 示例：模擬其他使用者如何調用你的函數，並實現流式輸出
# -----------------------------------------------------------------------------

async def example_usage():
    """
    這個函數展示了如何調用 `get_llm_prompt_and_context` 函數，
    並使用其返回的提示詞來實現一個流式 LLM 調用。
    """
    query_text = "概括故事主題"
    
    print(f"\n--- 模擬使用者調用你的模組，並查詢：'{query_text}' ---")
    
    result = await get_llm_prompt_and_context(query_text)

    print("\n--- 成功獲取提示詞，準備調用 LLM ---")
    print(f"獲取的原始上下文長度: {len(result['context'])}")
    
    print("\n--- 開始流式輸出 ---")
    try:
        client = openai.AsyncAzureOpenAI(
            azure_endpoint=azure_api_base,
            api_key=api_key,
            api_version=azure_api_version,
        )
        
        stream = await client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": result['system_prompt']},
                {"role": "user", "content": result['final_prompt']},
            ],
            stream=True,
        )
        
        # 關鍵修正：增加多層檢查，防止 list index out of range 錯誤
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)

        print("\n\n--- 流式輸出結束。---")
    except Exception as e:
        print(f"\n調用 LLM 時發生錯誤：{e}")

# -----------------------------------------------------------------------------
# 主執行入口
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(example_usage())