# Failure Cause Item 1
## Title
Span-boundary error: agent trimmed the answer span instead of using the exact context text

## Description
The agent correctly identified the relevant passage containing the answer but extracted only "eucalyptus" instead of the full answer span "a eucalyptus tree" as stated in the context. This is a span-selection error where the agent preferred a minimal core entity name over the complete phrase provided by the source text.

## Content
The first passage in the retrieved context explicitly states: "Flowering plants range in size from the duckweed at 1/50" long to this Australian gum tree that reaches 300 feet in height | a eucalyptus tree." The agent's reasoning shows it found this passage and recognized "a eucalyptus tree" as the answer, but then decided to output just "eucalyptus" by stripping the article "a" and the word "tree". The EM score was 0.0 because "eucalyptus" does not exactly match "a eucalyptus tree", while F1 was 0.667 indicating partial overlap. The fix requires extracting the full answer span verbatim from the context rather than attempting to minimize or normalize the answer.

# Failure Memory Item 1
## Title
Extract the exact answer span from the context without trimming articles or descriptors

## Description
When the retrieved context contains a direct answer to the question, the model should extract the complete answer span as it appears in the text, including articles (a, an, the) and any accompanying nouns or descriptors. Trimming these elements to produce a "minimal" answer often causes exact-match failures even when the core entity is correct.

## Content
In this case, the context clearly states "a eucalyptus tree" as the answer. The agent correctly identified the entity but incorrectly assumed that "eucalyptus" alone would suffice. For tasks requiring exact span extraction, the safest strategy is to copy the full phrase that directly answers the question from the source text, preserving all words that are part of the answer span. This applies particularly to Jeopardy-style questions where the answer format is fixed and includes articles.

# Failure Memory Item 2
## Title
When context provides a direct Q&A pair, use it verbatim as the answer

## Description
If the retrieved context contains a question-answer pair (such as Jeopardy clues with their answers), the answer portion should be taken exactly as written without modification, normalization, or shortening.

## Content
The first document in the context is a Jeopardy dataset entry with the format "QUESTION | ANSWER". The answer field contains "a eucalyptus tree" which is the complete expected answer. Agents should recognize this pattern and treat the entire answer field as the target span, rather than attempting to parse out what they consider the "core" entity. This generalizes to any structured Q&A format where the answer is explicitly provided in the context.

ACTION: TASK_COMPLETE
