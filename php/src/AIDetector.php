<?php

declare(strict_types=1);

namespace TextHumanize;

use TextHumanize\Lang\Registry;

/**
 * AI Text Detector — statistical detector of AI-generated text.
 *
 * Combines 12+ metrics without neural network dependencies.
 * Works fully offline.
 *
 * Metrics:
 *  1. Text entropy (character-level, word-level, conditional)
 *  2. Burstiness (sentence/paragraph length variation)
 *  3. Lexical diversity (TTR, MATTR, Yule's K, Hapax ratio)
 *  4. Zipf distribution (adherence to Zipf's law)
 *  5. Stylometry (function words, punctuation)
 *  6. AI patterns (overused words, connectors)
 *  7. Text rhythm (syllable patterns, stress)
 *  8. Punctuation profile
 *  9. Coherence (paragraph uniformity)
 * 10. Grammatical "perfection"
 * 11. Sentence opening diversity
 * 12. Readability consistency
 *
 * Final score: 0.0 (definitely human) — 1.0 (definitely AI).
 */

// ═══════════════════════════════════════════════════════════════
//  DETECTION RESULT
// ═══════════════════════════════════════════════════════════════

/**
 * DetectionResult — result of AI text detection.
 */
class DetectionResult
{
    /** Main score: 0.0–1.0 */
    public float $aiProbability = 0.0;

    /** Confidence: 0.0–1.0 */
    public float $confidence = 0.0;

    /** Verdict: "human", "mixed", "ai", "unknown" */
    public string $verdict = 'unknown';

    // Detailed metrics (each 0.0–1.0, where 1.0 = "AI-like")
    public float $entropyScore = 0.0;
    public float $burstinessScore = 0.0;
    public float $vocabularyScore = 0.0;
    public float $zipfScore = 0.0;
    public float $stylometryScore = 0.0;
    public float $patternScore = 0.0;
    public float $punctuationScore = 0.0;
    public float $coherenceScore = 0.0;
    public float $grammarScore = 0.0;
    public float $openingScore = 0.0;
    public float $readabilityScore = 0.0;
    public float $rhythmScore = 0.0;

    /** @var array<string, mixed> */
    public array $details = [];

    /** @var list<string> */
    public array $explanations = [];

    /**
     * Probability that the text was written by a human.
     */
    public function humanProbability(): float
    {
        return 1.0 - $this->aiProbability;
    }

    /**
     * Short summary of the result.
     */
    public function summary(): string
    {
        $lines = [
            sprintf('AI Probability: %.1f%%', $this->aiProbability * 100),
            sprintf('Verdict: %s', $this->verdict),
            sprintf('Confidence: %.1f%%', $this->confidence * 100),
            '',
            'Feature Scores (0=human, 1=AI):',
            sprintf('  Entropy:        %.3f', $this->entropyScore),
            sprintf('  Burstiness:     %.3f', $this->burstinessScore),
            sprintf('  Vocabulary:     %.3f', $this->vocabularyScore),
            sprintf('  Zipf Law:       %.3f', $this->zipfScore),
            sprintf('  Stylometry:     %.3f', $this->stylometryScore),
            sprintf('  AI Patterns:    %.3f', $this->patternScore),
            sprintf('  Punctuation:    %.3f', $this->punctuationScore),
            sprintf('  Coherence:      %.3f', $this->coherenceScore),
            sprintf('  Grammar:        %.3f', $this->grammarScore),
            sprintf('  Openings:       %.3f', $this->openingScore),
            sprintf('  Readability:    %.3f', $this->readabilityScore),
            sprintf('  Rhythm:         %.3f', $this->rhythmScore),
        ];

        if ($this->explanations) {
            $lines[] = '';
            $lines[] = 'Key Findings:';
            foreach (array_slice($this->explanations, 0, 10) as $exp) {
                $lines[] = "  • {$exp}";
            }
        }

        return implode("\n", $lines);
    }
}

// ═══════════════════════════════════════════════════════════════
//  AI-CHARACTERISTIC WORDS (language-specific)
// ═══════════════════════════════════════════════════════════════

/**
 * AIDetector — comprehensive statistical detector of AI-generated text.
 *
 * Uses 12 independent metrics without ML dependencies.
 * All computations are pure statistics and linguistic analysis.
 */
class AIDetector
{
    /** @var array<string, array<string, list<string>>> AI-characteristic words per language */
    private const AI_WORDS = [
        'en' => [
            'adverbs' => [
                'significantly', 'substantially', 'considerably', 'remarkably',
                'exceptionally', 'tremendously', 'profoundly', 'fundamentally',
                'essentially', 'particularly', 'specifically', 'notably',
                'increasingly', 'effectively', 'ultimately', 'consequently',
                'inherently', 'intrinsically', 'predominantly', 'invariably',
            ],
            'adjectives' => [
                'comprehensive', 'crucial', 'pivotal', 'paramount',
                'innovative', 'robust', 'seamless', 'holistic',
                'cutting-edge', 'state-of-the-art', 'groundbreaking',
                'transformative', 'synergistic', 'multifaceted',
                'nuanced', 'intricate', 'meticulous', 'imperative',
            ],
            'verbs' => [
                'utilize', 'leverage', 'facilitate', 'implement',
                'foster', 'enhance', 'streamline', 'optimize',
                'underscore', 'delve', 'navigate', 'harness',
                'exemplify', 'spearhead', 'revolutionize', 'catalyze',
                'necessitate', 'elucidate', 'delineate', 'substantiate',
            ],
            'connectors' => [
                'however', 'furthermore', 'moreover', 'nevertheless',
                'nonetheless', 'additionally', 'consequently', 'therefore',
                'thus', 'hence', 'accordingly', 'subsequently',
                'in conclusion', 'to summarize', 'in essence',
                'it is important to note', 'it is worth mentioning',
            ],
            'phrases' => [
                'plays a crucial role', 'is of paramount importance',
                'in today\'s world', 'in the modern era',
                'a wide range of', 'it goes without saying',
                'in light of', 'due to the fact that',
                'at the end of the day', 'it is important to note that',
                'it should be noted that', 'it is worth mentioning that',
                'first and foremost', 'last but not least',
                'in order to', 'with regard to', 'as a matter of fact',
            ],
        ],
        'ru' => [
            'adverbs' => [
                'значительно', 'существенно', 'чрезвычайно', 'безусловно',
                'несомненно', 'неоспоримо', 'принципиально', 'непосредственно',
                'кардинально', 'всесторонне', 'исключительно', 'преимущественно',
            ],
            'adjectives' => [
                'комплексный', 'всеобъемлющий', 'инновационный', 'ключевой',
                'основополагающий', 'первостепенный', 'фундаментальный',
                'принципиальный', 'многогранный', 'всесторонний',
            ],
            'verbs' => [
                'осуществлять', 'реализовывать', 'способствовать',
                'обеспечивать', 'характеризоваться', 'представлять собой',
                'являться', 'функционировать', 'оказывать влияние',
            ],
            'connectors' => [
                'однако', 'тем не менее', 'вместе с тем', 'кроме того',
                'более того', 'помимо этого', 'таким образом',
                'следовательно', 'безусловно', 'несомненно',
                'в заключение', 'подводя итог', 'исходя из вышесказанного',
                'необходимо отметить', 'стоит подчеркнуть',
            ],
            'phrases' => [
                'играет ключевую роль', 'имеет первостепенное значение',
                'в современном мире', 'на сегодняшний день',
                'широкий спектр', 'не подлежит сомнению',
                'является одним из', 'представляет собой',
                'в рамках данного', 'с учётом того что',
                'необходимо подчеркнуть', 'следует отметить',
            ],
        ],
        'uk' => [
            'adverbs' => [
                'значно', 'суттєво', 'надзвичайно', 'безумовно',
                'безсумнівно', 'незаперечно', 'принципово', 'безпосередньо',
                'кардинально', 'всебічно', 'виключно', 'переважно',
            ],
            'adjectives' => [
                'комплексний', 'всеосяжний', 'інноваційний', 'ключовий',
                'основоположний', 'першочерговий', 'фундаментальний',
                'принциповий', 'багатогранний', 'всебічний',
            ],
            'connectors' => [
                'однак', 'тим не менш', 'разом з тим', 'крім того',
                'більш того', 'окрім цього', 'таким чином',
                'отже', 'безумовно', 'безсумнівно',
                'на завершення', 'підсумовуючи',
                'необхідно зазначити', 'варто підкреслити',
            ],
            'phrases' => [
                'відіграє ключову роль', 'має першочергове значення',
                'у сучасному світі', 'на сьогоднішній день',
                'широкий спектр', 'є одним з',
                'являє собою', 'у рамках даного',
            ],
        ],
    ];

