<?php

declare(strict_types=1);

namespace TextHumanize\Tests;

use PHPUnit\Framework\TestCase;
use TextHumanize\Profiles;
use TextHumanize\RandomHelper;
use TextHumanize\Lang\Registry;
use TextHumanize\Pipeline\RepetitionReducer;
use TextHumanize\Pipeline\StructureDiversifier;
use TextHumanize\Pipeline\TextNaturalizer;
use TextHumanize\Pipeline\LivelinessInjector;
use TextHumanize\Pipeline\UniversalProcessor;

class PipelineStagesTest extends TestCase
{
    // ==================== RepetitionReducer ====================

    public function testRepetitionReducerBasic(): void
    {
        $reducer = new RepetitionReducer();
        $langPack = Registry::get('en');
        $profile = Profiles::get('web');
        $rng = new RandomHelper(42);

        $text = 'The system is important. The system provides performance. The system ensures coverage. The system handles everything well.';
        $result = $reducer->process($text, $langPack, $profile, 70, $rng);

        $this->assertIsString($result);
        $this->assertNotEmpty($result);
    }

    public function testRepetitionReducerTracksChanges(): void
    {
        $reducer = new RepetitionReducer();
        $langPack = Registry::get('en');
        $profile = Profiles::get('web');
        $rng = new RandomHelper(42);

        $text = 'The important system is important. This important feature provides important coverage.';
        $reducer->process($text, $langPack, $profile, 70, $rng);

        $this->assertIsArray($reducer->changes);
    }

    public function testRepetitionReducerEmptyText(): void
    {
        $reducer = new RepetitionReducer();
        $langPack = Registry::get('en');
        $profile = Profiles::get('web');
        $rng = new RandomHelper(1);

        $result = $reducer->process('', $langPack, $profile, 50, $rng);
        $this->assertSame('', $result);
    }

    public function testRepetitionReducerNoRepetitions(): void
    {
        $reducer = new RepetitionReducer();
        $langPack = Registry::get('en');
        $profile = Profiles::get('web');
        $rng = new RandomHelper(42);

        $text = 'Each word here is unique. No repetition exists anywhere.';
        $result = $reducer->process($text, $langPack, $profile, 50, $rng);
        $this->assertNotEmpty($result);
    }

    public function testRepetitionReducerRussian(): void
    {
        $reducer = new RepetitionReducer();
        $langPack = Registry::get('ru');
        $profile = Profiles::get('web');
        $rng = new RandomHelper(42);

        $text = 'Система обеспечивает результат. Система показывает данные. Система работает хорошо.';
        $result = $reducer->process($text, $langPack, $profile, 60, $rng);
        $this->assertNotEmpty($result);
    }

    // ==================== StructureDiversifier ====================

    public function testStructureDiversifierBasic(): void
    {
        $diversifier = new StructureDiversifier();
        $langPack = Registry::get('en');
        $profile = Profiles::get('web');
        $rng = new RandomHelper(42);

        $text = 'Furthermore, the implementation is comprehensive. Moreover, the solution is robust. Additionally, the system is scalable. Consequently, we can proceed.';
        $result = $diversifier->process($text, $langPack, $profile, 70, $rng);

        $this->assertIsString($result);
        $this->assertNotEmpty($result);
    }

    public function testStructureDiversifierTracksChanges(): void
    {
        $diversifier = new StructureDiversifier();
        $langPack = Registry::get('en');
        $profile = Profiles::get('chat');
        $rng = new RandomHelper(42);

        $text = 'Furthermore, the system works. Moreover, the results are good. Additionally, we proceed forward.';
        $diversifier->process($text, $langPack, $profile, 80, $rng);
        $this->assertIsArray($diversifier->changes);
    }

    public function testStructureDiversifierEmptyText(): void
    {
        $diversifier = new StructureDiversifier();
        $langPack = Registry::get('en');
        $profile = Profiles::get('web');
        $rng = new RandomHelper(1);

        $result = $diversifier->process('', $langPack, $profile, 50, $rng);
        $this->assertSame('', $result);
    }

