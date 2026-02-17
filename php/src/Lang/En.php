<?php

declare(strict_types=1);

namespace TextHumanize\Lang;

/**
 * English language pack.
 */
class En
{
    public static function pack(): array
    {
        return [
            'code' => 'en',
            'name' => 'English',
            'trigrams' => ['the', 'and', 'ing', 'ion', 'tio', 'ent', 'ati', 'for',
                'her', 'ter', 'hat', 'tha', 'ere', 'ate', 'his', 'con', 'res',
                'ver', 'all', 'ons', 'nce', 'men', 'ith', 'ted', 'ers', 'pro',
                'thi', 'wit', 'are', 'ess', 'not', 'ive', 'was', 'ect', 'rea',
                'com', 'eve', 'per', 'int', 'est', 'sta', 'cti', 'ica', 'ist',
                'ear', 'ain', 'one'],
            'stop_words' => self::stopWords(),
            'bureaucratic' => self::bureaucratic(),
            'bureaucratic_phrases' => self::bureaucraticPhrases(),
            'ai_connectors' => self::aiConnectors(),
            'synonyms' => self::synonyms(),
            'sentence_starters' => self::sentenceStarters(),
            'colloquial_markers' => [
                'by the way', 'actually', 'honestly', 'you know',
                'basically', 'in fact', 'look', 'essentially',
                'frankly', 'interestingly',
            ],
            'abbreviations' => [
                'Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Sr', 'Jr',
                'vs', 'etc', 'e.g', 'i.e', 'approx', 'dept',
                'est', 'vol', 'inc', 'corp', 'ltd', 'assn',
                'bros', 'gen', 'gov', 'sgt', 'capt', 'cmdr',
                'lt', 'col', 'maj', 'pvt', 'Rev', 'Hon',
                'Jan', 'Feb', 'Mar', 'Apr', 'Aug', 'Sept',
                'Oct', 'Nov', 'Dec',
            ],
            'conjunctions' => ['and', 'but', 'so', 'while', 'or', 'yet', 'because'],
            'split_conjunctions' => [
                'which', 'that', 'because', 'although', 'while',
                'whereas', 'since', 'unless', 'though', 'where', 'when',
            ],
            'profile_targets' => [
                'chat' => ['min' => 8, 'max' => 18],
                'web' => ['min' => 10, 'max' => 22],
                'seo' => ['min' => 12, 'max' => 25],
                'docs' => ['min' => 12, 'max' => 28],
                'formal' => ['min' => 15, 'max' => 30],
            ],
        ];
    }

    private static function stopWords(): array
    {
        return ['a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'shall', 'can',
            'need', 'dare', 'ought', 'used', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'between',
            'out', 'off', 'over', 'under', 'again', 'further', 'then',
            'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all',
            'each', 'every', 'both', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
            'so', 'than', 'too', 'very', 'just', 'because', 'but', 'and',
            'or', 'if', 'while', 'about', 'up', 'it', 'its', 'his', 'her',
            'my', 'your', 'our', 'their', 'this', 'that', 'these', 'those',
            'i', 'me', 'we', 'us', 'you', 'he', 'she', 'they', 'them',
            'what', 'which', 'who', 'whom'];
    }

