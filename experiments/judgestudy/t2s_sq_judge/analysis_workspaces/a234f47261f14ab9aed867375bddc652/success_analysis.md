# Success Memory Item 1
## Title
Explicit Entity-Attribute Mapping
## Description
Prioritize direct textual evidence that explicitly links the queried property to a specific entity, using exact phrasing alignment as the primary selection criterion.
## Content
When processing factoid or trivia-style questions, scan retrieved passages for sentences that directly state the relationship (e.g., "[X] contains [Y]"). Favor candidates backed by explicit mentions over those requiring inference, especially when the question uses phrasing that closely mirrors a specific document snippet.

# Success Memory Item 2
## Title
Specificity-Driven Disambiguation
## Description
Resolve overlapping or broad answer candidates by selecting the most specific subtype that aligns with the question's grammatical framing and contextual support.
## Content
If multiple terms satisfy the query (e.g., a general category vs. a distinct variant), evaluate which best matches the question's implied scope. Prefer concrete subcategories when the context explicitly ties the target attribute to that narrower term, ensuring the answer precisely fits the "type" or specific instance requested.

# Success Memory Item 3
## Title
Constraint-Aligned Extraction
## Description
Isolate the final determined answer into its core lexical form and enclose it strictly within the mandated output tags, omitting all reasoning or auxiliary text.
## Content
After identifying the correct answer, strip away modifiers, explanations, or conversational filler. Extract only the essential noun phrase or value and place it directly inside the required tags (e.g., `<answer>...</answer>`) to guarantee compatibility with automated evaluation pipelines and strict formatting rules.
