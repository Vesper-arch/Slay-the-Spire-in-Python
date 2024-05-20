from enum import StrEnum, auto

class PlayerClass(StrEnum):
    IRONCLAD = 'Ironclad'
    SILENT = 'Silent'
    DEFECT = 'Defect'
    WATCHER = 'Watcher'
    ANY = 'Any'

class CombatTier(StrEnum):
    NORMAL = 'Normal'
    ELITE = 'Elite'
    BOSS = 'Boss'

class EncounterType(StrEnum):
    START = auto()
    NORMAL = auto()
    ELITE = auto()
    REST_SITE = auto()
    BOSS = auto()
    SHOP = auto()
    UNKNOWN = auto()

class Rarity(StrEnum):
    BASIC ='Basic'
    BOSS ='Boss'
    COMMON ='Common'
    CURSE ='Curse'
    EVENT ='Event'
    RARE ='Rare'
    SHOP ='Shop'
    SPECIAL ='Special'
    STARTER ='Starter'
    UNCOMMON ='Uncommon'

class CardType(StrEnum):
    ATTACK = 'Attack'
    SKILL = 'Skill'
    POWER = 'Power'
    STATUS = 'Status'
    CURSE = 'Curse'

class TargetType(StrEnum):
    ANY = 'Any'
    AREA = 'Area'
    ENEMY = 'Enemy'
    NOTHING = 'Nothing'
    RANDOM = 'Random'
    SINGLE = 'Single'
    PLAYER = 'Yourself'

class CardCategory(StrEnum):
    CARD = 'Card'
    POTION = 'Potion'
    RELIC = 'Relic'

class State(StrEnum):
    ALIVE = 'Alive'
    DEAD = 'Dead'
    ESCAPED = 'Escaped'
    INTANGIBLE = 'Intangible'

