# Failure Cause Item 1
## Title
Over-specification of Entity Identity
## Description
The agent correctly identified the target entity 'U2' but included the descriptive modifier 'tribute band' in the answer span, resulting in 'U2 tribute band' instead of the concise 'U2'.
## Content
The retrieved context repeatedly defines 'Achtung Babies' as a 'U2 Tribute Band'. The agent reasoned that this full definition was the answer. However, for the query 'Rock group Achtung Babies', the expected answer is the specific rock group being referenced ('U2'), not the full descriptive label. The agent failed to strip the category 'tribute band' from the entity name, leading to a mismatch with the gold answer 'U2'.

# Failure Memory Item 1
## Title
Extract Core Entity, Not Descriptive Phrase
## Description
When the context describes an entity as '[Entity] [Category]' (e.g., 'U2 Tribute Band'), the answer to a question asking for the entity should often be just '[Entity]', excluding the category.
## Content
In many QA tasks, especially those involving bands or organizations, the 'type' (tribute band, record label, etc.) is metadata. If the question asks for the group or entity, extract the proper noun name only. Do not include the common noun classifier in the final answer span unless the question explicitly asks for the type.

# Failure Memory Item 2
## Title
Handle Ambiguous Noun Phrases as Entity Queries
## Description
Questions formatted as 'Noun Phrase' (e.g., 'Rock group Achtung Babies') are often entity identification queries seeking the primary associated entity.
## Content
When the input is a noun phrase rather than a full question sentence, treat it as a request to identify the main entity associated with that phrase. If the context links the phrase to a well-known entity (e.g., Achtung Babies -> U2), prioritize extracting that well-known entity name as the answer.

ACTION: TASK_COMPLETE
