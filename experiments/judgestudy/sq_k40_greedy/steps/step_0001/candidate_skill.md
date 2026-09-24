# Question Answering Skill

## Core Principles
- **Recognize Clue-Based Formats**: Treat questions as Jeopardy-style trivia, definitions, or fill-in-the-blank clues. Map descriptive phrases directly to the target entity (person, place, term, work).
- **Direct Keyword Matching & Scanning**: Prioritize scanning document titles, snippets, and paragraphs for exact or near-exact keyword matches. Quickly locate supporting sentences using unique identifiers (dates, numbers, quotes, proper nouns) before reading deeply.
- **Noise & Redundancy Filtering**: Contexts often contain overlapping sources or metadata. Rapidly isolate the single passage that explicitly defines or links to the clue, disregarding tangential details.
- **Strict Formatting**: Always wrap the final answer in `<answer>...</answer>` tags. Keep the content inside strictly to the answer itself (typically a few words or a short phrase), omitting introductory phrases or reasoning.
- **Constraint Verification**: Cross-check the extracted entity against specific constraints in the question (e.g., years, roles, locations) using the context to ensure accuracy.

## Handling Statement or Fragment Questions
Many questions are phrased as statements or incomplete phrases (common in trivia/Jeopardy). Treat these as requests to identify the specific subject or entity being described. Do not respond with "True"/"False", nor with a generic category or descriptive phrase. Instead, extract the exact proper noun or term that fits the blank or completes the thought.

## Answer Precision and Conciseness
Answers must be stripped to their core identifier.
- Omit articles, descriptors, and explanatory phrases (e.g., output "Genet" not "Jean Genet", "C" not "Vitamin C", "U2" not "A U2 tribute band").
- If the context uses a surname, nickname, or single letter, prefer that form.
- Do not add titles, roles, or units unless they are part of the official name.

## Distractor Management
Contexts often contain multiple names or related terms. Focus strictly on the entity that directly satisfies the question's query. Ignore tangential mentions, secondary figures, or unrelated topics that appear in other paragraphs. When in doubt, choose the most frequently referenced or prominently featured entity in the immediate vicinity of the clue.
