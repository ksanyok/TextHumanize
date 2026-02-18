<?php

declare(strict_types=1);

namespace TextHumanize;

/**
 * Tone level enum.
 */
enum ToneLevel: string
{
    case FORMAL = 'formal';
    case ACADEMIC = 'academic';
    case PROFESSIONAL = 'professional';
    case NEUTRAL = 'neutral';
    case FRIENDLY = 'friendly';
    case CASUAL = 'casual';
    case MARKETING = 'marketing';
}

/**
 * ToneReport — result of tone analysis.
 */
class ToneReport
{
    public function __construct(
        public readonly ToneLevel $primaryTone = ToneLevel::NEUTRAL,
        public readonly array $scores = [],
        public readonly float $formality = 0.5,
        public readonly float $subjectivity = 0.5,
        public readonly float $confidence = 0.0,
        public readonly array $markers = [],
    ) {
    }

    /**
     * Convert report to associative array.
     */
    public function toArray(): array
    {
        return [
            'primary_tone' => $this->primaryTone->value,
            'scores' => $this->scores,
            'formality' => $this->formality,
            'subjectivity' => $this->subjectivity,
            'confidence' => $this->confidence,
            'markers' => $this->markers,
        ];
    }
}

/**
 * ToneAnalyzer — analyses and adjusts text tone.
 *
 * Determines the tone of text (formal, neutral, friendly,
 * academic, marketing, casual) and can adjust it.
 */
class ToneAnalyzer
{
    private string $lang;
    /** @var array<string, list<string>> */
    private array $markers;

    // ═══════════════════════════════════════════════════════════════
    //  FORMALITY MARKERS
    // ═══════════════════════════════════════════════════════════════

    /** @var array<string, array<string, list<string>>> */
    private const FORMAL_MARKERS = [
        'en' => [
            'very_formal' => [
                'herein', 'thereof', 'whereby', 'aforementioned', 'notwithstanding',
                'pursuant', 'hereunder', 'hitherto', 'therein', 'theretofore',
                'inasmuch', 'heretofore', 'whomsoever', 'insofar',
            ],
            'formal' => [
                'consequently', 'furthermore', 'moreover', 'nevertheless',
                'accordingly', 'subsequently', 'pertaining', 'regarding',
                'concerning', 'facilitate', 'commence', 'endeavor',
                'implement', 'utilize', 'constitute', 'demonstrate',
                'establish', 'incorporate', 'subsequent', 'prior to',
                'in accordance with', 'with respect to', 'in regard to',
            ],
            'informal' => [
                'gonna', 'wanna', 'gotta', 'kinda', 'sorta', 'dunno',
                'yeah', 'yep', 'nope', 'hey', 'oh', 'wow', 'huh',
                'ok', 'okay', 'stuff', 'thing', 'things', 'like',
                'basically', 'literally', 'actually', 'pretty',
                'awesome', 'cool', 'super', 'totally', 'honestly',
                'damn', 'hell', 'crap', 'mess', 'weird', 'crazy',
            ],
            'subjective' => [
                'i think', 'i believe', 'in my opinion', 'i feel',
                'it seems', 'perhaps', 'maybe', 'probably', 'possibly',
                'hopefully', 'unfortunately', 'surprisingly', 'obviously',
                'clearly', 'certainly', 'definitely', 'absolutely',
                'amazing', 'terrible', 'wonderful', 'horrible',
                'fantastic', 'awful', 'brilliant', 'stunning',
            ],
            'academic' => [
                'hypothesis', 'methodology', 'paradigm', 'empirical',
                'theoretical', 'significant', 'correlation', 'variables',
                'findings', 'literature', 'framework', 'furthermore',
                'et al', 'cf.', 'ibid', 'viz.', 'i.e.', 'e.g.',
                'in contrast', 'on the other hand', 'taken together',
                'it is worth noting', 'it should be noted',
            ],
            'marketing' => [
                'revolutionary', 'exclusive', 'premium', 'innovative',
                'best-in-class', 'cutting-edge', 'world-class', 'unique',
                'limited', 'free', 'guaranteed', 'proven', 'powerful',
                'effortless', 'seamless', 'transform', 'unlock',
                'supercharge', 'game-changing', 'breakthrough', 'ultimate',
                'discover', 'unleash', 'skyrocket', 'maximize',
            ],
        ],
        'ru' => [
            'very_formal' => [
                'нижеследующий', 'вышеизложенный', 'нижеуказанный',
                'сим', 'настоящим', 'надлежащий', 'оный',
                'таковой', 'каковой', 'коего', 'сего',
            ],
            'formal' => [
                'осуществлять', 'обеспечивать', 'предусматривать',
                'регламентировать', 'следовательно', 'вследствие',
                'в соответствии с', 'ввиду', 'касательно', 'относительно',
                'содействовать', 'способствовать', 'являться',
                'представлять собой', 'в рамках', 'в целях',
            ],
            'informal' => [
                'прям', 'щас', 'типа', 'короче', 'ваще', 'блин',
                'фигня', 'норм', 'ок', 'лол', 'чё', 'ну',
                'вообще-то', 'кстати', 'кароче', 'прикольно',
                'классно', 'круто', 'фигово', 'реально', 'жесть',
            ],
            'subjective' => [
                'я думаю', 'я считаю', 'по-моему', 'мне кажется',
                'наверное', 'возможно', 'может быть', 'вероятно',
                'к сожалению', 'к счастью', 'очевидно', 'безусловно',
                'конечно', 'определённо', 'несомненно',
                'потрясающий', 'ужасный', 'замечательный', 'отвратительный',
            ],
            'academic' => [
                'гипотеза', 'методология', 'парадигма', 'эмпирический',
                'теоретический', 'корреляция', 'переменная', 'детерминант',
                'результаты', 'рассмотрим', 'анализ показывает',
                'следует отметить', 'необходимо подчеркнуть',
            ],
        ],
        'uk' => [
            'formal' => [
                'здійснювати', 'забезпечувати', 'передбачати',
                'регламентувати', 'отже', 'внаслідок',
                'відповідно до', 'зважаючи на', 'стосовно',
                'сприяти', 'являти собою', 'в межах', 'з метою',
            ],
            'informal' => [
                'типу', 'короче', 'взагалі', 'блін', 'фігня',
                'норм', 'ок', 'ну', 'до речі', 'класно',
                'круто', 'реально',
            ],
            'subjective' => [
                'я думаю', 'я вважаю', 'на мою думку', 'мені здається',
                'мабуть', 'можливо', 'напевно', 'безумовно',
                'на жаль', 'на щастя', 'очевидно',
            ],
        ],
    ];

