<?php

declare(strict_types=1);

namespace TextHumanize;

use TextHumanize\Lang\Registry;

/**
 * TextAnalyzer — computes artificiality metrics for text.
 */
class TextAnalyzer
{
    private string $lang;
    private array $langPack;

    public function __construct(string $lang = 'en')
    {
        $this->lang = $lang;
        $this->langPack = Registry::get($lang);
    }

    /**
     * Analyze text and return an AnalysisReport.
     */
    public function analyze(string $text): AnalysisReport
    {
        $text = trim($text);
        if ($text === '') {
            return new AnalysisReport(
                lang: $this->lang,
                totalChars: 0,
                totalWords: 0,
                totalSentences: 0,
                avgSentenceLength: 0.0,
                sentenceLengthVariance: 0.0,
                bureaucraticRatio: 0.0,
                connectorRatio: 0.0,
                repetitionScore: 0.0,
                typographyScore: 0.0,
                burstinessScore: 0.5,
                artificialityScore: 0.0,
            );
        }

        $sentences = $this->splitSentences($text);
        $words = preg_split('/\s+/', $text);
        $totalWords = count($words);
        $totalSentences = count($sentences);

        // Sentence lengths
        $sentenceLengths = array_map(
            fn(string $s): int => count(preg_split('/\s+/', trim($s))),
            $sentences
        );

        $avgLen = $totalSentences > 0 ? array_sum($sentenceLengths) / $totalSentences : 0;

        $variance = 0;
        foreach ($sentenceLengths as $len) {
            $variance += ($len - $avgLen) ** 2;
        }
        $variance = $totalSentences > 0 ? $variance / $totalSentences : 0;

        // Metrics
        $bureaucraticRatio = $this->calcBureaucraticRatio($text, $totalWords);
        $connectorRatio = $this->calcConnectorRatio($text, $totalSentences);
        $repetitionScore = $this->calcRepetitionScore($text);
        $typographyScore = $this->calcTypographyScore($text);
        $burstinessScore = $this->calcBurstinessScore($sentenceLengths, $avgLen);

        $details = [
            'sentence_lengths' => $sentenceLengths,
            'found_bureaucratic' => [],
            'found_connectors' => [],
            'typography_issues' => [],
            'burstiness_cv' => 0.0,
        ];

        // Artificiality score
        $artificialityScore = $this->calcArtificialityScore(
            $variance, $avgLen, $bureaucraticRatio, $connectorRatio,
            $repetitionScore, $typographyScore, $burstinessScore
        );

        return new AnalysisReport(
            lang: $this->lang,
            totalChars: mb_strlen($text),
            totalWords: $totalWords,
            totalSentences: $totalSentences,
            avgSentenceLength: round($avgLen, 2),
            sentenceLengthVariance: round($variance, 2),
            bureaucraticRatio: round($bureaucraticRatio, 4),
            connectorRatio: round($connectorRatio, 4),
            repetitionScore: round($repetitionScore, 4),
            typographyScore: round($typographyScore, 4),
            burstinessScore: round($burstinessScore, 4),
            artificialityScore: round($artificialityScore, 2),
            details: $details,
        );
    }

    /**
     * @return string[]
     */
    private function splitSentences(string $text): array
    {
        $parts = preg_split('/(?<=[.!?…])\s+/u', trim($text));
        return array_values(array_filter($parts, fn(string $s): bool => trim($s) !== ''));
    }

    private function calcBureaucraticRatio(string $text, int $totalWords): float
    {
        if ($totalWords === 0) {
            return 0.0;
        }

        $lower = mb_strtolower($text);
        $hits = 0;

        // Phrase hits
        foreach (($this->langPack['bureaucratic_phrases'] ?? []) as $phrase => $_) {
            $pattern = '/' . preg_quote($phrase, '/') . '/ui';
            $hits += preg_match_all($pattern, $lower);
        }

        // Word hits
        foreach (($this->langPack['bureaucratic'] ?? []) as $word => $_) {
            $pattern = '/\b' . preg_quote($word, '/') . '\b/ui';
            $hits += preg_match_all($pattern, $lower);
        }

        return min($hits / $totalWords, 1.0);
    }

    private function calcConnectorRatio(string $text, int $totalSentences): float
    {
        if ($totalSentences === 0) {
            return 0.0;
        }

        $hits = 0;
        foreach (($this->langPack['ai_connectors'] ?? []) as $connector => $_) {
            $pattern = '/\b' . preg_quote($connector, '/') . '\b/ui';
            $hits += preg_match_all($pattern, $text);
        }

        return min($hits / $totalSentences, 1.0);
    }

    private function calcRepetitionScore(string $text): float
    {
        $stopWords = array_flip($this->langPack['stop_words'] ?? []);

        preg_match_all('/[\p{L}]+/u', $text, $matches);
        $allWords = $matches[0];
        $contentWords = [];

        foreach ($allWords as $word) {
            $lower = mb_strtolower($word);
            if (mb_strlen($lower) > 2 && !isset($stopWords[$lower])) {
                $contentWords[] = $lower;
            }
        }

        if (count($contentWords) < 3) {
            return 0.0;
        }

        // Lexical diversity
        $unique = count(array_unique($contentWords));
        $diversity = $unique / count($contentWords);

        // Bigram repetition
        $bigrams = [];
        for ($i = 0; $i < count($contentWords) - 1; $i++) {
            $bg = $contentWords[$i] . ' ' . $contentWords[$i + 1];
            $bigrams[$bg] = ($bigrams[$bg] ?? 0) + 1;
        }
        $repeatedBigrams = count(array_filter($bigrams, fn(int $c): bool => $c >= 2));
        $bigramRatio = count($bigrams) > 0 ? $repeatedBigrams / count($bigrams) : 0;

        return (1 - $diversity) * 0.5 + $bigramRatio * 0.5;
    }

    private function calcTypographyScore(string $text): float
    {
        $hits = 0;
        $checks = 6;

        if (str_contains($text, '—')) $hits++;
        if (preg_match('/[«»„""]/u', $text)) $hits++;
        if (str_contains($text, '…')) $hits++;
        if (str_contains($text, "\xC2\xA0")) $hits++; // non-breaking space
        if (preg_match('/;.*?;/u', $text)) $hits++; // Multiple semicolons
        if (preg_match('/:.*?:.*?:/u', $text)) $hits++; // Multiple colons

        return $hits / $checks;
    }

    private function calcBurstinessScore(array $lengths, float $avg): float
    {
        if (count($lengths) < 2 || $avg <= 0) {
            return 0.5;
        }

        $variance = 0;
        foreach ($lengths as $len) {
            $variance += ($len - $avg) ** 2;
        }
        $variance /= count($lengths);
        $cv = sqrt($variance) / $avg;

        // Normalize: 0 = uniform (AI), 1 = varied (human)
        return min($cv, 1.0);
    }

    private function calcArtificialityScore(
        float $variance, float $avgLen,
        float $bureaucratic, float $connector,
        float $repetition, float $typography,
        float $burstiness,
    ): float {
        $score = 0.0;
        $cv = $avgLen > 0 ? sqrt($variance) / $avgLen : 0;

        // Low variance = AI-like
        if ($cv < 0.3) {
            $score += 20;
        } elseif ($cv < 0.5) {
            $score += 10;
        }

        $score += $bureaucratic * 25;
        $score += $connector * 20;
        $score += $repetition * 15;
        $score += $typography * 20;

        // Low burstiness = AI-like
        if ($burstiness < 0.3) {
            $score += 15;
        } elseif ($burstiness < 0.5) {
            $score += 5;
        }

        return min($score, 100.0);
    }
}
