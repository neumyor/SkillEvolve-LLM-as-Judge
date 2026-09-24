# Success Memory Item 1
## Title
Parse Conditional Substitution Logic
## Description
Decompose workaround-style prompts into their core variable triad (known inputs + action → unknown target) to guide targeted context scanning.
## Content
When a question frames a scenario as "use X with Y if you lack Z," isolate X and Y as search anchors. Filter retrieved documents for instructional sentences that explicitly pair those anchors with a missing noun. This transforms open-ended trivia into a structured pattern-matching task, reducing ambiguity and focusing retrieval on substitution hacks rather than general definitions.

# Success Memory Item 2
## Title
Anchor to Verbatim Instructional Phrasing
## Description
Prioritize exact semantic matches between the prompt's scenario and direct how-to statements in the context over inferred or paraphrased information.
## Content
Life-hack and trivia queries typically originate from specific listicles or guides. Locate the sentence in the context that mirrors the prompt's structure and intent. The correct answer is usually the immediate noun completing that conditional clause. Relying on verbatim alignment prevents hallucination and ensures the extracted term matches the source material's exact terminology.

# Success Memory Item 3
## Title
Extract and Isolate the Core Entity
## Description
Strip all surrounding explanation, synonyms, or modifiers from the matched sentence to return only the precise lexical item requested.
## Content
Once the anchoring sentence is identified, extract the single noun or short phrase that fulfills the blank. Discard alternatives, brand names, or descriptive adjectives unless explicitly required. Wrap only this isolated term in the mandated tags to guarantee exact-match scoring and comply with strict output constraints.
