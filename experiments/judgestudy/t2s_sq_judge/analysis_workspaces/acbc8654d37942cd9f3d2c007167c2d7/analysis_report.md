# Failure Cause Item 1
## Title
Misinterpretation of Question Intent: Answering "what is the gravy called" instead of "what are the innards"
## Description
The agent misread the question's syntactic structure. The question "pass the gravy made with these turkey innards including the heart & gizzard" is a Jeopardy-style clue where the answer is the entity described (the innards themselves), not the dish name. The agent interpreted it as asking for the name of the gravy ("Giblet Gravy") rather than identifying the innards ("Giblets").
## Content
The agent's reasoning explicitly states: "The user wants to know what the 'gravy made with these turkey innards...' is called... So the gravy is 'Giblet Gravy'." This reflects a failure to recognize that "these turkey innards" is the target of the query, and the phrase "made with..." is descriptive context. The correct answer is the name of the innards collectively, which the context defines as "giblets" (e.g., "[DOC] ...the giblets (that is, the heart and the gizzards)...").

# Failure Memory Item 1
## Title
Jeopardy-Style Clue Parsing: Identify the Described Entity, Not the Container
## Description
When a question follows the pattern "X made with Y," determine whether the question asks for X or Y. In Jeopardy-style clues, the answer is typically the specific entity being defined or described by the surrounding context, not the broader category or container.
## Content
In this case, "gravy made with [innards]" describes the innards. The agent incorrectly answered with the gravy name. Future agents should parse such questions by asking: "What is being defined here?" If the question says "gravy made with Z," and Z is the unknown, the answer is Z, not the gravy.

# Failure Memory Item 2
## Title
Span Selection: Extract the Defined Term, Not the Recipe Name
## Description
When the context provides a definition like "giblets (the turkey heart, liver, gizzard and neck)," the answer span should be the term being defined ("giblets"), not the title of a document about a recipe using those terms ("Giblet Gravy").
## Content
The agent latched onto multiple document titles containing "Giblet Gravy" and selected that as the answer. However, the question asks for the identity of the innards, which the context explicitly labels as "giblets." Agents should prioritize extracting the term that directly matches the description in the question over matching document titles.

ACTION: TASK_COMPLETE
