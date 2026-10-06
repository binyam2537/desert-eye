"""Ordinary-person lenses. Assigning a random everyday persona to each seed is the
cheapest proven way to stop parallel LLM ideation from converging on the same ideas
(ordinary personas beat 'creative expert' personas at recovering idea diversity)."""

GENERATION_PERSONAS = [
    "a night-shift nurse in a big public hospital",
    "a long-haul truck driver",
    "a primary-school teacher in a crowded classroom",
    "a smallholder farmer dealing with unpredictable rain",
    "a city bus dispatcher",
    "a retired engineer living alone",
    "a single parent working two jobs",
    "a first-generation university student",
    "a restaurant owner with thin margins",
    "a municipal water-utility technician",
    "a refugee resettlement caseworker",
    "a warehouse picker on a 10-hour shift",
    "a community health worker visiting rural villages",
    "a firefighter",
    "an insurance claims adjuster",
    "a construction site foreman",
    "a pharmacist in a small town",
    "a ride-hailing driver",
    "a hotel housekeeper",
    "a mid-size factory maintenance lead",
    "a high-school sports coach",
    "a person who uses a wheelchair and commutes daily",
    "a call-centre agent",
    "a street-market vendor",
    "a hospital administrator fighting budget cuts",
    "a parent of a child with a chronic illness",
    "a delivery cyclist",
    "a mayor of a mid-size city",
    "an elderly person managing six medications",
    "a fisherman whose catch is shrinking",
    "a landlord of a ten-unit building",
    "a school bus driver",
    "an emergency dispatcher",
    "a migrant worker sending money home",
    "a small-town librarian",
    "a security guard at a large mall",
]

# The tournament judges: the non-technical audience the pitch must win over.
JUDGE_PANEL = [
    {"name": "Investor", "lens": "Would I fund this? Is the problem big, the market obvious, the story memorable?"},
    {"name": "City official / policymaker", "lens": "Would this visibly help many citizens? Could I announce it?"},
    {"name": "Journalist", "lens": "Is there a headline here a general reader would click and remember?"},
    {"name": "Everyday user", "lens": "Do I instantly get it, and would my life clearly be better?"},
]
