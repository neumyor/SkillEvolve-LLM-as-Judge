# Failure Cause Item 1
## Title
Misinterpretation of Ambiguous Trivia Prompt as Genre Identification
## Description
The agent interpreted the ambiguous prompt "A 1961 classic: 'West Side Story'" as a request to identify the genre or medium (e.g., "musical film") rather than the source material. It relied on the first sentence of the primary Wikipedia passage ("West Side Story is a 1961 American romantic musical drama film...") and ignored other passages that explicitly linked the work to its literary predecessor.
## Content
The question format "A [Year] classic: '[Title]'" in trivia datasets often asks for the origin, director, or key fact associated with the title. The agent failed to consider that the expected answer might be the source story. While it saw passages stating it was an "adaptation of the classic romantic tragedy, 'Romeo and Juliet'" and a "loose re-telling of Shakespeare's Romeo and Juliet", it did not prioritize this information over the generic definition. The agent committed to "musical film" because it assumed the question asked "What is West Side Story?" in terms of type, missing the specific relational intent targeted by the gold answer.

# Failure Memory Item 1
## Title
Prioritize Specific Relational Facts Over Generic Definitions in Ambiguous Prompts
## Description
When faced with an ambiguous short-form question (e.g., "A 1961 classic: 'X'"), agents should look for specific relationships (source, director, award) mentioned in the context rather than defaulting to generic definitions (genre, medium). If multiple passages provide different types of facts, the one that answers a specific "who/what based on" relationship is often more likely to be the target than a broad category label.
## Content
In this case, the context contained both a generic definition ("romantic musical drama film") and a specific relational fact ("adaptation of Romeo and Juliet"). The agent chose the generic definition. A better strategy is to check if the question style implies a specific attribute (like origin) and select the most specific, non-trivial fact supported by the context. Vague answers like "film" or "musical" are often incorrect in trivia contexts where a specific entity name is expected.

# Failure Memory Item 2
## Title
Avoid Guessing Intent Without Evidence; Use Context Clues
## Description
Agents should not guess the intent of a truncated or ambiguous question based on common patterns alone. Instead, they should scan all retrieved passages for strong signals. If multiple passages highlight a specific connection (e.g., "based on Romeo and Juliet"), this consistency suggests that connection is the key fact, even if the question phrasing is unclear.
## Content
The agent considered "Romeo and Juliet" as a possibility but dismissed it in favor of "musical film". It failed to recognize that the repeated mention of the Shakespearean origin across multiple independent sources (IMDb, Greatest Films, etc.) was a stronger signal for the intended answer than the single-sentence genre definition. Agents should weigh the frequency and specificity of supporting evidence when adjudicating between possible interpretations of an ambiguous query.

ACTION: TASK_COMPLETE
