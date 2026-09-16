import os
import chromadb
from chromadb.utils import embedding_functions
from langchain_core.tools import tool
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.config import RULES_DIR, CHROMA_PERSIST_DIR, CHROMA_COLLECTION

_chroma_collection = None


def _get_embedding_func():
    return embedding_functions.DefaultEmbeddingFunction()


def _load_and_split_docs():
    """加载规章制度文档并切分为文档片段。"""
    loader = DirectoryLoader(
        RULES_DIR,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "；", "，", " "],
    )
    return splitter.split_documents(docs)


def build_vectorstore():
    """加载规章制度文档，切分后写入向量库。首次运行时调用。"""
    chunks = _load_and_split_docs()

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    emb_fn = _get_embedding_func()
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        embedding_function=emb_fn,
        metadata={"hnsw:space": "cosine"},
    )

    ids = [f"doc_{i}" for i in range(len(chunks))]
    documents = [c.page_content for c in chunks]
    metadatas = [{"source": os.path.basename(c.metadata.get("source", "未知"))} for c in chunks]

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    print(f"向量库构建完成：{len(chunks)} 个文档片段已写入。")
    return collection


def get_collection():
    """获取向量库集合，首次调用时自动构建。"""
    global _chroma_collection

    if _chroma_collection is not None:
        return _chroma_collection

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    try:
        _chroma_collection = client.get_collection(
            name=CHROMA_COLLECTION,
            embedding_function=_get_embedding_func(),
        )
        count = _chroma_collection.count()
        if count == 0:
            _chroma_collection = build_vectorstore()
    except Exception:
        _chroma_collection = build_vectorstore()

    return _chroma_collection


@tool
def rag_search(question: str) -> str:
    """检索会议室规章制度知识库，回答关于使用规则、预约政策、设备配置的问题。

    当用户询问规章制度相关问题（如"取消要提前多久"、"能带宠物吗"、"有什么设备"）时使用此工具。

    参数:
        question: 用户的规章制度问题

    返回: 从知识库检索到的相关文档片段
    """
    collection = get_collection()
    results = collection.query(query_texts=[question], n_results=3)

    documents = results.get("documents", [[]])
    metadatas = results.get("metadatas", [[]])

    if not documents or not documents[0]:
        return "未在知识库中找到相关内容。"

    output = []
    for i, (doc, meta) in enumerate(zip(documents[0], metadatas[0] if metadatas[0] else []), 1):
        source = meta.get("source", "未知") if meta else "未知"
        output.append(f"[片段{i} | 来源：{source}]\n{doc}")

    return "\n\n---\n\n".join(output)
