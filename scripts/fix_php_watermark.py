#!/usr/bin/env python3
"""Fix PHP WatermarkDetector to separate typography from suspicious homoglyphs."""

f = "/home/topbit/texthumanize.link/www/vendor/ksanyok/text-humanize/php/src/WatermarkDetector.php"
with open(f, "r") as fh:
    content = fh.read()

# 1. Replace const header
content = content.replace(
    '/** Special homoglyphs (look like normal chars but from other code blocks) */',
    '/** Suspicious homoglyphs (actual watermark evidence) */'
)

# 2. Remove typography chars from SPECIAL_HOMOGLYPHS and create TYPOGRAPHY_NORMALIZE
old_block = '''        // Confusable punctuation
        "\\u{2018}" => "'", "\\u{2019}" => "'", "\\u{201c}" => '"', "\\u{201d}" => '"',
        "\\u{2012}" => '-', "\\u{2013}" => '-', "\\u{2014}" => '-',
        "\\u{2212}" => '-', // minus sign vs hyphen
        "\\u{00a0}" => ' ', // Non-breaking space
        "\\u{2003}" => ' ', // Em space
        "\\u{2002}" => ' ', // En space
        "\\u{2009}" => ' ', // Thin space
        "\\u{200a}" => ' ', // Hair space
        "\\u{205f}" => ' ', // Medium Mathematical Space
        "\\u{3000}" => ' ', // Ideographic Space
    ];'''

new_block = '''    ];

    /** Common typography chars — normalize but do NOT flag as watermark */
    private const TYPOGRAPHY_NORMALIZE = [
        "\\u{2018}" => "'", "\\u{2019}" => "'", "\\u{201c}" => '"', "\\u{201d}" => '"',
        "\\u{2012}" => '-', "\\u{2013}" => '-', "\\u{2014}" => '-',
        "\\u{2212}" => '-', // minus sign vs hyphen
        "\\u{00a0}" => ' ', // Non-breaking space
        "\\u{2003}" => ' ', // Em space
        "\\u{2002}" => ' ', // En space
        "\\u{2009}" => ' ', // Thin space
        "\\u{200a}" => ' ', // Hair space
        "\\u{205f}" => ' ', // Medium Mathematical Space
        "\\u{3000}" => ' ', // Ideographic Space
    ];'''

if old_block in content:
    content = content.replace(old_block, new_block)
    print("OK: Split SPECIAL_HOMOGLYPHS into two consts")
else:
    print("WARN: Could not find old typography block in SPECIAL_HOMOGLYPHS")

# 3. Update detectHomoglyphs method to handle typography separately
old_detect = '''            // Check special homoglyphs
            if (isset(self::SPECIAL_HOMOGLYPHS[$ch])) {
                $expected = self::SPECIAL_HOMOGLYPHS[$ch];
                if ($ch !== $expected) {
                    $homoglyphs[] = [$ch, $expected, $i];
                    $chars[$i] = $expected;
                }
            }
        }

        if ($homoglyphs !== []) {
            $report->watermarkTypes[] = 'homoglyph_substitution';
            $report->homoglyphsFound = $homoglyphs;
            $count = count($homoglyphs);
            $report->details[] = "Found {$count} homoglyph substitutions";
            $report->charactersRemoved += $count;
            $report->cleanedText = implode('', $chars);
        }'''

new_detect = '''            // Check suspicious homoglyphs (real watermark evidence)
            if (isset(self::SPECIAL_HOMOGLYPHS[$ch])) {
                $expected = self::SPECIAL_HOMOGLYPHS[$ch];
                if ($ch !== $expected) {
                    $homoglyphs[] = [$ch, $expected, $i];
                    $chars[$i] = $expected;
                }
            }

            // Typography normalization (clean but do NOT flag as watermark)
            if (isset(self::TYPOGRAPHY_NORMALIZE[$ch])) {
                $expected = self::TYPOGRAPHY_NORMALIZE[$ch];
                if ($ch !== $expected) {
                    $chars[$i] = $expected;
                }
            }
        }

        // Always normalize text (typography + real homoglyphs)
        $report->cleanedText = implode('', $chars);

        if ($homoglyphs !== []) {
            $report->watermarkTypes[] = 'homoglyph_substitution';
            $report->homoglyphsFound = $homoglyphs;
            $count = count($homoglyphs);
            $report->details[] = "Found {$count} homoglyph substitutions";
            $report->charactersRemoved += $count;
        }'''

if old_detect in content:
    content = content.replace(old_detect, new_detect)
    print("OK: Updated detectHomoglyphs method")
else:
    print("WARN: Could not find old detectHomoglyphs block")

# 4. Also fix content_provenance regex if present (remove AI-Generated match)
old_re = "AI[\-\\s]?Generated|Machine[\-\\s]?Generated|"
if old_re in content:
    content = content.replace(old_re, "")
    print("OK: Removed AI-Generated from content_provenance regex")

with open(f, "w") as fh:
    fh.write(content)

print("Done! PHP WatermarkDetector fixed.")