    /** Metric weights (calibrated for maximum accuracy) */
    private const WEIGHTS = [
        'entropy'     => 0.08,
        'burstiness'  => 0.14,   // Strong signal: AI = uniform sentences
        'vocabulary'  => 0.07,
        'zipf'        => 0.03,   // Unreliable for short texts
        'stylometry'  => 0.08,
        'pattern'     => 0.20,   // AI patterns — strongest signal
        'punctuation' => 0.06,
        'coherence'   => 0.08,
        'grammar'     => 0.06,
        'opening'     => 0.09,
        'readability' => 0.05,
        'rhythm'      => 0.06,
    ];

    private string $lang;

    public function __construct(string $lang = 'auto')
    {
        $this->lang = $lang;
    }

    // ─── Convenience static method ──────────────────────────

    /**
     * Detect AI-generated text (convenience static method).
     *
     * @param string $text Text to analyse
     * @param string $lang Language code ('auto', 'ru', 'uk', 'en', etc.)
     * @return DetectionResult Result with AI probability and detailed metrics
     */
    public static function detectAi(string $text, string $lang = 'auto'): DetectionResult
    {
        $detector = new self($lang);
        return $detector->detect($text);
    }

    /**
     * Detect AI-generated text in a batch.
     *
     * @param list<string> $texts  Texts to analyse
     * @param string       $lang   Language code
     * @return list<DetectionResult>
     */
    public static function detectAiBatch(array $texts, string $lang = 'auto'): array
    {
        $detector = new self($lang);
        return array_map(fn(string $t): DetectionResult => $detector->detect($t), $texts);
    }

    // ─── Main detection ─────────────────────────────────────

    /**
     * Detect probability of AI generation.
     */
    public function detect(string $text, ?string $lang = null): DetectionResult
    {
        $effectiveLang = $lang ?? $this->lang;
        if ($effectiveLang === 'auto') {
            $effectiveLang = LangDetector::detect($text);
        }

        $result = new DetectionResult();

        if ($text === '' || mb_strlen(trim($text)) < 50) {
            $result->verdict = 'unknown';
            $result->confidence = 0.0;
            $result->explanations[] = 'Text too short for reliable detection';
            return $result;
        }

        // Preparation
        $splitter  = new SentenceSplitter($effectiveLang);
        $sentences = $splitter->split($text);
        $words     = preg_split('/\s+/u', $text, -1, PREG_SPLIT_NO_EMPTY);
        $langPack  = Registry::get($effectiveLang);

        if (count($sentences) < 3) {
            $result->verdict = 'unknown';
            $result->confidence = 0.1;
            $result->explanations[] = 'Too few sentences for reliable detection';
            return $result;
        }

        // ── Compute all 12 metrics ──

        $result->entropyScore     = $this->calcEntropy($text, $words);
        $result->burstinessScore  = $this->calcBurstiness($sentences);
        $result->vocabularyScore  = $this->calcVocabulary($text, $words, $langPack);
        $result->zipfScore        = $this->calcZipf($words, $langPack);
        $result->stylometryScore  = $this->calcStylometry($text, $words, $sentences, $langPack);
        $result->patternScore     = $this->calcAiPatterns($text, $words, $sentences, $effectiveLang);
        $result->punctuationScore = $this->calcPunctuation($text, $sentences);
        $result->coherenceScore   = $this->calcCoherence($text, $sentences);
        $result->grammarScore     = $this->calcGrammar($text, $sentences);
        $result->openingScore     = $this->calcOpenings($sentences);
        $result->readabilityScore = $this->calcReadabilityConsistency($sentences);
        $result->rhythmScore      = $this->calcRhythm($sentences);

        // ── Weighted aggregation ──

        $scores = [
            'entropy'     => $result->entropyScore,
            'burstiness'  => $result->burstinessScore,
            'vocabulary'  => $result->vocabularyScore,
            'zipf'        => $result->zipfScore,
            'stylometry'  => $result->stylometryScore,
            'pattern'     => $result->patternScore,
            'punctuation' => $result->punctuationScore,
            'coherence'   => $result->coherenceScore,
            'grammar'     => $result->grammarScore,
            'opening'     => $result->openingScore,
            'readability' => $result->readabilityScore,
            'rhythm'      => $result->rhythmScore,
        ];

        $weightedSum = 0.0;
        foreach ($scores as $k => $v) {
            $weightedSum += $v * self::WEIGHTS[$k];
        }
        $totalWeight     = array_sum(self::WEIGHTS);
        $rawProbability  = $weightedSum / $totalWeight;

        // Sigmoidal calibration for better separation
        $result->aiProbability = self::calibrate($rawProbability);

        // Confidence depends on text length and metric spread
        $textLengthFactor = min(count($words) / 200, 1.0);
        $metricValues     = array_values($scores);
        $metricAgreement  = 1.0 - self::stdev($metricValues);
        $result->confidence = min($textLengthFactor * 0.7 + $metricAgreement * 0.3, 1.0);

        // Verdict
        if ($result->aiProbability > 0.75) {
            $result->verdict = 'ai';
        } elseif ($result->aiProbability > 0.45) {
            $result->verdict = 'mixed';
        } else {
            $result->verdict = 'human';
        }

        // Explanations
        $result->explanations = $this->generateExplanations($scores, $result, $effectiveLang);

        // Details
        $result->details = [
            'lang'            => $effectiveLang,
            'word_count'      => count($words),
            'sentence_count'  => count($sentences),
            'raw_probability' => $rawProbability,
            'scores'          => $scores,
            'weights'         => self::WEIGHTS,
        ];

        return $result;
    }