    public function testStructureDiversifierLongSentences(): void
    {
        $diversifier = new StructureDiversifier();
        $langPack = Registry::get('en');
        $profile = Profiles::get('web');
        $rng = new RandomHelper(42);

        $text = 'This is a very long sentence that goes on and on with many clauses and subordinate ideas that make it quite difficult to read and understand in a single pass because it contains so many different thoughts and concepts all strung together without adequate punctuation or pauses.';
        $result = $diversifier->process($text, $langPack, $profile, 70, $rng);
        $this->assertNotEmpty($result);
    }

    public function testStructureDiversifierShortSentences(): void
    {
        $diversifier = new StructureDiversifier();
        $langPack = Registry::get('en');
        $profile = Profiles::get('web');
        $rng = new RandomHelper(42);

        $text = 'Short one. Also short. Very brief. Tiny. Small too.';
        $result = $diversifier->process($text, $langPack, $profile, 70, $rng);
        $this->assertNotEmpty($result);
    }

    // ==================== TextNaturalizer ====================

    public function testTextNaturalizerBasic(): void
    {
        $naturalizer = new TextNaturalizer();
        $profile = Profiles::get('web');
        $rng = new RandomHelper(42);

        $text = 'It is important to note that the implementation ensures comprehensive coverage. The solution provides robust performance.';
        $result = $naturalizer->process($text, 'en', $profile, 70, $rng);

        $this->assertIsString($result);
        $this->assertNotEmpty($result);
    }

    public function testTextNaturalizerTracksChanges(): void
    {
        $naturalizer = new TextNaturalizer();
        $profile = Profiles::get('chat');
        $rng = new RandomHelper(42);

        $text = 'It is important to note that this is crucial. We need to ensure this works.';
        $naturalizer->process($text, 'en', $profile, 80, $rng);
        $this->assertIsArray($naturalizer->changes);
    }

    public function testTextNaturalizerEmptyText(): void
    {
        $naturalizer = new TextNaturalizer();
        $profile = Profiles::get('web');
        $rng = new RandomHelper(1);

        $result = $naturalizer->process('', 'en', $profile, 50, $rng);
        $this->assertSame('', $result);
    }

    public function testTextNaturalizerChatProfile(): void
    {
        $naturalizer = new TextNaturalizer();
        $profile = Profiles::get('chat');
        $rng = new RandomHelper(42);

        $text = 'The solution does not provide adequate coverage. It is not meant for production use. We cannot proceed without this.';
        $result = $naturalizer->process($text, 'en', $profile, 80, $rng);
        $this->assertNotEmpty($result);
    }

    public function testTextNaturalizerFormalProfile(): void
    {
        $naturalizer = new TextNaturalizer();
        $profile = Profiles::get('formal');
        $rng = new RandomHelper(42);

        $text = 'The implementation ensures comprehensive coverage of all requirements.';
        $result = $naturalizer->process($text, 'en', $profile, 50, $rng);
        $this->assertNotEmpty($result);
    }

    public function testTextNaturalizerRussian(): void
    {
        $naturalizer = new TextNaturalizer();
        $profile = Profiles::get('web');
        $rng = new RandomHelper(42);

        $text = 'Необходимо отметить что система обеспечивает надлежащее функционирование.';
        $result = $naturalizer->process($text, 'ru', $profile, 60, $rng);
        $this->assertNotEmpty($result);
    }

    // ==================== LivelinessInjector ====================

    public function testLivelinessInjectorBasic(): void
    {
        $injector = new LivelinessInjector();
        $langPack = Registry::get('en');
        $profile = Profiles::get('chat');
        $rng = new RandomHelper(42);

        $text = 'The system works well. The performance is good. The results are satisfactory. Everything seems fine.';
        $result = $injector->process($text, $langPack, $profile, 80, $rng);

        $this->assertIsString($result);
        $this->assertNotEmpty($result);
    }

    public function testLivelinessInjectorTracksChanges(): void
    {
        $injector = new LivelinessInjector();
        $langPack = Registry::get('en');
        $profile = Profiles::get('chat');
        $rng = new RandomHelper(42);

        $text = 'The system works properly. Results look good. Everything runs smoothly.';
        $injector->process($text, $langPack, $profile, 80, $rng);
        $this->assertIsArray($injector->changes);
    }

