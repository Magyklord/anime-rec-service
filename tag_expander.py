import re

# ── Genre expansions ──────────────────────────────────────────────────────────
# AniList genres are broad strokes. These expansions translate each genre
# into viewer-experience language so the embedding model can match mood queries.
GENRE_EXPANSIONS = {
    "Action":        "intense combat and physical confrontation, fast-paced choreography, adrenaline-driven tension, battles and fights",
    "Adventure":     "journey through unfamiliar lands, discovery of the unknown, exploration beyond familiar boundaries, travel and quests",
    "Comedy":        "comedic timing and humorous misunderstandings, lighthearted situations, jokes laughter and absurdity",
    "Drama":         "deep emotional conflict, character-driven tension through relationships and personal stakes, weighty feelings and consequences",
    "Fantasy":       "magic systems and mythical creatures, invented worlds with their own laws and lore, the impossible made real",
    "Horror":        "fear-inducing imagery and sustained dread, monsters or psychological terror, unsettling atmosphere and existential threat",
    "Mahou Shoujo":  "magical girls with transformation sequences, hope and friendship against dark forces, pastel aesthetics hiding serious themes",
    "Mecha":         "giant robot suits and mechanical warfare, pilots bonded to machines, technological spectacle and the human inside the machine",
    "Music":         "performance art at the story's center, rhythm melody and concerts, characters whose souls are defined by their art, jazz soul blues improvisation mellow grooves soundtrack-driven emotion",
    "Mystery":       "unsolved puzzles and careful deduction, the tension of not knowing, secrets slowly uncovered through investigation",
    "Psychological": "the mental and emotional interior laid bare, mind games and manipulation, identity crises and distorted perception of reality",
    "Romance":       "emotional longing and developing attraction, love confessions and heartbreak, the vulnerability of opening yourself to another",
    "Sci-Fi":        "futuristic technology and speculative science, space exploration and artificial intelligence, what humanity could become",
    "Slice of Life": "everyday mundane moments made meaningful, quiet human interactions and small pleasures, ordinary life observed with care",
    "Sports":        "athletic competition and rigorous training, the teamwork of pushing limits together, the fire of wanting to win",
    "Supernatural":  "entities and forces beyond natural law, spirits demons and powers outside science, the uncanny breaking into daily life",
    "Thriller":      "sustained tension and high stakes, a sense of danger and paranoia that never lets up, edge-of-seat pacing",
    "Ecchi":         "suggestive content and mild sexual situations, fanservice, playful or provocative scenarios",
}

