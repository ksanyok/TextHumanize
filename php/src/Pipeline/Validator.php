<?php

declare(strict_types=1);

namespace TextHumanize\Pipeline;

use TextHumanize\AnalysisReport;
use TextHumanize\HumanizeOptions;
use TextHumanize\TextAnalyzer;

/**
 * ValidationResult — returned by the Validator.
 */
class ValidationResult
{
    public function __construct(
        public readonly bool $isValid,
        public readonly bool $shouldRollback,
        public readonly array $errors = [],
        public readonly array $warnings = [],
    ) {}
}

/**
 * Validator — ensures humanization hasn't degraded the text.
 */
class Validator
{
    public function validate(
        string $original,
        string $processed,
        HumanizeOptions $options,
    ): ValidationResult {
        $errors = [];
        $warnings = [];

        // 1. Change ratio check
        $changeRatio = $this->calcChangeRatio($original, $processed);
        if ($changeRatio > 0.70) {
            $errors[] = "Change ratio too high: {$changeRatio}";
        } elseif ($changeRatio > 0.55) {
            $warnings[] = "Change ratio elevated: {$changeRatio}";
        }

        // 2. Length ratio check
        $origLen = mb_strlen($original);
        $procLen = mb_strlen($processed);
        if ($origLen > 0) {
            $lengthRatio = $procLen / $origLen;
            if ($lengthRatio < 0.5 || $lengthRatio > 2.0) {
                $errors[] = "Length ratio out of bounds: {$lengthRatio}";
            } elseif ($lengthRatio < 0.7 || $lengthRatio > 1.5) {
                $warnings[] = "Length ratio elevated: {$lengthRatio}";
            }
        }

        // 3. Keywords preserved
        $keywords = $options->preserve['keywords'] ?? [];
        foreach ($keywords as $kw) {
            if (mb_stripos($processed, $kw) === false) {
                $errors[] = "Keyword lost: {$kw}";
            }
        }

        // 4. Numbers preserved
        preg_match_all('/\d+[\.,]?\d*/u', $original, $origNums);
        preg_match_all('/\d+[\.,]?\d*/u', $processed, $procNums);
        $origNumsSorted = $origNums[0]; sort($origNumsSorted);
        $procNumsSorted = $procNums[0]; sort($procNumsSorted);
        if ($origNumsSorted !== $procNumsSorted) {
            $warnings[] = 'Some numbers may have changed';
        }

        // 5. Sentence count check
        $origSent = $this->countSentences($original);
        $procSent = $this->countSentences($processed);
        if ($origSent > 0) {
            $sentRatio = $procSent / $origSent;
            if ($sentRatio < 0.5 || $sentRatio > 2.0) {
                $warnings[] = "Sentence count changed significantly: {$origSent} → {$procSent}";
            }
        }

        // 6. Paragraph / line-structure preserved
        $origLines = array_filter(explode("\n", $original), fn(string $s): bool => trim($s) !== '');
        $procLines = array_filter(explode("\n", $processed), fn(string $s): bool => trim($s) !== '');
        if (count($origLines) > 0 && count($procLines) > 0) {
            $lineRatio = count($procLines) / count($origLines);
            if ($lineRatio < 0.7) {
                $warnings[] = sprintf(
                    'Line structure lost: %d → %d lines',
                    count($origLines),
                    count($procLines),
                );
            }
        }

        $isValid = count($errors) === 0;
        $shouldRollback = count($errors) >= 2;

        return new ValidationResult(
            isValid: $isValid,
            shouldRollback: $shouldRollback,
            errors: $errors,
            warnings: $warnings,
        );
    }

    private function calcChangeRatio(string $a, string $b): float
    {
        $wordsA = preg_split('/\s+/u', trim($a));
        $wordsB = preg_split('/\s+/u', trim($b));

        $setA = array_count_values($wordsA);
        $setB = array_count_values($wordsB);

        $common = 0;
        foreach ($setA as $word => $countA) {
            $countB = $setB[$word] ?? 0;
            $common += min($countA, $countB);
        }

        $total = max(count($wordsA), count($wordsB));
        if ($total === 0) {
            return 0.0;
        }

        return round(1 - ($common / $total), 4);
    }

    private function countSentences(string $text): int
    {
        $parts = preg_split('/(?<=[.!?…])\s+/u', trim($text));
        return count(array_filter($parts, fn(string $s): bool => trim($s) !== ''));
    }
}
