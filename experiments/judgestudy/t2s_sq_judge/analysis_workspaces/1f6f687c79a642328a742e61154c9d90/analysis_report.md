# Failure Cause Item 1
## Title
Question-Type Misinterpretation: Bare Phrase Questions Seek Entities, Not Definitions
## Description
The agent treated the bare phrase question "Tippecanoe and Tyler too" as a "what is this?" query asking for a definition, producing a descriptive sentence. In SearchQA, bare phrases typically ask for the primary entity associated with that phrase — not a description of what it is.
## Content
The agent had all the correct information in context (the slogan was for William Henry Harrison and John Tyler) but committed to the wrong answer type. It output "A campaign slogan for William Henry Harrison and John Tyler in the 1840 U.S. presidential election" instead of extracting the key entity "William Henry Harrison." The agent's reasoning explicitly states "I should answer what it is" and "This implies asking for its definition or identity," revealing a systematic misinterpretation of the question format. The context clearly identifies Harrison as the central figure (presidential candidate, hero of Tippecanoe), making him the correct entity extraction target.

# Failure Memory Item 1
## Title
Recognize Question Format Signals for Answer Granularity
## Description
Bare phrase questions in SearchQA typically ask for the key entity associated with that phrase, not a definition or description. Agents should look for signals: if the question is just a name/title/phrase without interrogative words, the expected answer is usually a specific named entity.
## Content
When the question is a standalone phrase (e.g., "Tippecanoe and Tyler too", "Battle of Gettysburg", "Mona Lisa"), the task is entity identification — who/what is primarily associated with this phrase? The agent should scan context for the main person, place, or thing linked to the phrase, not produce a definitional sentence. Interrogative questions ("What is...", "Who wrote...") may legitimately expect descriptions, but bare phrases signal entity extraction.

# Failure Memory Item 2
## Title
Prefer Named Entity Extraction Over Descriptive Sentences
## Description
When context contains a clear named entity that answers the question, prefer extracting that exact entity rather than producing a paraphrased or descriptive answer. This aligns with SearchQA's evaluation metrics which favor exact entity matches.
## Content
Even when an agent correctly identifies the relevant information, producing a full sentence ("A campaign slogan for...") can fail EM/F1 scoring against gold entity answers. The agent should identify the most specific, minimal span that answers the question — in this case, "William Henry Harrison" — rather than expanding into a descriptive clause. This applies broadly: when context says "X was Y" or "Y is associated with X," extract X if the question points to the entity.

ACTION: TASK_COMPLETE