    // ══════════════════════════════════════════════════════════
    //  HELPER: statistics
    // ══════════════════════════════════════════════════════════

    /**
     * Sample standard deviation (like Python statistics.stdev).
     *
     * @param list<float|int> $values
     */
    private static function stdev(array $values): float
    {
        $n = count($values);
        if ($n < 2) {
            return 0.0;
        }
        $mean = array_sum($values) / $n;
        $sumSq = 0.0;
        foreach ($values as $v) {
            $sumSq += ($v - $mean) ** 2;
        }
        return sqrt($sumSq / ($n - 1));
    }

    /**
     * Sample variance (like Python statistics.variance).
     *
     * @param list<float|int> $values
     */
    private static function variance(array $values): float
    {
        $n = count($values);
        if ($n < 2) {
            return 0.0;
        }
        $mean = array_sum($values) / $n;
        $sumSq = 0.0;
        foreach ($values as $v) {
            $sumSq += ($v - $mean) ** 2;
        }
        return $sumSq / ($n - 1);
    }

    /**
     * Arithmetic mean.
     *
     * @param list<float|int> $values
     */
    private static function mean(array $values): float
    {
        if ($values === []) {
            return 0.0;
        }
        return array_sum($values) / count($values);
    }

    /**
     * Strip punctuation from a word (equivalent to Python strip('.,;:!?"\'()[]{}'))
     */
    private static function stripPunct(string $word): string
    {
        return trim($word, ".,;:!?\"'()[]{}");
    }

    /**
     * Count occurrences of a substring (case-insensitive, mb-safe).
     */
    private static function mbSubstrCount(string $haystack, string $needle): int
    {
        $haystack = mb_strtolower($haystack);
        $needle   = mb_strtolower($needle);
        if ($needle === '') {
            return 0;
        }
        $count  = 0;
        $offset = 0;
        $needleLen = mb_strlen($needle);
        while (($pos = mb_strpos($haystack, $needle, $offset)) !== false) {
            $count++;
            $offset = $pos + $needleLen;
        }
        return $count;
    }

    // ═══════════════════════════════════════════════════════════
    //  1. ENTROPY
    // ═══════════════════════════════════════════════════════════

    /**
     * Text entropy — AI has low entropy (predictable).
     *
     * Analysis: character-level, word-level, conditional (bigram) entropy.
     * Returns: 0.0 (high entropy = human) — 1.0 (low = AI)
     */
    private function calcEntropy(string $text, array $words): float
    {
        if (count($words) < 10) {
            return 0.5;
        }

        // Character-level Shannon entropy
        $charFreq   = array_count_values(mb_str_split(mb_strtolower($text)));
        $totalChars = array_sum($charFreq);
        $charEntropy = 0.0;
        foreach ($charFreq as $c) {
            if ($c > 0) {
                $p = $c / $totalChars;
                $charEntropy -= $p * log($p, 2);
            }
        }

        // Word-level entropy
        $cleanWords = array_map(fn(string $w): string => mb_strtolower(self::stripPunct($w)), $words);
        $wordFreq   = array_count_values($cleanWords);
        $totalWords = array_sum($wordFreq);
        $wordEntropy = 0.0;
        foreach ($wordFreq as $c) {
            if ($c > 0) {
                $p = $c / $totalWords;
                $wordEntropy -= $p * log($p, 2);
            }
        }

        // Conditional entropy (bigram entropy − unigram entropy)
        $wordList = array_values(array_filter($cleanWords, fn(string $w): bool => $w !== ''));
        $bigrams  = [];
        $n = count($wordList);
        for ($i = 0; $i < $n - 1; $i++) {
            $key = $wordList[$i] . "\0" . $wordList[$i + 1];
            $bigrams[$key] = ($bigrams[$key] ?? 0) + 1;
        }
        $totalBigrams = array_sum($bigrams);

        if ($totalBigrams > 0) {
            $bigramEntropy = 0.0;
            foreach ($bigrams as $c) {
                if ($c > 0) {
                    $p = $c / $totalBigrams;
                    $bigramEntropy -= $p * log($p, 2);
                }
            }
            $conditionalEntropy = $bigramEntropy - $wordEntropy;
        } else {
            $conditionalEntropy = $wordEntropy;
        }

        // Normalize into 0–1 scale (1 = AI-like low entropy)
        $charScore = max(0.0, 1.0 - ($charEntropy - 3.0) / 2.0);
        $wordScore = max(0.0, 1.0 - ($wordEntropy - 5.0) / 5.0);
        $condScore = max(0.0, 1.0 - $conditionalEntropy / 3.0);

        $score = $charScore * 0.2 + $wordScore * 0.5 + $condScore * 0.3;
        return max(0.0, min(1.0, $score));
    }

    // ═══════════════════════════════════════════════════════════
    //  2. BURSTINESS
    // ═══════════════════════════════════════════════════════════

    /**
     * Sentence length variation.
     *
     * AI generates sentences of equal length (CV < 0.3).
     * Humans: CV > 0.5.
     * Returns: 0.0 (diverse = human) — 1.0 (uniform = AI)
     */
    private function calcBurstiness(array $sentences): float
    {
        if (count($sentences) < 4) {
            return 0.5;
        }

        $lengths = array_map(
            fn(string $s): int => count(preg_split('/\s+/u', $s, -1, PREG_SPLIT_NO_EMPTY)),
            $sentences,
        );
        $avg = self::mean($lengths);
        if ($avg == 0) {
            return 0.5;
        }

        $sd = self::stdev($lengths);
        $cv = $sd / $avg;

        // AI: CV ≈ 0.15–0.35, Human: CV ≈ 0.5–0.9+
        $score = max(0.0, 1.0 - ($cv - 0.1) / 0.7);

        // Check for extreme sentence lengths (very short / very long)
        $short = 0;
        $long  = 0;
        foreach ($lengths as $l) {
            if ($l <= 5) { $short++; }
            if ($l >= 30) { $long++; }
        }
        $extremes = ($short + $long) / count($lengths);

        if ($extremes < 0.05) {
            $score = min($score + 0.15, 1.0);
        } elseif ($extremes > 0.2) {
            $score = max($score - 0.1, 0.0);
        }

        // Fragments (1–2 words) — humans sometimes write "Yes." or "No."
        $fragments = 0;
        foreach ($lengths as $l) {
            if ($l <= 2) { $fragments++; }
        }
        if ($fragments === 0 && count($sentences) > 8) {
            $score = min($score + 0.05, 1.0);
        }

        return max(0.0, min(1.0, $score));
    }

