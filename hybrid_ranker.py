from sentence_transformers import SentenceTransformer, util
import numpy as np
from datetime import datetime

# Load BERT model once
bert_model = SentenceTransformer('all-MiniLM-L6-v2')


def get_similarity_scores(query, abstracts):
    query_emb = bert_model.encode(query, convert_to_tensor=True)
    doc_emb = bert_model.encode(abstracts, convert_to_tensor=True)
    scores = util.cos_sim(query_emb, doc_emb)
    return scores[0].cpu().numpy()


def compute_recency_score(year):
    current_year = datetime.now().year

    if year >= current_year - 1:
        return 1.0
    elif year >= current_year - 5:
        return 0.6
    else:
        return 0.2


def hybrid_ranking(query, papers, sim_w=0.6, cite_w=0.3, rec_w=0.1):

    if not papers:
        return []

    abstracts = [paper.get("summary", "") for paper in papers]
    similarities = get_similarity_scores(query, abstracts)

    # Normalize citation score
    max_citations = max(
        [paper.get("citations", 0) for paper in papers]
    ) if papers else 1

    ranked_papers = []

    for i, paper in enumerate(papers):

        similarity_score = float(similarities[i])

        citation_score = (
            paper.get("citations", 0) / max_citations
            if max_citations > 0 else 0
        )

        recency_score = compute_recency_score(
            paper.get("year", datetime.now().year)
        )

        final_score = (
            sim_w * similarity_score +
            cite_w * citation_score +
            rec_w * recency_score
        )

        paper["similarity"] = round(similarity_score, 3)
        paper["final_score"] = round(final_score, 3)

        ranked_papers.append(paper)

    ranked_papers = sorted(
        ranked_papers,
        key=lambda x: x["final_score"],
        reverse=True
    )

    return ranked_papers