    // ═══════════════════════════════════════════════════════════════
    //  TONE REPLACEMENTS
    // ═══════════════════════════════════════════════════════════════

    /** @var array<string, array<string, array<string, string>>> */
    private const TONE_REPLACEMENTS = [
        'en' => [
            'informal_to_formal' => [
                'get' => 'obtain', 'buy' => 'purchase', 'ask' => 'inquire',
                'help' => 'assist', 'start' => 'commence', 'end' => 'conclude',
                'big' => 'significant', 'good' => 'favorable', 'bad' => 'unfavorable',
                'show' => 'demonstrate', 'need' => 'require', 'try' => 'attempt',
                'find out' => 'determine', 'set up' => 'establish',
                'look at' => 'examine', 'think about' => 'consider',
                'put off' => 'postpone', 'come up with' => 'devise',
                'deal with' => 'address', 'go up' => 'increase',
                'go down' => 'decrease', 'talk about' => 'discuss',
            ],
            'formal_to_informal' => [
                'obtain' => 'get', 'purchase' => 'buy', 'inquire' => 'ask',
                'assist' => 'help', 'commence' => 'start', 'conclude' => 'end',
                'demonstrate' => 'show', 'require' => 'need', 'attempt' => 'try',
                'determine' => 'find out', 'establish' => 'set up',
                'examine' => 'look at', 'consider' => 'think about',
                'postpone' => 'put off', 'devise' => 'come up with',
                'address' => 'deal with', 'utilize' => 'use',
                'facilitate' => 'help with', 'implement' => 'do',
            ],
        ],
        'ru' => [
            'informal_to_formal' => [
                'делать' => 'осуществлять', 'начать' => 'приступить',
                'показать' => 'продемонстрировать', 'нужно' => 'необходимо',
                'помочь' => 'оказать содействие', 'думать' => 'полагать',
                'сделать' => 'выполнить', 'большой' => 'значительный',
                'хороший' => 'надлежащий', 'плохой' => 'неудовлетворительный',
            ],
            'formal_to_informal' => [
                'осуществлять' => 'делать', 'обеспечивать' => 'давать',
                'необходимо' => 'нужно', 'полагать' => 'думать',
                'содействовать' => 'помогать', 'являться' => 'быть',
                'представлять собой' => 'быть', 'в целях' => 'чтобы',
                'в рамках' => 'в', 'вследствие' => 'из-за',
            ],
        ],
    ];