    private static function bureaucratic(): array
    {
        return [
            'utilize' => ['use'],
            'utilizes' => ['uses'],
            'utilized' => ['used'],
            'utilizing' => ['using'],
            'utilization' => ['use'],
            'implement' => ['do', 'carry out', 'set up'],
            'implements' => ['does', 'carries out'],
            'implementation' => ['setup', 'doing', 'work'],
            'facilitate' => ['help', 'enable', 'make easier'],
            'facilitates' => ['helps', 'enables'],
            'facilitation' => ['help', 'support'],
            'demonstrate' => ['show'],
            'demonstrates' => ['shows'],
            'constitute' => ['make up', 'form', 'are'],
            'constitutes' => ['is', 'makes up', 'forms'],
            'approximately' => ['about', 'around', 'roughly'],
            'subsequently' => ['then', 'later', 'after that'],
            'additionally' => ['also', 'plus', 'on top of that'],
            'consequently' => ['so', 'as a result'],
            'furthermore' => ['also', 'plus', 'and'],
            'nevertheless' => ['still', 'even so', 'but'],
            'notwithstanding' => ['despite', 'in spite of'],
            'aforementioned' => ['this', 'the above', 'mentioned'],
            'methodology' => ['method', 'approach', 'way'],
            'comprehensive' => ['full', 'complete', 'thorough'],
            'significant' => ['big', 'major', 'notable'],
            'considerable' => ['big', 'large', 'much'],
            'sufficient' => ['enough'],
            'numerous' => ['many', 'a lot of'],
            'commence' => ['start', 'begin'],
            'commences' => ['starts', 'begins'],
            'terminate' => ['end', 'stop', 'finish'],
            'terminates' => ['ends', 'stops'],
            'endeavor' => ['try', 'attempt', 'effort'],
            'endeavors' => ['tries', 'attempts'],
            'necessitate' => ['need', 'require'],
            'necessitates' => ['needs', 'requires'],
            'accomplish' => ['do', 'achieve', 'finish'],
            'accomplishes' => ['does', 'achieves'],
            'ascertain' => ['find out', 'learn', 'determine'],
            'procure' => ['get', 'obtain', 'buy'],
            'disseminate' => ['spread', 'share', 'distribute'],
            'endeavour' => ['try', 'attempt'],
            'leverage' => ['use', 'take advantage of'],
            'leverages' => ['uses', 'takes advantage of'],
            'optimal' => ['best', 'ideal'],
            'optimizes' => ['improves'],
            'paramount' => ['key', 'crucial', 'top'],
            'pertaining' => ['about', 'related to'],
            'regarding' => ['about', 'on'],
            'possess' => ['have', 'own'],
            'possesses' => ['has', 'owns'],
            'prior' => ['before', 'earlier'],
            'subsequent' => ['next', 'following', 'later'],
            'sufficient' => ['enough'],
            'thereby' => ['so', 'by doing this'],
        ];
    }

    private static function bureaucraticPhrases(): array
    {
        return [
            'it is important to note' => ['notably', 'worth noting'],
            'it should be noted that' => ['notably', 'note that'],
            'it is worth mentioning' => ['notably', 'also'],
            'in order to' => ['to'],
            'due to the fact that' => ['because', 'since'],
            'in the event that' => ['if'],
            'for the purpose of' => ['to', 'for'],
            'with regard to' => ['about', 'on'],
            'with respect to' => ['about', 'regarding'],
            'in accordance with' => ['per', 'according to', 'following'],
            'by means of' => ['through', 'via', 'with'],
            'in conjunction with' => ['with', 'along with'],
            'at the present time' => ['now', 'currently'],
            'at this point in time' => ['now', 'right now'],
            'in the near future' => ['soon'],
            'a large number of' => ['many', 'lots of'],
            'the vast majority of' => ['most'],
            'on the other hand' => ['but', 'however', 'then again'],
            'as a matter of fact' => ['actually', 'in fact'],
            'take into consideration' => ['consider'],
            'take into account' => ['consider', 'account for'],
            'make a decision' => ['decide'],
            'come to a conclusion' => ['conclude'],
            'is able to' => ['can'],
            'has the ability to' => ['can'],
            'in light of' => ['given', 'considering'],
            'plays a crucial role' => ['matters', 'is key'],
            'is of great importance' => ['matters', 'is important'],
        ];
    }

