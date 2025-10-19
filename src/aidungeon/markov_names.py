import random
from collections import defaultdict

MINECRAFT_MONSTERS = [
    "Zombie", "Skeleton", "Creeper", "Spider", "Enderman", "Witch", "Slime",
    "Ghast", "Blaze", "Wither", "Piglin", "Vindicator", "Evoker", "Illusioner",
    "Pillager", "Husk", "Drowned", "Phantom", "Stray", "Guardian", "Elder Guardian",
    "Shulker", "Silverfish", "Endermite", "Magma Cube", "Ravager", "Warden",
    "Vex", "Zoglin", "Piglin Brute", "Hoglin", "Zombified Piglin", "Strider",
    "Sniffer", "Allay", "Breeze", "Tadpole", "Camel", "Armorsmith", "Necromancer",
    "Warlock", "Specter", "Shade", "Lurker", "Wraith", "Stalker", "Ghoul",
    "Banshee", "Fiend", "Revenant"
]


class MarkovNameGenerator:
    """Простой 3-граммный генератор имён на основе цепей Маркова."""

    def __init__(self, names, n=3):
        self.n = n
        self.model = defaultdict(list)
        self._train(names)

    def _train(self, names):
        for name in names:
            padded = "~" * (self.n - 1) + name.lower() + "$"
            for i in range(len(padded) - self.n + 1):
                prefix = padded[i:i+self.n-1]
                next_char = padded[i+self.n-1]
                self.model[prefix].append(next_char)

    def generate(self, min_len=4, max_len=10):
        prefix = "~" * (self.n - 1)
        result = ""
        while True:
            next_char = random.choice(self.model[prefix])
            if next_char == "$" or len(result) >= max_len:
                break
            result += next_char
            prefix = (prefix + next_char)[-self.n+1:]
        if len(result) < min_len:
            return self.generate(min_len, max_len)
        return result.capitalize()