    // ═══════════════════════════════════════════════════════════
    //  3. LEXICAL DIVERSITY
    // ═══════════════════════════════════════════════════════════

    /**
     * Lexical diversity — AI uses a "safe" vocabulary.
     *
     * Metrics: TTR, MATTR, Yule's K, Hapax legomena ratio.
     * Returns: 0.0 (diverse = human) — 1.0 (poor = AI)
     */
    private function calcVocabulary(string $text, array $words, array $langPack): float
    {
        if (count($words) < 20) {
            return 0.5;
        }

        $stopWords = $langPack['stop_words'] ?? [];
        // Normalise stop_words to a lookup set
        $stopSet = [];
        foreach ($stopWords as $sw) {
            $stopSet[mb_strtolower($sw)] = true;
        }

        $contentWords = [];
        foreach ($words as $w) {
            $cw = mb_strtolower(self::stripPunct($w));
            if ($cw !== '' && mb_strlen($cw) > 2 && !isset($stopSet[$cw])) {
                $contentWords[] = $cw;
            }
        }

        $tokens = count($contentWords);
        if ($tokens < 10) {
            return 0.5;
        }

        // TTR
        $types = count(array_unique($contentWords));
        $ttr   = $types / $tokens;

        // MATTR (window of 25 words)
        $window = 25;
        if ($tokens >= $window) {
            $mattrValues = [];
            for ($i = 0; $i <= $tokens - $window; $i++) {
                $slice = array_slice($contentWords, $i, $window);
                $mattrValues[] = count(array_unique($slice)) / $window;
            }
            $mattr = self::mean($mattrValues);
        } else {
            $mattr = $ttr;
        }

        // Yule's K
        $wordCounts   = array_count_values($contentWords);
        $freqSpectrum = array_count_values($wordCounts);
        $N = $tokens;
        $M = 0;
        foreach ($freqSpectrum as $i => $fi) {
            $M += $i * $i * $fi;
        }
        $yuleK = $N > 1 ? 10000 * ($M - $N) / ($N * $N) : 0;

        // Hapax legomena ratio (words occurring once)
        $hapaxCount = 0;
        foreach ($wordCounts as $cnt) {
            if ($cnt === 1) { $hapaxCount++; }
        }
        $hapaxRatio = $types > 0 ? $hapaxCount / $types : 0;

        $lengthReliability = min($tokens / 150, 1.0);

        // TTR score (AI has lower TTR)
        $ttrScore   = max(0.0, 1.0 - ($ttr - 0.3) / 0.4);
        $mattrScore = max(0.0, 1.0 - ($mattr - 0.6) / 0.3);
        $yuleScore  = min($yuleK / 150, 1.0);
        $hapaxScore = max(0.0, 1.0 - $hapaxRatio / 0.5);

        $rawScore = $ttrScore * 0.2
                  + $mattrScore * 0.3
                  + $yuleScore * 0.25
                  + $hapaxScore * 0.25;

        // Short texts: shift toward 0.5 (unreliable)
        $score = 0.5 + ($rawScore - 0.5) * $lengthReliability;
        return max(0.0, min(1.0, $score));
    }

    // ═══════════════════════════════════════════════════════════
    //  4. ZIPF'S LAW
    // ═══════════════════════════════════════════════════════════

    /**
     * Zipf's law adherence.
     *
     * Natural text follows Zipf distribution well.
     * AI text may deviate (too uniform in mid-range).
     * Returns: 0.0 (good fit = human) — 1.0 (AI)
     */
    private function calcZipf(array $words, array $langPack): float
    {
        $cleanWords = [];
        foreach ($words as $w) {
            $cw = mb_strtolower(self::stripPunct($w));
            if ($cw !== '') {
                $cleanWords[] = $cw;
            }
        }

        if (count($cleanWords) < 50) {
            return 0.5;
        }

        $freq = array_count_values($cleanWords);
        $sortedFreqs = array_values($freq);
        rsort($sortedFreqs);

        if (count($sortedFreqs) < 10) {
            return 0.5;
        }

        // Theoretical Zipf: f(r) = f(1) / r
        $f1 = $sortedFreqs[0];
        $n  = min(50, count($sortedFreqs));

        $deviations = [];
        for ($rank = 1; $rank <= $n; $rank++) {
            $actual   = $sortedFreqs[$rank - 1];
            $expected = $f1 / $rank;
            if ($expected > 0) {
                $deviations[] = abs($actual - $expected) / $expected;
            }
        }

        if ($deviations === []) {
            return 0.5;
        }

        $avgDeviation = self::mean($deviations);

        $lengthReliability = min(count($cleanWords) / 200, 1.0);

        // Check tail of the distribution
        $tailStart = intdiv(count($sortedFreqs), 3);
        $tail      = array_slice($sortedFreqs, $tailStart);

        if ($tail !== [] && count($tail) > 2) {
            $tailMean = self::mean($tail);
            // Check if all tail values are identical
            $allSame = true;
            foreach ($tail as $v) {
                if ($v !== $tail[0]) { $allSame = false; break; }
            }
            if ($allSame) {
                $tailScore = 0.5;
            } else {
                $tailCv    = $tailMean > 0 ? self::stdev($tail) / $tailMean : 0;
                $tailScore = max(0.0, 1.0 - $tailCv / 0.8);
            }
        } else {
            $tailScore = 0.5;
        }

        $rawScore = $avgDeviation * 0.5 + $tailScore * 0.5;
        $score    = 0.5 + ($rawScore - 0.5) * $lengthReliability;
        return max(0.0, min(1.0, $score));
    }

    // ═══════════════════════════════════════════════════════════
    //  5. STYLOMETRY
    // ═══════════════════════════════════════════════════════════

