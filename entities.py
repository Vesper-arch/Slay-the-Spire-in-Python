import math
import sys
import random
from time import sleep
from ast import literal_eval
from copy import deepcopy
from ansi_tags import ansiprint
from items import Card, relics, cards, potions, activate_sacred_bark
from helper import active_enemies, combat_turn, view, gen, ei
from definitions import CombatTier, State

class Player:
    """
    Attributes:::
    health: The player's current health
    block: The amount of damage the player can take before losing health. Removed at the start of their turn
    name: The player's name
    player_class: Ironclad, Silent, Defect, and Watcher
    max_health: The max amount health the player can have
    energy: Resource used to play cards. Replenished at the start of their turn
    max_energy/energy_gain: The base amount of energy the player gains at the start of their turn
    deck: All the cards the player has
    potions: Consumables that have varying effects.
    max_potions: The max amount of potions the player can have
    """

    def __init__(self, health: int, block: int, max_energy: int, deck: list, powers: dict=None):
        if not powers:
            powers = {}
        self.health: int = health
        self.block: int = block
        self.name: str = "Ironclad"
        self.player_class: str = "Ironclad"
        self.in_combat = False
        self.floors = 1
        self.fresh_effects: list[str] = [] # Shows what effects were applied after the player's turn
        self.max_health: int = health
        self.energy: int = 0
        self.max_energy: int = max_energy
        self.energy_gain: int = max_energy
        self.deck: list[dict] = deck
        self.potions: list[dict] = []
        self.relics: list[dict] = []
        self.max_potions: int = 3
        self.hand: list[dict] = []
        self.draw_pile: list[dict] = []
        self.discard_pile: list[dict] = []
        self.card_reward_choices: int = 3
        self.draw_strength: int = 5
        self.exhaust_pile: list[dict] = []
        self.orbs = []
        self.orb_slots: int = 3
        self.gold: int = 100
        self.debuffs: dict[str: int] = ei.init_effects("Player Debuffs") | powers
        self.buffs: dict[str: int] = ei.init_effects("Player Buffs") | powers
        # Alternate debuff/buff effects
        self.combusts_played = 0
        self.the_bomb_countdown = 3
        self.deva_energy = 1
        # Relic buffs
        self.pen_nib_attacks: int = 0
        self.ancient_tea_set: bool = False
        self.attacks_played_this_turn: bool = False  # Used for the Art of War relic
        self.taken_damage: bool = False  # Used for the Centennial Puzzle relic
        self.gold_on_card_add: bool = False  # Used for the Ceramic Fish relic
        self.happy_flower: int = 0
        self.block_curses: int = 0  # Used for the Omamori relic
        self.nunckaku_attacks: int = 0
        self.starting_strength: int = 0  # Used for the Red Skull and Vajra relic
        self.golden_bark: bool = False  # Used for the Golden Bark relic
        # Used for the Molten, Toxic, and Frozen Egg relics
        self.upgrade_attacks = False
        self.upgrade_skills = False
        self.upgrade_powers = False
        self.red_skull_active = False
        self.inked_cards = 0  # Used for the Ink Bottle relic
        self.kunai_attacks = 0  # Used for the Kunai relic
        self.letter_opener_skills = 0  # Used for the Letter Opener relic
        self.ornament_fan_attacks = 0  # Used for the Ornamental Fan relic
        self.meat_on_the_bone = False
        self.darkstone_health = False
        self.shuriken_attacks = 0
        self.draw_shuffles = 0 # Used for the Sundial relic
        self.incense_turns = 0 # Used for the Incense Burner relic
        self.girya_charges = 3 # Stores how many times the player can gain Energy from Girya
        self.plays_this_turn = 0 # Counts how many cards the played plays each turn
        self.stone_calender = 0
        self.choker_cards_played = 0 # Used for the Velvet Choker relic

    def __str__(self):
        return f'(<italic>Player</italic>)Ironclad(<red>{self.health} / {self.max_health}</red> | <yellow>{self.gold} Gold</yellow> | Deck: {len(self.deck)})'

    def __repr__(self):
        if self.in_combat is True:
            status = f"\n{self.name} (<red>{self.health} </red>/ <red>{self.max_health}</red> | <light-blue>{self.block} Block</light-blue> | <light-red>{self.energy} / {self.max_energy} Energy</light-red>)"
            for buff in self.buffs:
                if int(self.buffs[buff]) >= 1:
                    status += f" | <buff>{buff}</buff>{f' {self.buffs[buff]}' if isinstance(self.buffs[buff], int) else ''}"
            for debuff in self.debuffs:
                if int(self.debuffs[debuff]) >= 1:
                    status += f" | <debuff>{debuff}</debuff>{f' {self.debuffs[debuff]}' if isinstance(self.debuffs[debuff], int) else ''}"
        else:
            status = f"\n{self.name} (<red>{self.health} </red>/ <red>{self.max_health}</red> | <yellow>{self.gold} Gold</yellow>)"
        return status + '' if status == f"\n{self.name} (<red>{self.health} </red>/ <red>{self.max_health}</red> | <light-blue>{self.block} Block</light-blue> | <light-red>{self.energy} / {self.max_energy}</light-red>)" else status + '\n'

    def show_effects(self):
        for buff in self.buffs:
            if int(self.buffs[buff]) > 0:
                ansiprint(f'<buff>{buff}</buff>: {ei.ALL_EFFECTS[buff].replace("X", str(self.buffs[buff]))}')
        for debuff in self.debuffs:
            ansiprint(f'<debuff>{debuff}</debuff>: {ei.ALL_EFFECTS[debuff].replace("X", str(self.debuffs[debuff]))}')

    def use_card(self, card: dict, target: 'Enemy', exhaust, pile) -> None:
        """
        Uses a card
        Wow!
        """
        if card['Type'] in ('Status', 'Curse') and card['Name'] not in ('Slimed', 'Pride'):
            ansiprint("<red>This card is not playable. This message shouldn't appear outside of tests.</red>")
            return
        if card.get('Target') == 'Single':
            card['Function'](target, card, self)
        elif card.get('Target') in ('Area', 'Random'):
            card['Function'](active_enemies, card, self)
        elif card.get('Target') == 'Yourself':
            card['Function'](card, self)
        elif not card.get('Target') and (card['Name'] not in ('Slimed', 'Pride') and card['Type'] not in ("Status", "Curse")):
            raise KeyError(f"{card['Name']} does not have a 'Target' key.")
        if card.get('Type') == 'Attack' and relics['Pen Nib'] in self.relics:
            self.pen_nib_attacks += 1
        if card.get('Type') == 'Attack' and relics['Nunchaku'] in self.relics:
            self.nunckaku_attacks += 1
            if self.nunckaku_attacks == 10:
                self.energy += 1
                ansiprint('You gained 1 Energy from <bold>Nunckaku</bold>.')
                self.nunckaku_attacks = 0
        self.on_card_play(card)
        if self.buffs['Corruption']:
            exhaust = True

        if self.buffs['Double Tap'] > 0 and card.get('Type') == 'Attack':
            self.buffs['Double Tap'] -= 1
            sleep(1.5)
            view.clear()
            self.use_card(card=card, target=target, exhaust=True, pile=None)
        if card.get('Type') == 'Status' and relics['Medical Kit'] in player.relics:
            exhaust = True
        elif card.get('Type') == 'Curse' and relics['Blue Candle'] in player.relics:
            self.take_sourceless_dmg(1)
            exhaust = True
        if pile is not None:
            if exhaust is True or card.get('Exhaust') is True:
                ansiprint(f"{card['Name']} was <bold>Exhausted</bold>.")
                self.move_card(card=card, destination=self.exhaust_pile, start=pile, cost_energy=True)
            else:
                self.move_card(card=card, destination=self.discard_pile, start=pile, cost_energy=True)
        if target.buffs["Sharp Hide"] > 0:
            target.attack(target.buffs["Sharp Hide"], 1)
        sleep(0.5)
        view.clear()

    def on_relic_pickup(self, relic):
        self.gold_on_card_add = relic['Name'] == "Ceramic Fish"
        self.max_potions += 2 if relic['Name'] == 'Potion Belt' else 0
        self.starting_strength += int(relic['Name'] == 'Vajra')
        if relic['Name'] in ('Bottled Flame', 'Bottled Lightning', 'Bottled Tornado'):
            relic_to_type = {'Bottled Flame': 'Attack', 'Bottled Lightning': 'Skill', 'Bottled Tornado': 'Power'}
            self.bottle_card(relic_to_type[relic['Name']])
        elif 'Egg' in relic.get('Name'):
            relic_variables = {'Molten Egg': self.upgrade_attacks,
                              'Frozen Egg': self.upgrade_skills,
                              'Toxic Egg': self.upgrade_powers}
            relic_variables[relic['Name']] = True

        elif relic['Name'] in ('Whetstone', 'War Paint'):
            valid_card_types = {'Whetstone': 'Attack', 'War Paint': 'Skill'}
            valid_cards = [card for card in self.deck if card.get('Type') == valid_card_types[relic['Name']]]
            ansiprint(f"<bold>{relic['Name']}</bold>:")
            for _ in range(min(len(valid_cards), 2)):
                chosen_card = random.randint(0, len(self.deck) - 1)
                self.deck[chosen_card] = self.card_actions(self.deck[chosen_card], 'Upgrade', valid_cards)
        elif relic.get('Name') in ('Strawberry', 'Pear', 'Mango'):
            health_values = {'Strawberry': 7, 'Pear': 10, 'Mango': 14}
            self.health_actions(health_values[relic['Name']], 'Max Health')
        elif relic['Name'] in ('Mark of Pain', 'Busted Crown', 'Coffee Dripper', 'Cursed Key', 'Ectoplasm', 'Fusion Hammer', "Philosopher's Stone", 'Runic Dome', 'Sozu', 'Velvet Choker'):
            self.max_energy += 1
        elif relic['Name'] == 'Astrolabe':
            while True:
                try:
                    view.view_piles(self.deck, self, False, 'Removable')
                    target_cards = literal_eval(f"({input('Choose 3 cards to <keyword>Transform</keyword> and <keyword>Upgrade</keyword> separated by colons > ')})")
                    if len(target_cards) != 3:
                        raise TypeError("")
                    for card in target_cards:
                        self.deck[card] = self.card_actions(self.deck[card], 'Transform', cards)
                        self.deck[card] = self.card_actions(self.deck[card], "Upgrade", cards)
                    break
                except (TypeError, ValueError):
                    ansiprint("<red>Incorrect syntax, wrong length, or invalid card number</red> Correct: '_, _, _'")
                    sleep(1.5)
                    view.clear()
                    continue
        elif relic['Name'] == 'Calling Bell':
            gen.card_rewards(CombatTier.NORMAL, False, self, None, [cards['Call of the Bell']])
            for _ in range(3):
                gen.claim_relics(True, self, 3)
        elif relic['Name'] == 'Empty Cage':
            view.view_piles(self.deck, self, False, 'Removable')
            backup_counter = 2 # Used to account for wrong or invalid inputs
            for _ in range(backup_counter):
                option = view.list_input("Choose a card to remove > ", self.deck, view.view_piles, lambda card: card.get("Removable") is False, "That card is not removable.")
                self.deck[option] = self.card_actions(self.deck[option], 'Remove', cards)
        elif relic['Name'] == "Pandora's Box":
            for card in self.deck:
                if card['Name'] in ('Strike', 'Defend'):
                    card = self.card_actions(card, 'Upgrade', cards)
        elif relic['Name'] == 'Sacred Bark':
            activate_sacred_bark()
        elif relic['Name'] == "Tiny House":
            gen.claim_potions(False, 1, self, potions)
            self.gain_gold(50)
            self.health_actions(5, "Max Health")
            gen.card_rewards('Normal', True, self, cards)
            upgrade_card = random.choice((index for index in range(len(self.deck)) if not self.deck[index].get("Upgraded") and (self.deck[index]['Name'] == "Burn" or self.deck[index]['Type'] not in ("Status", "Curse"))))
            self.deck[upgrade_card] = self.card_actions(self.deck[upgrade_card], "Upgrade")
        elif relic['Name'] == 'Velvet Choker':
            self.max_energy += 1
        elif relic['Name'] == 'Black Blood':
            burning_blood_index = self.relics.index(relics['Burning Blood']) # Will have to change once other characters are added
            self.deck[burning_blood_index] = relic
        elif relic['Name'] == 'Mark of Pain':
            self.max_energy += 1
        _ = self.gain_gold(300) if relic['Name'] == 'Old Coin' else None
        self.card_reward_choices += 1 if relic['Name'] == 'Question Card' else 0

    def on_card_play(self, card):
        if relics['Kunai'] in self.relics and card.get('Type') == 'Attack':
            self.kunai_attacks += 1
            if self.kunai_attacks == 3:
                ansiprint("<bold>Kunai</bold> activated: ", end='')
                ei.apply_effect(self, self, 'Dexterity', 1)
                self.kunai_attacks = 0
        if relics['Ornamental Fan'] in self.relics and card.get('Type') == 'Attack':
            self.ornament_fan_attacks += 1
            if self.ornament_fan_attacks == 3:
                ansiprint("<bold>Ornamental Fan</bold> activated: ", end='')
                self.blocking(4, False)
        if relics['Letter Opener'] in self.relics and card.get('Type') == 'Skill':
            self.letter_opener_skills += 1
            if self.letter_opener_skills == 3:
                ansiprint("<bold>Letter Opener</bold> activated")
                for enemy in active_enemies:
                    self.attack(enemy, dmg=5)
                self.letter_opener_skills = 0
        if relics['Mummified Hand'] in self.relics and card.get('Type') == 'Power':
            ansiprint('<bold>Mummified Hand</bold> activated: ', end='')
            target_card = random.choice(self.hand)
            target_card = modify_energy_cost(0, 'Set', target_card)
        if relics['Shuriken'] in self.relics and card.get('Type') == 'Attack':
            self.shuriken_attacks += 1
            if self.shuriken_attacks == 3:
                ansiprint('<bold>Shuriken</bold> activated: ', end='')
                ei.apply_effect(self, self, 'Strength', 1)
        if relics['Ink Bottle'] in self.relics:
            self.inked_cards += 1
            if self.inked_cards == 10:
                ansiprint("<bold>Ink Bottle</bold> activated: ", end='')
                self.draw_cards(True, 1)
                self.inked_cards = 0
        if relics['Duality'] in self.relics and card.get('Type') == 'Attack':
            ansiprint('<bold>Duality</bold> activated: ', end='')
            ei.apply_effect(self, self, 'Dexterity', 1)
        if relics['Bird-Faced Urn'] in self.relics and card.get('Type') == 'Power':
            ansiprint('<bold>Bird-Faced Urn</bold> activated: ', end='')
            self.health_actions(2, 'Heal')
        if relics['Velvet Choker'] in self.relics:
            self.choker_cards_played += 1

    def draw_cards(self, middle_of_turn: bool=True, cards: int = 0):
        '''Draws [draw_cards] cards.'''
        if cards == 0:
            cards = self.draw_strength
        while True:
            if self.debuffs["No Draw"] is True:
                print("You can't draw any more cards")
                break
            if middle_of_turn is False:
                cards += self.buffs["Draw Up"]
                if relics['Bag of Preparation'] in self.relics:
                    cards += 2
                if relics['Ring of the Snake'] in self.relics:
                    cards += 2
            if len(player.draw_pile) < cards:
                player.draw_pile.extend(random.sample(player.discard_pile, len(player.discard_pile)))
                player.discard_pile = []
                if relics['Sundial'] in self.relics:
                    self.draw_shuffles += 1
                    if self.draw_shuffles == 3:
                        ansiprint('<bold>Sundial</bold> gave you 2 <italic><red>Energy</red></italic>')
                        self.energy += 2
                        self.draw_shuffles = 0
                ansiprint("<bold>Discard pile shuffled into draw pile.</bold>")
            self.hand.extend(player.draw_pile[-cards:])
            # Removes those cards
            player.draw_pile = player.draw_pile[:-cards]
            print(f"Drew {cards} cards.")
            for card in player.hand[-cards:]:
                if card['Type'] in ('Status', 'Curse') and self.buffs['Fire Breathing'] > 0:
                    for enemy in active_enemies:
                        self.attack(self.buffs['Fire Breathing'], enemy)
                if card['Type'] == 'Status' and self.buffs['Evolve'] > 0:
                    view.clear()
                    self.draw_cards(True, self.buffs['Evolve'])
            break

    def blocking(self, block: int=0, card: Card=None):
        '''Gains [block] Block. Cards are affected by Dexterity and Frail.'''
        block_affected_by = ''
        block = block if not card else card.block
        if card:
            block += self.buffs["Dexterity"]
            if self.buffs["Dexterity"] > 0:
                block_affected_by += f'{self.buffs["Dexterity"]} <{"light-cyan" if self.buffs["Dexterity"] > 0 else "red"}>Dexterity</{"light-cyan" if self.buffs["Dexterity"] > 0 else "red"}>({"+" if self.buffs["Dexterity"] > 0 else "-"}{self.buffs["Dexterity"]} Block) | '
            if self.debuffs["Frail"] > 0 and card:
                block = math.floor(block * 0.75)
                block_affected_by += '<light-cyan>Frail</light-cyan> (x0.75 block) | '
        self.block += block
        ansiprint(f'{self.name} gained {block} <blue>Block</blue>')
        if self.buffs['Juggernaut'] > 0:
            self.attack(self.buffs['Juggernaut'], random.choice(active_enemies))
        print('Affected by:')
        ansiprint(block_affected_by if block_affected_by else 'Nothing')

    def health_actions(self, heal: int, heal_type: str):
        '''If [heal_type] is 'Heal', you heal for [heal] HP. If [heal_type] is 'Max Health', increase your max health by [heal].'''
        if heal_type == "Heal":
            heal = round(heal * 1.5 if self.in_combat and relics['Magic Flower'] in self.relics else 1)
            self.health += heal
            self.health = min(self.health, self.max_health)
            ansiprint(f"You heal <green>{min(self.max_health - self.health, heal)}</green> <light-blue>HP</light-blue>")
            if self.health >= math.floor(self.health * 0.5) and relics['Red Skull'] in self.relics:
                ansiprint('<red><bold>Red Skull</bold> deactivates</red>.')
                self.starting_strength -= 3
        elif heal_type == "Max Health":
            self.max_health += heal
            self.health += heal
            ansiprint(f"Your Max HP is {'increased' if heal > 0 else 'decreased'} by <{'light-blue' if heal > 0 else 'red'}>{heal}</{'light-blue' if heal > 0 else 'red'}>")

    def card_actions(self, subject_card: dict, action: str,  card_pool: list[dict] = None):
        '''[action] == 'Remove', remove [card] from your deck.
        [action] == 'Upgrade', Upgrade [card]
        [action] == 'Transform', transform a card into another random card.
        [action] == 'Store', (Only in the Note From Yourself event) stores a card to be collected from the event in another run.
        '''
        if card_pool is None:
            card_pool = cards
        while True:
            if action == "Remove":
                del subject_card
            elif action == 'Transform':
                # Curse cards can only be transformed into other Curses
                ansiprint(f"{subject_card['Name']} was <bold>transformed</bold> into ", end='')
                if subject_card.get('Type') == 'Curse':
                    options = [valid_card for valid_card in cards.values() if valid_card.get('Type') == 'Curse' and valid_card.get('Rarity') != 'Special']
                else:
                    options = [valid_card for valid_card in cards.values() if valid_card.get('Class') == valid_card.get('Class') and valid_card.get('Type') not in ('Status', 'Curse', 'Special') and valid_card.get('Upgraded') is not True and valid_card.get('Rarity') != 'Basic']
                while True:
                    new_card = random.choice(options)
                    if new_card == subject_card:
                        continue
                    ansiprint(f"{new_card['Name']} | <yellow>{new_card['Info']}</yellow>")
                    return new_card
            elif action == 'Upgrade':
                if "Searing Blow" not in subject_card['Name']:
                    effects_plus: dict = subject_card.pop('Effects+')
                    subject_card['Name'] += '+'
                    for stat, new_value in effects_plus.items():
                        subject_card[stat] = new_value
                    subject_card['Upgraded'] = True
                else:
                    n = subject_card['Upgrade Count']
                    n += 1
                    subject_card['Name'] += f"+{n}"
                    subject_card['Damage'] = n * (n + 7) / 2 + 12
                    subject_card['Info'] = f"Deal Σ{subject_card['Damage']}. Can be <bold>upgraded</bold> any number of times."

                ansiprint(f"{subject_card['Name'].replace('+', '')} was upgraded to <green>{subject_card['Name']}</green>")
                return subject_card

    def end_player_turn(self):
        self.discard_pile += self.hand
        if relics['Runic Pyramid'] not in self.relics:
            self.hand.clear()
        self.end_of_turn_effects()
        self.end_of_turn_relics()
        sleep(1.5)
        view.clear()

    def move_card(self, card, destination, start, cost_energy=False, shuffle=False):
        if cost_energy is True:
            self.energy -= card['Energy'] if isinstance(card['Energy'], int) else 0
        start.remove(card)
        if shuffle is True:
            destination.insert(random.randint(0, len(destination) - 1), card)
        else:
            destination.append(card)
        if self.buffs["Dark Embrace"] > 0 and destination == self.exhaust_pile:
            ansiprint("<bold>Dark Embrace</bold> allows you to draw 1 card to your hand.")
            self.draw_cards(True, 1)
        if relics['Dead Branch'] in self.relics and destination == self.exhaust_pile:
            random_card = deepcopy(random.choice([card for card in cards.values() if card.get('Upgraded') is not True and card.get('Class') == self.player_class]))
            ansiprint(f"<bold>Dead Branch</bold> allows you to draw a <bold>{random_card['Name']}</bold> card to your hand.")
            self.hand.append(random_card)
        if relics["Charon's Ashes"] in self.relics and destination == self.exhaust_pile:
            for enemy in active_enemies:
                self.attack(enemy, dmg=3)

    def curse_status_effects(self):
        if cards['Burn'] in self.relics:
            self.take_sourceless_dmg(2)

    def attack(self, target: 'Enemy', card=None, dmg: int=0, ignore_block=False):
        dmg_affected_by: str = ''
        dmg = dmg if not card else card.damage
        # Check if already dead and skip if so
        if target.health <= 0:
            return
        if card is not None and card.get('Type') not in ('Status', 'Curse'):  # noqa: SIM102
            if not ignore_block:
                if dmg <= target.block:
                    target.block -= dmg
                    dmg = 0
                    ansiprint("<blue>Blocked</blue>")
                elif dmg > target.block:
                    dmg -= target.block
                    dmg = max(0, dmg)
                    if self.buffs['Envenom'] > 0:
                        target.debuffs['Poison'] += 1
                        ansiprint(f"<light-cyan>Envenom</light-cyan> applied {self.buffs['Envenom']} <red>Poison</red>.")
                    if dmg <= 4 and relics['The Boot'] in self.relics and card.get('Type') == 'Attack':
                        dmg = 5
                        dmg_affected_by += "<bold>The Boot</bold>(dmg increased to 5) | "
                    target.health -= dmg
                    ansiprint(f"You dealt {dmg} damage(<light-blue>{target.block} Blocked</light-blue>) to {target.name}")
                    ansiprint(f"Affected by: \n{dmg_affected_by.rstrip(' | ') if dmg_affected_by else 'Nothing'}")
                    target.block = 0
                    if dmg_affected_by.count(" | ") > 0:
                        sleep(math.log(dmg_affected_by.count(" | "), 12) + 0.2)
                    if target.health <= 0:
                        target.die()
                    if 'Reaper' in card['Name']:
                        self.health_actions(dmg, 'Heal')

    def gain_gold(self, gold, dialogue=True):
        if relics['Ectoplasm'] not in self.relics:
            self.gold += gold
        else:
            ansiprint("You cannot gain <yellow>Gold</yellow> because of <bold>Ectoplasm</bold>.")
        if dialogue is True:
            ansiprint(f"You gained <green>{gold}</green> <yellow>Gold</yellow>(<yellow>{self.gold}</yellow> Total)")
        sleep(1)

    def bottle_card(self, card_type):
        while True:
            valid_cards = [card for card in self.deck if card.get("Type") == card_type]
            for possible_card in self.deck:
                counter = 1
                if possible_card in valid_cards:
                    ansiprint(f"{counter}: <blue>{possible_card['Name']}</blue> | <light-black>{possible_card['Type']}</light-black> | <light-red>{possible_card['Energy']} Energy</light-red> | <yellow>{possible_card['Info']}</yellow>")
                    counter += 1
                    sleep(0.05)
                else:
                    ansiprint(f"{counter}: <light-black>{possible_card['Name']} | {possible_card['Type']} | {possible_card['Energy']} Energy | {possible_card['Info']}</light-black>")
                    counter += 1
                    sleep(0.05)
            option = view.list_input('What card do you want to bottle? > ', self.deck, view.view_piles, lambda card: card['Type'] == card_type, f"That card is not {'an' if card_type == 'Attack' else 'a'} {card_type}.")
            bottled_card = self.deck[option].copy()
            bottled_card['Bottled'] = True
            self.deck.insert(option, bottled_card)
            del self.deck[option + 1]
            ansiprint(f"<blue>{self.deck[option]['Name']}</blue> is now bottled.")
            sleep(0.8)
            break

    def start_turn(self):
        ansiprint(f"<underline><bold>{self.name}</bold></underline>:")
        # Start of turn effects
        self.draw_cards(False, (self.draw_strength + 3) if self.plays_this_turn <= 3 and relics['Pocketwatch'] in self.relics and combat_turn > 1 else 0)
        self.plays_this_turn = 0
        ei.tick_effects(self)
        self.fresh_effects.clear()
        self.start_of_turn_relics()
        self.start_of_turn_effects()
        if combat_turn > 0:
            if relics['Incense Burner'] in self.relics:
                self.incense_turns += 1
                if self.incense_turns == 6:
                    ansiprint('<bold>Incense Burner</bold> caused: ', end='')
                    self.buff('Intangible', 1, False)
                    self.incense_turns = 0
            if relics['Stone Calender'] in self.relics:
                self.stone_calender += 1
                if self.stone_calender == 7:
                    for enemy in active_enemies:
                        self.attack(52, enemy)
        self.energy = self.energy if relics['Ice Cream'] in self.relics else 0
        self.energy += self.energy_gain + self.buffs["Energized"] + self.buffs["Berzerk"]
        if self.buffs["Energized"] > 0:
            ansiprint(f"You gained {self.buffs['Energized']} extra energy because of <light-cyan>Energized</light-cyan>")
            self.buffs["Energized"] = 0
            ansiprint("<light-cyan>Energized wears off.")
        if self.buffs["Berzerk"] > 0:
            ansiprint(f"You gained {self.buffs['Berzerk']} extra energy because of <light-cyan>Berzerk</light-cyan>")
        if self.buffs['Barricade']:
            if combat_turn > 1:
                ansiprint('You kept your block because of <light-cyan>Barriacade</light-cyan>')
        elif relics['Calipers'] in self.relics and self.block > 15:
            self.block -= 15
            ansiprint(f'You kept {self.block} <light-blue>Block</light-blue> because of <bold>Calipers</bold>')
        else:
            self.block = 0

    def end_of_turn_effects(self):
        if self.debuffs['Strength Down'] > 0:
            self.buffs['Strength'] -= self.debuffs['Strength Down']
            ansiprint(f'<debuff>Strength Down</debuff> reduced <buff>Strength</buff> to {self.buffs["Strength"]}')
            self.debuffs['Strength Down'] = 0
            ansiprint('<debuff>Strength Down</debuff>')
        if self.buffs["Regeneration"] > 0:
            self.health_actions(self.buffs["Regeneration"], False)
        if self.buffs["Metallicize"] > 0:
            print("Metallicize: ", end='')
            self.blocking(self.buffs["Metallicize"], False)
        if self.buffs["Plated Armor"] > 0:
            print("Plated Armor: ", end='')
            self.blocking(self.buffs["Plated Armor"], False)
        if self.buffs["Ritual"] > 0:
            print("Ritual: ", end='')
            ei.apply_effect(self, self, 'Strength', self.buffs['Ritual'])
        if self.buffs["Combust"] > 0:
            self.take_sourceless_dmg(self.combusts_played)
            for enemy in active_enemies:
                self.attack(self.buffs['Combust'], enemy)
                sleep(0.1)
        if self.buffs["Omega"] > 0:
            for enemy in active_enemies:
                self.attack(self.buffs['Omega'], enemy)
                sleep(0.5)
        if self.buffs["The Bomb"] > 0:
            self.the_bomb_countdown -= 1
            if self.the_bomb_countdown == 0:
                for enemy in active_enemies:
                    self.attack(self.buffs['The Bomb'], enemy)
                self.buffs["The Bomb"] = 0
                ansiprint("<light-cyan>The Bomb</light-cyan> wears off")
                self.the_bomb_countdown = 3

    def start_of_turn_effects(self):
        if self.buffs['Brutality'] > 0:
            ansiprint("From <buff>Brutality</buff>: ")
            self.take_sourceless_dmg(self.buffs['Brutality'])
            self.draw_cards(True, self.buffs['Brutality'])
        if self.buffs["Next Turn Block"] > 0:
            self.blocking(self.buffs["Next Turn Block"], False)
            self.buffs["Next Turn Block"] = 0
            ansiprint('<light-cyan>Next Turn Block</light-cyan> wears off')
        if self.debuffs['Bias'] > 0:
            self.buffs['Focus'] -= self.debuffs['Bias']
            ansiprint(f"<red>Bias</red> reduced <light-cyan>Focus</light-cyan> by {self.debuffs['Bias']}. You now have {self.buffs['Focus']} <light-cyan>Focus</light-cyan>.")
        if relics['Brimstone'] in self.relics:
            ansiprint("From <bold>Brimstone</bold>:")
            for enemy in active_enemies:
                ei.apply_effect(enemy, self, 'Strength', 1)
            ei.apply_effect(self, self, 'Strength', 2)
        if self.buffs['Demon Form'] > 0:
            ansiprint("From <buff>Demon Form</buff>: ", end='')
            ei.apply_effect(self, self, 'Strength', self.buffs['Demon Form'])
        if relics['Warped Tongs'] in self.relics:
            ansiprint("From <bold>Warped Tongs</bold>:")
            chosen_card = random.randint(0, len(self.hand) - 1)
            self.hand[chosen_card] = self.card_actions(self.hand[chosen_card], 'Upgrade', cards)
        if relics['Horn Cleat'] in self.relics:
            self.blocking(14, False)

    def start_of_turn_relics(self):
        if relics['Anchor'] in self.relics and combat_turn == 1:
            ansiprint('From <bold>Anchor</bold>: ', end='')
            self.blocking(10, False)
        if relics['Horn Cleat'] in self.relics and combat_turn == 2:
            ansiprint("From <bold>Horn Cleat</bold>: ", end='')
            self.blocking(14, False)
        if relics["Captain's Wheel"] in self.relics and combat_turn == 3:
            ansiprint("From <bold>Captain's Wheel</bold>: ", end='')
            self.blocking(18, False)
        if self.attacks_played_this_turn is False and relics['Art of War'] in self.relics:
            self.energy += 1
            ansiprint('You gained 1 Energy from <bold>Art of War</bold>.')
        if relics['Damaru'] in self.relics:
            ansiprint('From <bold>Damaru</bold>: ', end='')
            self.buff('Mantra', 1, False)
        if relics['Lantern'] in self.relics:
            ansiprint('From <bold>Lantern</bold: ', end='')
            self.buff('Energized', 1, False)
        if relics['Happy Flower'] in self.relics:
            if self.happy_flower % 3 != 0:
                self.happy_flower += 1
                if self.happy_flower == 3:
                    ansiprint('From <bold>Happy Flower</bold>: ', end='')
                    self.buff('Energized', 1, False)
        if relics['Mercury Hourglass'] in self.relics:
            for enemy in active_enemies:
                ansiprint("<bold>Mercury Hourglass</bold> activated.")
                self.attack(3, enemy)

    def end_of_turn_relics(self):
        if relics['Orichaicum'] in self.relics and self.block == 0:
            ansiprint('From <bold>Orichaicum</bold>: ', end='')
            self.blocking(6, False)

    def take_sourceless_dmg(self, dmg):
        if relics['Tungsten Rod'] in self.relics:
            dmg -= 1
        self.health -= dmg
        ansiprint(f"<light-red>You lost {dmg} health.</light-red>")
        if relics['Red Skull'] in self.relics and self.health <= math.floor(self.max_health * 0.5) and not self.red_skull_active:
            self.starting_strength += 3
            ansiprint("<bold>Red Skull</bold> activated. You now start combat with 3 <light-cyan>Strength</light-cyan>.")
            self.red_skull_active = True
        if relics['Runic Cube'] and dmg > 0:
            self.draw_cards(False, 1)

    def start_of_combat_relics(self, combat_type):
        if relics['Snecko Eye'] in self.relics:
            ei.apply_effect(self, self, 'Confused')
        if relics["Slaver's Collar"] in self.relics and combat_type in (CombatTier.BOSS, CombatTier.ELITE):
            self.max_energy += 1
        if relics['Du-Vu Doll'] in self.relics:
            num_curses = len([card for card in self.deck if card.get('Type') == 'Curse'])
            if num_curses > 0:
                ansiprint('From <bold>Du-Vu Doll</bold>: ', end='')
                ei.apply_effect(self, self, 'Strength', num_curses)
        if relics['Pantograph'] in self.relics and combat_type == CombatTier.BOSS:
            ansiprint('From <bold>Pantograph</bold>: ', end='')
            self.health_actions(25, 'Heal')
        if relics['Fossilized Helix'] in self.relics:
            ei.apply_effect(self, self, 'Buffer', 1)
        if relics['Thread and Needle'] in self.relics:
            self.buff("Plated Armor", 4, False)
        if relics['Akabeko'] in self.relics:
            self.buff('Vigor', 8, False)
        if self.ancient_tea_set is True and relics['Ancient Tea Set'] in self.relics and combat_turn == 1:
            self.energy += 2
            ansiprint('You gained 2 Energy from <bold>Ancient Tea Set</bold>')
        if relics['Bag of Marbles'] in self.relics:
            for enemy in active_enemies:
                ansiprint('From <bold>Bag of Marbles</bold>: ', end='')
                self.debuff('Vulnerable', 1, enemy, False)
        # Bag of Preparation and Ring of the Snake are coded in the .draw_cards() method above.
        if relics['Blood Vial'] in self.relics:
            ansiprint('From <bold>Blood Vial</bold>: ', end='')
            self.health_actions(2, 'Heal')
        if relics['Bronze Scales'] in self.relics:
            ansiprint('From <bold>Bronze Scales</bold>: ', end='')
            self.buff('Thorns', 3, False)
        if relics['Oddly Smooth Stone'] in self.relics:
            ansiprint('From <bold>Oddly Smooth Stone</bold>: ', end='')
            self.buff('Dexterity', 1, False)
        if relics['Data Disk'] in self.relics:
            ansiprint('From <bold>Data Disk</bold>: ', end='')
            self.buff('Focus', 1, False)
        if relics["Philosopher's Stone"] in self.relics:
            for enemy in active_enemies:
                ei.apply_effect(enemy, self, 'Strength', 1)
        if relics['Mark of Pain'] in self.relics:
            for _ in range(2):
                self.hand.append(deepcopy(cards['Wound']))

    def die(self):
        view.clear()
        ansiprint("<red>You Died</red>")
        input('Press enter > ')
        sys.exit()

    def end_of_combat_effects(self, combat_type):
        if relics["Slaver's Collar"] in self.relics and combat_type in (CombatTier.BOSS, CombatTier.ELITE):
            self.max_energy -= 1
        if relics['Meat on the Bone'] in self.relics and self.health <= math.floor(self.max_health * 0.5):
            ansiprint("<bold>Meat on the Bone</bold> activated.")
            self.health_actions(12, "Heal")
        if relics['Burning Blood'] in self.relics:
            ansiprint("<bold>Burning Blood</bold> activated.")
            self.health_actions(6, 'Heal')
        elif relics['Black Blood'] in player.relics:
            ansiprint("<bold>Black Blood</bold> activated.")
            self.health_actions(12, 'Heal')
        if self.buffs['Repair'] > 0:
            ansiprint("<light-cyan>Self Repair</light-cyan>: ", end='')
            self.health_actions(self.buffs['Repair'], 'Heal')


