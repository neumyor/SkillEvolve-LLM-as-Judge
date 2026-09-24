# Failure Cause Item 1
## Title
Misattribution of "first and foremost" quote to wrong Mississippi senator
## Description
The agent saw the phrase "first and foremost" in a passage quoting Roger Wicker ("Of course, first and foremost we have a job to do, said Wicker") and incorrectly mapped this to the question's clue about being "first & foremost a senator from Mississippi." It ignored that Trent Lott is explicitly identified in the context as a former Senate GOP Leader from Mississippi (R-MS), which directly matches the question's description of a GOP leader who is a senator from Mississippi.
## Content
The agent correctly identified both Wicker and Lott as Mississippi senators but failed to recognize that Lott held the GOP leadership position referenced in the question ("being GOP leader is important"). The agent latched onto the superficial keyword match of "first and foremost" with Wicker, despite Wicker not being a GOP leader at the time of the documents, while Lott's title "NPR : Sen. Trent Lott (R-MS) Gives Up Senate GOP Leader's Post" directly supports him as the answer.

# Failure Memory Item 1
## Title
Prioritize role/position matches over keyword surface matches
## Description
When answering entity identification questions, prioritize passages that confirm the subject's role or position (e.g., "GOP Leader," "Senate Majority Leader") over superficial keyword overlaps (e.g., "first and foremost"). A keyword match on a descriptive phrase should not override a stronger match on the core identifying attribute (the person's actual title/role).
## Content
In this case, the question asks for a "GOP leader" who is a "senator from Mississippi." The agent found a "first and foremost" quote from Wicker but ignored that Lott was explicitly a Senate GOP Leader from Mississippi. The correct approach is to filter candidates by the primary role constraint first, then use secondary clues (like quotes) to disambiguate.

# Failure Memory Item 2
## Title
Verify candidate's role against question constraints before committing
## Description
Before finalizing an answer, verify that the candidate satisfies all key constraints in the question, especially role/title descriptors. If a candidate does not hold the specified role (e.g., GOP leader), they should be eliminated even if other clues (like state or partial phrases) match.
## Content
Roger Wicker was not a GOP leader in the context timeframe (he became Minority Whip later), while Trent Lott was explicitly a former Senate GOP Leader. The agent should have eliminated Wicker based on the "GOP leader" constraint and selected Lott, who fits both the role and state constraints.

ACTION: TASK_COMPLETE