    /**
     * Stylometric analysis.
     *
     * AI has a characteristic "style fingerprint":
     * - High function-word ratio
     * - Uniform POS distribution
     * - Preference for certain syntactic constructions
     *
     * Returns: 0.0 (human style) — 1.0 (AI style)
     */
    private function calcStylometry(string $text, array $words, array $sentences, array $langPack): float
    {
        if (count($words) < 20) {
            return 0.5;
        }

        $stopWords = $langPack['stop_words'] ?? [];
        $stopSet   = [];
        foreach ($stopWords as $sw) {
            $stopSet[mb_strtolower($sw)] = true;
        }

        $wordLengths = [];
        foreach ($words as $w) {
            $cw = self::stripPunct($w);
            if ($cw !== '') {
                $wordLengths[] = mb_strlen($cw);
            }
        }

        if ($wordLengths === []) {
            return 0.5;
        }

        // 1. Average word length (AI prefers longer words)
        $avgWordLen   = self::mean($wordLengths);
        $wordLenScore = max(0.0, ($avgWordLen - 4.0) / 3.0);

        // 2. Word length variation (AI is more uniform)
        if (count($wordLengths) > 5) {
            $wordLenCv   = $avgWordLen > 0 ? self::stdev($wordLengths) / $avgWordLen : 0;
            $wordVarScore = max(0.0, 1.0 - $wordLenCv / 0.7);
        } else {
            $wordVarScore = 0.5;
        }

        // 3. Ratio of long words (>8 chars)
        $longWords = 0;
        foreach ($wordLengths as $l) {
            if ($l > 8) { $longWords++; }
        }
        $longRatio = $longWords / count($wordLengths);
        $longScore = min($longRatio / 0.15, 1.0);

        // 4. Average sentence length
        $sentLengths = array_map(
            fn(string $s): int => count(preg_split('/\s+/u', $s, -1, PREG_SPLIT_NO_EMPTY)),
            $sentences,
        );
        $avgSentLen   = self::mean($sentLengths);
        $sentLenScore = max(0.0, ($avgSentLen - 10) / 15);

        // 5. Stop word ratio
        $stopCount = 0;
        foreach ($words as $w) {
            if (isset($stopSet[mb_strtolower(self::stripPunct($w))])) {
                $stopCount++;
            }
        }
        $stopRatio = count($words) > 0 ? $stopCount / count($words) : 0;
        $stopScore = max(0.0, 1.0 - ($stopRatio - 0.25) / 0.3);

        $score = $wordLenScore * 0.2
               + $wordVarScore * 0.15
               + $longScore * 0.2
               + $sentLenScore * 0.25
               + $stopScore * 0.2;

        return max(0.0, min(1.0, $score));
    }

    // ═══════════════════════════════════════════════════════════
    //  6. AI PATTERNS
    // ═══════════════════════════════════════════════════════════

    /**
     * AI pattern detection — the most powerful signal.
     *
     * Returns: 0.0 (no patterns = human) — 1.0 (many = AI)
     */
    private function calcAiPatterns(string $text, array $words, array $sentences, string $lang): float
    {
        if (count($words) < 20) {
            return 0.5;
        }

        $textLower  = mb_strtolower($text);
        $totalWords = count($words);

        $aiDict = self::AI_WORDS[$lang] ?? self::AI_WORDS['en'] ?? [];

        $totalHits    = 0;
        $weightedHits = 0.0;

        // 1. AI-overused words
        $categories = [
            ['adverbs', 1.5],
            ['adjectives', 1.3],
            ['verbs', 1.5],
            ['connectors', 2.0],
        ];
        foreach ($categories as [$category, $weight]) {
            $catWords = $aiDict[$category] ?? [];
            foreach ($catWords as $w) {
                $count = self::mbSubstrCount($textLower, mb_strtolower($w));
                if ($count > 0) {
                    $totalHits    += $count;
                    $weightedHits += $count * $weight;
                }
            }
        }

        // 2. AI phrases (strongest signal — triple weight)
        $phrases = $aiDict['phrases'] ?? [];
        foreach ($phrases as $phrase) {
            $count = self::mbSubstrCount($textLower, mb_strtolower($phrase));
            if ($count > 0) {
                $totalHits    += $count;
                $weightedHits += $count * 3.0;
            }
        }

        // Normalise by text length
        $density = $totalWords > 0 ? $weightedHits / $totalWords : 0;

        // 3. Connector density
        $connectorCount = 0;
        $connectors     = $aiDict['connectors'] ?? [];
        foreach ($connectors as $conn) {
            if (mb_strpos($textLower, mb_strtolower($conn)) !== false) {
                $connectorCount++;
            }
        }
        $connectorDensity = count($sentences) > 0
            ? $connectorCount / count($sentences)
            : 0;

        // 4. Formal sentence starters
        $formalStarts = 0;
        $formalStarters = [
            'however', 'furthermore', 'moreover', 'additionally',
            'consequently', 'nevertheless', 'nonetheless',
            'однако', 'кроме того', 'более того', 'помимо этого',
            'таким образом', 'следовательно', 'тем не менее',
            'однак', 'крім того', 'більш того', 'окрім цього',
            'таким чином', 'отже',
        ];

        foreach ($sentences as $sent) {
            $sentWords   = preg_split('/\s+/u', $sent, 4, PREG_SPLIT_NO_EMPTY);
            $firstPhrase = mb_strtolower(rtrim(implode(' ', array_slice($sentWords, 0, 3)), '.,;:'));
            foreach ($formalStarters as $starter) {
                if (str_starts_with($firstPhrase, $starter)) {
                    $formalStarts++;
                    break;
                }
            }
        }

        $formalStartRatio = count($sentences) > 0
            ? $formalStarts / count($sentences)
            : 0;

        // Combining
        $densityScore   = min($density / 0.05, 1.0);
        $connectorScore = min($connectorDensity / 0.15, 1.0);
        $formalScore     = min($formalStartRatio / 0.2, 1.0);

        $score = $densityScore * 0.4
               + $connectorScore * 0.3
               + $formalScore * 0.3;

        return max(0.0, min(1.0, $score));
    }

    // ═══════════════════════════════════════════════════════════
    //  7. PUNCTUATION
    // ═══════════════════════════════════════════════════════════

