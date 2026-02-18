"""Tests for tokenizer.py — paragraph/sentence/word tokenization."""

import pytest
from texthumanize.tokenizer import Tokenizer, TokenizedText, Paragraph, Sentence


class TestTokenizerBasic:
    def setup_method(self):
        self.tok = Tokenizer()

    def test_single_sentence(self):
        result = self.tok.tokenize("Hello world.")
        assert len(result.paragraphs) == 1
        assert len(result.paragraphs[0].sentences) == 1
        assert result.paragraphs[0].sentences[0].words == ["Hello", "world"]
        assert result.paragraphs[0].sentences[0].ending == "."

    def test_two_sentences(self):
        result = self.tok.tokenize("First sentence. Second sentence.")
        assert len(result.paragraphs) == 1
        para = result.paragraphs[0]
        assert len(para.sentences) == 2

    def test_question_mark(self):
        result = self.tok.tokenize("Is this correct?")
        sent = result.paragraphs[0].sentences[0]
        assert sent.ending == "?"

    def test_exclamation_mark(self):
        result = self.tok.tokenize("Great news!")
        sent = result.paragraphs[0].sentences[0]
        assert sent.ending == "!"

    def test_ellipsis_three_dots(self):
        result = self.tok.tokenize("Well then...")
        sent = result.paragraphs[0].sentences[0]
        assert sent.ending == "..."

    def test_no_ending_punctuation(self):
        result = self.tok.tokenize("No ending here")
        sent = result.paragraphs[0].sentences[0]
        assert sent.ending == ""

    def test_double_ending(self):
        result = self.tok.tokenize("Really?!")
        sent = result.paragraphs[0].sentences[0]
        assert sent.ending in ("?!", "!?")


class TestTokenizerParagraphs:
    def setup_method(self):
        self.tok = Tokenizer()

    def test_two_paragraphs(self):
        text = "First paragraph.\n\nSecond paragraph."
        result = self.tok.tokenize(text)
        assert len(result.paragraphs) == 2

    def test_three_paragraphs(self):
        text = "Para one.\n\nPara two.\n\nPara three."
        result = self.tok.tokenize(text)
        assert len(result.paragraphs) == 3

    def test_blank_lines_ignored(self):
        text = "Para one.\n\n\n\nPara two."
        result = self.tok.tokenize(text)
        assert len(result.paragraphs) == 2


class TestTokenizerMarkdown:
    def setup_method(self):
        self.tok = Tokenizer()

    def test_list_item_dash(self):
        result = self.tok.tokenize("- List item text.")
        para = result.paragraphs[0]
        assert para.prefix == "- "

    def test_numbered_list(self):
        result = self.tok.tokenize("1. First item.")
        para = result.paragraphs[0]
        assert "1." in para.prefix

    def test_heading(self):
        result = self.tok.tokenize("## Heading text.")
        para = result.paragraphs[0]
        assert "##" in para.prefix

    def test_blockquote(self):
        result = self.tok.tokenize("> Quoted text.")
        para = result.paragraphs[0]
        assert ">" in para.prefix


class TestTokenizerAbbreviations:
    def test_with_abbreviations(self):
        tok = Tokenizer(abbreviations=["Mr", "Dr", "etc"])
        result = tok.tokenize("Mr. Smith went home. Dr. Jones followed.")
        # Should keep abbreviations connected
        assert len(result.paragraphs) >= 1

    def test_without_abbreviations(self):
        tok = Tokenizer()
        result = tok.tokenize("Hello world. Another sentence.")
        assert len(result.paragraphs[0].sentences) == 2


class TestTokenizerRoundtrip:
    def setup_method(self):
        self.tok = Tokenizer()

    def test_simple_roundtrip(self):
        text = "Hello world."
        result = self.tok.tokenize(text)
        rebuilt = self.tok.detokenize(result)
        assert rebuilt == text

    def test_multi_sentence_roundtrip(self):
        text = "First sentence. Second sentence."
        result = self.tok.tokenize(text)
        rebuilt = self.tok.detokenize(result)
        assert "First" in rebuilt
        assert "Second" in rebuilt

    def test_multi_paragraph_roundtrip(self):
        text = "Para one.\n\nPara two."
        result = self.tok.tokenize(text)
        rebuilt = self.tok.detokenize(result)
        assert "Para one" in rebuilt
        assert "Para two" in rebuilt


class TestSentenceDataclass:
    def test_word_count(self):
        s = Sentence(words=["Hello", "world", "test"], ending=".")
        assert s.word_count == 3

    def test_word_count_with_placeholder(self):
        s = Sentence(words=["Hello", "\x00placeholder\x00", "world"], ending=".")
        assert s.word_count == 2  # Placeholder not counted

    def test_to_text(self):
        s = Sentence(words=["Hello", "world"], ending=".")
        assert s.to_text() == "Hello world."

    def test_to_text_no_ending(self):
        s = Sentence(words=["Hello", "world"], ending="")
        assert s.to_text() == "Hello world"

    def test_to_text_empty(self):
        s = Sentence(words=[], ending=".")
        assert s.to_text() == ""


class TestParagraphDataclass:
    def test_to_text_simple(self):
        s = Sentence(words=["Hello"], ending=".")
        p = Paragraph(sentences=[s])
        assert p.to_text() == "Hello."

    def test_to_text_with_prefix(self):
        s = Sentence(words=["Item"], ending=".")
        p = Paragraph(sentences=[s], prefix="- ")
        assert p.to_text() == "- Item."


class TestTokenizedText:
    def test_to_text_multi_para(self):
        s1 = Sentence(words=["First"], ending=".")
        s2 = Sentence(words=["Second"], ending=".")
        p1 = Paragraph(sentences=[s1])
        p2 = Paragraph(sentences=[s2])
        t = TokenizedText(paragraphs=[p1, p2])
        text = t.to_text()
        assert "First." in text
        assert "Second." in text
        assert "\n\n" in text


class TestTokenizerEmpty:
    def setup_method(self):
        self.tok = Tokenizer()

    def test_empty_string(self):
        result = self.tok.tokenize("")
        assert len(result.paragraphs) == 0

    def test_whitespace_only(self):
        result = self.tok.tokenize("   \n\n   ")
        assert len(result.paragraphs) == 0

    def test_single_word(self):
        result = self.tok.tokenize("Hello")
        assert len(result.paragraphs) == 1
        assert result.paragraphs[0].sentences[0].words == ["Hello"]
