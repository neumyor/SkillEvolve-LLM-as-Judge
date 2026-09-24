# Failure Cause Item 1
## Title
Span-Boundary Over-Inclusion with Redundant Nouns
## Description
The agent extracted "Bear Market" instead of "bear" because it took the full phrase following the question stem in the source text, failing to exclude the word "Market" which was already present in the question ("this market").
## Content
In the retrieved context, the flashcard reads: "YOU CAN GET MAULED WHEN IT'S THIS MARKET THAT FEATURES A LENGTHY PERIOD OF PRICE DROPS, BEAR MARKET." The agent correctly identified this passage but committed to the full two-word span "Bear Market". Since the question explicitly asks about "this market," the expected answer is the specific modifier "bear" (or "the bear"), not the repeated compound noun. This resulted in an F1 of 0.667 despite correct entity identification (sub_EM=1.0). The fix was to trim the answer span to the core term "bear".

# Failure Memory Item 1
## Title
Exclude Question Nouns from Answer Spans
## Description
When a question contains a generic noun (e.g., "this market", "what type of animal"), the answer span should typically exclude that noun and only include the distinguishing modifier or specific term.
## Content
Questions often frame the answer within a category already mentioned in the prompt. For example, "What kind of market..." expects "bear" rather than "bear market". Agents should parse the question to identify nouns that serve as categories and ensure the extracted answer span does not redundantly repeat them, focusing instead on the precise differentiating term.

# Failure Memory Item 2
## Title
Flashcard Context Answer Extraction
## Description
In flashcard or Q&A style snippets where the answer immediately follows the question text, verify whether the trailing word is the answer itself or a restatement of the question's subject.
## Content
Source texts like study flashcards often format content as "Question, Answer." or "Question, Answer Category." Agents must distinguish between the core answer and appended categorical labels. If the question already specifies the category (e.g., "this market"), the answer is likely just the specific identifier (e.g., "bear"), not the full label (e.g., "bear market"). Always prefer the minimal span that fully satisfies the query.

ACTION: TASK_COMPLETE