    /**
     * Punctuation profile analysis.
     *
     * AI overuses: semicolons, colons, em dashes.
     * AI underuses: ellipsis, exclamation marks, parenthetical notes.
     * Returns: 0.0 (human) — 1.0 (AI)
     */
    private function calcPunctuation(string $text, array $sentences): float
    {
        if (mb_strlen($text) < 50) {
            return 0.5;
        }

        $totalChars = mb_strlen($text);

        $semicolons   = substr_count($text, ';');
        $colons       = substr_count($text, ':');
        $emDashes     = substr_count($text, '—') + substr_count($text, '–');
        $ellipsis     = substr_count($text, '...') + substr_count($text, '…');
        $exclamations = substr_count($text, '!');
        $questions    = substr_count($text, '?');
        $parens       = substr_count($text, '(');

        // Per 1000 chars
        $k = 1000 / $totalChars;

        $semiRate     = $semicolons * $k;
        $colonRate    = $colons * $k;
        $dashRate     = $emDashes * $k;
        $ellipsisRate = $ellipsis * $k;
        $exclRate     = $exclamations * $k;

        $semiScore     = min($semiRate / 3.0, 1.0);
        $colonScore    = min($colonRate / 3.0, 1.0);
        $dashScore     = min($dashRate / 4.0, 1.0);
        $ellipsisScore = max(0.0, 1.0 - $ellipsisRate / 2.0);
        $exclScore     = max(0.0, 1.0 - $exclRate / 2.0);

        // Punctuation diversity: AI uses fewer types
        $punctCounts = [$semicolons, $colons, $emDashes, $ellipsis, $exclamations, $questions, $parens];
        $punctTypes  = 0;
        foreach ($punctCounts as $pc) {
            if ($pc > 0) { $punctTypes++; }
        }
        $diversityScore = max(0.0, 1.0 - $punctTypes / 5.0);

        $score = $semiScore * 0.2
               + $colonScore * 0.15
               + $dashScore * 0.15
               + $ellipsisScore * 0.15
               + $exclScore * 0.1
               + $diversityScore * 0.25;

        return max(0.0, min(1.0, $score));
    }

    // ═══════════════════════════════════════════════════════════
    //  8. COHERENCE
    // ═══════════════════════════════════════════════════════════

    /**
     * Coherence analysis — AI writes "too coherently".
     *
     * AI consistently links every sentence to the previous one.
     * Humans sometimes make topic jumps, use associative transitions.
     * Returns: 0.0 (natural transitions = human) — 1.0 (perfect links = AI)
     */
    private function calcCoherence(string $text, array $sentences): float
    {
        if (count($sentences) < 5) {
            return 0.5;
        }

        // Lexical overlap between adjacent sentences
        $overlaps = [];
        for ($i = 1; $i < count($sentences); $i++) {
            $wordsPrev = [];
            foreach (preg_split('/\s+/u', $sentences[$i - 1], -1, PREG_SPLIT_NO_EMPTY) as $w) {
                $cw = mb_strtolower(self::stripPunct($w));
                if (mb_strlen($cw) > 3) {
                    $wordsPrev[$cw] = true;
                }
            }
            $wordsCurr = [];
            foreach (preg_split('/\s+/u', $sentences[$i], -1, PREG_SPLIT_NO_EMPTY) as $w) {
                $cw = mb_strtolower(self::stripPunct($w));
                if (mb_strlen($cw) > 3) {
                    $wordsCurr[$cw] = true;
                }
            }

            if ($wordsPrev !== [] && $wordsCurr !== []) {
                $intersection = count(array_intersect_key($wordsPrev, $wordsCurr));
                $minSize      = min(count($wordsPrev), count($wordsCurr));
                $overlaps[]   = $intersection / $minSize;
            }
        }

        if ($overlaps === []) {
            return 0.5;
        }

        $avgOverlap      = self::mean($overlaps);
        $overlapVariance  = self::variance($overlaps);

        $overlapScore = min($avgOverlap / 0.25, 1.0);

        $varianceScore = count($overlaps) > 3
            ? max(0.0, 1.0 - $overlapVariance / 0.02)
            : 0.5;

        // Check paragraph-level transitions
        $paragraphs = array_values(array_filter(
            array_map('trim', explode("\n\n", $text)),
            fn(string $p): bool => $p !== '',
        ));

        if (count($paragraphs) > 2) {
            $transitionStarts = 0;
            $transitionWords  = [
                'however', 'furthermore', 'moreover', 'in addition',
                'consequently', 'therefore', 'additionally', 'on the other hand',
                'однако', 'кроме того', 'более того', 'в дополнение',
                'таким образом', 'в заключение', 'помимо',
                'однак', 'крім того', 'більш того', 'таким чином',
            ];

            for ($pi = 1; $pi < count($paragraphs); $pi++) {
                $paraWords   = preg_split('/\s+/u', $paragraphs[$pi], 4, PREG_SPLIT_NO_EMPTY);
                $firstPhrase = mb_strtolower(implode(' ', array_slice($paraWords, 0, 3)));
                foreach ($transitionWords as $tw) {
                    if (str_starts_with($firstPhrase, $tw)) {
                        $transitionStarts++;
                        break;
                    }
                }
            }

            $transRatio      = $transitionStarts / (count($paragraphs) - 1);
            $transitionScore = min($transRatio / 0.4, 1.0);
        } else {
            $transitionScore = 0.5;
        }

        $score = $overlapScore * 0.3 + $varianceScore * 0.3 + $transitionScore * 0.4;
        return max(0.0, min(1.0, $score));
    }

    // ═══════════════════════════════════════════════════════════
    //  9. GRAMMAR PERFECTION
    // ═══════════════════════════════════════════════════════════

