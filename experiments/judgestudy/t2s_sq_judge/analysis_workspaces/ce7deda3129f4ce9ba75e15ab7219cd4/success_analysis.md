# Success Memory Item 1
## Title
Exact Phrase Matching for Trivia and Quiz Prompts
## Description
Detect when a question follows a standardized trivia or quiz format and search for verbatim matches in the retrieved context to locate pre-existing Q&A pairs.
## Content
Many trivia questions are sourced directly from datasets, forums, or game shows. When the prompt closely mirrors a known format, scan the context for exact string matches. If a match is found, the answer is typically embedded in the same line or paragraph. Extracting directly from this match ensures high accuracy without additional reasoning.

# Success Memory Item 2
## Title
Parse Delimiter-Separated Answer Structures
## Description
Identify common structural markers in retrieved documents that separate questions from their corresponding answers, enabling precise extraction.
## Content
Retrieved contexts from quizzes, datasets, or user-generated content often use consistent formatting patterns (e.g., pipes `|`, colons, dashes, or explicit labels) to distinguish queries from responses. Once a matching question is located, look immediately before or after these markers to isolate the answer. This approach minimizes noise and prevents misattribution in multi-part texts.

# Success Memory Item 3
## Title
Prioritize Verbatim Context Over Semantic Synthesis
## Description
Favor direct extraction from exact matches rather than synthesizing information across multiple partial results when the prompt is highly specific.
## Content
Highly specific or uniquely phrased questions often appear verbatim in niche sources. When such a match is present in the context, treat it as a definitive reference point. Extract the associated answer directly from that location instead of aggregating or inferring from broader semantic matches, which reduces error rates and computational overhead.