# ── Tag expansions ─────────────────────────────────────────────────────────────
# AniList tags are much more specific than genres. Each one captures a structural
# or tonal feature of the anime. The expansions below are the result of deep
# analysis: what does this tag FEEL like to the viewer?
TAG_EXPANSIONS = {

    # ── Setting ──────────────────────────────────────────────────────────────
    "Isekai": (
        "protagonist suddenly transported from modern Japan into a fantasy world with entirely different rules, "
        "often gaining unusual powers, navigating a medieval or game-like hierarchy from scratch"
    ),
    "Space": (
        "the cosmic void and interstellar travel, alien civilizations and empty starfields, "
        "the existential smallness of humanity drifting against the infinite universe"
    ),
    "Post-Apocalyptic": (
        "civilization has collapsed, survivors navigate ruins and scarcity, "
        "themes of rebuilding human society and the resilience required to continue existing after everything breaks"
    ),
    "Historical": (
        "anchored in a real past era with period-accurate aesthetics, historical events or figures as backdrop, "
        "the weight of a world shaped by what actually happened"
    ),
    "High School": (
        "adolescent social dynamics and first experiences, the charged atmosphere of school clubs and rivalries, "
        "coming-of-age within the walls of teenage life"
    ),
    "Middle School": (
        "early adolescence and the confusion of early teenage years, social hierarchies just beginning to form"
    ),
    "Elementary School": (
        "childhood innocence and early friendship, the simplicity and wonder of young children navigating their world"
    ),
    "University": (
        "early adult life, academic pressure and newfound freedom, the transition from teenager to adult self",
    ),
    "Military": (
        "armed forces structure and the discipline of soldiers, battlefield tactics and the camaraderie forged under fire, "
        "rank and duty and the human cost of organized violence"
    ),
    "Urban Fantasy": (
        "magic hidden within or layered over a modern city, the supernatural coexisting secretly with everyday commutes and convenience stores"
    ),
    "Rural": (
        "quiet countryside life, nature and slower rhythms, the peace or isolation of being far from the city"
    ),
    "Virtual World": (
        "characters inhabiting a digital or game world, blurring of real and virtual identity, "
        "the stakes of a world that feels real but runs on code"
    ),
    "Alternate Universe": (
        "a world that diverges from our own history or reality, asking 'what if' on a civilizational scale"
    ),
    "Parallel World": (
        "multiple versions of reality coexisting or accessible, characters navigating between timelines or dimensions"
    ),
    "Dungeon": (
        "labyrinthine underground spaces full of monsters and traps, the thrill of exploration with life-or-death stakes"
    ),
    "Workplace": (
        "professional environments and adult work life, office politics and career ambition, "
        "the comedy or drama of spending your days with coworkers"
    ),

    # ── Character types ────────────────────────────────────────────────────
    "Anti-Hero": (
        "protagonist who pursues goals through morally grey or outright dark means, "
        "blurring the line between hero and villain, forcing the viewer to root for someone who does terrible things, "
        "lone drifter wandering outsider living on the margins belonging nowhere, "
        "a solitary figure haunted by their past unable to settle or connect"
    ),
    "Found Family": (
        "characters not related by blood who form bonds as deep as family through shared struggle, "
        "choosing each other again and again with unconditional loyalty"
    ),
    "Ensemble Cast": (
        "no single dominant protagonist, story distributes emotional weight equally across many characters, "
        "each one carrying their own arc and depth"
    ),
    "Male Protagonist": "story follows a male lead character as its center of gravity",
    "Female Protagonist": "story follows a female lead character as its center of gravity",
    "Kuudere": (
        "a character who presents as cold, stoic, and emotionally unreachable, "
        "hiding deep feeling beneath an impenetrable surface that gradually yields"
    ),
    "Tsundere": (
        "a character who oscillates between open hostility and surprising tenderness, "
        "concealing genuine affection behind a wall of aggression and denial"
    ),
    "Yandere": (
        "a character whose love becomes obsessive and possessive, their devotion curdling into something dangerous"
    ),
    "Harem": (
        "multiple characters romantically interested in a single protagonist, "
        "comedic or dramatic tension from competing affections"
    ),
    "Reverse Harem": (
        "multiple characters romantically interested in a single female protagonist"
    ),
    "Heterosexual": "central romantic relationship is between a man and a woman",
    "Shounen-ai": "romantic or emotional focus on male-male relationships, generally not explicit",
    "Shoujo-ai": "romantic or emotional focus on female-female relationships, generally not explicit",
    "Yaoi": "explicit male-male romantic or sexual relationships",
    "Yuri": "explicit female-female romantic or sexual relationships",
    "Child Protagonist": "story centered on a child's perspective and the particular logic of childhood",
    "Elderly Protagonist": "story follows an older character whose life experience shapes how they see everything",
    "Villain Protagonist": "the story follows someone who is unambiguously the bad guy, told from the perspective of evil",

    # ── Themes ──────────────────────────────────────────────────────────────
    "Coming of Age": (
        "a young character's formative journey from innocence to experience, "
        "the painful and necessary work of discovering who you actually are"
    ),
    "Revenge": (
        "protagonist's core motivation is retribution for past wrongs, "
        "a burning need that drives every choice and distorts their sense of self"
    ),
    "Redemption": (
        "a character's arc toward atoning for past failures or sins, "
        "often uncertain and costly, asking whether forgiveness is possible or deserved"
    ),
    "Tragedy": (
        "narrative shaped by inevitable loss, suffering, and failure, "
        "a cathartic emotional devastation that feels meaningful rather than cheap"
    ),
    "Philosophy": (
        "characters grapple seriously with abstract questions about existence, consciousness, morality, "
        "and the meaning of a human life"
    ),
    "Politics": (
        "power structures and governance explored with seriousness, faction conflict and the mechanisms of control, "
        "the way power shapes people and vice versa"
    ),
    "War": (
        "armed conflict as the central force shaping the world, the horror and the heroism of battle, "
        "the way war unmakes everything it touches"
    ),
    "Survival": (
        "characters must use wit intelligence and sheer will to stay alive, "
        "against a hostile environment or other humans who would kill them"
    ),
    "Class Struggle": (
        "socioeconomic inequality drives the central conflict, examining how class determines identity and limits opportunity"
    ),
    "Amnesia": (
        "a character has lost their memories and must reconstruct their own identity from fragments, "
        "creating a mystery about who they used to be"
    ),
    "Time Travel": (
        "manipulation of time creates paradoxes and moral dilemmas, "
        "what would you change about the past, and what would that cost"
    ),
    "Psychological Trauma": (
        "past wounds shape present behavior in visible and invisible ways, "
        "the invisible damage of lived experience that follows a character everywhere"
    ),
    "Grief": (
        "loss as a sustained emotional reality, the process of mourning and the difficulty of continuing to exist "
        "after someone who mattered is gone"
    ),
    "Isolation": (
        "characters cut off from meaningful connection, either physically stranded or emotionally alone in a crowd, "
        "loneliness as a defining condition"
    ),
    "Identity": (
        "the question of who a character truly is, challenged by external pressures, hidden truths about their origin, "
        "or the roles others force onto them"
    ),
    "Friendship": (
        "bonds of platonic loyalty tested and deepened over time, "
        "the meaning of choosing someone and continuing to choose them"
    ),
    "Power Struggle": (
        "conflict for dominance between factions, individuals, or ideologies, the chess-like maneuvering for control"
    ),
    "Self-Discovery": (
        "a character learning what they truly want, what they believe, and who they are beneath what they were told to be"
    ),
    "Sacrifice": (
        "characters giving up something precious — their safety, their dreams, their life — for someone or something they love"
    ),
    "Corruption": (
        "a character or institution slowly becoming something worse than it was, power and circumstance degrading what was once good"
    ),
    "Obsession": (
        "a character consumed by a singular fixation that overrides everything else, often at tremendous personal cost"
    ),
    "Betrayal": (
        "trust broken by someone who was supposed to be safe, the particular devastation of being destroyed by your own side"
    ),
    "Love Triangle": (
        "three characters entangled in competing romantic feelings, the tension of who chooses whom"
    ),
    "Unrequited Love": (
        "loving someone who does not love you back, the sustained ache of feeling invisible to the one you want"
    ),
    "Reincarnation": (
        "a character born again into a new life while retaining memories of a previous one, "
        "themes of what carries over across death"
    ),
    "Demons": (
        "demonic entities as antagonists or complex figures, often tied to themes of temptation, sin, or the darkness within"
    ),
    "Gods": (
        "divine beings with immense power shaping the world, questions about the nature of divinity and humanity's place beneath it"
    ),
    "Magic": (
        "systems of supernatural ability governed by rules, the wonder and cost of wielding power beyond natural limits"
    ),
    "Martial Arts": (
        "physical combat as a path of discipline and self-mastery, the philosophy and artistry inside violence"
    ),
    "Swordplay": (
        "blade-on-blade combat with weight and technique, the elegance and lethality of the sword as storytelling device"
    ),
    "Shapeshifting": (
        "characters or creatures who can alter their form, themes of identity and what remains constant when appearance changes"
    ),
    "Vampires": (
        "immortal beings who feed on the living, themes of eternal loneliness, predator-prey relationships, and the weight of centuries"
    ),
    "Zombies": (
        "the undead as horror or metaphor, survival against those who were once human, civilization unraveling"
    ),
    "Pirates": (
        "sea-faring outlaws with their own codes, freedom on the open ocean, treasure and the bonds of a loyal crew, "
        "sailing the seas maritime voyage ship crew adventure on the water, "
        "the high seas and the horizon, ocean wind and the thrill of open waters"
    ),
    "Samurai": (
        "the warrior code of feudal Japan, honor duty and the katana, life structured around discipline and the threat of death"
    ),
    "Ninja": (
        "stealth assassins operating in shadows, hidden conflict and loyalty to clan above all"
    ),
    "Super Power": (
        "characters who possess abilities beyond normal human limits, the social dynamics of living in a world of powered individuals"
    ),
    "Superpowers": (
        "characters who possess abilities beyond normal human limits, the social dynamics of living in a world of powered individuals"
    ),
    "Monsters": (
        "creatures of threat and wonder, often embodying fears or forces the human characters must confront"
    ),
    "Dragons": (
        "ancient immensely powerful beings, symbols of terror or majesty, often at the center of world mythology"
    ),
    "Bounty Hunter": (
        "mercenaries who hunt targets for payment, operating in the grey zone between law and crime, "
        "morality shaped by whoever is paying"
    ),
    "Delinquents": (
        "teenage rebels who reject mainstream society, the raw energy of youth refusing to comply"
    ),
    "Otaku Culture": (
        "deep dive into anime manga and game fandom culture, characters whose passion for fiction defines their identity"
    ),
    "NEET": (
        "young adults who have withdrawn from work and society, themes of social anxiety, isolation, and eventual re-engagement"
    ),

    # ── Tone and style ───────────────────────────────────────────────────────
    "Dark Themes": (
        "unflinching engagement with suffering, cruelty, moral failure, and the difficult parts of human experience"
    ),
    "Gore": (
        "graphic visceral depiction of violence and bodily destruction, not softened or implied but shown directly"
    ),
    "Philosophical": (
        "the narrative makes genuine space for characters to debate ideas about existence, ethics, and what a life means"
    ),
    "Melancholy": (
        "a sustained emotional undertone of sadness, longing, and impermanence, a bittersweet awareness of loss"
    ),
    "Atmospheric": (
        "mood and setting carry as much weight as plot, a strong physical and emotional sense of place"
    ),
    "Comedic": (
        "broadly funny, prioritizing jokes and laughter over weight, the world tends toward absurdity"
    ),
    "Wholesome": (
        "warm, affirming, and emotionally safe, the story wants you to feel good"
    ),
    "Healing": (
        "gentle and restorative, watching it feels like rest, characters and viewer both recovering together"
    ),
    "Cute Girls Doing Cute Things": (
        "a relaxed low-stakes atmosphere centered on charming female characters in pleasant everyday scenarios"
    ),
    "Cyberpunk": (
        "high technology and low life, neon-soaked dystopian cities where corporations rule and humans are modified, "
        "the cost of technological progress paid in flesh"
    ),
    "Steampunk": (
        "Victorian-era aesthetics combined with advanced steam-powered technology, a retro-futuristic world of gears and airships"
    ),
    "Wuxia": (
        "Chinese martial arts fantasy, warriors with supernatural combat abilities, honor-bound clans and ancient technique"
    ),
    "Noir": (
        "morally ambiguous detectives in a corrupt world, rain-soaked cynicism and the sense that no one comes out clean"
    ),
    "Idols": (
        "the Japanese pop idol industry, the performance of perfection and the hidden human cost of manufactured stardom"
    ),
    "Music": (
        "music as the central language of the story, performance as a way of expressing what words cannot reach"
    ),

    # ── Narrative structure ──────────────────────────────────────────────────
    "Non-linear": (
        "story is told out of chronological order, fragments of timeline assembled by the viewer into meaning"
    ),
    "Multiple Endings": "story has branching or alternate resolutions depending on choices or perspective",
    "Unreliable Narrator": (
        "the character telling the story cannot be fully trusted, what we're shown may not be what actually happened"
    ),
    "Anthology": "collection of self-contained stories sharing a world or theme rather than a continuous narrative",
    "Episodic": "each episode is largely self-contained, no continuous overarching plot arc",
    "Based on a Game": "adapted from a video game, often carries game structure like levels quests and power progression",
    "Based on a Manga": "adapted from Japanese comics, visual storytelling translated to animation",
    "Based on a Novel": "adapted from prose fiction, often character-rich and plot-dense source material",
    "Based on a Light Novel": "adapted from Japanese light novels, often features isekai or game-like mechanics",
    "Original Work": "created specifically for animation, no prior source material, genuine creative freedom",

    # ── Demographic tags ────────────────────────────────────────────────────
    "Shounen": (
        "aimed at young male readers, emphasizes growth through effort, the power of friendship, and escalating challenges"
    ),
    "Seinen": (
        "aimed at adult male readers, allows for more complex morality, real-world grittiness, and ambiguous outcomes"
    ),
    "Josei": (
        "aimed at adult women, often features realistic emotional romance and the interior lives of women navigating adult life"
    ),
    "Shoujo": (
        "aimed at young girls, emphasizes emotional relationships, inner character development, and the texture of feeling"
    ),
}