    /**
     * AI writes "too perfect" grammar.
     *
     * Humans allow: lower-case sentence starts, informal constructions,
     * unmatched parentheses, inconsistent formatting.
     * Returns: 0.0 (human-like = imperfect) — 1.0 (perfect grammar = AI)
     */
    private function calcGrammar(string $text, array $sentences): float
    {
        if (count($sentences) < 3) {
            return 0.5;
        }

        $indicators = [];

        // 1. All sentences start with uppercase?
        $allUppercase = 0;
        foreach ($sentences as $s) {
            if ($s !== '' && mb_strtoupper(mb_substr($s, 0, 1)) === mb_substr($s, 0, 1)
                && mb_strtolower(mb_substr($s, 0, 1)) !== mb_substr($s, 0, 1)) {
                $allUppercase++;
            }
        }
        $upperRatio = count($sentences) > 0 ? $allUppercase / count($sentences) : 0;
        $indicators[] = $upperRatio === 1.0 ? 1.0 : max(0.0, ($upperRatio - 0.9) * 10);

        // 2. All sentences end with punctuation?
        $allPunctEnd = 0;
        foreach ($sentences as $s) {
            $s = rtrim($s);
            if ($s !== '') {
                $lastChar = mb_substr($s, -1, 1);
                if (in_array($lastChar, ['.', '!', '?', '…'], true)) {
                    $allPunctEnd++;
                }
            }
        }
        $punctRatio   = count($sentences) > 0 ? $allPunctEnd / count($sentences) : 0;
        $indicators[] = $punctRatio === 1.0 ? 1.0 : max(0.0, ($punctRatio - 0.85) * 6.7);

        // 3. Paired parentheses — AI always closes them
        $openParens  = substr_count($text, '(');
        $closeParens = substr_count($text, ')');
        $parenBalance = abs($openParens - $closeParens);
        $indicators[] = ($parenBalance === 0 && $openParens > 0) ? 1.0 : 0.0;

        // 4. No contractions (don't, isn't) in EN — AI writes full forms
        if (preg_match('/[a-zA-Z]/', $text)) {
            $contractions    = preg_match_all("/\\b\\w+'(?:t|s|re|ve|ll|d|m)\\b/iu", $text);
            $totalW          = count(preg_split('/\s+/u', $text, -1, PREG_SPLIT_NO_EMPTY));
            $contractionRatio = $totalW > 0 ? $contractions / $totalW : 0;
            $indicators[]     = max(0.0, 1.0 - $contractionRatio / 0.03);
        }

        // 5. Uniform paragraph lengths — AI makes them equal
        $paragraphs = array_values(array_filter(
            array_map('trim', explode("\n\n", $text)),
            fn(string $p): bool => $p !== '',
        ));
        if (count($paragraphs) > 2) {
            $paraLengths = array_map(
                fn(string $p): int => count(preg_split('/\s+/u', $p, -1, PREG_SPLIT_NO_EMPTY)),
                $paragraphs,
            );
            $avgPara = self::mean($paraLengths);
            if ($avgPara > 0) {
                $paraCv       = count($paraLengths) > 1 ? self::stdev($paraLengths) / $avgPara : 0;
                $indicators[] = max(0.0, 1.0 - $paraCv / 0.5);
            }
        }

        $score = $indicators !== [] ? self::mean($indicators) : 0.5;
        return max(0.0, min(1.0, $score));
    }

    // ═══════════════════════════════════════════════════════════
    //  10. SENTENCE OPENING DIVERSITY
    // ═══════════════════════════════════════════════════════════

    /**
     * AI often starts sentences the same way.
     *
     * Patterns: repeated "The", "This", "It"; always subject-first.
     * Returns: 0.0 (diverse = human) — 1.0 (uniform = AI)
     */
    private function calcOpenings(array $sentences): float
    {
        if (count($sentences) < 5) {
            return 0.5;
        }

        $firstWords   = [];
        $firstBigrams = [];
        foreach ($sentences as $s) {
            $sWords = preg_split('/\s+/u', $s, -1, PREG_SPLIT_NO_EMPTY);
            if ($sWords !== []) {
                $fw = mb_strtolower(rtrim($sWords[0], '.,;:'));
                $firstWords[] = $fw;
                if (count($sWords) >= 2) {
                    $firstBigrams[] = $fw . ' ' . mb_strtolower(rtrim($sWords[1], '.,;:'));
                }
            }
        }

        if ($firstWords === []) {
            return 0.5;
        }

        $cnt = count($firstWords);

        // 1. Unique first-word ratio
        $uniqueRatio = count(array_unique($firstWords)) / $cnt;
        $uniqueScore = max(0.0, 1.0 - ($uniqueRatio - 0.2) / 0.6);

        // 2. Max repetition of one opening word
        $firstCounter = array_count_values($firstWords);
        $maxRepeat    = max($firstCounter);
        $repeatRatio  = $maxRepeat / $cnt;
        $repeatScore  = min($repeatRatio / 0.3, 1.0);

        // 3. Subject-first starts
        $subjectProns = [
            'i', 'he', 'she', 'it', 'they', 'we', 'you', 'the', 'this',
            'я', 'он', 'она', 'оно', 'они', 'мы', 'вы', 'это', 'эти',
            'він', 'вона', 'воно', 'вони', 'ми', 'ви', 'це', 'ці',
        ];
        $subjectSet = array_flip($subjectProns);
        $subjectStarts = 0;
        foreach ($firstWords as $fw) {
            if (isset($subjectSet[$fw])) {
                $subjectStarts++;
            }
        }
        $subjectRatio = $subjectStarts / $cnt;
        $subjectScore = min($subjectRatio / 0.5, 1.0);

        // 4. Consecutive same starts
        $consecutiveSame = 0;
        for ($i = 1; $i < $cnt; $i++) {
            if ($firstWords[$i] === $firstWords[$i - 1]) {
                $consecutiveSame++;
            }
        }
        $consecRatio = $cnt > 1 ? $consecutiveSame / ($cnt - 1) : 0;
        $consecScore = min($consecRatio / 0.15, 1.0);

        $score = $uniqueScore * 0.3
               + $repeatScore * 0.25
               + $subjectScore * 0.2
               + $consecScore * 0.25;

        return max(0.0, min(1.0, $score));
    }

    // ═══════════════════════════════════════════════════════════
    //  11. READABILITY CONSISTENCY
    // ═══════════════════════════════════════════════════════════

    /**
     * AI writes with constant complexity, humans vary.
     *
     * Split text into windows, compute readability per window.
     * AI has minimal spread between windows.
     * Returns: 0.0 (varying = human) — 1.0 (uniform = AI)
     */
    private function calcReadabilityConsistency(array $sentences): float
    {
        if (count($sentences) < 6) {
            return 0.5;
        }

        $windowSize = 3;
        $windows    = [];

        for ($i = 0; $i <= count($sentences) - $windowSize; $i += $windowSize) {
            $windowSents = array_slice($sentences, $i, $windowSize);
            $windowText  = implode(' ', $windowSents);
            $wWords      = preg_split('/\s+/u', $windowText, -1, PREG_SPLIT_NO_EMPTY);

            if ($wWords !== []) {
                $avgWordLen = self::mean(array_map('mb_strlen', $wWords));
                $sentLens   = array_map(
                    fn(string $s): int => count(preg_split('/\s+/u', $s, -1, PREG_SPLIT_NO_EMPTY)),
                    $windowSents,
                );
                $avgSentLen  = self::mean($sentLens);
                $readability = $avgWordLen * 0.5 + $avgSentLen * 0.5;
                $windows[]   = $readability;
            }
        }

        if (count($windows) < 3) {
            return 0.5;
        }

        $avgR = self::mean($windows);
        if ($avgR == 0) {
            return 0.5;
        }

        $sdR = self::stdev($windows);
        $cvR = $sdR / $avgR;

        // AI: CV < 0.1, Human: CV > 0.15
        $score = max(0.0, 1.0 - $cvR / 0.2);
        return max(0.0, min(1.0, $score));
    }

    // ═══════════════════════════════════════════════════════════
    //  12. TEXT RHYTHM
    // ═══════════════════════════════════════════════════════════

