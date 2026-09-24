# Failure Cause Item 1
## Title
Span-boundary error: included descriptor word "Network" as part of the answer entity

## Description
The agent identified the correct core entity ("SCTV") but incorrectly extended the answer span to include "Network," producing "SCTV Network" instead of "SCTV." The question asks for the name of the comic "network" — the word "network" appears in quotation marks as a descriptor/clue term, not as part of the entity's proper name. The agent saw "SCTV Network" in the IMDb awards listing and treated the entire phrase as the answer without recognizing that "Network" was either part of the formal Emmy category title or a redundant descriptor.

## Content
The agent's reasoning explicitly considered both "SCTV Network" and "Second City Television" as candidates and settled on "SCTV Network" because the IMDb passage listed it that way. However, the gold answer is "SCTV" — the standard short form of the show's title. The Wikipedia passage defines "SCTV (Second City Television)" as the show name, and the J! Archive trivia clue uses "network" as a generic descriptor in quotes. The agent failed to recognize that the quoted word "network" in the question signals a category, not a component of the answer string. This is a classic span-boundary problem where the agent trusted a longer surface-form match over the minimal correct entity name.

# Failure Memory Item 1
## Title
Distinguish entity names from formatting/descriptor words in award listings

## Description
When extracting answers from award or credits listings (e.g., IMDb), the formal entry may include extra words like "Network," "TV Series," or "Show" that are part of the database categorization rather than the entity's actual name. The correct answer span should be the minimal entity name, not the full listing label.

## Content
In this case, "SCTV Network" appeared in the IMDb awards context, but the entity is simply "SCTV." Similar patterns occur with entries like "Star Trek: The Next Generation (TV Series)" where the answer is "Star Trek: The Next Generation," not the parenthetical suffix. Always check whether appended words are descriptive metadata versus part of the canonical name.

# Failure Memory Item 2
## Title
Quoted terms in questions are typically descriptors, not answer components

## Description
When a question places a word in quotation marks (e.g., 'this comic "network"'), the quoted word usually functions as a hint or category descriptor, not as part of the expected answer string. Agents should treat such quoted terms as semantic guidance rather than literal text to include in the answer span.

## Content
The question "Andrea Martin & Martin Short were among winners in 1983 for writing for this comic 'network'" uses "network" in quotes to indicate the type of entity being asked about (a TV network/show). The answer is the name of that entity ("SCTV"), not "SCTV Network." This pattern appears frequently in Jeopardy-style clues and trivia questions where quotation marks signal a definitional role rather than a verbatim component.

ACTION: TASK_COMPLETE
