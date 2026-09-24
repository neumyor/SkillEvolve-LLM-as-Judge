# Failure Cause Item 1
## Title
Misinterpretation of Query Intent via Context Bias
## Description
The agent allowed the retrieved context (which heavily featured a specific 1993 movie) to bias its interpretation of a short, ambiguous query, leading it to describe the movie instead of identifying the originating franchise.
## Content
The query "Yabba Dabba Do!" is a famous catchphrase. The retrieved context included many results for the 1993 TV movie "I Yabba-Dabba Do!". The agent reasoned that since the context highlighted the movie, the question must be about the movie. It failed to consider that the phrase originates from "The Flintstones" and that the question likely asks for the source show. The agent should have prioritized the most fundamental entity associated with the phrase over specific derivative titles present in the search results.

# Failure Memory Item 1
## Title
Identify Originating Entity for Catchphrases
## Description
For queries consisting of famous catchphrases or slogans, prioritize the originating media property (show/movie) over specific episodes, spinoffs, or derivative works.
## Content
When the query is a well-known phrase (e.g., "Yabba Dabba Do!"), the correct answer is typically the primary franchise (e.g., "The Flintstones"). Even if the search results are dominated by specific derivative content (e.g., a 1993 TV movie), the agent should recognize the phrase's origin and output the main entity name rather than a description of the derivative work.

# Failure Memory Item 2
## Title
Concise Entity Answers for Trivia Queries
## Description
For short trivia-style queries, prefer concise entity names over descriptive sentences.
## Content
The agent generated a long descriptive answer ("A 1993 animated television film based on The Flintstones") when a simple entity name ("The Flintstones") was appropriate. In SearchQA tasks, short queries often expect short, precise entity answers. Agents should avoid adding extra qualifiers (year, type) unless explicitly requested or necessary for disambiguation.

ACTION: TASK_COMPLETE