def clean_description(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\(Source:[^)]*\)', '', text)
    text = re.sub(r'\[Written by MAL Rewrite\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def build_rich_soup(media: dict) -> str:
    """
    Converts raw AniList media data into a rich descriptive text that the
    embedding model can understand as viewer-experience language.

    The structure: description → genre phrases (doubled for weight) →
    high-confidence tag phrases → moderate-confidence tag phrases
    """
    description = clean_description(media.get("description", ""))
    genres = media.get("genres", [])
    tags = media.get("tags", [])

    # Expand genres into experiential language
    genre_phrases = []
    for g in genres:
        expanded = GENRE_EXPANSIONS.get(g)
        if expanded:
            genre_phrases.append(expanded)
        else:
            genre_phrases.append(g.lower())

    genre_block = " ".join(genre_phrases)

    # High-confidence tags (rank 75+) are defining features — expand fully
    high_tags = [t for t in tags if t.get("rank", 0) >= 75]
    high_phrases = []
    for t in high_tags:
        expanded = TAG_EXPANSIONS.get(t["name"])
        if expanded:
            high_phrases.append(expanded)
        else:
            high_phrases.append(t["name"].lower())

    # Medium-confidence tags (60-74) add supporting colour
    mid_tags = [t for t in tags if 60 <= t.get("rank", 0) < 75]
    mid_phrases = []
    for t in mid_tags:
        expanded = TAG_EXPANSIONS.get(t["name"])
        if expanded:
            mid_phrases.append(expanded)
        else:
            mid_phrases.append(t["name"].lower())

    parts = [
        description,
        genre_block,
        genre_block,          # genres repeated to increase their semantic weight
        " ".join(high_phrases),
        " ".join(mid_phrases),
    ]

    return " ".join(p for p in parts if p).strip()
