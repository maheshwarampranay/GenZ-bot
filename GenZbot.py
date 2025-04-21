import logging
import random
import re

log = logging.getLogger(__name__)


class Trigger:
    def __init__(self, term, priority, patterns):
        self.term = term
        self.priority = priority
        self.patterns = patterns


class Pattern:
    def __init__(self, parts, store_memory, responses):
        self.parts = parts
        self.store_memory = store_memory
        self.responses = responses
        self.index = 0


class GenZAdvisor:
    def __init__(self):
        self.greetings = []
        self.goodbyes = []
        self.exit_words = []
        self.pre_subs = {}
        self.post_subs = {}
        self.synonyms = {}
        self.triggers = {}
        self.memory_bank = []

    def load_data(self, filepath):
        current_trigger = None
        current_pattern = None
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                tag, content = [p.strip() for p in line.split(":", 1)]

                if tag == "initial":
                    self.greetings.append(content)
                elif tag == "final":
                    self.goodbyes.append(content)
                elif tag == "quit":
                    self.exit_words.append(content)
                elif tag == "pre":
                    parts = content.split(" ")
                    self.pre_subs[parts[0]] = parts[1:]
                elif tag == "post":
                    parts = content.split(" ")
                    self.post_subs[parts[0]] = parts[1:]
                elif tag == "synon":
                    parts = content.split(" ")
                    self.synonyms[parts[0]] = parts
                elif tag == "key":
                    parts = content.split(" ")
                    term = parts[0]
                    priority = int(parts[1]) if len(parts) > 1 else 1
                    current_trigger = Trigger(term, priority, [])
                    self.triggers[term] = current_trigger
                elif tag == "decomp":
                    parts = content.split(" ")
                    store = False
                    if parts[0] == "$":
                        store = True
                        parts = parts[1:]
                    current_pattern = Pattern(parts, store, [])
                    current_trigger.patterns.append(current_pattern)
                elif tag == "reasmb":
                    parts = content.split(" ")
                    current_pattern.responses.append(parts)

    def _recursive_match(self, parts, tokens, captures):
        if not parts and not tokens:
            return True
        if not parts or (not tokens and parts != ["*"]):
            return False
        if parts[0] == "*":
            for i in range(len(tokens), -1, -1):
                captures.append(tokens[:i])
                if self._recursive_match(parts[1:], tokens[i:], captures):
                    return True
                captures.pop()
            return False
        elif parts[0].startswith("@"):  # synonym
            root = parts[0][1:]
            if root not in self.synonyms:
                return False
            if tokens[0].lower() not in self.synonyms[root]:
                return False
            captures.append([tokens[0]])
            return self._recursive_match(parts[1:], tokens[1:], captures)
        elif parts[0].lower() != tokens[0].lower():
            return False
        else:
            return self._recursive_match(parts[1:], tokens[1:], captures)

    def _get_response(self, pattern, captures):
        response = pattern.responses[pattern.index % len(pattern.responses)]
        pattern.index += 1
        output = []
        for word in response:
            if word.startswith("(") and word.endswith(")"):
                idx = int(word[1:-1])
                if 1 <= idx <= len(captures):
                    segment = captures[idx - 1]
                    output.extend(segment)
            else:
                output.append(word)
        return output

    def _apply_subs(self, words, subs):
        output = []
        for w in words:
            lw = w.lower()
            if lw in subs:
                output.extend(subs[lw])
            else:
                output.append(w)
        return output

    def _try_match(self, tokens, trigger):
        for pattern in trigger.patterns:
            captures = []
            if self._recursive_match(pattern.parts, tokens, captures):
                captures = [self._apply_subs(c, self.post_subs) for c in captures]
                response = self._get_response(pattern, captures)
                if pattern.store_memory:
                    self.memory_bank.append(response)
                    continue
                return response
        return None

    def generate_reply(self, message):
        if message.lower() in self.exit_words:
            return None

        message = re.sub(r"\s*[.,;]+\s*", " ", message)
        tokens = message.split()
        tokens = self._apply_subs(tokens, self.pre_subs)

        triggers_found = [
            self.triggers[w.lower()] for w in tokens if w.lower() in self.triggers
        ]
        triggers_found = sorted(triggers_found, key=lambda t: -t.priority)

        for trigger in triggers_found:
            reply = self._try_match(tokens, trigger)
            if reply:
                return " ".join(reply)

        if self.memory_bank:
            return " ".join(
                self.memory_bank.pop(random.randrange(len(self.memory_bank)))
            )

        fallback = self.triggers["xnone"].patterns[0]
        return " ".join(self._get_response(fallback, []))

    def start_chat(self):
        print(random.choice(self.greetings))
        while True:
            user_input = input("You: ")
            bot_reply = self.generate_reply(user_input)
            if bot_reply is None:
                break
            print("Bot:", bot_reply)
        print(random.choice(self.goodbyes))


def main():
    bot = GenZAdvisor()
    bot.load_data("wdyc.txt")
    bot.start_chat()


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    main()
