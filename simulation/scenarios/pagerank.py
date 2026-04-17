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
    """Build the PageRank case study as a sequence of temporal events."""
    events = []
    
    # Cycle 1-3: Deep immersion in web structure
    events.append({"cycle": 1, "type": "tension", "data": {
        "title": "Web search quality is terrible",
        "description": "Existing search engines (AltaVista, Excite) return irrelevant results. Keyword matching is easily gamed by spammers stuffing pages with repeated terms.",
        "stake_weight": 1.5
    }})
    
    events.append({"cycle": 2, "type": "tension", "data": {
        "title": "How to measure page importance objectively",
        "description": "Need a way to rank web pages that is resistant to manipulation and reflects genuine quality/authority.",
        "stake_weight": 2.0
    }})
    
    # Cycle 3-5: Early approaches and failures
    events.append({"cycle": 3, "type": "tension", "data": {
        "title": "Keyword frequency is gameable",
        "description": "Ranking by keyword density means anyone can stuff a page with repeated words to rank #1.",
        "stake_weight": 1.0
    }})
    
    events.append({"cycle": 4, "type": "failure", "data": {
        "tension_id": None,  # will be set after creation
        "description": "Meta tags approach failed — webmasters lie about page content"
    }})
    
    # Cycle 5-7: Cross-domain exposure — academic citations
    events.append({"cycle": 5, "type": "seed", "data": {
        "description": "Academic papers are ranked by citation count — more citations = more important",
        "tags": ["citation", "ranking", "academia", "authority"],
        "tension_ids": []
    }})
    
    events.append({"cycle": 6, "type": "tension", "data": {
        "title": "Web links are structurally similar to academic citations",
        "description": "A hyperlink from page A to page B is like page A 'citing' page B. But not all citations are equal — a citation from a Nobel laureate means more than one from an unknown grad student.",
        "stake_weight": 2.0
    }})
    
    events.append({"cycle": 6, "type": "seed", "data": {
        "description": "Not all links/citations are equal — a link from a highly-linked page should count more",
        "tags": ["weighted-citation", "recursive-authority", "eigenvector"],
    }})
    
    # Cycle 7-9: Contradiction and near-misses
    events.append({"cycle": 7, "type": "tension", "data": {
        "title": "Simple link counting is also gameable",
        "description": "Just counting inbound links is nearly as gameable as keyword density — create many pages linking to yourself.",
        "stake_weight": 1.5
    }})
    
    events.append({"cycle": 8, "type": "tension", "data": {
        "title": "HITS algorithm exists but has problems",
        "description": "Kleinberg's HITS algorithm separates hubs and authorities but is query-dependent and computationally expensive to run per-query.",
        "stake_weight": 1.0
    }})
    
    events.append({"cycle": 8, "type": "seed", "data": {
        "description": "What if page importance was computed ONCE for the whole web, not per-query?",
        "tags": ["precomputation", "global-ranking", "efficiency"],
    }})
    
    # Cycle 9-12: Pressure builds, pattern recognition
    events.append({"cycle": 9, "type": "seed", "data": {
        "description": "Recursive definition: a page is important if important pages link to it. This is an eigenvector problem.",
        "tags": ["recursion", "eigenvector", "linear-algebra", "citation-authority"],
    }})
    
    # Resource pressure (PhD timeline)
    events.append({"cycle": 10, "type": "resource_pressure", "data": {
        "resource": "wall_clock_minutes", "amount": 15
    }})
    
    events.append({"cycle": 11, "type": "seed", "data": {
        "description": "Random surfer model: imagine a person randomly clicking links. The probability of landing on a page = its importance.",
        "tags": ["random-walk", "markov-chain", "probability", "web-surfing"],
    }})
    
    # Cycle 12+: Convergence toward commitment
    events.append({"cycle": 12, "type": "seed", "data": {
        "description": "Combine: recursive citation weight + random surfer + damping factor for dead ends = PageRank",
        "tags": ["pagerank", "damping", "convergence", "eigenvector", "citation", "random-walk"],
    }})
    
    return events