    private static function aiConnectors(): array
    {
        return [
            'However' => ['But', 'Still', 'Yet'],
            'Furthermore' => ['Also', 'Plus', 'And'],
            'Moreover' => ['Also', 'Plus', 'On top of that'],
            'Additionally' => ['Also', 'Plus'],
            'Consequently' => ['So', 'As a result', 'Because of this'],
            'Nevertheless' => ['Still', 'Even so', 'But'],
            'Nonetheless' => ['Still', 'Even so'],
            'Therefore' => ['So', 'That\'s why', 'Because of this'],
            'Thus' => ['So', 'This way'],
            'Hence' => ['So', 'That\'s why'],
            'In conclusion' => ['All in all', 'To sum up', 'Overall'],
            'To summarize' => ['In short', 'To sum up'],
            'In essence' => ['Basically', 'At its core'],
            'Notably' => ['Especially', 'In particular'],
            'Specifically' => ['In particular', 'Namely'],
            'Ultimately' => ['In the end', 'Finally'],
            'Significantly' => ['Greatly', 'Largely'],
            'In particular' => ['Especially', 'Specifically'],
            'As a result' => ['So', 'Because of this'],
            'On the contrary' => ['But', 'Actually'],
            'In other words' => ['Put simply', 'That is'],
            'For instance' => ['For example', 'Like'],
            'For example' => ['Like', 'Say'],
            'In addition' => ['Also', 'Plus'],
            'Undoubtedly' => ['Clearly', 'No doubt'],
        ];
    }

    private static function synonyms(): array
    {
        return [
            'important' => ['significant', 'key', 'essential', 'crucial', 'vital'],
            'big' => ['large', 'huge', 'major', 'substantial', 'considerable'],
            'small' => ['tiny', 'minor', 'modest', 'slight'],
            'good' => ['great', 'fine', 'solid', 'strong', 'effective'],
            'bad' => ['poor', 'weak', 'flawed', 'problematic'],
            'fast' => ['quick', 'rapid', 'swift', 'speedy'],
            'slow' => ['gradual', 'unhurried', 'leisurely'],
            'difficult' => ['hard', 'tough', 'challenging', 'complex'],
            'easy' => ['simple', 'straightforward', 'effortless'],
            'new' => ['fresh', 'novel', 'modern', 'recent'],
            'old' => ['dated', 'aging', 'previous', 'former'],
            'effective' => ['efficient', 'productive', 'successful'],
            'different' => ['various', 'diverse', 'distinct'],
            'main' => ['key', 'primary', 'chief', 'central'],
            'process' => ['procedure', 'method', 'approach', 'workflow'],
            'result' => ['outcome', 'effect', 'consequence'],
            'development' => ['growth', 'progress', 'advancement'],
            'problem' => ['issue', 'challenge', 'difficulty'],
            'system' => ['framework', 'platform', 'setup'],
            'approach' => ['method', 'strategy', 'way', 'technique'],
            'increase' => ['growth', 'rise', 'boost', 'gain'],
            'create' => ['build', 'make', 'develop', 'produce'],
            'provide' => ['give', 'offer', 'supply', 'deliver'],
            'ensure' => ['guarantee', 'make sure', 'secure'],
            'significant' => ['notable', 'major', 'key', 'meaningful'],
            'various' => ['different', 'diverse', 'multiple'],
            'specific' => ['particular', 'certain', 'given'],
            'relevant' => ['related', 'applicable', 'pertinent'],
            'complex' => ['complicated', 'intricate', 'involved'],
            'potential' => ['possible', 'likely', 'prospective'],
            'consider' => ['think about', 'examine', 'look at'],
            'improve' => ['enhance', 'boost', 'upgrade', 'refine'],
            'achieve' => ['reach', 'attain', 'get', 'accomplish'],
            'determine' => ['find', 'figure out', 'establish'],
            'require' => ['need', 'call for', 'demand'],
        ];
    }

    private static function sentenceStarters(): array
    {
        return [
            'This' => ['It', 'That', 'The'],
            'The' => ['This', 'A', 'One'],
            'It' => ['This', 'That'],
            'They' => ['People', 'Users', 'These'],
            'We' => ['You', 'One', 'People'],
            'There' => ['Here', 'Now'],
            'These' => ['Such', 'Those', 'The'],
            'That' => ['This', 'It', 'The'],
            'Such' => ['These', 'Those', 'This kind of'],
            'Many' => ['Several', 'A lot of', 'Numerous'],
        ];
    }
}