    public function testLivelinessInjectorEmptyText(): void
    {
        $injector = new LivelinessInjector();
        $langPack = Registry::get('en');
        $profile = Profiles::get('web');
        $rng = new RandomHelper(1);

        $result = $injector->process('', $langPack, $profile, 50, $rng);
        $this->assertSame('', $result);
    }

    public function testLivelinessInjectorFormalProfile(): void
    {
        $injector = new LivelinessInjector();
        $langPack = Registry::get('en');
        // formal profile may have liveliness_intensity = 0
        $profile = Profiles::get('formal');
        $rng = new RandomHelper(42);

        $text = 'The important system provides coverage.';
        $result = $injector->process($text, $langPack, $profile, 50, $rng);
        $this->assertIsString($result);
    }

    public function testLivelinessInjectorRussian(): void
    {
        $injector = new LivelinessInjector();
        $langPack = Registry::get('ru');
        $profile = Profiles::get('chat');
        $rng = new RandomHelper(42);

        $text = 'Система работает хорошо. Результаты удовлетворительные. Всё функционирует нормально.';
        $result = $injector->process($text, $langPack, $profile, 70, $rng);
        $this->assertNotEmpty($result);
    }

    // ==================== UniversalProcessor ====================

    public function testUniversalProcessorBasic(): void
    {
        $processor = new UniversalProcessor();
        $profile = Profiles::get('web');
        $rng = new RandomHelper(42);

        $text = 'The system works well. The performance is good. The results look promising. Everything runs properly.';
        $result = $processor->process($text, $profile, 70, $rng);

        $this->assertIsString($result);
        $this->assertNotEmpty($result);
    }

    public function testUniversalProcessorTracksChanges(): void
    {
        $processor = new UniversalProcessor();
        $profile = Profiles::get('web');
        $rng = new RandomHelper(42);

        $text = 'Some sample text. Another sentence here. Third one too.';
        $processor->process($text, $profile, 60, $rng);
        $this->assertIsArray($processor->changes);
    }

    public function testUniversalProcessorEmptyText(): void
    {
        $processor = new UniversalProcessor();
        $profile = Profiles::get('web');
        $rng = new RandomHelper(1);

        $result = $processor->process('', $profile, 50, $rng);
        $this->assertSame('', $result);
    }

    public function testUniversalProcessorNormalizesUnicode(): void
    {
        $processor = new UniversalProcessor();
        $profile = Profiles::get('web');
        $rng = new RandomHelper(42);

        // Text with special Unicode characters
        $text = "Hello\u{2014}world. Test\u{2026} more text here. And\u{00A0}some content.";
        $result = $processor->process($text, $profile, 50, $rng);
        $this->assertIsString($result);
    }

    public function testUniversalProcessorHighIntensity(): void
    {
        $processor = new UniversalProcessor();
        $profile = Profiles::get('chat');
        $rng = new RandomHelper(42);

        $text = 'Short one. Another short one. Yet another. And one more. Plus this. Also that. Something else too.';
        $result = $processor->process($text, $profile, 90, $rng);
        $this->assertNotEmpty($result);
    }

    // ==================== Cross-stage Integration ====================

    public function testMultipleStagesSequential(): void
    {
        $langPack = Registry::get('en');
        $profile = Profiles::get('web');
        $rng = new RandomHelper(42);

        $text = 'Furthermore, the comprehensive implementation provides robust coverage. Moreover, it ensures effective performance. Additionally, the system is scalable.';

        // Run through multiple stages
        $diversifier = new StructureDiversifier();
        $text = $diversifier->process($text, $langPack, $profile, 70, $rng);

        $reducer = new RepetitionReducer();
        $text = $reducer->process($text, $langPack, $profile, 70, $rng);

        $naturalizer = new TextNaturalizer();
        $text = $naturalizer->process($text, 'en', $profile, 70, $rng);

        $this->assertNotEmpty($text);
    }
}
