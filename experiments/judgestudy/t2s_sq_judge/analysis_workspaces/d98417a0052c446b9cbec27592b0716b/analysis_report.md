# Failure Cause Item 1
## Title
Over-specified answer span due to external knowledge bias
## Description
The agent correctly identified that the Montgolfier chair's back is shaped like a balloon, but output "hot air balloon" instead of the gold-standard "a balloon" (or simply "balloon"). The context explicitly states "the Montgolfier chair featuring a wooden splat shaped as a hot air balloon," which supports both "balloon" and "hot air balloon." However, the gold answer uses the shorter form "a balloon." The agent committed to the more verbose "hot air balloon" likely because it felt more precise or complete, not realizing that the evaluation metric (EM) requires exact string match. This is a span-boundary/verbosity problem: the agent chose a longer, semantically equivalent span over the shorter canonical one.
## Content
The agent's reasoning was sound in identifying the correct entity (balloon/hot air balloon), but it failed to recognize that the expected answer format prefers the minimal span "balloon" over "hot air balloon." In trivia QA tasks with EM scoring, the shortest unambiguous answer supported by the context is typically preferred. The agent should have chosen "balloon" as it is directly supported by phrases like "Balloon Chair," "shaped as a hot air balloon," and matches the gold answer granularity.

# Failure Memory Item 1
## Title
Prefer minimal answer spans when multiple equivalent options exist
## Description
When the context supports multiple phrasings of an answer (e.g., "balloon" vs. "hot air balloon"), choose the shortest span that is directly supported by the text. Over-specification leads to EM failures even when the semantic content is correct.
## Content
In SearchQA-style tasks with exact-match scoring, the answer must match the gold string exactly. If the context mentions both "balloon" and "hot air balloon," and the gold is "a balloon," the agent should extract the minimal noun phrase "balloon" rather than expanding it. Always check whether a shorter variant exists in the context before committing to a longer one.

# Failure Memory Item 2
## Title
Distinguish between Jeopardy clue structure and direct factual statements
## Description
Jeopardy clues often use incomplete sentences ("shaped like one of these") that require the contestant to supply the missing term. Agents should not treat the clue itself as containing the answer; instead, they must infer the answer from supporting context passages that explicitly state the relationship.
## Content
The agent correctly noted that the Jeopardy clue "The Montgolfier is a Louis XVI chair created by Georges Jacob with a back shaped like one of these" does not contain the answer. It then used other passages (e.g., "shaped as a hot air balloon") to infer the answer. This is the correct approach. However, the agent should also be aware that Jeopardy answers are typically single words or short phrases, so the inferred answer should be concise.

ACTION: TASK_COMPLETE
