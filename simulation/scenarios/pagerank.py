"""PageRank Case Study — Larry Page's insight about academic citation as web ranking.

This is a well-documented case where:
1. Page was a PhD student studying web link structure (deep immersion)
2. He noticed academic citation parallels with web links (cross-domain collision)
3. Existing search engines ranked by keyword matching (tension: search quality was poor)
4. Multiple failed/partial approaches existed (keyword density, meta tags, HITS algorithm)
5. The insight crystallized: treat links as votes, weighted by the voter's importance (recursive)
6. This was non-obvious because it required recursive/eigenvector thinking

Sources: Page & Brin's original paper, Stanford interviews, "In the Plex" by Steven Levy
"""

def build_pagerank_scenario():
    """Build the PageRank case study as a sequence of temporal events.
    
    Richer scenario that drives the full SIA pipeline:
    - Tensions with shared keywords link to seeds
    - Seeds share tags so clustering detects recurrence
    - Resource pressure escalates over time
    - Near-misses and contradictions build pressure
    """
    events = []
    
    # === PHASE 1: Deep immersion in web structure (Cycles 1-4) ===
    events.append({"cycle": 1, "type": "tension", "data": {
        "title": "Web search ranking quality is terrible",
        "description": "Existing search engines return irrelevant results. Keyword matching ranking is easily gamed by spammers.",
        "stake_weight": 1.5
    }})
    
    events.append({"cycle": 2, "type": "tension", "data": {
        "title": "How to measure page importance for ranking objectively",
        "description": "Need a way to rank web pages that is resistant to manipulation and reflects genuine authority.",
        "stake_weight": 2.0
    }})
    
    events.append({"cycle": 3, "type": "tension", "data": {
        "title": "Keyword frequency ranking is gameable",
        "description": "Ranking by keyword density means anyone can stuff a page with repeated words to rank number one.",
        "stake_weight": 1.0
    }})
    
    # Seed: initial exposure to the idea of structural ranking
    events.append({"cycle": 3, "type": "seed", "data": {
        "description": "Web link structure contains information about page importance and ranking",
        "tags": ["ranking", "authority", "web", "link-structure", "importance"],
    }})
    
    # === PHASE 2: Failed approaches build pressure (Cycles 4-6) ===
    events.append({"cycle": 4, "type": "tension", "data": {
        "title": "Meta tags ranking approach fails — webmasters lie about content",
        "description": "Using meta tags for ranking fails because page authors self-report inaccurately. Need external signal.",
        "stake_weight": 1.2
    }})
    
    # Near-miss: link counting works partially
    events.append({"cycle": 5, "type": "tension", "data": {
        "title": "Simple link counting for ranking is also gameable",
        "description": "Just counting inbound links for ranking is nearly as gameable — create many pages linking to yourself.",
        "stake_weight": 1.5
    }})
    
    # === PHASE 3: Cross-domain collision — academic citations (Cycles 5-7) ===
    events.append({"cycle": 5, "type": "seed", "data": {
        "description": "Academic papers are ranked by citation count — more citations means more authority and importance",
        "tags": ["citation", "ranking", "academia", "authority", "importance"],
    }})
    
    events.append({"cycle": 6, "type": "seed", "data": {
        "description": "Not all citations are equal for ranking — a citation from an authority should count more",
        "tags": ["citation", "ranking", "authority", "weighted", "recursive-authority", "importance"],
    }})
    
    events.append({"cycle": 6, "type": "tension", "data": {
        "title": "Web links are structurally similar to academic citations for ranking",
        "description": "A hyperlink from page A to page B is like page A citing page B. Citation authority and ranking are linked.",
        "stake_weight": 2.0
    }})
    
    # === PHASE 4: Partial solutions and near-misses (Cycles 7-9) ===
    events.append({"cycle": 7, "type": "tension", "data": {
        "title": "HITS algorithm ranking exists but has problems",
        "description": "Kleinberg's HITS separates hubs and authorities but is query-dependent and expensive. Not global ranking.",
        "stake_weight": 1.0
    }})
    
    events.append({"cycle": 7, "type": "seed", "data": {
        "description": "What if page importance ranking was computed ONCE globally, not per-query?",
        "tags": ["ranking", "precomputation", "global-ranking", "efficiency", "importance"],
    }})
    
    # Resource pressure starts (PhD timeline, advisor expectations)
    events.append({"cycle": 8, "type": "resource_pressure", "data": {
        "resource": "wall_clock_minutes", "amount": 10
    }})
    
    # === PHASE 5: Key insight seeds converge (Cycles 8-11) ===
    events.append({"cycle": 8, "type": "seed", "data": {
        "description": "Recursive definition: a page is important for ranking if important pages link to it. Authority is recursive.",
        "tags": ["recursion", "ranking", "authority", "eigenvector", "citation", "importance"],
    }})
    
    events.append({"cycle": 9, "type": "seed", "data": {
        "description": "Random surfer model: a person randomly clicking links — landing probability equals importance ranking",
        "tags": ["random-walk", "ranking", "probability", "importance", "authority", "web"],
    }})
    
    # More resource pressure
    events.append({"cycle": 10, "type": "resource_pressure", "data": {
        "resource": "wall_clock_minutes", "amount": 10
    }})
    
    # === PHASE 6: Crystallization convergence (Cycles 11-15) ===
    events.append({"cycle": 11, "type": "seed", "data": {
        "description": "Combine recursive citation authority weight plus random surfer plus damping factor equals PageRank ranking",
        "tags": ["pagerank", "ranking", "damping", "convergence", "eigenvector", "citation", "random-walk", "authority", "importance"],
    }})
    
    # Final resource pressure — PhD committee deadline
    events.append({"cycle": 12, "type": "resource_pressure", "data": {
        "resource": "wall_clock_minutes", "amount": 10
    }})
    
    return events
