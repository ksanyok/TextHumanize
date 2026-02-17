<?php

declare(strict_types=1);

namespace TextHumanize;

/**
 * AnalysisReport — text artificiality metrics.
 */
class AnalysisReport
{
    public function __construct(
        public readonly string $lang,
        public readonly int $totalChars,
        public readonly int $totalWords,
        public readonly int $totalSentences,
        public readonly float $avgSentenceLength,
        public readonly float $sentenceLengthVariance,
        public readonly float $bureaucraticRatio,
        public readonly float $connectorRatio,
        public readonly float $repetitionScore,
        public readonly float $typographyScore,
        public readonly float $burstinessScore,
        public readonly float $artificialityScore,
        public readonly array $details = [],
    ) {
    }

    /**
     * Convert report to associative array.
     */
    public function toArray(): array
    {
        return [
            'lang' => $this->lang,
            'total_chars' => $this->totalChars,
            'total_words' => $this->totalWords,
            'total_sentences' => $this->totalSentences,
            'avg_sentence_length' => $this->avgSentenceLength,
            'sentence_length_variance' => $this->sentenceLengthVariance,
            'bureaucratic_ratio' => $this->bureaucraticRatio,
            'connector_ratio' => $this->connectorRatio,
            'repetition_score' => $this->repetitionScore,
            'typography_score' => $this->typographyScore,
            'burstiness_score' => $this->burstinessScore,
            'artificiality_score' => $this->artificialityScore,
            'details' => $this->details,
        ];
    }
}
