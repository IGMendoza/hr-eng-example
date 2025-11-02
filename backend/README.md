to run, instead of

    python -m uvicorn .main:app --reload

do:

    python -m uvicorn backend.main:app --reload

## LLM usage I found kind of useful (ChaptGPT)

### Task: Pathfinding
- I implemented Dijkstra's algo. Is there a more efficient way in python?
    
    - got heapq library recommended
- If you'd do a code review, how is my code?
    - just a sanity check for:
        - separation of concern is handled
        - determinism
        - extendibility
        - testing
    - suggested further improvement i got from its review (already helping for the <b>State & Validation</b> task):
        - usage of 201 for creates
        - 422 for validation errors
    - mostly obvious stuff but I would save these checks for when deploying to prod

### Task: Scheduler
- given the code, what do you think this task should encompass - without code
    - got a step-by-step logic flow i could inspect and compare against my own to see where the LLM failed to understand something or where it was able to identify a step/edge case that I failed to consider.
- give me testing curls for edge cases
    - validated correct logic for tie breaking
    - regular curls on windows are weird - didn't spend too much time dealing with powershell curls thankfully

### Task: State & Validation
- when asking to rate my code and provide feedback, ChatGPT would "give me this task for free" by suggesting appropriate 4xx codes - which i'd then go and validate on google