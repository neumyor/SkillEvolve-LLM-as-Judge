# SearchQA Question Answering

## Read the evidence

- Read the retrieved passages before answering; the answer must come from the
  context, not from memory alone.
- Several passages may mention the same entity; prefer the passage whose
  wording matches the question's distinctive terms (names, dates, titles).

## Answer format

- Think step by step, then put the final answer inside
  `<answer>...</answer>` tags.
- Keep the answer concise — typically a few words or a short phrase.
- Do not repeat the question and do not add explanations inside the tags.