class Enemy:
    '''
    Attributes::
    health: Current health[int]
    max_health: Maximum health[int]
    block: Current block[int]
    name: Enemy name[str]
    order: Order of moves(planning on using parsing to run)[list]
    moves: All moves the enemy can use[2D dict]
    barricade: Block is not removed at the start of combat[bool]
    artifact: Blocks the next debuff[int]
    vulnerable: Takes 50% more damage from attacks[int](duration stack)
    weak: Deals 25% less damage with attacks[int](duration stack)
    strength: Deal X more damage[int](intensity stack)
    ritual: At the end of it's turn, gains X Strength(intensity stack)
    '''

    def __init__(self, health_range: list, block: int, name: str, powers: dict=None):
        if not powers:
            powers = {}
        actual_health = random.randint(health_range[0], health_range[1])
        self.health = actual_health
        self.max_health = actual_health
        self.block = block
        self.name = name
        self.state = State.ALIVE
        self.third_person_ref = f"{self.name}'s" # Python f-strings suck so I have to use this
        self.past_moves = ['place'] * 3
        self.intent: str = ''
        self.next_move: list[tuple[str, str, tuple] | tuple[str, tuple]] = ''
        self.buffs = ei.init_effects("Enemy Buffs") | powers
        self.debuffs = ei.init_effects("Enemy Debuffs")
        self.stolen_gold = 0
        self.awake_turns = 0
        self.mode = ""
        self.flames = -1
        self.upgrade_burn = False
        self.active_turns = 1
        if 'louse' in self.name:
            self.buffs["Curl Up"] = random.randint(3, 7)

    def __str__(self):
        return 'Enemy'

    def __repr__(self):
        status = f"{self.name} (<red>{self.health} </red>/ <red>{self.max_health}</red> | <light-blue>{self.block} Block</light-blue>) | "
        for buff in self.buffs:
            if self.buffs[buff] is True or self.buffs[buff] > 0:
                status += f"<buff>{buff}</buff>{f' {self.buffs[buff]}' if isinstance(self.buffs[buff], int) else ''} | "
        for debuff in self.debuffs:
            if self.debuffs[debuff] is True or self.debuffs[debuff] > 0:
                status += f"<debuff>{debuff}</debuff>{f' {self.debuffs[debuff]}' if isinstance(self.debuffs[debuff], int) else ''} | "
        if self.flames > 0:
            status += f"<yellow>{self.flames} Flames</yellow> | "
        actual_intent, _ = view.display_actual_damage(self.intent, player, self)
        status += 'Intent: ' + actual_intent if relics['Runic Dome'] not in player.relics else "<light-black>Hidden</light-black>"
        return status

    def show_effects(self):
        for buff in self.buffs:
            ansiprint(f'<buff>{buff}</buff>: {ei.ALL_EFFECTS[buff].replace("X", str(self.buffs[buff]))})')
        for debuff in self.debuffs:
            ansiprint(f'<debuff>{debuff}</debuff>: {ei.ALL_EFFECTS[debuff].replace("X", str(self.debuffs[debuff]))}')

    def set_intent(self):
        pass

    def execute_move(self) -> tuple[str]:
        moves = 1
        display_name = "DEFAULT: UNKNOWN"
        for action in self.next_move:
            if moves == 1 and len(action) > 2:
                display_name, action, parameters = action
            else:
                action, parameters = action
            if action in ('Cowardly', 'Sleeping', 'Stunned') or action not in ('Attack', 'Buff', 'Debuff', 'Status', 'Block'):
                self.misc_move()
                sleep(1)
                view.clear()
                return
            ansiprint(f"<bold>{display_name}</bold>\n" if moves == 1 else '', end='')
            sleep(0.6)
            if action == 'Attack':
                dmg = parameters[0]
                times = parameters[1] if len(parameters) > 1 else 1
                self.attack(dmg, times)
            elif action == 'Buff':
                buff_name = parameters[0]
                amount = parameters[1] if len(parameters) > 1 else 1
                target = parameters[2] if len(parameters) > 2 else self
                ei.apply_effect(target, self, buff_name, amount)
            elif action == 'Debuff':
                debuff_name = parameters[0]
                amount = parameters[1] if len(parameters) > 1 else 1
                ei.apply_effect(self, self, debuff_name, amount)
            elif action == 'Remove Effect':
                effect_name = parameters[0]
                effect_type = parameters[1]
                self.remove_effect(effect_name, effect_type)
            elif action == 'Status':
                assert len(parameters) >= 3, f"Status action requires 3 parameters: given {parameters}"
                status_name = parameters[0]
                amount = parameters[1]
                location = parameters[2].lower()
                self.status(status_name, amount, location)
            elif action == 'Block':
                block = parameters[0]
                target = parameters[1] if len(parameters) > 1 else None
                self.blocking(block, target)
            sleep(0.2)
            moves += 1
        if display_name == 'Inferno' and self.flames > -1:
            self.upgrade_burn = True
            self.flames = 0
        sleep(0.5)
        self.past_moves.append(display_name)
        self.active_turns += 1
        if not self.debuffs.get('Asleep'):
            self.awake_turns += 1
        if self.flames > -1:
            self.flames += 1

    def misc_move(self):
        if len(self.next_move[0]) > 2:
            name, func_name, parameters = self.next_move[0]
        else:
            name, func_name = self.next_move[0]
        ansiprint(f"<bold>{name}</bold>")
        sleep(0.6)
        if func_name == 'Cowardly':
            ansiprint("<italic>Hehe. Thanks for the money.<italic>")
            active_enemies.remove(self)
            ansiprint(f"<italic><red>{self.name} has escaped</red></italic>")
        elif func_name == 'Sleeping':
            sleeptalk = parameters[0]
            ansiprint(f'<italic>{sleeptalk}</italic>')
        elif func_name == 'Stunned':
            ansiprint("<italic>Stunned!</italic>")
        elif func_name == 'Summon':
            enemies = tuple(parameters[0])
            amount = int(parameters[1]) if len(parameters) > 1 else 1
            choice = bool(parameters[2]) if len(parameters) > 2 else False
            self.summon(enemies, amount, choice)
        elif func_name == 'Explode':
            pass
        elif func_name == 'Rebirth':
            for debuff in self.debuffs:
                if debuff not in ei.NON_STACKING_EFFECTS:
                    self.debuffs[debuff] = 0
                else:
                    self.debuffs[debuff] = False
            self.buffs['Curiosity'] = False
            self.buffs['Unawakened'] = False
        elif func_name == 'Revive':
            self.health = math.floor(self.health * 0.5)
            ansiprint(f"<bold>{self.name}</bold> revived!")
        elif func_name == 'Charging':
            message = parameters[0]
            ansiprint(f'{message}')
        elif func_name == 'Split':
            split_into = {"Slime Boss": (Enemy(self.health, 0, 'Acid Slime(L)'), Enemy(self.health, 0, 'Spike Slime (L)')),
                          "Acid Slime (L)": (Enemy(self.health, 0, 'Acid Slime(M)'), Enemy(self.health, 0, 'Acid Slime(M)')),
                          "Spike Slime (L)": (Enemy(self.health, 0, 'Spike Slime (M)'), Enemy(self.health, 0, "Spike Slime (M)"))}
            for _ in range(2):
                active_enemies.append(split_into[self.name])
            ansiprint(f'{self.name} split into 2 {split_into[self.name].name}s')
        self.active_turns += 1

    def die(self):
        """
        Dies.
        """
        print(f"{self.name} has died.")
        if relics['Gremlin Horn'] in player.relics:
            player.energy += 1
            player.draw_cards(True, 1)
        try:
            active_enemies.remove(self)
        except ValueError:
            raise Exception(f"{self.name} is not in the active enemies list.")

    def debuff_and_buff_check(self):
        """
        Not finished
        """

    def move_spam_check(self, target_move, max_count):
        '''Returns False if the move occurs [max_count] times in a row. Otherwise returns True'''
        use_count = 0

        for move in self.past_moves:
            if move == target_move:
                use_count += 1
                if use_count == max_count:
                    return False
            else:
                use_count = 0

        return True

    def attack(self, dmg: int, times: int):
        dmg_affected_by = ''
        for _ in range(times):
            if self.buffs['Strength'] != 0:
                dmg += self.buffs['Strength']
                dmg_affected_by += f"<{'red' if self.buffs['Strength'] < 0 else 'light-cyan'}>Strength</{'red' if self.buffs['Strength'] < 0 else 'light-cyan'}>({'-' if self.buffs['Strength'] < 0 else '+'}{self.buffs['Strength']} dmg) | "
            if player.debuffs['Vulnerable']:
                dmg = math.floor(dmg * 1.5)
                dmg_affected_by += "<red>Vulnerable</red>(x1.5 dmg) | "
            if self.debuffs['Weak'] > 0:
                dmg = math.floor(dmg * 0.75 - 0.15 if relics['Paper Krane'] in player.relics else 0)
                dmg_affected_by += "<red>Weak</red>(x0.75 dmg) | "
            if player.buffs['Intangible']  > 0:
                dmg = 1
                dmg_affected_by = "<light-cyan>Intangible</light-cyan>(Reduce ALL damage to 1)"
            if dmg <= player.block:
                player.block -= dmg
                dmg = 0
                ansiprint("<light-blue>Blocked</light-blue>")
            elif dmg > player.block:
                dmg -= player.block
                dmg = max(0, dmg)
                if relics['Torii'] in player.relics and dmg in range(2, 6):
                    dmg = min(dmg, 1)
                    dmg_affected_by += "<bold>Torii</bold>(dmg reduced to 1) | "
                if relics['Tungsten Rod'] in player.relics:
                    dmg -= 1
                    dmg_affected_by += "<bold>Tungsten Rod</bold>(dmg reduced by 1) | "
                if relics['Red Skull'] in player.relics and player.health <= math.floor(player.health * 0.5) and not player.red_skull_active:
                    player.starting_strength += 3
                    player.buffs['Strength'] += 3
                    ansiprint("<bold>Red Skull</bold> gives you 3 <light-cyan>Strength</light-cyan>.")
                if dmg > 0 and relics['Self-Forming Clay'] in player.relics:
                    ansiprint('<bold>Self-Forming Clay</bold> activated.')
                    player.buffs['Next Turn Block'] += 3
                ansiprint(f"{self.name} dealt {dmg}(<light-blue>{player.block} Blocked</light-blue>) damage to you.")
                player.block = 0
                player.health -= dmg
                if relics['Runic Cube'] in player.relics and dmg > 0:
                    player.draw_cards(True, 1)
            if player.buffs['Flame Barrier'] > 0:
                if self.block >= dmg:
                    self.block -= dmg
                else:
                    dmg -= self.block
                    self.health -= dmg
                    self.block = 0
                    ansiprint(f"{self.name} took {dmg}(<light-blue>{self.block} Blocked</light-blue>) damage from <buff>Fire Breathing</buff>.")
        if player.health <= math.floor(player.max_health * 0.5) and not player.meat_on_the_bone:
            player.meat_on_the_bone = True
            ansiprint("<bold>Meat on the Bone</bold>> activated.")
        sleep(1)

    def remove_effect(self, effect_name, effect_type):
        if effect_name not in ei.ALL_EFFECTS:
            raise ValueError(f"{effect_name} is not a member of any debuff or buff list.")
        effect_types = {"Buffs": self.buffs, "Debuffs": self.debuffs}
        if effect_name not in ei.NON_STACKING_EFFECTS:
            effect_types[effect_type][effect_name] = 0
        else:
            effect_types[effect_type][effect_name] = False

    def blocking(self, block: int, target: 'Enemy'=None):
        if not target:
            target = self
        target.block += block
        ansiprint(f"{target.name} gained {block} <blue>Block</blue>")
        sleep(1)

    def status(self, status_card_name: str, amount: int, location: str):
        locations = {'draw pile': player.draw_pile, 'discard pile': player.discard_pile, 'hand': player.hand}
        pile = locations[location]
        for _ in range(amount):
            status_card = deepcopy(cards[status_card_name])
            upper_bound = len(location) - 1 if len(location) > 0 else 1
            insert_index = random.randint(0, upper_bound)
            pile.insert(insert_index, status_card)
        ansiprint(f"{player.name} gained {amount} {status_card['Name']}({status_card['Info']}) \nPlaced into {location}")
        sleep(1)

    def summon(self, enemy, amount: int, random_enemy: bool):
        if len(enemy) == 1:
            enemy = enemy[0]
        for _ in range(amount):
            chosen_enemy = random.choice(enemy) if random_enemy else enemy
            active_enemies.append(chosen_enemy)
            ansiprint(f"<bold>{chosen_enemy.name}</bold> summoned!")

    def start_turn(self):
        ansiprint(f"<underline><bold>{self.name}</bold></underline>:")
        if "Block" not in self.intent: # Checks the last move used to see if the enemy Blocked last turn
            if self.buffs["Barricade"] is False:
                self.block = 0
            else:
                if self.active_turns > 1 and self.block > 0:
                    ansiprint(f"{self.name}'s Block was not removed because of <light-cyan>Barricade</light-cyan")
        ei.tick_effects(self)
        print()
        self.set_intent()

    def end_of_turn_effects(self):
        if self.buffs['Ritual'] > 0:
            ansiprint('<light-cyan>Ritual</light-cyan>: ', end='')
            ei.apply_effect(self, self, 'Strength', self.buffs['Ritual'])
        if self.buffs['Metallicize'] > 0:
            ansiprint('<light-cyan>Metallicize</light-cyan>: ', end='')
            self.blocking(self.buffs['Metallicize'])
        if self.buffs['Plated Armor'] > 0:
            ansiprint('<light-cyan>Plated Armor</light-cyan>: ', end='')
            self.blocking(self.buffs['Plated Armor'])
        if self.buffs['Regen'] > 0:
            ansiprint('<light-cyan>Regen</light-cyan>: ', end='')
            self.health = min(self.health + self.buffs['regen'], self.max_health)
        if self.buffs['Strength Up'] > 0:
            ansiprint('<light-cyan>Strength Up</light-cyan>: ', end='')
            ei.apply_effect(self, self, 'Strength', self.buffs['Strength Up'])


def create_player():
    return Player(80, 0, 3, [deepcopy(card) for card in [cards['Strike'], cards['Strike'], cards['Strike'], cards['Strike'], cards['Strike'], cards['Defend'], cards['Defend'], cards['Defend'], cards['Defend'], cards['Bash'],]])

# Characters
player = create_player()
player.relics.append(relics['Burning Blood'])
