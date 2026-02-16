"""Языковой пакет: Португальский (Português)."""

LANG_PT = {
    "code": "pt",
    "name": "Português",

    "trigrams": [
        "que", "ent", "ado", "ção", "ment", "est", "ção", "mos",
        "ara", "com", "nte", "ido", "ter", "ant", "par", "res",
        "ões", "ais", "cia", "pro", "era", "ais", "ica", "ura",
        "ora", "nto", "ort", "con", "uma", "por", "tra", "ali",
        "emp", "for", "pos", "rio", "des", "tos", "tes", "ade",
    ],

    "stop_words": {
        "o", "a", "os", "as", "um", "uma", "uns", "umas",
        "e", "ou", "mas", "nem", "que", "se", "não", "em",
        "de", "do", "da", "dos", "das", "ao", "aos",
        "com", "por", "para", "sem", "sobre", "entre",
        "eu", "tu", "ele", "ela", "nós", "eles", "elas",
        "é", "são", "está", "tem", "foi", "ser", "ter",
        "este", "esta", "estes", "estas", "esse", "essa",
        "meu", "minha", "teu", "tua", "seu", "sua",
        "mais", "menos", "muito", "bem", "como", "onde",
        "todo", "toda", "todos", "todas", "outro", "outra",
        "já", "ainda", "também", "só", "cada",
        "aqui", "ali", "quando", "enquanto",
    },

    "bureaucratic": {
        "implementar": ["pôr em prática", "realizar", "aplicar"],
        "otimizar": ["melhorar", "ajustar", "aperfeiçoar"],
        "viabilizar": ["possibilitar", "tornar possível"],
        "concetualizar": ["pensar", "conceber", "imaginar"],
        "operacionalizar": ["pôr em prática", "executar"],
        "significativo": ["notável", "importante", "expressivo"],
        "fundamental": ["essencial", "básico", "central"],
        "primordial": ["essencial", "principal", "vital"],
        "inerente": ["próprio", "natural", "intrínseco"],
        "subsequente": ["seguinte", "posterior"],
        "exaustivo": ["completo", "detalhado", "minucioso"],
        "inovador": ["novo", "criativo", "original"],
        "paradigmático": ["exemplar", "modelo", "típico"],
        "exponencial": ["rápido", "acelerado"],
        "abrangente": ["completo", "amplo", "detalhado"],
        "contundente": ["forte", "decisivo", "claro"],
    },

    "bureaucratic_phrases": {
        "importa referir": ["vale notar", "cabe dizer"],
        "no âmbito de": ["em", "dentro de", "durante"],
        "com o objetivo de": ["para", "a fim de"],
        "tendo em vista": ["considerando", "dado que"],
        "de forma significativa": ["muito", "bastante", "claramente"],
        "desempenha um papel crucial": ["é muito importante", "é central"],
        "reveste-se de importância": ["é importante", "importa"],
        "torna-se imprescindível": ["é preciso", "é necessário"],
        "no que diz respeito a": ["quanto a", "sobre"],
        "à luz de": ["dado", "considerando", "perante"],
    },

    "ai_connectors": {
        "Além disso": ["Também", "Mais ainda", "Por outro lado"],
        "No entanto": ["Mas", "Porém", "Contudo"],
        "Consequentemente": ["Por isso", "Assim", "Então"],
        "Todavia": ["Mas", "Porém", "Contudo"],
        "Ademais": ["Também", "Além do mais", "Mais ainda"],
        "Em suma": ["Resumindo", "Em resumo", "No fundo"],
        "Nesse sentido": ["Assim", "Nessa linha", "Aqui"],
        "Importa salientar": ["É de notar", "Vale dizer"],
        "Cumpre referir": ["Vale dizer", "De notar que"],
        "Em conclusão": ["Para concluir", "No final"],
        "Outrossim": ["Também", "Além disso"],
        "Destarte": ["Assim", "Dessa forma", "Então"],
    },

    "synonyms": {
        "importante": ["relevante", "essencial", "significativo"],
        "grande": ["amplo", "vasto", "considerável"],
        "pequeno": ["reduzido", "modesto", "escasso"],
        "rápido": ["veloz", "ágil", "breve"],
        "problema": ["dificuldade", "desafio", "obstáculo"],
        "solução": ["resposta", "saída", "remédio"],
        "resultado": ["efeito", "desfecho", "fruto"],
        "método": ["abordagem", "técnica", "sistema"],
        "processo": ["procedimento", "percurso", "curso"],
        "objetivo": ["meta", "propósito", "alvo"],
        "vantagem": ["benefício", "proveito", "ponto forte"],
        "desenvolvimento": ["evolução", "progresso", "avanço"],
        "análise": ["estudo", "avaliação", "exame"],
        "eficaz": ["efetivo", "produtivo", "útil"],
        "complexo": ["complicado", "elaborado", "difícil"],
        "moderno": ["atual", "contemporâneo", "recente"],
        "qualidade": ["nível", "padrão", "valor"],
    },

    "sentence_starters": {},

    "colloquial_markers": [
        "na verdade", "sinceramente", "no fundo",
        "digamos", "basicamente", "aliás",
    ],

    "abbreviations": [
        "Sr.", "Sra.", "Dr.", "Prof.", "etc.", "p. ex.",
        "vol.", "n.º", "pág.", "ed.",
    ],

    "profile_targets": {
        "chat": {"avg_len": (6, 16), "variance": 0.5},
        "web": {"avg_len": (8, 22), "variance": 0.4},
        "seo": {"avg_len": (10, 24), "variance": 0.3},
        "docs": {"avg_len": (10, 26), "variance": 0.3},
        "formal": {"avg_len": (12, 30), "variance": 0.25},
    },

    "conjunctions": ["e", "mas", "ou", "nem", "que", "pois"],

    "split_conjunctions": [
        " e ", " mas ", " contudo ", " enquanto ",
        " embora ", " porque ", " visto que ",
    ],
}
