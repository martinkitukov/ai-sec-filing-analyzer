import faiss
import numpy as np
from transformers import GPT2Tokenizer, GPT2Model
import torch
from typing import List, Dict, Any
import json
import os

class VectorStore:
    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
        self.model = GPT2Model.from_pretrained('gpt2')
        self.documents = []
        self.vector_id_to_doc = {}

    def _get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a text using GPT-2."""
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        # Use the last hidden state's mean as the embedding
        embedding = outputs.last_hidden_state.mean(dim=1).numpy()
        return embedding

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any] = None):
        """Add a document to the vector store."""
        embedding = self._get_embedding(content)
        self.index.add(embedding)
        self.documents.append({
            'id': doc_id,
            'content': content,
            'metadata': metadata or {}
        })
        self.vector_id_to_doc[len(self.documents) - 1] = doc_id

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using a query."""
        query_embedding = self._get_embedding(query)
        distances, indices = self.index.search(query_embedding, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # -1 indicates no result
                doc_id = self.vector_id_to_doc[idx]
                doc = next(d for d in self.documents if d['id'] == doc_id)
                results.append({
                    'id': doc_id,
                    'content': doc['content'],
                    'metadata': doc['metadata'],
                    'score': float(distances[0][i])
                })
        return results

    def save(self, directory: str):
        """Save the vector store to disk."""
        os.makedirs(directory, exist_ok=True)
        faiss.write_index(self.index, os.path.join(directory, 'index.faiss'))
        
        with open(os.path.join(directory, 'documents.json'), 'w') as f:
            json.dump(self.documents, f)
        
        with open(os.path.join(directory, 'vector_id_to_doc.json'), 'w') as f:
            json.dump(self.vector_id_to_doc, f)

    def load(self, directory: str):
        """Load the vector store from disk."""
        self.index = faiss.read_index(os.path.join(directory, 'index.faiss'))
        
        with open(os.path.join(directory, 'documents.json'), 'r') as f:
            self.documents = json.load(f)
        
        with open(os.path.join(directory, 'vector_id_to_doc.json'), 'r') as f:
            self.vector_id_to_doc = json.load(f) 