import os

import pandas as pd
import tiktoken

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
from graphrag.query.structured_search.global_search.search import GlobalSearch

from graphrag.query.question_gen.local_gen import LocalQuestionGen
from graphrag.query.structured_search.local_search.mixed_context import (
    LocalSearchMixedContext,
)
from graphrag.query.structured_search.local_search.search import LocalSearch
import asyncio

api_key = "cegVziITiNPb7wEZVLSB1GBXr3okwWwreE2h5ijICRTNjMLMGhmkJQQJ99BHACHYHv6XJ3w3AAABACOG3fBh"
llm_model = "gpt-4o"

config = LanguageModelConfig(
    type=ModelType.AzureOpenAIChat,
    api_base="https://tcamp.openai.azure.com/",
    api_version="2025-01-01-preview",
    auth_type="api_key",
    api_key="cegVziITiNPb7wEZVLSB1GBXr3okwWwreE2h5ijICRTNjMLMGhmkJQQJ99BHACHYHv6XJ3w3AAABACOG3fBh",
    model="gpt-4o",
    deployment_name="gpt-4o",
    model_supports_json=True,
    concurrent_requests=25,
    async_mode="threaded",
    retry_strategy="native",
    max_retries=10,
    tokens_per_minute=120000,
    requests_per_minute=100,
    encoding_model="cl100k_base",  # 可选，通常自动设置
)
model = ModelManager().get_or_create_chat_model(
    name="global_search",
    model_type=ModelType.AzureOpenAIChat,
    config=config,
)

token_encoder = tiktoken.get_encoding("cl100k_base")

# parquet files generated from indexing pipeline
INPUT_DIR = "./book5/output"
COMMUNITY_TABLE = "communities"
COMMUNITY_REPORT_TABLE = "community_reports"
ENTITY_TABLE = "entities"

# community level in the Leiden community hierarchy from which we will load the community reports
# higher value means we use reports from more fine-grained communities (at the cost of higher computation cost)
COMMUNITY_LEVEL = 2

community_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_TABLE}.parquet")
entity_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_TABLE}.parquet")
report_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_REPORT_TABLE}.parquet")

communities = read_indexer_communities(community_df, report_df)
reports = read_indexer_reports(report_df, community_df, COMMUNITY_LEVEL)
entities = read_indexer_entities(entity_df, community_df, COMMUNITY_LEVEL)

print(f"Total report count: {len(report_df)}")
print(
    f"Report count after filtering by community level {COMMUNITY_LEVEL}: {len(reports)}"
)

report_df.head()

context_builder = GlobalCommunityContext(
    community_reports=reports,
    communities=communities,
    entities=entities,  # default to None if you don't want to use community weights for ranking
    token_encoder=token_encoder,
)

async def global_retrieve(query: str):
    results = await context_builder.build_context(query=query, conversation_history=None, max_context_tokens=12_000, 
            use_community_summary=False,
            shuffle_data=True,
            include_community_rank=True,
            min_community_rank=0,
            community_rank_name="rank",
            include_community_weight=True,
            community_weight_name="occurrence weight",
            normalize_community_weight=True,
            max_tokens=10000,  # 从4000增加到10000
    )
    text = results.context_chunks
    tokenizer = tiktoken.get_encoding("cl100k_base")
    full_text = "\n".join(text)
    tokens = tokenizer.encode(full_text)
    max_tokens = 8000
    truncated_tokens = tokens[:max_tokens]
    context = tokenizer.decode(truncated_tokens)
    print(context)
    return context

if __name__ == "__main__":
    asyncio.run(global_retrieve("top themes"))

context_builder_params = {
    "use_community_summary": False,  # False means using full community reports. True means using community short summaries.
    "shuffle_data": True,
    "include_community_rank": True,
    "min_community_rank": 0,
    "community_rank_name": "rank",
    "include_community_weight": True,
    "community_weight_name": "occurrence weight",
    "normalize_community_weight": True,
    "max_tokens": 12_000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
    "context_name": "Reports",
}

map_llm_params = {
    "max_tokens": 1200,
    "temperature": 0.0,
    "response_format": {"type": "json_object"},
}

reduce_llm_params = {
    "max_tokens": 2500,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 1000-1500)
    "temperature": 0.0,
}

search_engine = GlobalSearch(
    model=model,
    context_builder=context_builder,
    token_encoder=token_encoder,
    max_data_tokens=12_000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
    map_llm_params=map_llm_params,
    reduce_llm_params=reduce_llm_params,
    allow_general_knowledge=False,  # set this to True will add instruction to encourage the LLM to incorporate general knowledge in the response, which may increase hallucinations, but could be useful in some use cases.
    json_mode=True,  # set this to False if your LLM model does not support JSON mode.
    context_builder_params=context_builder_params,
    concurrent_coroutines=128,
    response_type="multiple paragraphs",  # free form text describing the response type and format, can be anything, e.g. prioritized list, single paragraph, multiple paragraphs, multiple-page report
)

async def global_search(query: str):
    results = await search_engine.search(query)
    # print(results.response)
    return results
# if __name__ == "__main__":
#     asyncio.run(global_search("概括故事主题"))