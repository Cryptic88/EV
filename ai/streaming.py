"""Sentence buffering for incremental LLM text."""
import re


class SentenceBuffer:
    def __init__(self):
        self.text = ""

    def feed(self, text):
        self.text += text
        sentences = []
        while True:
            end = None
            for match in re.finditer(r'[.!?][\)\]"\u201d\u2019]*(?=\s)', self.text):
                candidate = self.text[:match.end()].strip()
                if re.search(r'(?:\b[A-Za-z]\.|\b(?:Mr|Mrs|Ms|Dr|Prof|St|vs|etc)\.)$', candidate, re.I):
                    continue
                end = match.end()
                break
            if end is None:
                break
            sentences.append(self.text[:end].strip())
            self.text = self.text[end:].lstrip()
        # Bound latency for long unpunctuated output without cutting words.
        if len(self.text) > 240:
            end = self.text.rfind(" ", 0, 240)
            if end > 0:
                sentences.append(self.text[:end].strip())
                self.text = self.text[end:].lstrip()
        return sentences

    def finish(self):
        tail, self.text = self.text.strip(), ""
        return [tail] if tail else []
