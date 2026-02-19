<?php
/**
 * TextHumanize PHP — Advanced Features Example
 *
 * Demonstrates: batch processing, tone analysis, plugins, chunked processing
 *
 * Run: php examples/advanced.php
 */

require_once __DIR__ . '/../vendor/autoload.php';

use TextHumanize\TextHumanize;
use TextHumanize\ToneAnalyzer;
use TextHumanize\Pipeline\Pipeline;

// ═══════════════════════════════════════════════════════════════
//  1. BATCH PROCESSING
// ═══════════════════════════════════════════════════════════════

echo "=== BATCH PROCESSING ===\n";

$texts = [
    "The implementation of the system requires careful consideration of multiple factors.",
    "Furthermore, the utilization of advanced methodologies ensures optimal performance.",
    "In conclusion, the comprehensive approach yields significant improvements.",
];

$results = TextHumanize::humanizeBatch($texts, profile: 'web', intensity: 50, seed: 42);

foreach ($results as $i => $result) {
    echo sprintf(
        "  Text %d: %.0f%% changed, quality: %.2f\n",
        $i + 1,
        $result->getChangeRatio() * 100,
        $result->getQualityScore()
    );
}

// ═══════════════════════════════════════════════════════════════
//  2. TONE ANALYSIS & ADJUSTMENT
// ═══════════════════════════════════════════════════════════════

echo "\n=== TONE ANALYSIS ===\n";

$formal_text = "The organization shall facilitate the implementation of the policy.";
$casual_text = "So basically we gotta get this thing done, right?";

$analyzer = new ToneAnalyzer('en');

$report1 = $analyzer->analyze($formal_text);
echo "Formal text:\n";
echo "  Primary tone: {$report1->primaryTone}\n";
echo sprintf("  Formality: %.2f\n", $report1->formality);

$report2 = $analyzer->analyze($casual_text);
echo "Casual text:\n";
echo "  Primary tone: {$report2->primaryTone}\n";
echo sprintf("  Formality: %.2f\n", $report2->formality);

// Adjust tone
echo "\n=== TONE ADJUSTMENT ===\n";
$adjusted = $analyzer->adjust($formal_text, 'casual');
echo "  Formal → Casual: {$adjusted}\n";

// ═══════════════════════════════════════════════════════════════
//  3. MULTILINGUAL SUPPORT
// ═══════════════════════════════════════════════════════════════

echo "\n=== MULTILINGUAL ===\n";

$ru_text = "Необходимо осуществлять мониторинг результатов в рамках данного проекта.";
$de_text = "Es ist notwendig, die Implementierung durchzuführen und die Ergebnisse zu gewährleisten.";

$ru_result = TextHumanize::humanize($ru_text, lang: 'ru', profile: 'chat');
echo "RU: {$ru_result->processed}\n";

$de_result = TextHumanize::humanize($de_text, lang: 'de', profile: 'web');
echo "DE: {$de_result->processed}\n";

// ═══════════════════════════════════════════════════════════════
//  4. CUSTOM PLUGINS
// ═══════════════════════════════════════════════════════════════

echo "\n=== PLUGINS ===\n";

// Register a custom plugin
Pipeline::registerPlugin(
    plugin: function (string $text, string $lang, string $profile, int $intensity): string {
        // Replace straight quotes with curly quotes
        return str_replace('"', "\u{201C}", $text);
    },
    after: 'typography',
);

$result = TextHumanize::humanize("She said \"hello\" to everyone.", profile: 'web');
echo "With plugin: {$result->processed}\n";

Pipeline::clearPlugins();

// ═══════════════════════════════════════════════════════════════
//  5. CHUNKED PROCESSING (LARGE TEXTS)
// ═══════════════════════════════════════════════════════════════

echo "\n=== CHUNKED PROCESSING ===\n";

$long_text = str_repeat(
    "The comprehensive implementation ensures optimal performance. " .
    "Furthermore, the methodology provides significant improvements. ",
    20
);

$result = TextHumanize::humanizeChunked($long_text, chunkSize: 500, profile: 'web');
echo "Processed " . strlen($long_text) . " chars → " . strlen($result->processed) . " chars\n";
echo sprintf("Change ratio: %.1f%%\n", $result->getChangeRatio() * 100);

// ═══════════════════════════════════════════════════════════════
//  6. PROFILES COMPARISON
// ═══════════════════════════════════════════════════════════════

echo "\n=== PROFILES COMPARISON ===\n";

$sample = "It is necessary to implement the solution in order to achieve the desired outcome.";

foreach (['chat', 'web', 'seo', 'docs', 'formal'] as $profile) {
    $r = TextHumanize::humanize($sample, profile: $profile, intensity: 60, seed: 1);
    echo sprintf("  %-7s (%.0f%% changed): %s\n", $profile, $r->getChangeRatio() * 100, $r->processed);
}
