# Success Memory Item 1
## Title
Query Structure Recognition for Trivia-Style Prompts
## Description
Identify when a question uses a narrative, clue-like, or fill-in-the-blank structure typical of trivia datasets, which signals a single-entity target rather than an explanatory response.
## Content
When prompts follow patterns like "For [duration] [Subject] performed [Action] as this [Role]...", treat the query as a direct pointer to a proper noun. Shift focus from synthesizing background information to locating the exact entity name that grammatically completes the implied blank.

# Success Memory Item 2
## Contextual Anchor Extraction
## Description
Leverage high-signal snippets (e.g., database exports, quiz archives, or metadata-rich sources) that mirror the prompt's syntax to isolate the precise answer string.
## Content
If retrieved documents contain structured fragments that closely replicate the question's phrasing, align the prompt with those lines. Extract the corresponding answer token directly from the matched fragment rather than deriving it from longer biographical or descriptive paragraphs, reducing ambiguity and preserving exact naming conventions.

# Success Memory Item 3
## Syntactic Answer Pruning
## Description
Trim extracted entities to the minimal grammatical unit required to satisfy the prompt's structural cue, avoiding redundant descriptors.
## Content
After identifying the target entity, evaluate whether modifiers (e.g., occupational titles, brand suffixes) are necessary for correctness. Default to the core identifier alone when the prompt already establishes the category (e.g., "manicurist"), ensuring the final output is concise and directly responsive to the query's framing.
