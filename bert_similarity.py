from sentence_transformers import SentenceTransformer, util
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text):
    return model.encode(text, convert_to_tensor=True)

def similarity_score(query, documents):
    query_emb = get_embedding(query)
    doc_emb = model.encode(documents, convert_to_tensor=True)
    scores = util.pytorch_cos_sim(query_emb, doc_emb)
    return scores[0].cpu().numpy()