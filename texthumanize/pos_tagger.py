"""Rule-based POS tagger — no ML dependencies.

Suffix/prefix rules + exception dictionary. Accuracy ~85-90%
for European languages, sufficient for context-aware replacement.

Usage:
    from texthumanize.pos_tagger import POSTagger

    tagger = POSTagger(lang="en")
    tags = tagger.tag("The quick brown fox jumps")
    # [("The", "DET"), ("quick", "ADJ"), ("brown", "ADJ"),
    #  ("fox", "NOUN"), ("jumps", "VERB")]

    # Single word
    tag = tagger.tag_word("running")  # "VERB"

    # With context
    tag = tagger.tag_word("running", prev="was")  # "VERB"
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Universal tagset ──────────────────────────────────────────
NOUN = "NOUN"
VERB = "VERB"
ADJ = "ADJ"
ADV = "ADV"
DET = "DET"
PREP = "PREP"
CONJ = "CONJ"
PRON = "PRON"
NUM = "NUM"
PART = "PART"
INTJ = "INTJ"
PUNCT = "PUNCT"
X = "X"

# ── Tokenizer regex ──────────────────────────────────────────
_TOKEN_RE = re.compile(
    r"[A-Za-z\u00C0-\u024F\u0400-\u04FF\u0500-\u052F"
    r"\u1E00-\u1EFF\u00DF]+"
    r"|[0-9]+(?:[.,][0-9]+)*"
    r"|[^\s]",
    re.UNICODE,
)

_PUNCT_RE = re.compile(
    r'^[.,!?;:\-\—\–\"\'`\(\)\[\]{}<>/\\@#$%^&*_=+|~]+$'
)
_NUM_RE = re.compile(r'^[0-9]+(?:[.,][0-9]+)*$')

# ═══════════════════════════════════════════════════════════════
# English data
# ═══════════════════════════════════════════════════════════════

# Comparative adjectives with doubled consonant (e.g. bigger, fatter)
_EN_COMP_DOUBLED: frozenset[str] = frozenset({
    "bigger", "fatter", "hotter", "sadder", "thinner",
    "wetter", "redder", "madder", "fitter", "flatter",
    "dimmer", "slimmer", "tanner",
})

# Common comparative adjectives (base + er)
_EN_COMP_REGULAR: frozenset[str] = frozenset({
    "faster", "slower", "taller", "smaller", "older",
    "younger", "longer", "shorter", "wider", "newer",
    "cheaper", "deeper", "richer", "darker", "lighter",
    "cleaner", "louder", "softer", "sharper", "stronger",
    "weaker", "cooler", "warmer", "closer", "nicer",
    "safer", "simpler", "gentler", "humbler", "nobler",
    "later", "earlier", "higher", "lower", "brighter",
})

_EN_EXCEPTIONS: Dict[str, str] = {}

# ── Determiners ───────────────────────────────────────────────
for _w in (
    "the", "a", "an", "this", "that", "these", "those",
    "my", "your", "his", "her", "its", "our", "their",
    "some", "any", "no", "every", "each", "all", "both",
    "few", "several", "many", "much", "enough", "either",
    "neither", "another", "such", "what", "whatever",
    "whichever", "certain", "other",
):
    _EN_EXCEPTIONS[_w] = DET

# ── Prepositions ──────────────────────────────────────────────
for _w in (
    "in", "on", "at", "to", "for", "with", "by", "from",
    "of", "about", "into", "through", "during", "before",
    "after", "between", "among", "under", "above", "below",
    "near", "across", "against", "along", "around", "behind",
    "beyond", "despite", "except", "inside", "outside",
    "onto", "throughout", "toward", "towards", "upon",
    "via", "within", "without", "beside", "besides",
    "beneath", "unlike", "until", "till", "past",
    "regarding", "concerning", "per",
    "over", "off", "up", "down", "out",
):
    _EN_EXCEPTIONS[_w] = PREP

# ── Conjunctions ──────────────────────────────────────────────
for _w in (
    "and", "but", "or", "nor", "so", "yet", "because",
    "although", "while", "if", "when", "unless", "since",
    "though", "whereas", "whether", "however", "moreover",
    "furthermore", "nevertheless", "therefore", "thus",
    "hence", "meanwhile", "otherwise", "nonetheless",
    "wherever", "whenever", "whoever", "whomever",
    "provided", "once", "lest",
):
    _EN_EXCEPTIONS[_w] = CONJ

# ── Pronouns ─────────────────────────────────────────────────
for _w in (
    "i", "me", "you", "he", "him", "she", "it", "we",
    "us", "they", "them", "myself", "yourself", "himself",
    "herself", "itself", "ourselves", "yourselves",
    "themselves", "who", "whom", "whose", "which",
    "where", "how", "why", "somebody", "someone",
    "something", "anybody", "anyone", "anything",
    "everybody", "everyone", "everything", "nobody",
    "nothing", "none", "one", "ones", "mine", "yours",
    "his", "hers", "ours", "theirs", "whatever",
    "whichever", "whoever", "whomever",
):
    _EN_EXCEPTIONS[_w] = PRON

# fix: "his" is DET primarily (possessive determiner)
_EN_EXCEPTIONS["his"] = DET

# ── Adverbs ───────────────────────────────────────────────────
for _w in (
    "very", "really", "quite", "rather", "too", "also",
    "already", "still", "just", "never", "always", "often",
    "sometimes", "usually", "here", "there", "now", "then",
    "soon", "maybe", "perhaps", "almost", "even", "only",
    "again", "ago", "anyway", "anywhere", "else",
    "elsewhere", "ever", "everywhere", "fast",
    "formerly", "hardly", "hence", "henceforth",
    "hereby", "herein", "however", "immediately",
    "indeed", "instead", "lately", "later", "likewise",
    "long", "moreover", "mostly", "namely", "nearby",
    "nearly", "nonetheless", "nowadays", "otherwise",
    "overall", "partly", "presently", "previously",
    "primarily", "probably", "seldom", "shortly",
    "simply", "since", "slightly", "somehow",
    "somewhere", "thereby", "therefore", "thus",
    "today", "together", "tomorrow", "tonight",
    "twice", "ultimately", "upward", "downward",
    "forward", "backward", "inward", "outward",
    "well", "yesterday", "yet", "abroad", "apart",
    "away", "furthermore", "ahead", "aside",
    "below", "beneath", "besides", "meanwhile",
    "nevertheless", "nonetheless", "nowhere",
    "otherwise", "overhead", "somewhat",
    "thereafter", "thoroughly", "throughout",
    "underneath", "utterly", "wholly",
    "widely", "already", "apparently",
    "certainly", "clearly", "closely",
    "commonly", "consequently", "constantly",
    "currently", "daily", "deeply",
    "definitely", "deliberately", "directly",
    "effectively", "entirely", "equally",
    "especially", "essentially", "eventually",
    "exactly", "exclusively", "explicitly",
    "extremely", "fairly", "finally",
    "frequently", "fully", "generally",
    "gradually", "greatly", "hopefully",
    "increasingly", "inevitably", "initially",
    "largely", "merely", "naturally",
    "necessarily", "normally", "notably",
    "obviously", "occasionally", "originally",
    "particularly", "perfectly", "permanently",
    "personally", "poorly", "potentially",
    "precisely", "presumably", "properly",
    "purely", "quickly", "rapidly",
    "rarely", "recently", "regularly",
    "relatively", "repeatedly", "reportedly",
    "respectively", "roughly", "secretly",
    "separately", "seriously", "severely",
    "significantly", "similarly", "solely",
    "specifically", "steadily", "strongly",
    "subsequently", "substantially",
    "successfully", "suddenly", "sufficiently",
    "supposedly", "surely", "surprisingly",
    "temporarily", "traditionally",
    "tremendously", "truly", "typically",
    "unfortunately", "uniformly", "uniquely",
    "universally", "urgently", "vastly",
    "virtually", "voluntarily",
):
    _EN_EXCEPTIONS[_w] = ADV

# ── Common verbs ──────────────────────────────────────────────
for _w in (
    "be", "is", "am", "are", "was", "were", "been",
    "being", "have", "has", "had", "having", "do",
    "does", "did", "doing", "will", "would", "can",
    "could", "shall", "should", "may", "might", "must",
    "need", "dare", "ought", "go", "goes", "went",
    "gone", "going", "come", "comes", "came", "coming",
    "get", "gets", "got", "gotten", "getting",
    "make", "makes", "made", "making", "take", "takes",
    "took", "taken", "taking", "give", "gives", "gave",
    "given", "giving", "know", "knows", "knew", "known",
    "knowing", "think", "thinks", "thought", "thinking",
    "say", "says", "said", "saying", "see", "sees",
    "saw", "seen", "seeing", "want", "wants", "wanted",
    "wanting", "seem", "seems", "seemed", "seeming",
    "become", "becomes", "became", "becoming",
    "keep", "keeps", "kept", "keeping",
    "let", "lets", "letting",
    "begin", "begins", "began", "begun", "beginning",
    "show", "shows", "showed", "shown", "showing",
    "hear", "hears", "heard", "hearing",
    "play", "plays", "played", "playing",
    "run", "runs", "ran", "running",
    "move", "moves", "moved", "moving",
    "live", "lives", "lived", "living",
    "believe", "believes", "believed", "believing",
    "hold", "holds", "held", "holding",
    "bring", "brings", "brought", "bringing",
    "happen", "happens", "happened", "happening",
    "write", "writes", "wrote", "written", "writing",
    "sit", "sits", "sat", "sitting",
    "stand", "stands", "stood", "standing",
    "lose", "loses", "lost", "losing",
    "pay", "pays", "paid", "paying",
    "meet", "meets", "met", "meeting",
    "include", "includes", "included", "including",
    "continue", "continues", "continued",
    "set", "sets", "setting",
    "learn", "learns", "learned", "learning",
    "change", "changes", "changed", "changing",
    "lead", "leads", "led", "leading",
    "understand", "understands", "understood",
    "watch", "watches", "watched", "watching",
    "follow", "follows", "followed", "following",
    "stop", "stops", "stopped", "stopping",
    "create", "creates", "created", "creating",
    "speak", "speaks", "spoke", "spoken", "speaking",
    "read", "reads", "reading",
    "allow", "allows", "allowed", "allowing",
    "add", "adds", "added", "adding",
    "spend", "spends", "spent", "spending",
    "grow", "grows", "grew", "grown", "growing",
    "open", "opens", "opened", "opening",
    "walk", "walks", "walked", "walking",
    "win", "wins", "won", "winning",
    "offer", "offers", "offered", "offering",
    "remember", "remembers", "remembered",
    "love", "loves", "loved", "loving",
    "consider", "considers", "considered",
    "appear", "appears", "appeared", "appearing",
    "buy", "buys", "bought", "buying",
    "wait", "waits", "waited", "waiting",
    "serve", "serves", "served", "serving",
    "die", "dies", "died", "dying",
    "send", "sends", "sent", "sending",
    "expect", "expects", "expected", "expecting",
    "build", "builds", "built", "building",
    "stay", "stays", "stayed", "staying",
    "fall", "falls", "fell", "fallen", "falling",
    "cut", "cuts", "cutting",
    "reach", "reaches", "reached", "reaching",
    "kill", "kills", "killed", "killing",
    "remain", "remains", "remained", "remaining",
    "suggest", "suggests", "suggested",
    "raise", "raises", "raised", "raising",
    "pass", "passes", "passed", "passing",
    "sell", "sells", "sold", "selling",
    "put", "puts", "putting",
    "try", "tries", "tried", "trying",
    "ask", "asks", "asked", "asking",
    "tell", "tells", "told", "telling",
    "call", "calls", "called", "calling",
    "turn", "turns", "turned", "turning",
    "help", "helps", "helped", "helping",
    "start", "starts", "started", "starting",
    "look", "looks", "looked", "looking",
    "use", "uses", "used", "using",
    "find", "finds", "found", "finding",
    "feel", "feels", "felt", "feeling",
    "leave", "leaves", "left", "leaving",
    "work", "works", "worked", "working",
    "mean", "means", "meant", "meaning",
    "carry", "carries", "carried", "carrying",
    "talk", "talks", "talked", "talking",
    "eat", "eats", "ate", "eaten", "eating",
    "draw", "draws", "drew", "drawn", "drawing",
    "choose", "chooses", "chose", "chosen",
    "cause", "causes", "caused", "causing",
    "point", "points", "pointed", "pointing",
    "receive", "receives", "received",
    "agree", "agrees", "agreed", "agreeing",
    "wish", "wishes", "wished", "wishing",
    "drop", "drops", "dropped", "dropping",
    "develop", "develops", "developed",
    "drive", "drives", "drove", "driven",
    "explain", "explains", "explained",
    "rise", "rises", "rose", "risen", "rising",
    "pull", "pulls", "pulled", "pulling",
    "push", "pushes", "pushed", "pushing",
    "pick", "picks", "picked", "picking",
    "lie", "lies", "lay", "lain", "lying",
    "break", "breaks", "broke", "broken",
    "fill", "fills", "filled", "filling",
    "fight", "fights", "fought", "fighting",
    "wear", "wears", "wore", "worn", "wearing",
    "hit", "hits", "hitting",
    "miss", "misses", "missed", "missing",
    "catch", "catches", "caught", "catching",
    "suppose", "supposes", "supposed",
    "deal", "deals", "dealt", "dealing",
    "bear", "bears", "bore", "borne", "bearing",
    "save", "saves", "saved", "saving",
    "act", "acts", "acted", "acting",
    "face", "faces", "faced", "facing",
    "form", "forms", "formed", "forming",
    "shake", "shakes", "shook", "shaken",
    "wonder", "wonders", "wondered",
    "enjoy", "enjoys", "enjoyed", "enjoying",
    "hang", "hangs", "hung", "hanging",
    "seek", "seeks", "sought", "seeking",
    "cost", "costs", "costing",
    "fit", "fits", "fitted", "fitting",
    "throw", "throws", "threw", "thrown",
    "sing", "sings", "sang", "sung", "singing",
    "teach", "teaches", "taught", "teaching",
    "sleep", "sleeps", "slept", "sleeping",
    "buy", "buys", "bought", "buying",
    "ring", "rings", "rang", "rung", "ringing",
    "wake", "wakes", "woke", "woken", "waking",
    "fly", "flies", "flew", "flown", "flying",
    "swim", "swims", "swam", "swum", "swimming",
    "prove", "proves", "proved", "proving",
    "hide", "hides", "hid", "hidden", "hiding",
    "argue", "argues", "argued", "arguing",
    "apply", "applies", "applied", "applying",
    "involve", "involves", "involved",
    "claim", "claims", "claimed", "claiming",
    "occur", "occurs", "occurred", "occurring",
    "achieve", "achieves", "achieved",
    "avoid", "avoids", "avoided", "avoiding",
    "define", "defines", "defined", "defining",
    "manage", "manages", "managed", "managing",
    "prepare", "prepares", "prepared",
    "produce", "produces", "produced",
    "reduce", "reduces", "reduced", "reducing",
    "require", "requires", "required",
    "support", "supports", "supported",
    "jump", "jumped", "jumping",
    "drink", "drinks", "drank", "drunk",
    "kick", "kicked", "kicking",
    "grab", "grabbed", "grabbing",
    "fix", "fixed", "fixing",
    "mix", "mixed", "mixing",
    "cry", "cries", "cried", "crying",
    "cook", "cooked", "cooking",
    "clean", "cleaned", "cleaning",
    "dance", "danced", "dancing",
    "smile", "smiled", "smiling",
    "climb", "climbed", "climbing",
    "count", "counted", "counting",
    "cross", "crossed", "crossing",
    "deliver", "delivered", "delivering",
    "describe", "described", "describing",
    "destroy", "destroyed", "destroying",
    "discover", "discovered", "discovering",
    "discuss", "discussed", "discussing",
    "divide", "divided", "dividing",
    "enter", "entered", "entering",
    "escape", "escaped", "escaping",
    "examine", "examined", "examining",
    "exist", "existed", "existing",
    "express", "expressed", "expressing",
    "fail", "failed", "failing",
    "finish", "finished", "finishing",
    "flow", "flowed", "flowing",
    "force", "forced", "forcing",
    "forgive", "forgave", "forgiven",
    "gather", "gathered", "gathering",
    "handle", "handled", "handling",
    "imagine", "imagined", "imagining",
    "improve", "improved", "improving",
    "indicate", "indicated", "indicating",
    "introduce", "introduced",
    "invite", "invited", "inviting",
    "join", "joined", "joining",
    "judge", "judged", "judging",
    "jump", "jumped", "jumping",
    "knock", "knocked", "knocking",
    "lack", "lacked", "lacking",
    "last", "lasted", "lasting",
    "launch", "launched", "launching",
    "lift", "lifted", "lifting",
    "limit", "limited", "limiting",
    "link", "linked", "linking",
    "mark", "marked", "marking",
    "matter", "mattered", "mattering",
    "measure", "measured", "measuring",
    "mention", "mentioned", "mentioning",
    "note", "noted", "noting",
    "notice", "noticed", "noticing",
    "obtain", "obtained", "obtaining",
    "operate", "operated", "operating",
    "order", "ordered", "ordering",
    "paint", "painted", "painting",
    "perform", "performed", "performing",
    "permit", "permitted", "permitting",
    "place", "placed", "placing",
    "plant", "planted", "planting",
    "pour", "poured", "pouring",
    "practice", "practiced", "practicing",
    "prevent", "prevented", "preventing",
    "promise", "promised", "promising",
    "protect", "protected", "protecting",
    "prove", "proved", "proving",
    "provide", "provided", "providing",
    "publish", "published", "publishing",
    "refuse", "refused", "refusing",
    "release", "released", "releasing",
    "reply", "replied", "replying",
    "report", "reported", "reporting",
    "represent", "represented",
    "request", "requested", "requesting",
    "resolve", "resolved", "resolving",
    "respond", "responded", "responding",
    "rest", "rested", "resting",
    "result", "resulted", "resulting",
    "return", "returned", "returning",
    "reveal", "revealed", "revealing",
    "review", "reviewed", "reviewing",
    "roll", "rolled", "rolling",
    "rule", "ruled", "ruling",
    "rush", "rushed", "rushing",
    "search", "searched", "searching",
    "select", "selected", "selecting",
    "settle", "settled", "settling",
    "share", "shared", "sharing",
    "shoot", "shot", "shooting",
    "shout", "shouted", "shouting",
    "shut", "shutting",
    "sign", "signed", "signing",
    "slip", "slipped", "slipping",
    "solve", "solved", "solving",
    "sort", "sorted", "sorting",
    "store", "stored", "storing",
    "strike", "struck", "striking",
    "struggle", "struggled", "struggling",
    "study", "studied", "studying",
    "suffer", "suffered", "suffering",
    "supply", "supplied", "supplying",
    "survive", "survived", "surviving",
    "teach", "taught", "teaching",
    "test", "tested", "testing",
    "touch", "touched", "touching",
    "train", "trained", "training",
    "transfer", "transferred",
    "travel", "traveled", "traveling",
    "treat", "treated", "treating",
    "trust", "trusted", "trusting",
    "visit", "visited", "visiting",
    "wake", "woke", "woken", "waking",
    "warn", "warned", "warning",
    "wash", "washed", "washing",
    "wave", "waved", "waving",
    "wonder", "wondered", "wondering",
    "worry", "worried", "worrying",
    "wrap", "wrapped", "wrapping",
    "yield", "yielded", "yielding",
):
    _EN_EXCEPTIONS[_w] = VERB

# ── Auxiliaries / modals ──────────────────────────────────────
_EN_AUX = frozenset({
    "be", "is", "am", "are", "was", "were", "been",
    "being", "have", "has", "had", "having", "do",
    "does", "did", "will", "would", "can", "could",
    "shall", "should", "may", "might", "must",
    "need", "dare", "ought",
})

# ── Numbers ───────────────────────────────────────────────────
for _w in (
    "zero", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten", "eleven",
    "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
    "twenty", "thirty", "forty", "fifty", "sixty",
    "seventy", "eighty", "ninety", "hundred",
    "thousand", "million", "billion", "trillion",
    "first", "second", "third", "fourth", "fifth",
    "sixth", "seventh", "eighth", "ninth", "tenth",
    "eleventh", "twelfth", "last", "next",
    "dozen", "couple", "half", "quarter",
):
    _EN_EXCEPTIONS[_w] = NUM

# ── Particles ─────────────────────────────────────────────────
for _w in ("not", "n't"):
    _EN_EXCEPTIONS[_w] = PART

# ── Interjections ─────────────────────────────────────────────
for _w in (
    "oh", "ah", "wow", "oops", "hey", "hi", "hello",
    "ouch", "ugh", "yay", "bravo", "alas", "hurray",
    "gee", "gosh", "huh", "hmm", "phew", "shh",
    "tsk", "uh", "um", "er", "erm", "whoa",
    "damn", "darn", "yikes", "hooray", "boo",
    "cheers", "congrats", "goodbye", "bye",
):
    _EN_EXCEPTIONS[_w] = INTJ

# ── Common adjectives ────────────────────────────────────────
for _w in (
    "good", "great", "big", "small", "old", "young",
    "quick", "slow", "fast", "quiet", "loud",
    "new", "long", "little", "large", "high", "low",
    "bad", "best", "better", "worse", "worst",
    "right", "wrong", "true", "false", "real",
    "full", "free", "safe", "sure", "able", "own",
    "dark", "deep", "dry", "easy", "far", "fine",
    "flat", "glad", "hard", "hot", "cold", "kind",
    "late", "main", "major", "minor", "nice", "open",
    "poor", "rich", "sad", "sick", "soft", "strong",
    "tall", "short", "thin", "thick", "tough", "warm",
    "wide", "wild", "whole", "ready", "clear",
    "close", "common", "different", "early", "foreign",
    "human", "important", "local", "natural",
    "normal", "possible", "public", "recent",
    "serious", "simple", "single", "special",
    "similar", "various", "white", "black", "red",
    "blue", "green", "brown", "yellow", "golden",
    "grey", "gray", "pink", "orange", "purple",
    "bright", "heavy", "light", "rare", "raw",
    "rough", "sharp", "slow", "smooth", "strange",
    "sweet", "tiny", "vast", "weak", "rapid", "basic",
    "brief", "broad", "busy", "cheap", "clean",
    "cool", "cruel", "cute", "dead", "dear", "double",
    "drunk", "dull", "empty", "entire", "equal",
    "evil", "exact", "extra", "extreme", "faint",
    "fair", "familiar", "famous", "fat", "female",
    "fierce", "final", "firm", "fit", "fond",
    "formal", "former", "frequent", "fresh", "front",
    "funny", "gentle", "genuine", "giant", "grand",
    "grateful", "grave", "gross", "guilty", "happy",
    "harsh", "healthy", "huge", "humble", "hungry",
    "ideal", "ill", "inner", "keen", "key", "lazy",
    "legal", "lengthy", "likely", "liquid", "lonely",
    "loose", "loud", "lovely", "lucky", "mad", "male",
    "massive", "mature", "mere", "mild", "modest",
    "moral", "mutual", "naked", "narrow", "neat",
    "negative", "nervous", "noble", "odd", "obvious",
    "official", "ordinary", "outer", "pale", "plain",
    "pleasant", "polite", "positive", "precious",
    "present", "pretty", "primary", "prime",
    "principal", "prior", "private", "proper",
    "proud", "pure", "quiet", "random", "raw",
    "regular", "relevant", "reluctant", "remote",
    "rigid", "ripe", "round", "royal", "rude",
    "rural", "sacred", "secure", "senior", "severe",
    "shallow", "shy", "slight", "smart", "sole",
    "solid", "sophisticated", "spare", "specific",
    "stable", "standard", "steady", "steep",
    "stiff", "strict", "subtle", "sudden",
    "sufficient", "suitable", "super", "supreme",
    "tender", "terrible", "tight", "tired",
    "total", "tremendous", "typical", "ugly",
    "ultimate", "unique", "universal", "upper",
    "urban", "urgent", "usual", "vague", "valid",
    "vital", "vivid", "voluntary", "vulnerable",
    "warm", "wicked", "willing", "wise", "wonderful",
    "worthy", "absolute", "abstract", "academic",
    "acceptable", "accurate", "active", "actual",
    "adequate", "afraid", "aggressive", "alive",
    "alone", "alternative", "ancient", "angry",
    "annual", "anxious", "apparent", "appropriate",
    "attractive", "automatic", "available", "aware",
    "awful", "beautiful", "blind", "bold", "boring",
    "capable", "careful", "central", "chemical",
    "civil", "classic", "clinical", "cognitive",
    "comfortable", "complex", "comprehensive",
    "conscious", "considerable", "consistent",
    "content", "conventional", "correct", "creative",
    "critical", "cultural", "curious", "current",
    "dangerous", "decent", "deliberate",
    "delicate", "democratic", "dependent",
    "desperate", "digital", "distinct",
    "domestic", "dominant", "dramatic", "eager",
    "economic", "educational", "effective",
    "efficient", "elderly", "electric",
    "electronic", "elegant", "emotional",
    "enormous", "environmental", "essential",
    "ethnic", "evident", "excellent", "excessive",
    "exciting", "exclusive", "exotic", "expensive",
    "explicit", "extensive", "ordinary",
    "fantastic", "favorable", "favourite",
    "federal", "fellow", "financial", "flexible",
    "following", "foolish", "fundamental",
    "generous", "genetic", "global", "gorgeous",
    "graphic", "grim", "handsome", "hidden",
    "historic", "horizontal", "hostile",
    "identical", "immediate", "immense",
    "imperial", "impressive", "inadequate",
    "incredible", "independent", "indirect",
    "individual", "industrial", "inevitable",
    "infinite", "influential", "initial",
    "innocent", "innovative", "intense",
    "interesting", "internal", "international",
    "intimate", "invisible", "junior",
    "legitimate", "liberal", "linear",
    "literary", "logical", "magnificent",
    "married", "mathematical", "maximum",
    "mechanical", "medical", "mental", "military",
    "minimum", "mobile", "moderate", "modern",
    "molecular", "multiple", "municipal",
    "musical", "mysterious", "national",
    "native", "necessary", "nuclear",
    "numerous", "objective", "obvious",
    "occasional", "online", "operational",
    "opposite", "organic", "original",
    "outstanding", "overwhelming", "parallel",
    "particular", "passive", "patient",
    "peaceful", "perfect", "permanent",
    "personal", "physical", "plastic",
    "pleasant", "political", "popular",
    "portable", "potential", "powerful",
    "practical", "precise", "pregnant",
    "professional", "profound", "progressive",
    "prominent", "psychological", "racial",
    "radical", "rational", "reasonable",
    "regional", "related", "relative",
    "religious", "remarkable", "representative",
    "residential", "responsible", "revolutionary",
    "romantic", "routine", "scientific",
    "secondary", "secret", "sensitive",
    "sexual", "sick", "significant",
    "silent", "smooth", "social", "solar",
    "spiritual", "strategic", "structural",
    "subject", "substantial", "successful",
    "superior", "surgical", "suspicious",
    "symbolic", "sympathetic", "technical",
    "temporary", "theoretical", "thick",
    "thorough", "tiny", "toxic",
    "traditional", "tropical", "uncertain",
    "underground", "unfortunate", "uniform",
    "unlikely", "unusual", "various",
    "vertical", "violent", "virtual",
    "visible", "visual", "vital",
    "voluntary", "vulnerable", "worthy",
    "friendly", "ugly",
):
    _EN_EXCEPTIONS[_w] = ADJ

# ── Common nouns ──────────────────────────────────────────────
for _w in (
    "time", "year", "people", "way", "day", "man",
    "woman", "child", "world", "life", "hand", "part",
    "place", "case", "week", "company", "system",
    "program", "question", "work", "government",
    "number", "night", "point", "home", "water",
    "room", "mother", "area", "money", "story",
    "fact", "month", "lot", "right", "study",
    "book", "eye", "job", "word", "business",
    "issue", "side", "head", "house", "service",
    "friend", "father", "power", "hour", "game",
    "line", "end", "member", "law", "car", "city",
    "community", "name", "president", "team",
    "minute", "idea", "body", "information",
    "level", "person", "school", "thing", "student",
    "family", "group", "country", "problem",
    "state", "market", "morning", "table",
    "course", "war", "history", "door",
    "experience", "result", "food", "face",
    "reason", "research", "girl", "guy", "moment",
    "air", "teacher", "force", "education",
    "foot", "boy", "age", "policy", "process",
    "music", "bank", "paper", "summer", "class",
    "century", "plan", "relationship", "seat",
    "sense", "report", "mind", "town", "basis",
    "wall", "center", "note", "street", "machine",
    "news", "voice", "road", "role", "king",
    "heart", "rate", "church", "price", "model",
    "truth", "dog", "cat", "risk", "bed",
    "art", "hair", "earth", "garden", "language",
    "sun", "space", "stage", "army", "future",
    "film", "science", "baby", "song", "tree",
    "field", "type", "oil", "stone", "fire",
    "river", "sea", "window", "phone", "glass",
    "bridge", "movie", "boat", "fish", "bird",
    "star", "rain", "snow", "sky", "wing",
    "ship", "island", "mountain", "river", "lake",
    "beach", "forest", "moon", "cloud", "wind",
    "rock", "hill", "horse", "flower", "grass",
    "dinner", "lunch", "breakfast", "weather",
    "gold", "silver", "iron", "steel", "cotton",
    "wood", "apple", "farm", "store", "kitchen",
    "park", "library", "museum", "hospital",
    "station", "office", "airport", "hotel",
    "restaurant", "theater", "market", "stadium",
    "factory", "prison", "castle", "palace",
    "temple", "tower", "bridge", "tunnel",
    "harbor", "port",
):
    # don't override if already set (some overlap)
    if _w not in _EN_EXCEPTIONS:
        _EN_EXCEPTIONS[_w] = NOUN

# ── -ly adjectives (exceptions to -ly → ADV rule) ────────────
_EN_LY_ADJ = frozenset({
    "friendly", "lovely", "lonely", "ugly",
    "likely", "unlikely", "lively", "deadly",
    "costly", "ghastly", "homely", "comely",
    "manly", "womanly", "beastly", "cowardly",
    "elderly", "fatherly", "motherly", "brotherly",
    "sisterly", "orderly", "timely", "untimely",
    "worldly", "godly", "ungodly", "heavenly",
    "earthly", "kindly", "saintly", "scholarly",
    "priestly", "kingly", "queenly", "princely",
    "courtly", "stately", "portly", "burly",
    "curly", "surly", "jolly", "holy",
    "lowly", "seemly", "unseemly",
    "daily", "weekly", "monthly", "yearly",
    "hourly", "nightly", "early",
    "silly", "chilly", "hilly",
    "oily", "woolly", "bubbly", "crinkly",
    "prickly", "wrinkly", "sparkly",
    "smelly", "belly",
})

# ── EN suffix rules (longest-first within category) ──────────
_EN_NOUN_SUFFIXES = (
    "tion", "sion", "ment", "ness", "ity",
    "ance", "ence", "ism", "ist", "dom",
    "ship", "hood", "ure", "age", "ery",
    "ory", "ary", "eum", "ium",
    "ling", "ette", "let",
)

_EN_ADJ_SUFFIXES = (
    "ical", "ious", "eous", "ious", "uous",
    "ible", "able", "ible", "ful", "less",
    "ive", "ial", "ous", "ish", "ary",
    "ory", "ent", "ant", "ese",
    "ic", "al",
)

_EN_VERB_SUFFIXES = (
    "ize", "ise", "ate", "ify", "en",
)

_EN_ADV_SUFFIX = "ly"

# ═══════════════════════════════════════════════════════════════
# Russian data
# ═══════════════════════════════════════════════════════════════

_RU_EXCEPTIONS: Dict[str, str] = {}

# ── Prepositions ──────────────────────────────────────────────
for _w in (
    "в", "на", "с", "к", "по", "из", "за", "о",
    "до", "от", "при", "для", "без", "через",
    "между", "перед", "над", "под", "про", "ко",
    "во", "обо", "изо", "со", "ото", "подо",
    "надо", "передо", "около", "возле", "вокруг",
    "вдоль", "поперёк", "мимо", "после", "среди",
    "против", "насчёт", "вместо", "помимо",
    "кроме", "сквозь", "ради", "вследствие",
    "благодаря", "напротив", "навстречу",
    "наподобие", "вроде", "посреди",
):
    _RU_EXCEPTIONS[_w] = PREP

# ── Conjunctions ──────────────────────────────────────────────
for _w in (
    "и", "а", "но", "или", "что", "как", "если",
    "когда", "чтобы", "хотя", "потому", "поэтому",
    "однако", "либо", "зато", "причём", "притом",
    "будто", "словно", "точно", "ибо", "раз",
    "пока", "ведь", "тоже", "также", "затем",
    "оттого", "отчего", "покуда", "покамест",
    "дабы", "коли", "ежели",
):
    _RU_EXCEPTIONS[_w] = CONJ

# ── Pronouns ─────────────────────────────────────────────────
for _w in (
    "я", "ты", "он", "она", "оно", "мы", "вы",
    "они", "мне", "тебе", "ему", "ей", "нам",
    "вам", "им", "меня", "тебя", "его", "её",
    "нас", "вас", "их", "себя", "себе", "собой",
    "кто", "что", "который", "какой", "чей",
    "этот", "тот", "весь", "каждый", "сам",
    "мой", "твой", "свой", "наш", "ваш",
    "кого", "чего", "кому", "чему", "кем", "чем",
    "какого", "какому", "каким", "каком", "какая",
    "какое", "какие", "этого", "этому", "этим",
    "этом", "эта", "это", "эти", "того", "тому",
    "тем", "том", "та", "то", "те",
    "всего", "всему", "всем", "всём", "вся", "все",
    "самого", "самому", "самим", "самом",
    "сама", "само", "сами",
    "некто", "нечто", "некого", "нечего",
    "никто", "ничто", "никого", "ничего",
    "некоторый", "несколько",
):
    _RU_EXCEPTIONS[_w] = PRON

# ── Particles ─────────────────────────────────────────────────
for _w in (
    "не", "ни", "бы", "же", "ли", "ведь", "вот",
    "вон", "уже", "ещё", "даже", "только", "именно",
    "лишь", "разве", "неужели", "ка", "то",
    "либо", "нибудь", "таки", "мол", "дескать",
    "якобы", "авось", "пусть", "пускай",
    "давай", "давайте", "да", "нет",
):
    _RU_EXCEPTIONS[_w] = PART

# ── Adverbs ───────────────────────────────────────────────────
for _w in (
    "очень", "тоже", "также", "здесь", "тут",
    "там", "сюда", "туда", "потом", "теперь",
    "сейчас", "всегда", "никогда", "часто",
    "редко", "обычно", "вместе", "отсюда",
    "оттуда", "куда", "откуда", "везде", "всюду",
    "нигде", "никуда", "ниоткуда", "где",
    "быстро", "медленно", "хорошо", "плохо",
    "много", "мало", "сильно", "слабо",
    "давно", "недавно", "рано", "поздно",
    "высоко", "низко", "далеко", "близко",
    "легко", "трудно", "тихо", "громко",
    "просто", "сложно", "ясно", "верно",
    "точно", "прямо", "наверно", "наверное",
    "конечно", "может", "видимо", "вероятно",
    "случайно", "обязательно", "совершенно",
    "абсолютно", "совсем", "вполне", "достаточно",
    "слишком", "чуть", "почти", "около",
    "примерно", "приблизительно", "едва",
    "чересчур", "весьма", "крайне",
    "наконец", "снова", "опять", "вдруг",
    "сразу", "тотчас", "немедленно",
    "постепенно", "постоянно", "вечно",
    "иногда", "порой", "подчас", "впервые",
    "дважды", "трижды", "наверху", "внизу",
    "справа", "слева", "впереди", "позади",
    "снаружи", "внутри",
):
    _RU_EXCEPTIONS[_w] = ADV

# ── Common RU verbs ───────────────────────────────────────────
for _w in (
    "быть", "есть", "было", "будет", "стать",
    "мочь", "может", "могут", "хотеть", "хочет",
    "хочу", "хотим", "хотят", "хотите",
    "знать", "знает", "думать", "думает",
    "говорить", "говорит", "сказать", "скажет",
    "видеть", "видит", "дать", "даёт",
    "идти", "идёт", "стоять", "стоит",
    "жить", "живёт", "работать", "работает",
    "делать", "делает", "сделать",
    "взять", "возьмёт", "писать", "пишет",
    "читать", "читает", "любить", "любит",
    "иметь", "имеет", "понять", "поймёт",
    "помнить", "помнит", "ходить", "ходит",
    "нужно", "надо", "можно", "нельзя",
    "следует", "стоит", "пришлось",
    "казаться", "кажется", "оказаться",
    "считать", "считает", "решить", "решает",
    "начать", "начинает", "продолжать",
    "остаться", "остаётся", "получить",
    "получает", "найти", "находит",
    "поставить", "ставит", "положить", "кладёт",
    "бежать", "бежит", "лететь", "летит",
    "спать", "спит", "есть", "ест",
    "пить", "пьёт", "петь", "поёт",
    "играть", "играет", "учить", "учит",
    "учиться", "учится",
):
    _RU_EXCEPTIONS[_w] = VERB

# ── Common RU nouns ───────────────────────────
for _w in (
    "книга", "книгу", "книги", "книге", "книгой",
    "дом", "дома", "дому", "домом", "доме",
    "человек", "люди", "людей", "людям",
    "время", "день", "ночь", "год", "месяц",
    "город", "страна", "мир", "жизнь", "работа",
    "школа", "слово", "место", "вода", "земля",
    "рука", "голова", "глаз", "друг", "дело",
    "ребёнок", "дети", "женщина", "мужчина",
    "вопрос", "ответ", "час", "минута",
    "история", "дорога", "улица", "комната",
    "окно", "дверь", "стол", "стул", "машина",
    "деньги", "сила", "война", "мысль",
    "закон", "власть", "число", "имя",
    "путь", "правда", "ошибка", "помощь",
    "начало", "конец", "часть", "группа",
):
    if _w not in _RU_EXCEPTIONS:
        _RU_EXCEPTIONS[_w] = NOUN

# ── Common RU numbers ─────────────────────────────────────────
for _w in (
    "ноль", "один", "одна", "одно", "два", "две",
    "три", "четыре", "пять", "шесть", "семь",
    "восемь", "девять", "десять", "сто", "тысяча",
    "миллион", "миллиард", "первый", "второй",
    "третий", "четвёртый", "пятый", "шестой",
    "седьмой", "восьмой", "девятый", "десятый",
    "двадцать", "тридцать", "сорок", "пятьдесят",
    "шестьдесят", "семьдесят", "восемьдесят",
    "девяносто",
):
    _RU_EXCEPTIONS[_w] = NUM

# ── RU suffix rules ──────────────────────────────────────────
_RU_NOUN_SUFFIXES = (
    "ость", "ние", "ение", "мент", "ация",
    "яция", "тель", "щик", "чик", "ник",
    "ица", "ство", "тво", "ёнок", "онок",
    "ёк", "ок", "ек", "ка", "ша",
)

_RU_ADJ_SUFFIXES = (
    "ский", "ской", "ское", "ские",
    "ный", "ная", "ное", "ные",
    "ной", "ших", "ого",
    "ый", "ий", "ой", "ая", "яя",
    "ое", "ее", "ые", "ие",
)

_RU_VERB_INF_SUFFIXES = ("ть", "ти", "чь")

_RU_VERB_PRES_SUFFIXES = (
    "ует", "ёт", "ет", "ит", "ат", "ят",
    "ут", "ют", "ем", "им", "ам", "ям",
    "ешь", "ишь",
)

_RU_VERB_PAST_SUFFIXES = (
    "ал", "ил", "ел", "ул",
    "ла", "ло", "ли",
)

_RU_ADV_SUFFIXES = ("ски", "ьно", "ки")

# ═══════════════════════════════════════════════════════════════
# Ukrainian data
# ═══════════════════════════════════════════════════════════════

_UK_EXCEPTIONS: Dict[str, str] = {}

# ── Prepositions ──────────────────────────────────────────────
for _w in (
    "в", "у", "на", "з", "із", "зі", "до", "від",
    "по", "за", "о", "об", "при", "для", "без",
    "через", "між", "перед", "над", "під", "про",
    "ко", "біля", "поряд", "поруч", "навколо",
    "вздовж", "поперек", "мимо", "після", "серед",
    "проти", "замість", "крім", "крізь", "заради",
    "внаслідок", "завдяки", "напроти", "назустріч",
    "посеред", "щодо", "попри",
):
    _UK_EXCEPTIONS[_w] = PREP

# ── Conjunctions ──────────────────────────────────────────────
for _w in (
    "і", "й", "та", "а", "але", "або", "чи", "що",
    "як", "якщо", "коли", "щоб", "хоча", "тому",
    "бо", "проте", "зате", "причому", "притому",
    "нібито", "немов", "наче", "начебто",
    "поки", "адже", "також", "тож", "отже",
    "тобто", "себто",
):
    _UK_EXCEPTIONS[_w] = CONJ

# ── Pronouns ─────────────────────────────────────────────────
for _w in (
    "я", "ти", "він", "вона", "воно", "ми", "ви",
    "вони", "мені", "тобі", "йому", "їй", "нам",
    "вам", "їм", "мене", "тебе", "його", "її",
    "нас", "вас", "їх", "себе", "собі", "собою",
    "хто", "що", "який", "яка", "яке", "які",
    "чий", "чия", "чиє", "чиї",
    "цей", "ця", "це", "ці", "той", "та", "те", "ті",
    "весь", "вся", "все", "всі",
    "кожний", "кожна", "кожне", "кожні",
    "сам", "сама", "саме", "самі",
    "мій", "твій", "свій", "наш", "ваш",
    "моя", "твоя", "своя", "наша", "ваша",
    "моє", "твоє", "своє", "наше", "ваше",
    "мої", "твої", "свої", "наші", "ваші",
    "ніхто", "ніщо", "нікого", "нічого",
    "хтось", "щось", "дехто", "дещо",
):
    _UK_EXCEPTIONS[_w] = PRON

# ── Particles ─────────────────────────────────────────────────
for _w in (
    "не", "ні", "би", "б", "же", "ж", "чи",
    "ось", "от", "он", "ось", "ще", "навіть",
    "тільки", "лише", "саме", "якраз", "хіба",
    "невже", "так", "ні", "хай", "нехай",
    "давай", "давайте",
):
    _UK_EXCEPTIONS[_w] = PART

# ── Adverbs ───────────────────────────────────────────────────
for _w in (
    "дуже", "також", "тут", "там", "сюди", "туди",
    "потім", "тепер", "зараз", "завжди", "ніколи",
    "часто", "рідко", "зазвичай", "разом", "звідси",
    "звідти", "куди", "звідки", "скрізь", "всюди",
    "ніде", "нікуди", "нізвідки", "де",
    "швидко", "повільно", "добре", "погано",
    "багато", "мало", "сильно", "слабо",
    "давно", "нещодавно", "рано", "пізно",
    "високо", "низько", "далеко", "близько",
    "легко", "важко", "тихо", "голосно",
    "просто", "складно", "ясно", "вірно",
    "точно", "прямо", "мабуть", "напевно",
    "звичайно", "може", "мабуть", "ймовірно",
    "випадково", "обов'язково", "цілком",
    "абсолютно", "зовсім", "цілком", "досить",
    "занадто", "трохи", "майже", "ледве",
    "надто", "вельми", "вкрай",
    "нарешті", "знову", "раптом", "одразу",
    "негайно", "поступово", "постійно",
    "іноді", "інколи", "вперше",
    "двічі", "тричі", "нагорі", "внизу",
    "праворуч", "ліворуч", "попереду", "позаду",
    "зовні", "всередині",
):
    _UK_EXCEPTIONS[_w] = ADV

# ── Common UK verbs ───────────────────────────────────────────
for _w in (
    "бути", "є", "було", "буде",
    "могти", "може", "можуть",
    "хотіти", "хоче", "знати", "знає",
    "думати", "думає", "говорити", "говорить",
    "сказати", "скаже", "бачити", "бачить",
    "дати", "дає", "іти", "іде",
    "стояти", "стоїть", "жити", "живе",
    "працювати", "працює", "робити", "робить",
    "зробити", "писати", "пише",
    "читати", "читає", "любити", "любить",
    "мати", "має", "зрозуміти", "зрозуміє",
    "пам'ятати", "пам'ятає",
    "ходити", "ходить", "треба", "можна",
    "не можна", "слід",
    "хочу", "хочемо", "хочете", "хочуть",
):
    _UK_EXCEPTIONS[_w] = VERB

# ── Common UK nouns ───────────────────────────
for _w in (
    "книга", "книгу", "книги", "книзі",
    "книгою", "дім", "дому", "будинок",
    "людина", "люди", "людей", "людям",
    "час", "день", "ніч", "рік", "місяць",
    "місто", "країна", "світ", "життя",
    "робота", "школа", "слово", "місце",
    "вода", "земля", "рука", "голова",
    "око", "друг", "справа", "дитина",
    "діти", "жінка", "чоловік", "питання",
    "відповідь", "година", "хвилина",
    "історія", "дорога", "вулиця", "кімната",
    "вікно", "двері", "стіл", "стілець",
    "машина", "гроші", "сила", "війна",
    "думка", "закон", "влада", "число",
    "ім'я", "шлях", "правда", "помилка",
    "допомога", "початок", "кінець",
    "частина", "група",
):
    if _w not in _UK_EXCEPTIONS:
        _UK_EXCEPTIONS[_w] = NOUN

# ── UK numbers ────────────────────────────────────────────────
for _w in (
    "нуль", "один", "одна", "одне", "два", "дві",
    "три", "чотири", "п'ять", "шість", "сім",
    "вісім", "дев'ять", "десять", "сто", "тисяча",
    "мільйон", "мільярд", "перший", "другий",
    "третій", "четвертий", "п'ятий", "шостий",
    "сьомий", "восьмий", "дев'ятий", "десятий",
    "двадцять", "тридцять", "сорок",
):
    _UK_EXCEPTIONS[_w] = NUM

# ── UK suffix rules ──────────────────────────────────────────
_UK_NOUN_SUFFIXES = (
    "ість", "ння", "ення", "тель", "щик",
    "чик", "ник", "ство", "тво", "ця",
    "ка", "ша", "ок", "ець",
)

_UK_ADJ_SUFFIXES = (
    "ський", "ська", "ське", "ські",
    "ний", "ній", "на", "не", "ні",
    "ий", "ій", "а", "я", "е", "є",
)

_UK_VERB_INF_SUFFIXES = ("ти", "ть", "чи")

_UK_VERB_PRES_SUFFIXES = (
    "ує", "є", "ить", "ять", "ать",
    "ить", "ять", "уть", "ють",
    "емо", "имо", "ете", "ите",
    "еш", "иш",
)

_UK_VERB_PAST_SUFFIXES = (
    "ав", "ив", "ів",
    "ла", "ло", "ли",
)

_UK_ADV_SUFFIXES = ("ськи", "ьно", "ки")

# ═══════════════════════════════════════════════════════════════
# German data
# ═══════════════════════════════════════════════════════════════

# Common German nouns ending in -t that are NOT verbs
_DE_T_NOUNS: frozenset[str] = frozenset({
    "arbeit", "angst", "dienst", "frost", "gunst",
    "kunst", "macht", "nacht", "pracht", "recht",
    "markt", "welt", "zeit", "arzt", "wurst",
    "geist", "gast", "ast", "brust", "lust",
    "faust", "haut", "brut", "blut", "glut",
    "wut", "mut", "gut", "rat", "staat",
    "draht", "tat", "saat", "naht", "fahrt",
    "art", "wort", "ort", "sort", "sport",
    "bart", "start", "chart", "hart",
    "amt", "hemd", "punkt", "stadt",
    "frucht", "flucht", "zucht", "sucht",
    "sicht", "schicht", "pflicht", "licht",
    "gift", "schrift", "kraft", "luft", "kluft",
    "vernunft", "ankunft", "zukunft", "herkunft",
    "knecht", "fracht", "schlacht", "tracht",
})

_DE_EXCEPTIONS: Dict[str, str] = {}

# ── Articles / Determiners ────────────────────────────────────
for _w in (
    "der", "die", "das", "den", "dem", "des",
    "ein", "eine", "einem", "einen", "einer",
    "eines", "kein", "keine", "keinem", "keinen",
    "keiner", "keines", "mein", "meine", "meinem",
    "meinen", "meiner", "meines", "dein", "deine",
    "deinem", "deinen", "deiner", "deines",
    "sein", "seine", "seinem", "seinen", "seiner",
    "seines", "ihr", "ihre", "ihrem", "ihren",
    "ihrer", "ihres", "unser", "unsere", "unserem",
    "unseren", "unserer", "unseres", "euer",
    "eure", "eurem", "euren", "eurer", "eures",
    "dieser", "diese", "diesem", "diesen",
    "dieses", "jener", "jene", "jenem", "jenen",
    "jener", "jenes", "jeder", "jede", "jedem",
    "jeden", "jedes", "welcher", "welche",
    "welchem", "welchen", "welches",
    "mancher", "manche", "manchem", "manchen",
    "manches", "solcher", "solche", "solchem",
    "solchen", "solches", "alle", "allem",
    "allen", "aller", "alles", "beide", "beiden",
    "einige", "einigen", "einiger", "einiges",
    "mehrere", "mehreren", "viel", "viele",
    "vielem", "vielen", "vieler", "wenig",
    "wenige", "wenigem", "wenigen", "weniger",
):
    _DE_EXCEPTIONS[_w] = DET

# ── Prepositions ──────────────────────────────────────────────
for _w in (
    "in", "an", "auf", "zu", "für", "mit", "von",
    "aus", "nach", "bei", "über", "unter", "vor",
    "hinter", "neben", "zwischen", "durch",
    "gegen", "ohne", "um", "bis", "seit", "während",
    "wegen", "trotz", "statt", "anstatt",
    "außerhalb", "innerhalb", "oberhalb",
    "unterhalb", "diesseits", "jenseits",
    "entlang", "gegenüber", "gemäß", "laut",
    "mittels", "samt", "nebst", "dank", "kraft",
    "mangels", "zufolge", "zuliebe",
    "ab", "außer", "binnen", "halber",
):
    _DE_EXCEPTIONS[_w] = PREP

# ── Conjunctions ──────────────────────────────────────────────
for _w in (
    "und", "oder", "aber", "denn", "sondern",
    "doch", "jedoch", "dass", "ob", "weil",
    "wenn", "als", "obwohl", "obgleich",
    "während", "bevor", "nachdem", "damit",
    "sodass", "falls", "sofern", "soweit",
    "solange", "sobald", "seitdem", "bis",
    "indem", "also", "deshalb", "daher",
    "dennoch", "trotzdem", "außerdem",
    "nämlich", "allerdings", "andererseits",
    "folglich", "hingegen", "immerhin",
    "insofern", "insbesondere", "jedenfalls",
    "schließlich", "überdies", "übrigens",
    "weder", "noch", "sowohl", "entweder",
    "beziehungsweise",
):
    _DE_EXCEPTIONS[_w] = CONJ

# ── Pronouns ─────────────────────────────────────────────────
for _w in (
    "ich", "du", "er", "sie", "es", "wir", "ihr",
    "mich", "dich", "ihn", "uns", "euch",
    "mir", "dir", "ihm", "ihnen",
    "sich", "man", "wer", "wen", "wem", "wessen",
    "was", "wo", "wie", "warum", "weshalb",
    "wieso", "wohin", "woher", "wann",
    "jemand", "niemand", "etwas", "nichts",
    "selbst", "selber", "einander",
):
    _DE_EXCEPTIONS[_w] = PRON

# ── Adverbs ───────────────────────────────────────────────────
for _w in (
    "sehr", "auch", "schon", "noch", "nur", "immer",
    "nie", "niemals", "oft", "manchmal", "selten",
    "hier", "dort", "da", "jetzt", "nun", "dann",
    "bald", "vielleicht", "wohl", "gern", "gerne",
    "fast", "kaum", "etwa", "ungefähr",
    "genau", "eben", "bereits", "gleich",
    "sofort", "sogar", "ziemlich", "etwas",
    "besonders", "wirklich", "tatsächlich",
    "eigentlich", "natürlich", "sicher",
    "bestimmt", "wahrscheinlich", "hoffentlich",
    "leider", "glücklicherweise", "normalerweise",
    "meistens", "gewöhnlich", "plötzlich",
    "oben", "unten", "links", "rechts",
    "vorn", "vorne", "hinten", "draußen",
    "drinnen", "überall", "nirgends",
    "nirgendwo", "irgendwo", "dahin", "dorthin",
    "hierhin", "hin", "her", "herein", "heraus",
    "hinein", "hinaus", "damals", "früher",
    "später", "heute", "morgen", "gestern",
    "abends", "morgens", "nachts", "täglich",
    "wöchentlich", "monatlich", "jährlich",
    "ebenso", "genauso", "insgesamt", "zuerst",
    "zuletzt", "zunächst", "vorher", "nachher",
    "unterdessen", "inzwischen", "endlich",
    "ohnehin", "sowieso", "jedenfalls",
    "allerdings", "freilich", "immerhin",
    "nochmals", "abermals", "wiederum",
    "demnach", "demzufolge",
):
    _DE_EXCEPTIONS[_w] = ADV

# ── Common DE verbs ───────────────────────────────────────────
for _w in (
    "sein", "ist", "bin", "bist", "sind", "seid",
    "war", "warst", "waren", "wart", "gewesen",
    "haben", "hat", "habe", "hast", "habt",
    "hatte", "hattest", "hatten", "hattet",
    "gehabt", "werden", "wird", "werde", "wirst",
    "werdet", "wurde", "wurdest", "wurden",
    "wurdet", "geworden",
    "können", "kann", "kannst", "könnt", "konnte",
    "konntest", "konnten", "konntet", "gekonnt",
    "müssen", "muss", "musst", "müsst", "musste",
    "musstest", "mussten", "musstet", "gemusst",
    "sollen", "soll", "sollst", "sollt", "sollte",
    "solltest", "sollten", "solltet", "gesollt",
    "wollen", "will", "willst", "wollt", "wollte",
    "wolltest", "wollten", "wolltet", "gewollt",
    "dürfen", "darf", "darfst", "dürft", "durfte",
    "durftest", "durften", "durftet", "gedurft",
    "mögen", "mag", "magst", "mögt", "mochte",
    "mochtest", "mochten", "mochtet", "gemocht",
    "gehen", "geht", "ging", "gegangen",
    "kommen", "kommt", "kam", "gekommen",
    "machen", "macht", "machte", "gemacht",
    "geben", "gibt", "gab", "gegeben",
    "nehmen", "nimmt", "nahm", "genommen",
    "finden", "findet", "fand", "gefunden",
    "sagen", "sagt", "sagte", "gesagt",
    "wissen", "weiß", "weißt", "wisst",
    "wusste", "gewusst",
    "stehen", "steht", "stand", "gestanden",
    "lassen", "lässt", "ließ", "gelassen",
    "sehen", "sieht", "sah", "gesehen",
    "bringen", "bringt", "brachte", "gebracht",
    "denken", "denkt", "dachte", "gedacht",
    "sprechen", "spricht", "sprach", "gesprochen",
    "lesen", "liest", "las", "gelesen",
    "schreiben", "schreibt", "schrieb",
    "geschrieben",
    "fahren", "fährt", "fuhr", "gefahren",
    "essen", "isst", "gegessen",
    "trinken", "trinkt", "trank", "getrunken",
    "schlafen", "schläft", "schlief",
    "geschlafen",
    "laufen", "läuft", "lief", "gelaufen",
    "tragen", "trägt", "trug", "getragen",
    "helfen", "hilft", "half", "geholfen",
    "spielen", "spielt", "spielte", "gespielt",
    "arbeiten", "arbeitet", "arbeitete",
    "gearbeitet",
    "leben", "lebt", "lebte", "gelebt",
    "lieben", "liebt", "liebte", "geliebt",
    "lernen", "lernt", "lernte", "gelernt",
    "kaufen", "kauft", "kaufte", "gekauft",
    "verkaufen", "verkauft", "verkaufte",
    "verkauft",
    "öffnen", "öffnet", "öffnete", "geöffnet",
    "schließen", "schließt", "schloss",
    "geschlossen",
    "beginnen", "beginnt", "begann", "begonnen",
    "versuchen", "versucht", "versuchte",
    "versucht",
    "brauchen", "braucht", "brauchte",
    "gebraucht",
    "glauben", "glaubt", "glaubte", "geglaubt",
    "heißen", "heißt", "hieß", "geheißen",
    "kennen", "kennt", "kannte", "gekannt",
    "setzen", "setzt", "setzte", "gesetzt",
    "stellen", "stellt", "stellte", "gestellt",
    "legen", "legt", "legte", "gelegt",
    "ziehen", "zieht", "zog", "gezogen",
    "bleiben", "bleibt", "blieb", "geblieben",
    "fallen", "fällt", "fiel", "gefallen",
    "halten", "hält", "hielt", "gehalten",
    "tun", "tut", "tat", "getan",
    "liegen", "liegt", "lag", "gelegen",
    "sitzen", "sitzt", "saß", "gesessen",
    "folgen", "folgt", "folgte", "gefolgt",
    "verlieren", "verliert", "verlor", "verloren",
    "gewinnen", "gewinnt", "gewann", "gewonnen",
    "erreichen", "erreicht", "erreichte",
    "erreicht",
    "verstehen", "versteht", "verstand",
    "verstanden",
    "erhalten", "erhält", "erhielt", "erhalten",
    "führen", "führt", "führte", "geführt",
    "zeigen", "zeigt", "zeigte", "gezeigt",
    "bieten", "bietet", "bot", "geboten",
    "gehören", "gehört", "gehörte", "gehört",
    "scheinen", "scheint", "schien", "geschienen",
    "meinen", "meint", "meinte", "gemeint",
    "fragen", "fragt", "fragte", "gefragt",
    "rufen", "ruft", "rief", "gerufen",
    "warten", "wartet", "wartete", "gewartet",
    "hören", "hört", "hörte", "gehört",
    "fühlen", "fühlt", "fühlte", "gefühlt",
):
    _DE_EXCEPTIONS[_w] = VERB

# ── Common DE numbers ─────────────────────────────────────────
for _w in (
    "null", "eins", "zwei", "drei", "vier", "fünf",
    "sechs", "sieben", "acht", "neun", "zehn",
    "elf", "zwölf", "hundert", "tausend",
    "million", "milliarde", "erste", "zweite",
    "dritte", "vierte", "fünfte", "sechste",
    "siebte", "achte", "neunte", "zehnte",
    "zwanzig", "dreißig", "vierzig", "fünfzig",
    "sechzig", "siebzig", "achtzig", "neunzig",
    "erster", "ersten", "erstem", "erstes",
    "letzter", "letzte", "letztem", "letzten",
    "letztes",
):
    _DE_EXCEPTIONS[_w] = NUM

# ── Common DE adjectives ─────────────────────────────────────
for _w in (
    "gut", "schlecht", "groß", "klein", "alt",
    "neu", "jung", "lang", "kurz", "hoch",
    "tief", "breit", "eng", "dick", "dünn",
    "schwer", "leicht", "stark", "schwach",
    "schnell", "langsam", "laut", "leise",
    "hell", "dunkel", "warm", "kalt", "heiß",
    "nass", "trocken", "voll", "leer", "rund",
    "glatt", "rau", "weich", "hart", "fest",
    "locker", "sauber", "schmutzig", "schön",
    "hässlich", "reich", "arm", "teuer", "billig",
    "wichtig", "richtig", "falsch", "wahr",
    "frei", "offen", "geschlossen", "fertig",
    "bereit", "müde", "wach", "gesund", "krank",
    "tot", "lebendig", "nötig", "möglich",
    "unmöglich", "einfach", "schwierig",
    "verschieden", "gleich", "ähnlich",
    "bekannt", "fremd", "seltsam",
):
    _DE_EXCEPTIONS[_w] = ADJ

# Generate declined adjective forms (e/er/en/em/es)
_de_adj_bases = list(_DE_EXCEPTIONS.keys())
for _base in _de_adj_bases:
    if _DE_EXCEPTIONS.get(_base) != ADJ:
        continue
    for _sfx in ("e", "er", "en", "em", "es"):
        _form = _base + _sfx
        if _form not in _DE_EXCEPTIONS:
            _DE_EXCEPTIONS[_form] = ADJ

# ── Common DE nouns ───────────────────────────────────────────
for _w in (
    "zeit", "jahr", "mensch", "mann", "frau",
    "kind", "tag", "welt", "leben", "hand",
    "teil", "platz", "ort", "fall", "woche",
    "nacht", "frage", "arbeit", "stadt", "land",
    "haus", "wort", "kopf", "auge", "name",
    "seite", "ende", "bild", "weg", "grund",
    "stunde", "stimme", "freund", "tür", "geld",
    "macht", "wasser", "buch", "erde", "herr",
    "eltern", "schule", "staat", "recht",
    "krieg", "geschichte", "straße", "sache",
    "stelle", "idee", "morgen", "abend", "sonne",
    "mond", "stern", "himmel", "berg", "fluss",
    "meer", "wald", "baum", "blume", "tier",
    "hund", "katze", "vogel", "fisch",
):
    if _w not in _DE_EXCEPTIONS:
        _DE_EXCEPTIONS[_w] = NOUN

# ── DE interjections ──────────────────────────────────────────
for _w in (
    "ach", "oh", "na", "nein", "ja", "hallo",
    "tschüss", "danke", "bitte", "hurra",
    "pfui", "igitt", "aua", "huch", "ups",
    "mensch", "donnerwetter",
):
    _DE_EXCEPTIONS[_w] = INTJ

# ── DE suffix rules ──────────────────────────────────────────
_DE_NOUN_SUFFIXES = (
    "schaft", "ung", "heit", "keit", "nis",
    "tum", "ling", "chen", "lein",
)

_DE_ADJ_SUFFIXES = (
    "lich", "isch", "haft", "bar", "sam",
    "los", "ig", "ern", "voll",
)

_DE_VERB_SUFFIXES = ("en", "ern", "eln")

_DE_VERB_CONJ_SUFFIXES = (
    "st", "te", "tet", "ten",
)

_DE_ADV_SUFFIXES = ("weise", "lich")

# ═══════════════════════════════════════════════════════════════
# POSTagger class
# ═══════════════════════════════════════════════════════════════

class POSTagger:
    """Rule-based POS tagger for EN, RU, UK, DE.

    Thread-safe, no external dependencies.

    Parameters
    ----------
    lang : str
        Language code: ``"en"``, ``"ru"``, ``"uk"``,
        or ``"de"``.  Case-insensitive.
    """

    __slots__ = (
        "_lang",
        "_exceptions",
        "_noun_sfx",
        "_adj_sfx",
        "_verb_sfx",
        "_adv_sfx",
        "_verb_inf_sfx",
        "_verb_pres_sfx",
        "_verb_past_sfx",
        "_lock",
    )

    def __init__(self, lang: str = "en") -> None:
        self._lang = lang.lower().strip()
        self._lock = threading.Lock()
        self._verb_inf_sfx: Tuple[str, ...] = ()
        self._verb_pres_sfx: Tuple[str, ...] = ()
        self._verb_past_sfx: Tuple[str, ...] = ()

        if self._lang == "en":
            self._exceptions = _EN_EXCEPTIONS
            self._noun_sfx = _EN_NOUN_SUFFIXES
            self._adj_sfx = _EN_ADJ_SUFFIXES
            self._verb_sfx = _EN_VERB_SUFFIXES
            self._adv_sfx = (_EN_ADV_SUFFIX,)
        elif self._lang == "ru":
            self._exceptions = _RU_EXCEPTIONS
            self._noun_sfx = _RU_NOUN_SUFFIXES
            self._adj_sfx = _RU_ADJ_SUFFIXES
            self._verb_sfx = ()
            self._adv_sfx = _RU_ADV_SUFFIXES
            self._verb_inf_sfx = _RU_VERB_INF_SUFFIXES
            self._verb_pres_sfx = _RU_VERB_PRES_SUFFIXES
            self._verb_past_sfx = _RU_VERB_PAST_SUFFIXES
        elif self._lang == "uk":
            self._exceptions = _UK_EXCEPTIONS
            self._noun_sfx = _UK_NOUN_SUFFIXES
            self._adj_sfx = _UK_ADJ_SUFFIXES
            self._verb_sfx = ()
            self._adv_sfx = _UK_ADV_SUFFIXES
            self._verb_inf_sfx = _UK_VERB_INF_SUFFIXES
            self._verb_pres_sfx = _UK_VERB_PRES_SUFFIXES
            self._verb_past_sfx = _UK_VERB_PAST_SUFFIXES
        elif self._lang == "de":
            self._exceptions = _DE_EXCEPTIONS
            self._noun_sfx = _DE_NOUN_SUFFIXES
            self._adj_sfx = _DE_ADJ_SUFFIXES
            self._verb_sfx = _DE_VERB_SUFFIXES
            self._adv_sfx = _DE_ADV_SUFFIXES
        else:
            raise ValueError(
                f"Unsupported language: {self._lang!r}. "
                "Use 'en', 'ru', 'uk', or 'de'."
            )

    # ── Public API ────────────────────────────────────────────

    @property
    def lang(self) -> str:
        """Return the language code."""
        return self._lang

    def tag(
        self, text: str,
    ) -> List[Tuple[str, str]]:
        """Tag all tokens in *text*.

        Returns a list of ``(word, tag)`` tuples.
        Punctuation tokens get the ``PUNCT`` tag.
        """
        tokens = _TOKEN_RE.findall(text)
        if not tokens:
            return []

        result: List[Tuple[str, str]] = []
        prev_word: Optional[str] = None
        prev_tag: Optional[str] = None

        for tok in tokens:
            tag = self._tag_single(
                tok, prev_word, prev_tag
            )
            result.append((tok, tag))
            prev_word = tok.lower()
            prev_tag = tag

        return result

    def tag_word(
        self,
        word: str,
        prev: Optional[str] = None,
        prev_tag: Optional[str] = None,
    ) -> str:
        """Tag a single *word*.

        Optional *prev* (previous word) and *prev_tag*
        (previous POS tag) improve disambiguation.
        """
        return self._tag_single(
            word,
            prev.lower() if prev else None,
            prev_tag,
        )

    def is_noun(self, word: str) -> bool:
        """Check if *word* is tagged as NOUN."""
        return self.tag_word(word) == NOUN

    def is_verb(self, word: str) -> bool:
        """Check if *word* is tagged as VERB."""
        return self.tag_word(word) == VERB

    def is_adj(self, word: str) -> bool:
        """Check if *word* is tagged as ADJ."""
        return self.tag_word(word) == ADJ

    def is_adv(self, word: str) -> bool:
        """Check if *word* is tagged as ADV."""
        return self.tag_word(word) == ADV

    # ── Internal ──────────────────────────────────────────────

    def _tag_single(
        self,
        token: str,
        prev_word: Optional[str],
        prev_tag: Optional[str],
    ) -> str:
        """Core tagging logic for a single token."""
        # Punctuation
        if _PUNCT_RE.match(token):
            return PUNCT

        # Numeric
        if _NUM_RE.match(token):
            return NUM

        low = token.lower()

        # Exception dictionary lookup
        exc_tag = self._exceptions.get(low)
        if exc_tag is not None:
            # Context-based override for English
            tag = self._apply_context(
                low, exc_tag, prev_word, prev_tag,
            )
            return tag

        # Suffix-based tagging
        tag = self._suffix_tag(low)

        # Context refinement
        tag = self._apply_context(
            low, tag, prev_word, prev_tag,
        )

        # German: capitalize → likely noun
        if (
            self._lang == "de"
            and tag == X
            and token[0:1].isupper()
        ):
            tag = NOUN

        return tag

    def _suffix_tag(self, low: str) -> str:
        """Assign POS based on suffix rules."""
        length = len(low)
        if length < 2:
            return X

        # ── English-specific suffix logic ─────────────────
        if self._lang == "en":
            return self._en_suffix_tag(low, length)

        # ── German-specific suffix logic ──────────────────
        if self._lang == "de":
            return self._de_suffix_tag(low, length)

        # ── Slavic (RU / UK) verb infinitive ──────────────
        if self._lang in ("ru", "uk"):
            for sfx in self._verb_inf_sfx:
                if low.endswith(sfx):
                    return VERB

        # ── Noun suffixes ─────────────────────────────────
        for sfx in self._noun_sfx:
            if low.endswith(sfx) and length > len(sfx) + 1:
                return NOUN

        # ── Adjective suffixes ────────────────────────────
        for sfx in self._adj_sfx:
            if low.endswith(sfx) and length > len(sfx) + 1:
                return ADJ

        # ── Slavic present-tense verb ─────────────────────
        for sfx in self._verb_pres_sfx:
            if low.endswith(sfx) and length > len(sfx) + 1:
                return VERB

        # ── Slavic past-tense verb ────────────────────────
        for sfx in self._verb_past_sfx:
            if low.endswith(sfx) and length > len(sfx) + 1:
                return VERB

        # ── Generic verb suffixes ─────────────────────────
        for sfx in self._verb_sfx:
            if low.endswith(sfx) and length > len(sfx) + 1:
                return VERB

        # ── Adverb suffixes ───────────────────────────────
        for sfx in self._adv_sfx:
            if low.endswith(sfx) and length > len(sfx) + 1:
                return ADV

        return X

    def _en_suffix_tag(
        self, low: str, length: int,
    ) -> str:
        """English-specific suffix rules."""
        # -ly → ADV (with adjective exceptions)
        if low.endswith("ly") and length > 3:
            if low in _EN_LY_ADJ:
                return ADJ
            return ADV

        # -ing → VERB (gerund / present participle)
        if low.endswith("ing") and length > 4:
            return VERB

        # -ed → VERB (past tense / past participle)
        if low.endswith("ed") and length > 3:
            return VERB

        # -est → ADJ (superlative)
        if low.endswith("est") and length > 4:
            return ADJ

        # -er → context-dependent (ADJ comparative or NOUN agent)
        if low.endswith("er") and length > 3:
            # Common agent-noun suffixes (-eer, -ier always NOUN)
            if low.endswith(("eer", "ier")):
                return NOUN
            if low in _EN_COMP_DOUBLED:
                return ADJ
            if low in _EN_COMP_REGULAR:
                return ADJ
            # Heuristic: if the word without -er (or -r) is in common
            # short adjective patterns (≤6 chars base + er), lean ADJ
            base = low[:-2] if not low.endswith("ier") else low[:-3] + "y"
            if len(base) <= 6 and base.endswith(
                ("t", "d", "g", "k", "p", "n", "l", "w", "m")
            ):
                # Could be comparative — but default to NOUN since
                # agent nouns are more common overall
                pass
            # Default: agent noun (teacher, writer, player, etc.)
            return NOUN

        # Noun suffixes
        for sfx in self._noun_sfx:
            if low.endswith(sfx) and length > len(sfx) + 1:
                return NOUN

        # Adjective suffixes
        for sfx in self._adj_sfx:
            if low.endswith(sfx) and length > len(sfx) + 1:
                return ADJ

        # Verb suffixes (-ize, -ise, -ate, -ify, -en)
        for sfx in self._verb_sfx:
            if low.endswith(sfx) and length > len(sfx) + 1:
                return VERB

        # -s → check if base is a known verb
        if low.endswith("s") and length > 3:
            base = low[:-1]
            if self._exceptions.get(base) == VERB:
                return VERB
            # -es → base without -es
            if (
                low.endswith("es")
                and length > 4
            ):
                base2 = low[:-2]
                if (
                    self._exceptions.get(base2)
                    == VERB
                ):
                    return VERB
            # Default: noun plural
            return NOUN

        return X

    def _de_suffix_tag(
        self, low: str, length: int,
    ) -> str:
        """German-specific suffix rules."""
        # Past participle: ge-...-t / ge-...-en
        if (
            low.startswith("ge")
            and length > 4
        ):
            if low.endswith("t") or low.endswith("en"):
                return VERB

        # Noun suffixes (longest first)
        for sfx in _DE_NOUN_SUFFIXES:
            if (
                low.endswith(sfx)
                and length > len(sfx) + 1
            ):
                return NOUN

        # Adjective suffixes
        for sfx in _DE_ADJ_SUFFIXES:
            if (
                low.endswith(sfx)
                and length > len(sfx) + 1
            ):
                return ADJ

        # Verb infinitive suffixes (-en, -ern, -eln)
        for sfx in _DE_VERB_SUFFIXES:
            if (
                low.endswith(sfx)
                and length > len(sfx) + 1
            ):
                return VERB

        # Verb conjugation (-st, -te, -tet, -ten)
        for sfx in _DE_VERB_CONJ_SUFFIXES:
            if (
                low.endswith(sfx)
                and length > len(sfx) + 2
            ):
                return VERB

        # 3rd person singular -t (springt, kommt)
        # BUT many German nouns end in -t (Arbeit, Angst, Dienst, etc.)
        # Only tag as VERB if it doesn't match common noun patterns.
        if low.endswith("t") and length > 3:
            if low in _DE_T_NOUNS:
                return NOUN
            # Capitalized words in German are usually nouns
            # (handled elsewhere), so here we only tag lowercase
            # words ending in -t as likely verb forms.
            return VERB

        # Adverb suffixes (-weise, -lich)
        for sfx in _DE_ADV_SUFFIXES:
            if (
                low.endswith(sfx)
                and length > len(sfx) + 1
            ):
                return ADV

        return X

    def _apply_context(
        self,
        low: str,
        tag: str,
        prev_word: Optional[str],
        prev_tag: Optional[str],
    ) -> str:
        """Refine *tag* using contextual clues."""
        if prev_tag is None and prev_word is None:
            return tag

        # ── English context rules ─────────────────────────
        if self._lang == "en":
            return self._en_context(
                low, tag, prev_word, prev_tag,
            )

        # ── Generic context rules (all languages) ────────
        if prev_tag == DET:
            if tag in (X, VERB, ADV):
                return NOUN
            if tag == ADJ:
                return ADJ  # DET + ADJ is fine
        if prev_tag == PREP:
            if tag in (X, VERB, ADV):
                return NOUN
        if prev_tag == ADV:
            if tag == X:
                return ADJ

        return tag

    def _en_context(
        self,
        low: str,
        tag: str,
        prev_word: Optional[str],
        prev_tag: Optional[str],
    ) -> str:
        """English-specific context refinement."""
        # After "to" → prefer VERB
        if prev_word == "to" and tag in (X, NOUN):
            return VERB

        # After auxiliary → prefer VERB
        if (
            prev_word in _EN_AUX
            and tag in (X, NOUN, ADJ)
        ):
            return VERB

        # -ing after aux → VERB
        if (
            prev_word in _EN_AUX
            and low.endswith("ing")
        ):
            return VERB

        # After DET → prefer NOUN or ADJ
        if prev_tag == DET:
            if tag in (X, VERB, ADV):
                return NOUN

        # After PREP → prefer NOUN
        if prev_tag == PREP:
            if tag in (X, VERB, ADV):
                return NOUN

        # After ADV → prefer ADJ or VERB
        if prev_tag == ADV:
            if tag == X:
                return ADJ

        # After ADJ → prefer NOUN
        if prev_tag == ADJ:
            if tag in (X,):
                return NOUN

        return tag

    def __repr__(self) -> str:
        return (
            f"POSTagger(lang={self._lang!r})"
        )
