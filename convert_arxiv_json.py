import json
import pandas as pd

input_file = "arxiv-metadata-oai-snapshot.json"

titles = []
abstracts = []
subjects = []

with open(input_file, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i > 20000:   # limit for faster processing (20k papers)
            break
        
        paper = json.loads(line)
        
        titles.append(paper.get("title", ""))
        abstracts.append(paper.get("abstract", ""))
        subjects.append(paper.get("categories", ""))

df = pd.DataFrame({
    "title": titles,
    "abstract": abstracts,
    "subject": subjects
})

df.to_csv("research_dataset.csv", index=False)
print("CSV file created successfully!")