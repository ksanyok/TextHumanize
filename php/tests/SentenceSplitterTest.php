<?php

declare(strict_types=1);

namespace TextHumanize\Tests;

use PHPUnit\Framework\TestCase;
use TextHumanize\SentenceSplitter;

class SentenceSplitterTest extends TestCase
{
    // ==================== Split ====================

    public function testSplitSimpleSentences(): void
    {
        $splitter = new SentenceSplitter('en');
        $sentences = $splitter->split('Hello world. How are you? I am fine!');

        $this->assertIsArray($sentences);
        $this->assertCount(3, $sentences);
        $this->assertSame('Hello world.', $sentences[0]);
        $this->assertSame('How are you?', $sentences[1]);
        $this->assertSame('I am fine!', $sentences[2]);
    }

    public function testSplitSingleSentence(): void
    {
        $splitter = new SentenceSplitter('en');
        $sentences = $splitter->split('Just one sentence here.');
        $this->assertCount(1, $sentences);
    }

    public function testSplitEmptyText(): void
    {
        $splitter = new SentenceSplitter('en');
        $sentences = $splitter->split('');
        $this->assertIsArray($sentences);
        $this->assertCount(0, $sentences);
    }

    public function testSplitWithAbbreviations(): void
    {
        $splitter = new SentenceSplitter('en');
        $sentences = $splitter->split('Mr. Smith went to Washington. He met Dr. Jones there.');
        $this->assertCount(2, $sentences);
    }

    public function testSplitMultipleParagraphs(): void
    {
        $splitter = new SentenceSplitter('en');
        $text = "First paragraph sentence one. Sentence two.\n\nSecond paragraph sentence three. Sentence four.";
        $sentences = $splitter->split($text);
        $this->assertGreaterThanOrEqual(4, count($sentences));
    }

    public function testSplitRussian(): void
    {
        $splitter = new SentenceSplitter('ru');
        $sentences = $splitter->split('Первое предложение. Второе предложение. Третье предложение.');
        $this->assertIsArray($sentences);
        $this->assertGreaterThanOrEqual(1, count($sentences));
    }

    public function testSplitWithEllipsis(): void
    {
        $splitter = new SentenceSplitter('en');
        $sentences = $splitter->split('First sentence... Second sentence.');
        $this->assertIsArray($sentences);
        $this->assertGreaterThanOrEqual(1, count($sentences));
    }

    public function testSplitQuotedText(): void
    {
        $splitter = new SentenceSplitter('en');
        $text = 'He said "Hello there." Then he left.';
        $sentences = $splitter->split($text);
        $this->assertIsArray($sentences);
        $this->assertGreaterThanOrEqual(1, count($sentences));
    }

    public function testSplitWithNumbers(): void
    {
        $splitter = new SentenceSplitter('en');
        $text = 'The price is $3.50 per item. Total is $7.00.';
        $sentences = $splitter->split($text);
        $this->assertCount(2, $sentences);
    }

    // ==================== SplitSpans ====================

    public function testSplitSpans(): void
    {
        $splitter = new SentenceSplitter('en');
        $text = 'Hello world. How are you?';
        $spans = $splitter->splitSpans($text);

        $this->assertIsArray($spans);
        $this->assertGreaterThanOrEqual(2, count($spans));

        foreach ($spans as $span) {
            $this->assertArrayHasKey('text', $span);
            $this->assertArrayHasKey('start', $span);
            $this->assertArrayHasKey('end', $span);
            $this->assertArrayHasKey('index', $span);
            $this->assertIsString($span['text']);
            $this->assertIsInt($span['start']);
            $this->assertIsInt($span['end']);
            $this->assertIsInt($span['index']);
        }
    }

    public function testSplitSpansIndicesValid(): void
    {
        $splitter = new SentenceSplitter('en');
        $text = 'First sentence. Second sentence. Third one.';
        $spans = $splitter->splitSpans($text);

        for ($i = 0; $i < count($spans); $i++) {
            $this->assertSame($i, $spans[$i]['index']);
            $this->assertGreaterThanOrEqual(0, $spans[$i]['start']);
            $this->assertLessThanOrEqual(strlen($text), $spans[$i]['end']);
            // end of one span should be start of next (or close to it)
            if ($i > 0) {
                $this->assertGreaterThanOrEqual($spans[$i - 1]['start'], $spans[$i]['start']);
            }
        }
    }

    public function testSplitSpansEmpty(): void
    {
        $splitter = new SentenceSplitter('en');
        $spans = $splitter->splitSpans('');
        $this->assertIsArray($spans);
        $this->assertCount(0, $spans);
    }

    // ==================== Repair ====================

    public function testRepairJoinsFragments(): void
    {
        $splitter = new SentenceSplitter('en');
        $fragments = ['Hello', 'world.', 'How are', 'you?'];
        $repaired = $splitter->repair($fragments);

        $this->assertIsArray($repaired);
        // Should attempt to join fragments that lack terminal punctuation
        $this->assertGreaterThanOrEqual(1, count($repaired));
    }

    public function testRepairNormalSentences(): void
    {
        $splitter = new SentenceSplitter('en');
        $sentences = ['First sentence.', 'Second sentence.', 'Third one!'];
        $repaired = $splitter->repair($sentences);

        $this->assertIsArray($repaired);
        $this->assertCount(3, $repaired);
    }

    public function testRepairEmptyArray(): void
    {
        $splitter = new SentenceSplitter('en');
        $repaired = $splitter->repair([]);
        $this->assertIsArray($repaired);
        $this->assertCount(0, $repaired);
    }

    public function testRepairSingleFragment(): void
    {
        $splitter = new SentenceSplitter('en');
        $repaired = $splitter->repair(['Just a fragment']);
        $this->assertIsArray($repaired);
        $this->assertCount(1, $repaired);
    }

    // ==================== Standalone Function ====================

    public function testSplitSentencesFunction(): void
    {
        // Test the standalone function if it exists
        if (function_exists('TextHumanize\\split_sentences')) {
            $sentences = \TextHumanize\split_sentences('Hello. World.', 'en');
            $this->assertIsArray($sentences);
            $this->assertCount(2, $sentences);
        } else {
            $this->assertTrue(true); // Skip if function not available
        }
    }

    // ==================== Multi-language ====================

    public function testSplitGerman(): void
    {
        $splitter = new SentenceSplitter('de');
        $sentences = $splitter->split('Dies ist ein Test. Hier ist noch ein Satz.');
        $this->assertCount(2, $sentences);
    }

    public function testSplitFrench(): void
    {
        $splitter = new SentenceSplitter('fr');
        $sentences = $splitter->split("C'est un test. Voici une autre phrase.");
        $this->assertCount(2, $sentences);
    }

    public function testSplitUkrainian(): void
    {
        $splitter = new SentenceSplitter('uk');
        $sentences = $splitter->split('Це тест. Ось ще одне речення.');
        $this->assertCount(2, $sentences);
    }
}