    public function __construct(string $lang = 'en')
    {
        $this->lang = $lang;
        $this->markers = self::FORMAL_MARKERS[$lang] ?? self::FORMAL_MARKERS['en'] ?? [];
    }

    // ═══════════════════════════════════════════════════════════════
    //  ANALYSIS
    // ═══════════════════════════════════════════════════════════════

    /**
     * Analyse the tone of the given text.
     */
    public function analyze(string $text): ToneReport
    {
        $textLower = mb_strtolower($text);
        preg_match_all('/\b\w+\b/u', $textLower, $wordMatches);
        $words = $wordMatches[0];
        $wordCount = count($words);

        if ($wordCount < 5) {
            return new ToneReport();
        }

        // Count markers per category
        /** @var array<string, int> $categoryCounts */
        $categoryCounts = [];
        /** @var array<string, list<string>> $categoryFound */
        $categoryFound = [];

        foreach ($this->markers as $category => $markerList) {
            $count = 0;
            $found = [];
            foreach ($markerList as $marker) {
                $occurrences = mb_substr_count($textLower, $marker);
                if ($occurrences > 0) {
                    $count += $occurrences;
                    $found[] = $marker;
                }
            }
            $categoryCounts[$category] = $count;
            $categoryFound[$category] = $found;
        }

        // ─── Formality ───
        $formalScore = (
            ($categoryCounts['very_formal'] ?? 0) * 3 +
            ($categoryCounts['formal'] ?? 0) * 2 +
            ($categoryCounts['academic'] ?? 0) * 2
        );
        $informalScore = ($categoryCounts['informal'] ?? 0) * 2;

        $totalMarkers = $formalScore + $informalScore + 1;
        $formality = $formalScore / $totalMarkers;

        // Average word length
        $totalLen = 0;
        foreach ($words as $w) {
            $totalLen += mb_strlen($w);
        }
        $avgWordLen = $totalLen / $wordCount;

        if ($avgWordLen > 6) {
            $formality = min($formality + 0.1, 1.0);
        } elseif ($avgWordLen < 4.5) {
            $formality = max($formality - 0.1, 0.0);
        }

        // Contractions (don't, can't) → informality
        preg_match_all("/\\b\\w+'\\w+\\b/u", $text, $contractionMatches);
        $contractions = count($contractionMatches[0]);
        if ($contractions > $wordCount * 0.02) {
            $formality = max($formality - 0.15, 0.0);
        }

        // ─── Subjectivity ───
        $subjCount = $categoryCounts['subjective'] ?? 0;
        $subjectivity = min($subjCount / max($wordCount / 50, 1), 1.0);

        // ─── Tone scores ───
        $scores = [];
        $scores['formal'] = $formality;
        $scores['academic'] = min(
            ($categoryCounts['academic'] ?? 0) / max($wordCount / 100, 1),
            1.0
        );
        $scores['marketing'] = min(
            ($categoryCounts['marketing'] ?? 0) / max($wordCount / 80, 1),
            1.0
        );
        $scores['casual'] = 1.0 - $formality;
        $scores['friendly'] = max(
            0,
            min(0.7 - $formality + $subjectivity * 0.3, 1.0)
        );
        $scores['neutral'] = 1.0 - max(
            $formality,
            $subjectivity,
            $scores['marketing'] ?? 0
        );
        $scores['professional'] = max(
            0,
            $formality * 0.7 + (1 - $subjectivity) * 0.3
        );

        // ─── Primary tone ───
        $bestTone = 'neutral';
        $bestScore = -1.0;
        foreach ($scores as $tone => $score) {
            if ($score > $bestScore) {
                $bestScore = $score;
                $bestTone = $tone;
            }
        }

        $primaryTone = ToneLevel::tryFrom($bestTone) ?? ToneLevel::NEUTRAL;

        // ─── Confidence ───
        $sortedScores = array_values($scores);
        rsort($sortedScores);
        if (count($sortedScores) >= 2) {
            $gap = $sortedScores[0] - $sortedScores[1];
            $confidence = min($gap * 2 + 0.3, 1.0);
        } else {
            $confidence = 0.5;
        }

        return new ToneReport(
            primaryTone: $primaryTone,
            scores: $scores,
            formality: $formality,
            subjectivity: $subjectivity,
            confidence: $confidence,
            markers: $categoryFound,
        );
    }

