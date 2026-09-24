# Failure Cause Item 1
## Title
Over-extraction of descriptive span instead of precise entity name

## Description
The agent produced a long descriptive phrase ("A census-designated place in Baltimore County, Maryland") when the question "Timonium" called for the specific entity name identified in the context. The first passage explicitly states "Lutherville-Timonium" as the full name, which is the most direct answer. The agent trusted the definitional content but failed to extract the minimal, precise entity identifier.

## Content
The agent read the Wikipedia passage correctly but committed to outputting a full definition rather than the entity name itself. When a question asks for an entity (e.g., "Timonium"), the context often provides a canonical name or label — here, "Lutherville-Timonium" — that should be extracted directly. The agent's verbose answer, while factually supported, does not match the expected answer granularity. The fix was to replace the descriptive phrase with the exact entity name "Lutherville-Timonium" as stated in the source passage.

# Failure Memory Item 1
## Title
Prefer precise entity names over descriptive definitions

## Description
When answering entity questions, extract the exact name or label given in the context rather than a paraphrased description. If the context says "X is Y," and the question asks for X, the answer should be the canonical identifier (Y) if it's a short name, not a sentence describing what Y is.

## Content
In SearchQA-style tasks, questions are typically single entities. The retrieved context usually contains a direct identification (e.g., "Lutherville-Timonium was a census-designated place..."). The correct behavior is to extract the named entity itself ("Lutherville-Timonium") rather than its type or description ("census-designated place in Baltimore County, Maryland"). This applies whenever the context provides a clear proper noun or label that directly answers the question.

# Failure Memory Item 2
## Title
Minimize answer span to the smallest supported unit

## Description
After identifying the relevant passage, extract the shortest text span that fully answers the question. Avoid adding articles, prepositions, or contextual qualifiers unless they are part of the entity name itself.

## Content
The agent included "A" at the beginning and added "in Baltimore County, Maryland" as extra location detail. While these are true, they expand the answer beyond what is needed. A good heuristic: if the question is a single word/entity, the answer should also be a single concise term or name found verbatim in the context. Only include additional words if the context requires them to disambiguate or if the gold-standard answer format demands it.

ACTION: TASK_COMPLETE
