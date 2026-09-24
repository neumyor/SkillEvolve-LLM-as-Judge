# Failure Cause Item 1
## Title
Span-format mismatch on acronym expansion: hyphenated vs. non-hyphenated form
## Description
The agent correctly identified that PIP expands to "Picture in Picture" but selected the hyphenated variant "Picture-in-picture" from the context, while the gold answer uses the non-hyphenated form "Picture in Picture". This caused an exact-match failure (EM=0.0) despite the agent selecting the correct entity.
## Content
The question "If your TV has PIP, it has this feature" asks for the full name of the PIP acronym. The agent's reasoning correctly traced PIP → Picture-in-Picture using passages like "[DOC] How to Set Up the PIP on an Insignia TV | Techwalla.com [PAR] Picture-in-picture (PIP) is a popular feature...". However, the gold answer is "Picture in Picture" (no hyphens). Multiple other passages in the context use the non-hyphenated form: "[DOC] How do I use picture in picture (PIP) on my LED TV? - Samsung [PAR]" and "[DOC] Picture in Picture / PIP / POP - VIZIO Support [PAR]". The agent committed to the hyphenated variant without considering that the dataset's canonical form may differ. This is a span-boundary/formatting problem, not a wrong-entity error. The fix was to output "Picture in Picture" matching the non-hyphenated variant found in the Samsung and VIZIO support passages.

# Failure Memory Item 1
## Title
Prefer canonical/non-hyphenated forms when acronym expansions have variant spellings
## Description
When answering acronym-expansion questions, if the context contains multiple variants (e.g., "Picture-in-Picture" vs. "Picture in Picture"), select the form that appears most canonically or consistently across authoritative sources in the retrieved context, and be aware that dataset gold answers often use the non-hyphenated or lowercase variant.
## Content
Acronym expansion questions are sensitive to exact string matching. Hyphens, capitalization, and spacing differences between variants (e.g., "Picture-in-Picture" vs. "Picture in Picture") can cause EM=0 even when the entity is correct. To mitigate: (1) scan all passages for the acronym definition and note which variant appears most frequently; (2) prefer the variant used by major manufacturers or official documentation in the context; (3) avoid adding hyphens unless they are the dominant form in the source material.

# Failure Memory Item 2
## Title
Distinguish span-format errors from entity errors in near-miss diagnoses
## Description
When an agent's answer overlaps the correct entity but differs in formatting (hyphens, capitalization, spacing), diagnose it as a span-selection/formatting issue rather than a wrong-entity error. This changes the remediation strategy from finding a new entity to normalizing the existing one.
## Content
A near-miss where the answer is semantically correct but fails exact match due to formatting (e.g., "Picture-in-picture" vs. "Picture in Picture") should be diagnosed as a span-boundary problem. The agent did not choose the wrong entity — it chose the right concept but with incorrect orthography. Remediation involves selecting the exact string form present in the context that matches the expected format, not searching for a different entity. This distinction prevents misdiagnosing retrieval failures as reasoning failures.

ACTION: TASK_COMPLETE