    // ═══════════════════════════════════════════════════════════════
    //  ADJUSTMENT
    // ═══════════════════════════════════════════════════════════════

    /**
     * Adjust the tone of the text towards the target level.
     *
     * @param string    $text      Source text.
     * @param ToneLevel $target    Target tone.
     * @param float     $intensity 0..1 strength of adjustment.
     * @param int|null  $seed      Optional RNG seed for reproducibility.
     */
    public function adjust(
        string $text,
        ToneLevel $target = ToneLevel::NEUTRAL,
        float $intensity = 0.5,
        ?int $seed = null,
    ): string {
        $report = $this->analyze($text);
        $current = $report->primaryTone;

        if ($current === $target) {
            return $text;
        }

        $direction = self::getDirection($current, $target);
        if ($direction === null) {
            return $text;
        }

        $langReplacements = self::TONE_REPLACEMENTS[$this->lang] ?? [];
        $replacements = $langReplacements[$direction] ?? [];
        if (empty($replacements)) {
            return $text;
        }

        $rng = new RandomHelper($seed);
        $result = $text;
        $changesMade = 0;
        $maxChanges = max(1, (int) (count(preg_split('/\s+/', $text)) * $intensity * 0.1));

        foreach ($replacements as $old => $new) {
            if ($changesMade >= $maxChanges) {
                break;
            }

            $pattern = '/\b' . preg_quote($old, '/') . '\b/iu';
            if (preg_match($pattern, $result, $match, PREG_OFFSET_CAPTURE)) {
                if ($rng->random() > $intensity) {
                    continue;
                }

                $original = $match[0][0];
                $offset = (int) $match[0][1];
                $replacement = $new;

                // Preserve casing
                if (mb_strtoupper($original) === $original && mb_strlen($original) > 1) {
                    $replacement = mb_strtoupper($replacement);
                } elseif (mb_strtoupper(mb_substr($original, 0, 1)) === mb_substr($original, 0, 1)
                    && mb_strtolower(mb_substr($original, 0, 1)) !== mb_substr($original, 0, 1)
                ) {
                    $replacement = mb_strtoupper(mb_substr($replacement, 0, 1))
                        . mb_substr($replacement, 1);
                }

                $result = mb_substr($result, 0, $offset)
                    . $replacement
                    . mb_substr($result, $offset + mb_strlen($original));
                $changesMade++;
            }
        }

        return $result;
    }

    /**
     * Determine adjustment direction key.
     *
     * @return string|null Direction key like 'informal_to_formal', or null.
     */
    private static function getDirection(ToneLevel $current, ToneLevel $target): ?string
    {
        $formalLevels = [ToneLevel::FORMAL, ToneLevel::ACADEMIC, ToneLevel::PROFESSIONAL];
        $informalLevels = [ToneLevel::CASUAL, ToneLevel::FRIENDLY];

        $currentFormal = in_array($current, $formalLevels, true);
        $currentInformal = in_array($current, $informalLevels, true);
        $targetFormal = in_array($target, $formalLevels, true);
        $targetInformal = in_array($target, $informalLevels, true);

        if ($currentInformal && $targetFormal) {
            return 'informal_to_formal';
        }
        if ($currentFormal && $targetInformal) {
            return 'formal_to_informal';
        }
        if ($current === ToneLevel::NEUTRAL && $targetFormal) {
            return 'informal_to_formal';
        }
        if ($current === ToneLevel::NEUTRAL && $targetInformal) {
            return 'formal_to_informal';
        }

        return null;
    }

    // ═══════════════════════════════════════════════════════════════
    //  CONVENIENCE STATIC METHODS
    // ═══════════════════════════════════════════════════════════════

    /**
     * Quick tone analysis.
     */
    public static function analyzeTone(string $text, string $lang = 'en'): ToneReport
    {
        return (new self($lang))->analyze($text);
    }

    /**
     * Adjust tone of text.
     *
     * @param string $target One of: formal, casual, friendly, academic, professional, neutral, marketing.
     */
    public static function adjustTone(
        string $text,
        string $target = 'neutral',
        string $lang = 'en',
        float $intensity = 0.5,
    ): string {
        $toneLevel = ToneLevel::tryFrom($target) ?? ToneLevel::NEUTRAL;

        return (new self($lang))->adjust($text, $toneLevel, $intensity);
    }
}
