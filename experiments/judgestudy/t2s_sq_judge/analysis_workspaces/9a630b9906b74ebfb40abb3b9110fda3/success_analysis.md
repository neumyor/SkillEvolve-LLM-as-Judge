# Success Memory Item 1
## Title
Partial Quote Pattern Recognition
## Description
Identify when a question presents an incomplete phrase or lyric and map it directly to the full text in the retrieved context.
## Content
Treat the quoted portion as a fixed anchor. Search the context for exact string matches of the provided fragment. Once located, isolate the immediately following word or phrase that completes the sentence. This avoids overcomplication and targets the exact missing element.

# Success Memory Item 2
## Title
Cross-Source Phrase Alignment
## Description
Use repeated mentions of the target phrase across multiple context documents to confirm the correct completion without ambiguity.
## Content
When the retrieved context contains several snippets sharing the same partial quote, align them to identify the consistent ending. Consistent phrasing across independent sources strongly indicates the exact intended completion, allowing direct extraction without additional inference.

# Success Memory Item 3
## Title
Minimalist Extraction & Tagging
## Description
Extract only the precise missing term and enforce strict output formatting to satisfy automated evaluation metrics.
## Content
After confirming the completion, strip away surrounding context, synonyms, or explanatory text. Return solely the exact missing word(s) wrapped in the required `<answer>...</answer>` tags. This prevents format mismatches and ensures high similarity scores against expected outputs.