    /**
     * Rhythm analysis — sentence length pattern.
     *
     * AI: long-long-long (monotonous)
     * Human: long-short-medium-long-short (irregular)
     * Returns: 0.0 (irregular = human) — 1.0 (monotonous = AI)
     */
    private function calcRhythm(array $sentences): float
    {
        if (count($sentences) < 5) {
            return 0.5;
        }

        $lengths = array_map(
            fn(string $s): int => count(preg_split('/\s+/u', $s, -1, PREG_SPLIT_NO_EMPTY)),
            $sentences,
        );

        $n     = count($lengths);
        $meanL = self::mean($lengths);
        $varL  = self::variance($lengths);

        // 1. Autocorrelation lag-1
        if ($varL == 0) {
            $autocorr = 1.0; // All same length — very AI-like
        } else {
            $numerator = 0.0;
            for ($i = 0; $i < $n - 1; $i++) {
                $numerator += ($lengths[$i] - $meanL) * ($lengths[$i + 1] - $meanL);
            }
            $numerator /= ($n - 1);
            $autocorr   = $numerator / $varL;
        }

        // AC: AI ~0.3–0.6, Human ~−0.1–0.2
        $autocorrScore = max(0.0, ($autocorr + 0.1) / 0.7);

        // 2. Runs of same length category (S/M/L)
        $categories = [];
        foreach ($lengths as $l) {
            if ($l <= 8) {
                $categories[] = 'S';
            } elseif ($l <= 20) {
                $categories[] = 'M';
            } else {
                $categories[] = 'L';
            }
        }

        $runs = 1;
        for ($i = 1; $i < count($categories); $i++) {
            if ($categories[$i] !== $categories[$i - 1]) {
                $runs++;
            }
        }

        $expectedRuns = $n;
        $runRatio     = $expectedRuns > 0 ? $runs / $expectedRuns : 0;
        $runScore     = max(0.0, 1.0 - $runRatio / 0.8);

        // 3. Paired lengths (two consecutive sentences within ±3 words)
        $pairs = 0;
        for ($i = 0; $i < $n - 1; $i++) {
            if (abs($lengths[$i] - $lengths[$i + 1]) <= 3) {
                $pairs++;
            }
        }
        $pairRatio = $n > 1 ? $pairs / ($n - 1) : 0;
        $pairScore = min($pairRatio / 0.5, 1.0);

        $score = $autocorrScore * 0.4 + $runScore * 0.3 + $pairScore * 0.3;
        return max(0.0, min(1.0, $score));
    }

    // ═══════════════════════════════════════════════════════════
    //  CALIBRATION & EXPLANATIONS
    // ═══════════════════════════════════════════════════════════

    /**
     * Sigmoidal calibration for better separation.
     *
     * Amplifies differences in the middle zone (0.3–0.7).
     */
    private static function calibrate(float $raw): float
    {
        // Logistic function centered at 0.45
        $k = 8.0;
        return 1.0 / (1.0 + exp(-$k * ($raw - 0.45)));
    }

    /**
     * Generate human-readable explanations.
     *
     * @param array<string, float> $scores
     * @return list<string>
     */
    private function generateExplanations(array $scores, DetectionResult $result, string $lang): array
    {
        $explanations = [];
        $threshold    = 0.6;

        $featureNames = [
            'entropy'     => 'Low text entropy (predictable word choice)',
            'burstiness'  => 'Uniform sentence lengths (low burstiness)',
            'vocabulary'  => 'Limited vocabulary diversity',
            'zipf'        => 'Word frequency deviation from natural distribution',
            'stylometry'  => 'Formal/academic writing style typical of AI',
            'pattern'     => 'AI-characteristic words and phrases detected',
            'punctuation' => 'Punctuation profile typical of AI',
            'coherence'   => 'Overly consistent paragraph transitions',
            'grammar'     => 'Unnaturally perfect grammar and formatting',
            'opening'     => 'Repetitive sentence openings',
            'readability' => 'Uniform readability across text segments',
            'rhythm'      => 'Monotonous sentence length rhythm',
        ];

        $featureNamesRu = [
            'entropy'     => 'Низкая энтропия текста (предсказуемый выбор слов)',
            'burstiness'  => 'Однородная длина предложений (низкая вариативность)',
            'vocabulary'  => 'Ограниченное лексическое разнообразие',
            'zipf'        => 'Отклонение частот слов от естественного распределения',
            'stylometry'  => 'Формальный академический стиль, характерный для AI',
            'pattern'     => 'Обнаружены AI-характерные слова и фразы',
            'punctuation' => 'Пунктуационный профиль характерный для AI',
            'coherence'   => 'Излишне последовательные переходы между абзацами',
            'grammar'     => 'Неестественно идеальная грамматика и форматирование',
            'opening'     => 'Повторяющиеся начала предложений',
            'readability' => 'Одинаковая читаемость по всему тексту',
            'rhythm'      => 'Монотонный ритм длины предложений',
        ];

        $names = in_array($lang, ['ru', 'uk'], true) ? $featureNamesRu : $featureNames;

        // Sort by score descending (most AI-like first)
        arsort($scores);

        foreach ($scores as $feature => $score) {
            if ($score >= $threshold) {
                $explanations[] = sprintf('%s (%.0f%%)', $names[$feature] ?? $feature, $score * 100);
            }
        }

        // Add positive (human-like) indicators
        $humanFeatures = [];
        foreach ($scores as $feature => $score) {
            if ($score < 0.3) {
                $humanFeatures[] = [$feature, $score];
            }
        }

        if ($humanFeatures !== []) {
            $explanations[] = '';

            $namesHumanEn = [
                'entropy'    => 'Natural text entropy',
                'burstiness' => 'Good sentence length variation',
                'vocabulary' => 'Rich vocabulary',
                'pattern'    => 'Few AI-characteristic patterns',
                'opening'    => 'Diverse sentence openings',
                'rhythm'     => 'Natural writing rhythm',
            ];

            $namesHumanRu = [
                'entropy'    => 'Естественная энтропия текста',
                'burstiness' => 'Хорошая вариативность длины предложений',
                'vocabulary' => 'Богатый словарный запас',
                'pattern'    => 'Мало AI-характерных паттернов',
                'opening'    => 'Разнообразные начала предложений',
                'rhythm'     => 'Естественный ритм письма',
            ];

            $hn = in_array($lang, ['ru', 'uk'], true) ? $namesHumanRu : $namesHumanEn;

            foreach (array_slice($humanFeatures, 0, 3) as [$feature, $score]) {
                $explanation = $hn[$feature] ?? null;
                if ($explanation !== null) {
                    $explanations[] = "✓ {$explanation}";
                }
            }
        }

        return $explanations;
    }
}
