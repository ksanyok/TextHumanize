<?php
/**
 * TextHumanize PHP — Basic Usage Example
 *
 * Run: php examples/basic_usage.php
 */

require_once __DIR__ . '/../vendor/autoload.php';

use TextHumanize\TextHumanize;

// ═══════════════════════════════════════════════════════════════
//  1. HUMANIZE TEXT
// ═══════════════════════════════════════════════════════════════

$text = <<<TEXT
In order to facilitate the implementation of the aforementioned project, 
it is necessary to establish a comprehensive framework. Furthermore, 
the methodology should be designed to ensure optimal efficiency. 
Additionally, all stakeholders should be engaged in the process.
TEXT;

echo "=== ORIGINAL ===\n";
echo $text . "\n\n";

$result = TextHumanize::humanize($text, profile: 'web', intensity: 60);

echo "=== HUMANIZED ===\n";
echo $result->processed . "\n\n";
echo "Language: {$result->lang}\n";
echo "Profile: {$result->profile}\n";
echo sprintf("Change ratio: %.1f%%\n", $result->getChangeRatio() * 100);
echo sprintf("Similarity: %.1f%%\n", $result->getSimilarity() * 100);
echo sprintf("Quality score: %.2f\n", $result->getQualityScore());

// ═══════════════════════════════════════════════════════════════
//  2. ANALYZE TEXT
// ═══════════════════════════════════════════════════════════════

echo "\n=== ANALYSIS ===\n";
$report = TextHumanize::analyze($text);

echo "Artificiality score: {$report->artificialityScore}%\n";
echo "Words: {$report->totalWords}\n";
echo "Sentences: {$report->totalSentences}\n";
echo sprintf("Avg sentence length: %.1f words\n", $report->avgSentenceLength);
echo sprintf("Bureaucratic ratio: %.2f\n", $report->bureaucraticRatio);
echo sprintf("Connector ratio: %.2f\n", $report->connectorRatio);

// ═══════════════════════════════════════════════════════════════
//  3. EXPLAIN CHANGES
// ═══════════════════════════════════════════════════════════════

echo "\n=== EXPLAIN ===\n";
$explain = TextHumanize::explain($text, profile: 'chat', intensity: 70);
echo "Summary: {$explain['summary']}\n";
echo sprintf("Change ratio: %.1f%%\n", $explain['change_ratio'] * 100);
echo "Recommendations:\n";
foreach (array_slice($explain['recommendations'] ?? [], 0, 5) as $rec) {
    echo "  • {$rec}\n";
}

// ═══════════════════════════════════════════════════════════════
//  4. REPRODUCIBLE RESULTS (SEED)
// ═══════════════════════════════════════════════════════════════

echo "\n=== REPRODUCIBILITY ===\n";
$r1 = TextHumanize::humanize($text, seed: 42);
$r2 = TextHumanize::humanize($text, seed: 42);
echo "Same seed → same result: " . ($r1->processed === $r2->processed ? "YES" : "NO") . "\n";
