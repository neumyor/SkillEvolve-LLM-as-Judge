# Question Answering Skill

## Core Principles
- **Pointer & Implicit Target Resolution**: Map demonstratives ("this...", "that...") and descriptive clauses directly to their canonical entities in the provided text.

## Execution Workflow
1. **Parse & Identify**: Strip away narrative framing. Identify core descriptors, constraints, and implicit target slots. Recognize trivia-style or fragmented prompts as requests for a specific entity.
2. **Scan & Match**: Locate exact keywords or semantic equivalents in the context. Cross-reference aliases, nicknames, or colloquialisms with explicit definitions in the passages.
3. **Extract & Verify**: Pull the exact entity. Ensure it matches the implied granularity. If multiple sources appear, use overlapping information to lock the exact target term before formatting.
4. **Format Output**: Provide brief step-by-step reasoning outside tags. Place the final, concise answer strictly inside `<answer>...</answer>` tags.

## Handling Clues, Definitions, and Trivia
When the question is a descriptive clue, definition, or trivia statement (often lacking a direct question word):
- Identify the core concept or entity being defined. Output ONLY the precise target term. Do not add descriptors, categories, or explanatory clauses.
- Match expected granularity strictly: if the clue implies a surname, abbreviation, or single word, provide only that (e.g., `Brutus` not `Marcus Junius Brutus`, `Arthur` not `Chester A. Arthur`).
- Prefer the general category or term over specific examples found in the text (e.g., answer `Anti-perspirant` for a description of sweat-reducing agents, not `Witch hazel`).
- Maintain grammatical number: if the clue uses singular phrasing ("this is the term"), output the singular form (`an insulator` not `Insulators`).
- Strictly enforce all noun/adjective constraints in the prompt (e.g., "fruit crop" excludes non-fruits like coffee).
- If multiple candidates appear in the context, select the primary/most direct match and omit alternatives or parenthetical additions.
- Treat declarative statements as identification prompts, not True/False questions. Keep the final answer strictly concise.
