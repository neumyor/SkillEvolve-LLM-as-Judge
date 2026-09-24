# Success Memory Item 1
## Title
Syntactic Alignment for Direct Mapping
## Description
Match the grammatical structure and key entities of the prompt against context sentences to locate explicit definitions or equivalences.
## Content
When a question asks how a group or entity refers to something else, scan the retrieved text for parallel phrasing (e.g., "When X refer to 'Y' they mean..." or "What Z calls A, W calls B"). Extract the term that completes the equivalence directly stated in the source.

# Success Memory Item 2
## Title
Cross-Source Consistency Check
## Description
Identify converging evidence across multiple retrieved documents to confirm the most likely correct term.
## Content
If several independent snippets address the same relationship, prioritize the answer that appears consistently across them. This approach minimizes reliance on isolated excerpts and ensures the selected term reflects the dominant pattern in the provided material.

# Success Memory Item 3
## Title
Terminology Fidelity Over Inference
## Description
Prioritize exact or near-exact phrasing found in the context rather than applying external knowledge or making logical deductions.
## Content
When the context explicitly states the requested term, output it verbatim or with minimal grammatical adjustment. Avoid substituting synonyms or inferring broader categories unless the text explicitly supports them, ensuring the response remains tightly bound to the source material.
