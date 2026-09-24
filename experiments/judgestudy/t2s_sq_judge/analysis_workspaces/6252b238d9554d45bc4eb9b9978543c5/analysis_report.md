# Failure Cause Item 1
## Title
Over-reliance on Exact Title Matches Over Partial Matches
## Description
The agent prioritized entities with an exact title match to the query fragment ("On My Mind") while ignoring entries where the query is a suffix of a longer, well-known title (e.g., "Georgia on my mind").
## Content
When the query is a short phrase like "...on my mind", the agent should consider that it may be a trailing fragment of a longer entity name. In this case, the context contained "Georgia on my mind," a famous song title. The agent incorrectly filtered this out in favor of Ellie Goulding's song titled exactly "On My Mind" simply because it appeared first. The agent failed to evaluate the semantic plausibility of "Georgia" as the answer to "...on my mind" (i.e., filling in the blank or identifying the subject of the phrase).

# Failure Memory Item 1
## Title
Evaluate Partial Title Matches for Fragment Queries
## Description
For short or fragmented queries, consider that the answer may be the entity *modifying* or *preceding* the query phrase, not just the entity sharing the exact phrase as its title.
## Content
When processing queries like "...X" or "X...", check if any retrieved documents contain longer titles ending in X (e.g., "Y on my mind"). The correct answer might be Y, not the entity whose title is exactly "X". Agents should weigh the fame/cultural relevance of the full phrase against the exact match bias.

# Failure Memory Item 2
## Title
Avoid Recency Bias When Multiple Plausible Entities Exist
## Description
Do not automatically select the first matching entity if other entities in the context are equally or more semantically appropriate for the specific query phrasing.
## Content
The agent selected Ellie Goulding primarily because her documents appeared first in the retrieval list. However, the presence of "Georgia on my mind" (a classic standard) makes "Georgia" a highly plausible answer to the fragment "...on my mind". Agents must adjudicate between candidates based on semantic fit to the query structure, not just document order.

ACTION: TASK_COMPLETE
