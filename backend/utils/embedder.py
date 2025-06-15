import faiss
import numpy as np
from transformers import GPT2Tokenizer, GPT2Model
import torch
from typing import List, Dict, Any, Optional
import json
import os
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.llms import HuggingFacePipeline
import uuid

logger = logging.getLogger(__name__)

class DocumentEmbedder:
    def __init__(self, model_name: str = "gpt2", dimension: int = 768):
        self.model_name = model_name
        self.dimension = dimension
        self.tokenizer = GPT2Tokenizer.from_pretrained(model_name)
        self.model = GPT2Model.from_pretrained(model_name)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        self.vector_store = None
        self.vector_store_path = os.getenv("VECTOR_STORE_PATH", "data/vector_store")

    def _get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a text using GPT-2."""
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        # Use the last hidden state's mean as the embedding
        embedding = outputs.last_hidden_state.mean(dim=1).numpy()
        return embedding

    def process_document(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Process a document and store its embeddings."""
        # Split text into chunks
        chunks = self.text_splitter.split_text(content)
        
        # Create vector store if it doesn't exist
        if not self.vector_store:
            self.vector_store = FAISS.from_texts(
                chunks,
                self.embeddings,
                metadatas=[metadata or {}] * len(chunks)
            )
        else:
            self.vector_store.add_texts(
                chunks,
                metadatas=[metadata or {}] * len(chunks)
            )

        # Generate a unique ID for the document
        doc_id = str(uuid.uuid4())
        
        # Save the vector store
        self.save_vector_store(doc_id)
        
        return doc_id

    def query_document(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Query the document using semantic search."""
        if not self.vector_store:
            raise ValueError("No documents have been processed yet")

        # Create a QA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=HuggingFacePipeline.from_model_id(
                model_id=self.model_name,
                task="text-generation",
                device=0 if torch.cuda.is_available() else -1,
            ),
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(search_kwargs={"k": k}),
        )

        # Get the answer
        result = qa_chain({"query": query})
        
        return {
            "answer": result["result"],
            "sources": result.get("source_documents", [])
        }

    def save_vector_store(self, doc_id: str):
        """Save the vector store to disk."""
        os.makedirs(self.vector_store_path, exist_ok=True)
        self.vector_store.save_local(
            os.path.join(self.vector_store_path, f"index_{doc_id}")
        )

    def load_vector_store(self, doc_id: str):
        """Load the vector store from disk."""
        index_path = os.path.join(self.vector_store_path, f"index_{doc_id}")
        if os.path.exists(index_path):
            self.vector_store = FAISS.load_local(
                index_path,
                self.embeddings
            )
        else:
            raise ValueError(f"No vector store found for document {doc_id}") 