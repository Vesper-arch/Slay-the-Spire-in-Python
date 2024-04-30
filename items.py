import random
from copy import deepcopy
from time import sleep
from uuid import uuid4

from ansi_tags import ansiprint

from definitions import CardType, PlayerClass, Rarity, TargetType

from helper import ei, view
from message_bus import Message, Registerable


class Card(Registerable):
    def __init__(self, name, info, player_class: PlayerClass, card_type: CardType, rarity: Rarity, target=TargetType.NOTHING, energy_cost=-1, upgradeable=True):
        self.uid = uuid4()
        self.name = name
        self.info = info
        self.player_class = player_class
        self.card_type = card_type
        self.rarity = rarity
        self.target = target
        self.base_energy_cost = energy_cost
        self.energy_cost = energy_cost
        self.upgradeable = upgradeable
        self.upgrade_preview = f"{self.get_name()} -> <green>{self.name}+</green> | "
        self.reset_energy_next_turn = False

    def changed_energy(self):
        return self.base_energy_cost != self.energy_cost

    def is_upgradeable(self):
        return not self.upgraded and (self.name == "Burn" or self.type not in (CardType.STATUS, CardType.CURSE))

    def get_name(self):
        return f"<{self.rarity.lower()}>{self.name}</{self.rarity.lower()}"

    def pretty_print(self):
        return f"""{self.get_name()} | <{self.card_type.lower()}>{self.card_type}</{self.card_type.lower()}>{f' | <light-red>{"<green>" if self.changed_energy() else ""}{self.energy_cost}{"</green>" if self.changed_energy() else ""} Energy</light-red>' if self.energy_cost >= 0 else ''} | <yellow>{self.info}</yellow>"""

    def modify_energy_cost(self, amount, modify_type='Adjust', temporary=False):
        assert modify_type in ("Adjust", "Set"), "Argument modify_type has to be either 'Adjust' or 'Set'."

        if not (modify_type == 'Set' and amount != self.energy_cost) or not (modify_type == 'Adjust' and amount != 0):
            pass
        if modify_type == 'Adjust':
            self.energy_cost += amount
            ansiprint(f"{self.get_name()}'s Energy was {'<green>reduced</green>' if amount < 0 else '<red>increased</red>'} by {abs(amount)}")
        elif modify_type == 'Set':
            self.energy_cost = amount
            ansiprint(f"{self.get_name}'s Energy was set to {amount}.'")
        self.reset_energy_next_turn = temporary

    def modify_damage(self, amount, modify_type, context, permanent=False):
        assert getattr(self, 'damage', None) is not None, "Card must have a damage value initialized."
        assert modify_type in ("Adjust", "Set"), "Argument modify_type has to be either 'Adjust' or 'Set'."

        if modify_type == 'Adjust':
            if permanent:
                self.base_damage += amount
                self.damage += amount
            else:
                self.damage += amount
            ansiprint(f"{self.get_name()}'s damage was {'<red>decreased</red>' if amount < 0 else '<green>increased</green>'} by {abs(amount)} because of {context}.")
        elif modify_type == 'Set':
            if permanent:
                self.base_damage += amount
                self.damage = amount
            else:
                self.damage = amount
            ansiprint(f"{self.get_name()}'s damage was set to {amount} by {context}.")
        self.damage_affected_by.append(context)

    def modify_block(self, amount, modify_type, context, permanent=False):
        assert getattr(self, 'block', None) is not None, "Card must have a block value initialized."
        assert modify_type in ("Adjust", "Set"), "Argument modify_type has to be either 'Adjust' or 'Set'."

        if modify_type == 'Adjust':
            if permanent:
                self.base_block += amount
                self.block += amount
            else:
                self.block += amount
            ansiprint(f"{self.get_name()}'s <keyword>Block</keyword> was {'<red>decreased</red>' if amount < 0 else '<green>increased</green>'} by {amount} because of {context}.")
        elif modify_type == 'Set':
            if permanent:
                self.base_block += amount
                self.block = amount
            else:
                self.block = amount
            ansiprint(f"{self.get_name()}'s <keyword>Block</keyword> was set to {amount} by {context}.")
        self.block_affected_by.append(context)

class Relic(Registerable):
    def __init__(self, name, info, flavor_text, rarity: Rarity, player_class=PlayerClass.ANY):
        self.uid = uuid4()
        self.name = name
        self.info = info
        self.flavor_text = flavor_text
        self.rarity = rarity
        self.player_class = player_class

    def get_name(self):
        return f"<{self.rarity.lower()}>{self.name}</{self.rarity.lower()}>"

    def pretty_print(self):
        color_map = {"Ironclad": 'red', "Silent": 'dark_green', "Defect": 'true-blue', "Watcher": 'watcher_purple', "Any": 'white'}
        class_color = color_map[self.player_class]
        return f"{self.get_name()} | <yellow>{self.info}</yellow> | <dark_blue><italic>{self.flavor_text}</italic></dark_blue>{f' | <{class_color}>{self.player_class}</{class_color}>' if self.player_class != PlayerClass.ANY else ''}"

class Potion(Registerable):
    registers = [Message.ON_RELIC_ADD]
    def __init__(self, name, info, rarity: Rarity, target_type: TargetType, player_class=PlayerClass.ANY):
        self.uid = uuid4()
        self.name = name
        self.info = info
        self.rarity = rarity
        self.target_type = target_type
        self.player_class = player_class
        self.playable = True
        self.golden_stats = []
        self.golden_info = ""

    def get_name(self):
        return f"<{self.rarity.lower()}>{self.name}</{self.rarity.lower()}>"

    def pretty_print(self):
        color_map = {"Ironclad": 'red', "Silent": 'dark_green', "Defect": 'true-blue', "Watcher": 'watcher_purple', "Any": 'white'}
        class_color = color_map[self.player_class]
        return f"{self.get_name()} | <yellow>{self.info}</yellow>{f' | <{class_color}>{self.player_class}</{class_color}>' if self.player_class != PlayerClass.ANY else ''}"

    def callback(self, message, data):
        if message == Message.ON_RELIC_ADD:
            relic = data
            if relic.name == "Golden Bark":
                self.info = self.golden_info
                for stat in self.golden_stats:
                    stat *= 2

def modify_energy_cost(amount: int, modify_type: str, card: dict):
    assert modify_type in ('Set', 'Adjust'), f"modify_type must be 'Set' or 'Adjust', not {modify_type}"
    if card.get("Energy") is None:
        ansiprint("<red>This card is not playable and therefore its energy cannot be changed.</red>")
        return
    if (modify_type == 'Set' and amount != card['Energy']) or (modify_type == 'Adjust' and amount != 0):
        card['Changed Energy'] = True
    if modify_type == 'Set':
        card['Energy'] = amount
        ansiprint(f"{card['Name']} has its energy cost set to {amount}")
    elif modify_type == 'Adjust':
        card['Energy'] += amount
        ansiprint(f"{card['Name']} got its energy cost {'<green>reduced</green>' if amount < 0 else '<red>increased</red>'} by {abs(amount)}")
    return card

def use_strike(targeted_enemy: object, using_card, entity):
    '''Deals 6(9) damage.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)


def use_bash(targeted_enemy: object, using_card, entity):
    '''Deals 8(10) damage. Apply 2(3) Vulnerable'''
    print()
    entity.attack(using_card['Damage'], targeted_enemy, using_card)
    ei.apply_effect(targeted_enemy, entity, 'Vulnerable', using_card['Vulnerable'])


def use_defend(using_card, entity):
    '''Gain 5(8) Block'''
    entity.blocking(using_card['Block'])


def use_bodyslam(targeted_enemy, using_card, entity):
    '''Deals damage equal to your Block. Exhaust.(Don't Exhaust)'''
    entity.attack(dmg=entity.block, target=targeted_enemy, card=using_card)


def use_clash(targeted_enemy, using_card, entity):
    '''Can only be played if there are no non-attack cards in your hand. Deal 14(18) damage.'''
    for card in entity.hand:
        if card['Type'] != 'Attack':
            print('You have non-Attack cards in your hand')
            sleep(1.5)
            view.clear()
            return
    entity.attack(using_card['Damage'], targeted_enemy, using_card)


def use_heavyblade(targeted_enemy, using_card, entity):
    '''Deal 14(18) damage. Strength affects this card 3(5) times'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)


def use_cleave(enemies, using_card, entity):
    '''Deal 8(11) damage to ALL enemies.'''
    for enemy in enemies:
        entity.attack(using_card['Damage'], enemy, using_card)

def use_dramaticentrance(enemies, using_card, entity):
    '''Deal 8(12) damage to ALL enemies. Exhaust.'''
    for enemy in enemies:
        entity.attack(using_card['Damage'], enemy, using_card)

def use_blind(enemies, using_card, entity):
    '''Apply 2 Weak (to ALL enemies).'''
    for enemy in enemies:
        ei.apply_effect(enemy, entity, 'Weak', using_card['Weak'])


def use_perfectedstrike(targeted_enemy, using_card, entity):
    '''Deal 6 damage. Deals 2(3) additional damage for ALL your cards containing "Strike"'''
    total_damage = 6 + (len([card for card in entity.deck if 'strike' in card.get('Name')]) * using_card['Damage Per "Strike"'])
    print()
    entity.attack(total_damage, targeted_enemy, using_card)

def use_anger(targeted_enemy, using_card, entity):
    '''Deal 6(8) damage. Add a copy of this card to your discard pile.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)
    entity.discard_pile.append(deepcopy(using_card))

def use_apotheosis(using_card, entity):
    '''Upgrade ALL of your cards for the rest of combat. Exhaust.'''
    for card in entity.hand:
        card = entity.card_actions(card, 'Upgrade')
        sleep(0.3)

def use_armaments(using_card, entity):
    '''Gain 5 Block. Upgrade a(ALL) card(s) in your hand for the rest of combat.'''
    entity.blocking(5, False)
    if using_card.get('Upgraded'):
        for card in entity.hand:
            card = entity.card_actions(card, 'Upgrade')
            sleep(0.3)
    else:
        while True:
            option = view.list_input("Choose a card to upgrade > ", entity.hand, view.upgrade_preview, lambda card: not card.get("Upgraded") and (card['Name'] == "Burn" or card['Type'] not in ("Status", "Curse")), "That card is not upgradeable.")
            entity.hand[option] = entity.card_actions(entity.hand[option], 'Upgrade')
            break

def use_clothesline(targeted_enemy, using_card, entity):
    '''Deal 12(14) damage. Apply 2(3) Weak'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)
    ei.apply_effect(targeted_enemy, entity, 'Weak', using_card['Weak'])

def use_havoc(enemies, using_card, entity):
    '''Play the top card of your draw pile and Exhaust it.'''
    _ = using_card
    if len(entity.draw_pile) > 0:
        entity.use_card(entity.draw_pile[-1], random.choice(enemies), True, entity.draw_pile)

def use_flex(using_card, entity):
    '''Gain 2(4) Strength. At the end of your turn, lose 2(4) Strength'''
    ei.apply_effect(entity, entity, 'Strength', using_card['Strength'])
    ei.apply_effect(entity, entity, 'Strength Down', using_card['Strength'])

def use_headbutt(targeted_enemy, using_card, entity):
    '''Deal 9(12) damage. Put a card from your discard pile on top of your draw pile.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)
    while True:
        view.view_piles(entity.discard_pile, entity)
        choice = view.list_input('What card do you want to put on top of your draw pile? > ', entity.discard_pile, view.view_piles)
        entity.move_card(card=entity.discard_pile[choice], move_to=entity.draw_pile, from_location=entity.discard_pile, cost_energy=False)
        break

def use_handofgreed(targeted_enemy, using_card, entity):
    '''Deal 20(25) damage. If Fatal, gain 20(25) Gold.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)
    if targeted_enemy.health <= 0:
        entity.gold += using_card['Gold']
        ansiprint(f"You gained {using_card['Gold']} <keyword>Gold</keyword>.")

def use_shrugitoff(using_card, entity):
    '''Gain 8(11) Block. Draw 1 card.'''
    entity.blocking(using_card['Block'])
    entity.draw_cards(True, 1)

def use_swordboomerang(enemies, using_card, entity):
    '''Deal 3 damage to a random enemy 3(4) times.'''
    for _ in range(using_card['Times']):
        entity.attack(3, random.choice(enemies), using_card)

def use_thunderclap(enemies, using_card, entity):
    '''Deal 4(7) damage and apply 1 Vulnerable to ALL enemies.'''
    for enemy in enemies:
        entity.attack(using_card['Damage'], enemy, using_card)
        ei.apply_effect(enemy, entity, 'Vulnerable', 1, entity)
    sleep(0.5)
    view.clear()

def use_ironwave(targeted_enemy, using_card, entity):
    '''Gain 5(7) Block. Deal 5(7) damage.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)
    entity.blocking(using_card['Block'])


def use_pommelstrike(targeted_enemy, using_card, entity):
    '''Deal 9(10) damage. Draw 1(2) cards.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)
    entity.draw_cards(True, using_card['Cards'])

def use_masterofstrategy(using_card, entity):
    '''Draw 3(4) cards. Exhaust.'''
    entity.draw_cards(True, using_card['Cards'])

def use_truegrit(using_card, entity):
    '''Gain 7(9) Block. Exhaust a random(not random) card in your hand.'''
    entity.blocking(using_card['Block'])
    if using_card.get('Upgraded'):
        while True:
            view.view_piles(entity.hand, entity)
            option = view.list_input('Choose a card to <keyword>Exhaust</keyword>.', entity.hand, view.view_piles)
            entity.move_card(card=entity.deck[option], move_to=entity.exhaust_pile, from_location=entity.hand, cost_energy=False)
            break
    else:
        entity.move_card(card=random.choice(entity.hand), move_to=entity.exhaust_pile, from_location=entity.hand, cost_energy=False)

def use_twinstrike(targeted_enemy, using_card, entity):
    '''Deal 5(7) damage twice.'''
    for _ in range(2):
        entity.attack(using_card['Damage'], targeted_enemy, using_card)

def use_warcry(using_card, entity):
    '''Draw 1(2) cards. Put a card from your hand on top of your draw pile.'''
    entity.draw_cards(True, using_card['Cards'])
    while True:
        view.view_piles(entity.hand, entity)
        option = view.list_input('Choose a card to put on top of your draw pile.', entity.hand, view.view_piles)
        entity.draw_pile.append(entity.hand[option])
        del entity.hand[option]
        break

def use_wildstrike(targeted_enemy, using_card, entity):
    '''Deal 12(17) damage. Shuffle a Wound into your draw pile.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)
    if len(entity.draw_pile) > 0:
        entity.draw_pile.insert(random.randint(0, len(entity.draw_pile) - 1), deepcopy(cards['Wound']))
    else:
        entity.draw_pile.append(deepcopy(cards['Wound']))
    ansiprint("A <status>Wound</status> was shuffled into your draw pile.")

def use_battletrance(using_card, entity):
    '''Draw 3(4) cards. You cannot draw additonal cards this turn.'''
    entity.draw_cards(True, using_card['Cards'])
    ei.apply_effect(entity, entity, 'No Draw')

def use_bloodforblood(targeted_enemy, using_card, entity):
    '''Costs 1 less Energy for each time you lose HP this combat. Deal 18(22) damage.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)

def use_bloodletting(using_card, entity):
    '''Lose 2 HP. Gain 2(3) Energy.'''
    entity.take_sourceless_dmg(2)
    entity.energy += using_card['Energy Gain']
    ansiprint(f"You gained {using_card['Energy Gain']} <keyword>Energy</keyword>.")

def use_burningpact(using_card, entity):
    '''Exhaust one card. Draw 1(2) cards.'''
    while True:
        option = view.list_input('Choose a card to <keyword>Exhaust</keyword> > ', entity.hand, view.view_piles)
        entity.move_card(card=entity.hand[option], move_to=entity.exhaust_pile, from_location=entity.hand, cost_energy=False)
        ansiprint(f"{entity.hand[option]['Name']} was <keyword>Exhausted</keyword>")
        break
    entity.draw_cards(True, using_card['Cards'])

def use_carnage(targeted_enemy, using_card, entity):
    '''Ethereal. Deal 20(28) damage.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)

def use_combust(using_card, entity):
    '''At the end of your turn, lose 1 HP and deal 5(7) damage to ALL enemies.'''
    ei.apply_effect(entity, entity, 'Combust', using_card['Combust'])

def use_darkembrace(using_card, entity):
    '''Whenever a card is Exhausted, draw 1 card.'''
    _ = using_card
    ei.apply_effect(entity, entity, 'Dark Embrace', 1)

def use_disarm(targeted_enemy, using_card, entity):
    '''Enemy loses 2(3) Strength. Exhaust.'''
    ei.apply_effect(targeted_enemy, entity, 'Strength', -using_card['Strength Loss'])

def use_darkshackles(targeted_enemy, using_card, entity):
    '''Enemy loses 9(15) Strength for the rest of this turn.'''
    ei.apply_effect(targeted_enemy, entity, 'Strength', -using_card['Magic Number'])

def use_dropkick(targeted_enemy, using_card, entity):
    '''Deal 5(8) damage. If the enemy has Vulnerable, gain 1 Energy and draw 1 card.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)
    if targeted_enemy.debuffs['Vulnerable'] > 0:
        entity.energy += 1
        ansiprint('You gained 1 <keyword>Energy</keyword>.')
        entity.draw_cards(True, 1)

def use_dualwield(using_card, entity):
    '''Create a(2) copy(copies) of an Attack or Power card.'''
    while True:
        valid_cards = [(idx, card) for idx, card in enumerate(entity.hand) if card.get('Type') in ('Attack', 'Power')]
        view_cards = [card[1] for card in valid_cards]
        option = view.list_input(f"Choose a card to make {'a copy' if not using_card.get('Upgraded') else '2 copies'} of > ", view_cards, view.view_piles, lambda card: card['Type'] in ("Power", "Attack"), "That card is not a <keyword>Power</keyword> or an <keyword>Attack</keyword>.")
        #convert option to index of entity.hand
        option = valid_cards[option][0]
        for _ in range(using_card['Copies']):
            print("You made a copy of", entity.hand[option]['Name'])
            entity.hand.insert(option, deepcopy(entity.hand[option]))
        break

def use_entrench(using_card, entity):
    '''Double your Block'''
    _ = using_card
    entity.block *= 2
    ansiprint(f"You now have <light-blue>{entity.block} Block</light-blue>.")

def use_evolve(using_card, entity):
    '''Whenever you draw a Status card, draw 1(2) card.'''
    ei.apply_effect(entity, entity, 'Evolve', using_card['Evolve'])

def use_feelnopain(using_card, entity):
    '''Whenever a card is Exhausted, gain 3(4) Block.'''
    ei.apply_effect(entity, entity, 'Feel No Pain', using_card['Feel No Pain'])

def use_firebreathing(using_card, entity):
    '''Whenever you draw a Status or Curse card, deal 6(10) damage to ALL enemies.'''
    ei.apply_effect(entity, entity, 'Fire Breathing', using_card['Fire Breathing'])

def use_flamebarrier(using_card, entity):
    '''Gain 12(16) Block. Whenever you are attacked this turn, deal 4 damage back.'''
    entity.blocking(using_card['Block'])
    ei.apply_effect(entity, entity, 'Flame Barrier', 4)

def use_ghostlyarmor(using_card, entity):
    '''Ethereal. gain 10(13) Block.'''
    entity.blocking(using_card['Block'])

def use_hemokinesis(targeted_enemy, using_card, entity):
    '''Lose 2 HP. Deal 15(20) damage.'''
    entity.take_sourceless_dmg(2)
    entity.attack(using_card['Damage'], targeted_enemy, using_card)

def use_infernalblade(using_card, entity):
    '''Add a random Attack into your hand. It costs 0 this turn. Exhaust.'''
    _ = using_card
    valid_cards = [card for card in cards.values() if card.get('Type') == 'Attack' and card.get('Class') == entity.player_class]
    entity.hand.append(modify_energy_cost(0, 'Set', deepcopy(random.choice(valid_cards))))

def use_chrysalis(using_card, entity):
    '''Add 3(5) random Skills into your hand. They cost 0 this turn. Exhaust.'''
    valid_cards = [card for card in cards.values() if card.get('Type') == CardType.SKILL and card.get('Class') == entity.player_class]
    entity.hand.append(modify_energy_cost(amount=0, modify_type='Set', card=deepcopy(random.choice(valid_cards))))

def use_discovery(using_card, entity):
    '''Choose 1 of 3 random cards to add to your hand. It costs 0 this turn. Exhaust. (Don't Exhaust.)'''
    raise NotImplementedError("Need to have a user interaction here")

def use_inflame(using_card, entity):
    '''Gain 2(3) Strength'''
    ei.apply_effect(entity, entity, 'Strength', using_card['Strength'])

def use_intimidate(enemies, using_card, entity):
    '''Apply 1(2) Weak to ALL enemies. Exhaust.'''
    for enemy in enemies:
        ei.apply_effect(enemy, entity, 'Weak', using_card['Weak'])

def use_metallicize(using_card, entity):
    '''At the end of your turn, gain 3(4) Block'''
    ei.apply_effect(entity, entity, 'Metallicize', using_card['Metallicize'])

def use_powerthrough(using_card, entity):
    '''Add 2 Wounds into your hand. Gain 15(20) Block.'''
    for _ in range(2):
        entity.hand.append(deepcopy(cards['Wound']))
    ansiprint("2 <status>Wounds</status> have been added to your hand.")
    entity.blocking(using_card['Block'])

def use_pummel(targeted_enemy, using_card, entity):
    '''Deal 2 damage 4(5) times. Exhaust.'''
    for _ in range(using_card['Times']):
        entity.attack(2, targeted_enemy, using_card)
        sleep(0.5)

def use_rage(using_card, entity):
    '''Whenever you play an Attack this turn, gain 3(5) Block'''
    ei.apply_effect(entity, entity, 'Rage', using_card['Rage'])

def use_rampage(targeted_enemy, using_card, entity):
    '''Deal 8 damage. Increase this card's damage by 5(8).'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)
    using_card['Damage'] += using_card['Damage+']

def use_recklesscharge(targeted_enemy, using_card, entity):
    '''Deal 7(10) damage. Shuffle a Dazed into your draw pile.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)
    entity.draw_pile.insert(random.randint(0, len(entity.draw_pile) - 1), deepcopy(cards['Dazed']))
    ansiprint("A <status>Dazed</status> was shuffled into your draw pile.")

def use_deepbreath(using_card, entity):
    '''Shuffle your discard pile into your draw pile. Draw 1(2) cards.'''
    entity.draw_pile.extend(entity.discard_pile)
    entity.discard_pile = []
    entity.draw_cards(True, using_card['Cards'])

def use_rupture(using_card, entity):
    '''Whenever you lose HP from a card, gain 1(2) Strength.'''
    ei.apply_effect(entity, entity, 'Rupture', using_card['Rupture'])

def use_searingblow(targeted_enemy, using_card, entity):
    '''Deal 12(16) damage. Can be upgraded any number of times.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)

def use_secondwind(using_card, entity):
    '''Exhaust all non-Attack cards in your hand and gain 5(7) Block for each card Exhausted.'''
    cards_exhausted = 0
    for card in entity.hand:
        if card.get('Type') != 'Attack':
            cards_exhausted += 1
            entity.move_card(card=card, move_to=entity.exhaust_pile, from_location=entity.hand, cost_energy=False)
            ansiprint(f"{card['Name']} was <keyword>Exhausted</keyword>.")
            sleep(0.5)
    entity.blocking(using_card['Block Per Card'] * cards_exhausted)

def use_seeingred(using_card, entity):
    '''Gain 2 Energy. Exhaust.'''
    _ = using_card
    entity.energy += 2
    ansiprint('You gained 2 <keyword>Energy</keyword>.')

def use_sentinel(using_card, entity):
    '''Gain 5(8) Block. If this card is Exhausted, gain 2(3) Energy.'''
    entity.blocking(using_card['Block'])

def use_seversoul(targeted_enemy, using_card, entity):
    '''Exhaust all non-Attack cards in your hand. Deal 16(22) damage.'''
    for card in entity.hand:
        if card['Type'] != 'Attack':
            entity.move_card(card=card, move_to=entity.exhaust_pile, from_location=entity.hand, cost_energy=False)
            ansiprint(f"{card['Name']} was exhausted.")
            sleep(0.5)
    entity.attack(using_card['Damage'], targeted_enemy, using_card)

def use_shockwave(enemies, using_card, entity):
    '''Apply 3(5) Weak and Vulnerable to ALL enemies. Exhaust.'''
    for enemy in enemies:
        ei.apply_effect(enemy, entity, 'Weak', using_card['Weak/Vulnerable'])
        ei.apply_effect(enemy, entity, 'Vulnerable', using_card['Weak/Vulnerable'])

def use_uppercut(targeted_enemy, using_card, entity):
    '''Deal 10(13) damage. Apply 1(2) Weak. Apply 1(2) Vulnerable.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)
    sleep(1)
    ei.apply_effect(targeted_enemy, entity, 'Weak', using_card['Weak/Vulnerable'])
    ei.apply_effect(targeted_enemy, entity, 'Vulnerable', using_card['Weak/Vulnerable'])

def use_whirlwind(enemies, using_card, entity):
    '''Deal 5(8) damage to ALL enemies X times.'''
    for _ in range(entity.energy):
        for enemy in enemies:
            entity.attack(using_card['Damage'], enemy, using_card)
            sleep(0.5)
        sleep(1)
        view.clear()

def use_barricade(using_card, entity):
    '''Block is not removed at the start of your turn.'''
    _ = using_card
    ei.apply_effect(entity, entity, 'Barricade')

def use_berzerk(using_card, entity):
    '''Gain 2(1) Vulnerable. At the start of your turn, gain 1 Energy.'''
    ei.apply_effect(entity, entity, 'Vulnerable', using_card['Self Vulnerable'])
    ei.apply_effect(entity, entity, 'Berzerk', 1)

def use_bludgeon(targeted_enemy, using_card, entity):
    '''Deal 32(42) damage.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)

def use_brutality(using_card, entity):
    '''At the start of your turn, lose 1 HP and draw 1 card.'''
    _ = using_card
    ei.apply_effect(entity, entity, 'Brutality', 1)

def use_corruption(using_card, entity):
    '''Skills cost 0. Whenever you play a Skill, Exhaust it.'''
    _ = using_card
    ei.apply_effect(entity, entity, "Corruption")

def use_demonform(using_card, entity):
    '''At the start of your turn, gain 2(3) Strength'''
    ei.apply_effect(entity, entity, "Demon Form", using_card['Demon Form'])

def use_doubletap(using_card, entity):
    '''This turn, your next (2) Attack(s) is(are) played twice.'''
    ei.apply_effect(entity, entity, "Double Tap", using_card['Charges'])

def use_exhume(using_card, entity):
    '''Put a card from your exhaust pile into your hand. Exhaust.'''
    _ = using_card
    while True:
        view.view_piles(entity.exhaust_pile, entity)
        option = view.list_input("Choose a card to return to your hand > ", entity.exhaust_pile, view.view_piles)
        if option is None:
            ansiprint('<red>The card you entered is invalid</red>')
            sleep(1.5)
            view.clear()
            continue
        entity.hand.append(entity.exhaust_pile[option])
        del entity.exhaust_pile[option]
        break

def use_bandageup(using_card, entity):
    '''Heal 4(6) HP. Exhaust.'''
    entity.health_actions(4, 'Heal')

def use_feed(targeted_enemy, using_card, entity):
    '''Deal 10(12) damage. If Fatal, raise your Max HP by 3(4). Exhaust.'''
    entity.attack(using_card['Damage'], targeted_enemy, using_card)
    if targeted_enemy.health <= 0 and not targeted_enemy.buffs['Minion']:
        ansiprint(f"You gained {using_card['Max HP']} <keyword>Max HP</keyword>.")
        entity.health_actions(using_card['Max HP'], 'Max Health')

def use_fiendfire(targeted_enemy, using_card, entity):
    '''Exhaust all cards in your hand. Deal 7(10) damage for each card Exhausted. Exhaust.'''
    for card in entity.hand:
        if card != using_card:
            entity.move_card(card=card, move_to=entity.exhaust_pile, from_location=entity.hand, cost_energy=False)
            ansiprint(f"{card['Name']} was <keyword>Exhausted</keyword>.")
            entity.attack(using_card['Damage'], targeted_enemy, using_card)

def use_immolate(enemies, using_card, entity):
    '''Deal 21(28) damage to ALL enemies. Add a Burn to your discard pile.'''
    for enemy in enemies:
        entity.attack(using_card['Damage'], enemy, using_card)
        sleep(0.5)
    entity.discard_pile.append(deepcopy(cards['Burn']))

def use_impervious(using_card, entity):
    '''Gain 30(40) Block. Exhaust.'''
    entity.blocking(using_card['Block'])

def use_juggernaut(using_card, entity):
    '''Whenever you gain Block, deal 5(7) damage to a random enemy.'''
    ei.apply_effect(target=entity, user=entity, effect_name='Juggernaut', amount=using_card['Dmg On Block'])

def use_limitbreak(using_card, entity):
    '''Double your Strength. Exhaust.'''
    _ = using_card
    entity.buffs['Strength'] *= 2
    ansiprint(f"You now have {entity.buffs['Strength']} <buff>Strength</buff>.\n" if entity.buffs['Strength'] > 0 else '', end='')

def use_offering(using_card, entity):
    '''Lose 6 HP. Gain 2 Energy, Draw 3(5) cards. Exhaust.'''
    entity.take_sourceless_dmg(6)
    entity.energy += 2
    ansiprint("You gained 2 <keyword>Energy</keyword>.")
    entity.draw_cards(True, using_card['Cards'])

def use_reaper(enemies, using_card, entity):
    '''Deal 4(5) damage to ALL enemies. Heal HP equal to unblocked damage. Exhaust.'''
    for enemy in enemies:
        entity.attack(using_card['Damage'], enemy, using_card)
        sleep(0.5)
    sleep(1)
    view.clear()

relics: dict[str: dict] = {
    # Starter Relics
    'Burning Blood': {'Name': 'Burning Blood', 'Class': 'Ironclad', 'Rarity': 'Starter', 'Health': 6, 'Info': 'At the end of combat, heal 6 HP', 'Flavor': "Your body's own blood burns with an undying rage."},
    'Ring of the Snake': {'Name': 'Ring of the Snake', 'Class': 'Silent', 'Rarity': 'Starter', 'Cards': 2, 'Info': 'At the start of each combat, draw 2 additional cards.', 'Flavor': 'Made from a fossilized snake, represents great skill as a huntress.'},
    'Cracked Core': {'Name': 'Cracked Core', 'Class': 'Defect', 'Rarity': 'Starter', 'Lightning': 1, 'Info': 'At the start of each combat, <keyword>Channel</keyword> 1 <keyword>Lightning</keyword> orb.', 'Flavor': 'The mysterious life force which powers the Automatons within the Spire. It appears to be cracked.'},
    'Pure Water': {'Name': 'Pure Water', 'Class': 'Watcher', 'Rarity': 'Starter', 'Miracles': 1, 'Card': 'placehold', 'Info': 'At the start of each combat, add 1 <bold>Miracle</bold> card to your hand.', 'Flavor': 'Filtered through fine sand and free of impurities.'},
    # Common Relics
    'Akabeko': {'Name': 'Akabeko', 'Class': 'Any', 'Rarity': 'Common', 'Vigor': 8, 'Info': 'Your first <keyword>Attack</keyword> each combat deals 8 additional damage.', 'Flavor': 'Muuu~'},
    'Anchor': {'Name': 'Anchor', 'Class': 'Any', 'Rarity': 'Common', 'Block': 10, 'Info': 'At the start of combat, gain 10 <keyword>Block</keyword>.', 'Flavor': 'Holding this miniature trinket, your feel heavier and more stable.'},
    'Ancient Tea Set': {'Name': 'Ancient Tea Set', 'Class': 'Any', 'Rarity': 'Common', 'Energy': 2, 'Info': 'Whenever you enter a Rest Site, start the next combat with 2 additional energy.', 'Flavor': "The key to a refreshing night's rest."},
    'Art of War': {'Name': 'Art of War', 'Class': 'Any', 'Rarity': 'Common', 'Energy': 1, 'Info': 'If you do not play <keyword>Attacks</keyword> during your turn, gain an extra <keyword>Energy</keyword> next turn.', 'Flavor': 'The ancient manuscript contains wisdom from a past age.'},
    'Bag of Marbles': {'Name': 'Bag of Marbles', 'Class': 'Any', 'Rarity': 'Common', 'Target': 'Any', 'Vulnerable': 1, 'Info': 'At the start of each combat, apply 1 <debuff>Vulnerable</debuff> to ALL enemies.', 'Flavor': 'A once popular toy in the city. Useful for throwing enemies off balance.'},
    'Bag of Preparation': {'Name': 'Bag of Preparation', 'Class': 'Any', 'Rarity': 'Common', 'Cards': 2, 'Info': 'At the start of each combat, draw 2 additional cards.', 'Flavor': "Oversized adventurer's pack. Has many pockets and straps."},
    'Blood Vial': {'Name': 'Blood Vial', 'Class': 'Any', 'Rarity': 'Common', 'HP': 2, 'Info': 'At the start of each combat, heal 2 HP.', 'Flavor': 'A vial containing the blood of a pure and elder vampire.'},
    'Bronze Scales': {'Name': 'Bronze Scales', 'Class': 'Any', 'Rarity': 'Common', 'Thorns': 3, 'Info': 'Whenever you take damage, deal 3 damage back.', 'Flavor': 'The sharp scales of the Guardian. Rearranges itself to protect its user.'},
    'Centennial Puzzle': {'Name': 'Centennial Puzzle', 'Class': 'Any', 'Rarity': 'Common', 'Cards': 3, 'Info': 'The first time you lose HP each combat, draw 3 cards.', 'Flavor': 'Upon solving the puzzle you feel a powerful warmth in your chest.'},
    'Ceramic Fish': {'Name': 'Ceramic Fish', 'Class': 'Any', 'Rarity': 'Common', 'Gold': 9, 'Info': 'Whenever you add a card to your deck, gain 9 Gold.', 'Flavor': 'Meticulously painted, these fish were revered to bring great fortune.'},
    'Dream Catcher': {'Name': 'Dream Catcher', 'Class': 'Any', 'Rarity': 'Common', 'Info': 'Whenever you rest, you may add a card to your deck.', 'Flavor': 'The northern tribes would often use dream catchers at night, believing they led to entity improvement.'},
    'Happy Flower': {'Name': 'Happy Flower', 'Class': 'Any', 'Rarity': 'Common', 'Energy': 1, 'Info': 'Every 3 turns, gain 1 <keyword>Energy</keyword>.', 'Flavor': 'This unceasing joyous plant is a popular novelty item among nobles.'},
    'Juzu Bracelet': {'Name': 'Juzu Bracelet', 'Class': 'Any', 'Rarity': 'Common', 'Info': 'Regular enemy combats are no longer encountered in <bold>?</bold> rooms.', 'Flavor': 'A ward against the unknown.'},
    'Lantern': {'Name': 'Lantern', 'Class': 'Any', 'Rarity': 'Common', 'Energy': 1, 'Info': 'Gain 1 <keyword>Energy</keyword> on the first turn of each combat.', 'Flavor': 'An eerie lantern which illuminates only for the user.'},
    'Max Bank': {'Name': 'Maw Bank', 'Class': 'Any', 'Rarity': 'Common', 'Gold': 12, 'Info': 'Whenever you climb a floor, gain 12 Gold. No longer works when you spend any gold at the shop.', 'Flavor': 'Suprisingly popular, despite maw attacks being a common occurence.'},
    'Meal Ticket': {'Name': 'Meal Ticket', 'Class': 'Any', 'Rarity': 'Common', 'Health': 15, 'Info': 'Whenever you enter a shop, heal 15 HP.', 'Flavor': 'Complementary meatballs with every visit!'},
    'Nunchaku': {'Name': 'Nunchaku', 'Class': 'Any', 'Rarity': 'Common', 'Energy': 1, 'Info': 'Every time you play 10 <keyword>Attacks</keyword>, gain 1 <keyword>Energy</keyword>', 'Flavor': 'A good training tool. Inproves the posture and agility of the user.'},
    'Oddly Smooth Stone': {'Name': 'Oddly Smooth Stone', 'Class': 'Any', 'Rarity': 'Common', 'Dexterity': 1, 'Info': 'At the start of each combat, gain 1 <buff>Dexterity</buff>.', 'Flavor': 'You have never seen smething so smooth and pristine. This must be the work of the Ancients.'},
    'Omamori': {'Name': 'Omamori', 'Class': 'Any', 'Rarity': 'Common', 'Curses': 2, 'Info': 'Negate the next 2 <keyword>Curses</keyword> you obtain.', 'Flavor': 'A common charm for staving off vile spirits. This one seems to possess a spark of divine energy.'},
    'Orichaicum': {'Name': 'Orichaicum', 'Class': 'Any', 'Rarity': 'Common', 'Block': 6, 'Info': 'If you end your turn without <keyword>Block</keyword>, gain 6 <keyword>Block</keyword>.', 'Flavor': 'A green tinted metal from an unknown origin.'},
    'Pen Nib': {'Name': 'Pen Nib', 'Class': 'Any', 'Rarity': 'Common', 'Attacks': 10, 'Info': 'Every 10th <keyword>Attack</keyword> you play deals double damage.', 'Flavor': 'Holding the nib, you can see everyone ever slain by a previous owner of the pen. A violent history.'},
    'Potion Belt': {'Name': 'Potion Belt', "Class": 'Any', 'Rarity': 'Common', 'Potion Slots': 2, 'Info': 'Upon pickup, gain 2 potion slots.', 'Flavor': 'I can hold more potions using this belt!'},
    'Preserved Insect': {'Name': 'Preserved Insect', 'Class': 'Any', 'Rarity': 'Common', 'Hp Percent Loss': 25, 'Info': 'Enemies in <bold>Elite</bold> rooms have 20% less health.', 'Flavor': 'The insect seems to create a shrinking aura that targets particularly large enemies.'},
    'Regal Pillow': {'Name': 'Regal Pillow', 'Class': 'Any', 'Rarity': 'Common', 'Heal HP': 15, 'Info': 'Heal an additional 15 HP when you Rest.', 'Flavor': "Now you can get a proper night's rest."},
    'Smiling Mask': {'Name': 'Smiling Mask', 'Class': 'Any', 'Rarity': 'Common', 'Info': "The merchant's card removal service now always costs 50 Gold.", 'Flavor': 'Mask worn by the merchant. He must have spares...'},
    'Strawberry': {'Name': 'Strawberry', 'Class': 'Any', 'Rarity': 'Common', 'Max HP': 7, 'Info': "Upon pickup, raise your Max HP by 7.", 'Flavor': "'Delicious! Haven't seen any of these since the blight.' - Ranwid"},
    'The Boot': {'Name': 'The Boot', 'Class': 'Any', 'Rarity': 'Common', 'Info': 'When you would deal 4 or less unblocked <keyword>Attack</keyword> damage, increase it to 5.', 'Flavor': 'When wound up, the boot grows larger in size.'},
    'Tiny Chest': {'Name': 'Tiny Chest', 'Class': 'Any', 'Rarity': 'Common', 'Info': 'Every 4th <bold>?</bold> room is a <bold>Treasure</bold> room.', 'Flavor': '"A fine prototype." - The Architect'},
    # Class specific common relics
    'Red Skull': {'Name': 'Red Skull', 'Class': 'Ironclad', 'Rarity': 'Common', 'Info': 'While your HP is at or below 50%, you have 3 additional <buff>Strength</buff>.', 'Flavor': 'A small skull covered in ornamental paint.'},
    'Snecko Skull': {'Name': 'Snecko Skull', 'Class': 'Silent', 'Rarity': 'Common', 'Info': 'Whenever you apply <debuff>Poison</debuff>, apply an additional 1 <debuff>Poison</debuff>', 'Flavor': 'A snecko skull in pristine condition. Mysteriously clean and smooth, dirt and grime fall off inexplicably.'},
    'Data Disk': {'Name': 'Data Disk', 'Class': 'Defect', 'Rarity': 'Common', 'Info': 'Start each combat with 1 <buff>Focus</buff>.', 'Flavor': 'This dish contains precious data on birds and snakes.'},
    'Damaru': {'Name': 'Damaru', 'Class': 'Watcher', 'Rarity': 'Common', 'Info': 'At the start of your turn, gain 1 <buff>Mantra</buff>.', 'Flavor': 'The sound of the small drum keeps your mind awake, revealing a path forward.'},
    # Uncommon relics
    'Blue Candle': {'Name': 'Blue Candle', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': '<keyword>Curse</keyword> cards can now be played. Playing a <keyword>Curse</keyword> will make you lose 1 HP and <keyword>Exhaust</keyword> the card.', 'Flavor': 'The flame ignites when shrouded in darkness.'},
    'Bottled Flame': {'Name': 'Bottled Flame', 'Class': 'Any', 'Rarity': 'Uncommon', 'Card Type': 'Attack', 'Info': 'Upon pickup, choose an <keyword>Attack</keyword> card. At the start of your turn, this card will be in your hand.', 'Flavor': 'Inside the bottle resides a flame which eternally burns.'},
    'Bottled Lightning': {'Name': 'Bottled Lightning', 'Class': 'Any', 'Rarity': 'Uncommon', 'Card Type': 'Skill', 'Info': 'Upon pickup, choose an <keyword>Skill</keyword> card. At the start of your turn, this card will be in your hand.', 'Flavor': 'Peering into the swirling maelstrom, you see a part of yourself staring back.'},
    'Bottled Tornado': {'Name': 'Bottled Tornado', 'Class': 'Any', 'Rarity': 'Uncommon', 'Card Type': 'Power', 'Info': 'Upon pickup, choose an <keyword>Power</keyword> card. At the start of your turn, this card will be in your hand.', 'Flavor': 'The bottle gently hums and whirs.'},
    'Darkstone Periapt': {'Name': 'Darkstone Periapt', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Whenever you obtain a <keyword>Curse</keyword>, raise your Max HP by 6.', 'Flavor': 'The stone draws power from dark energy, converting it into vitality for the user.'},
    'Eternal Feather': {'Name': 'Eternal Feather', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'For every 5 cards in your deck, heal 3 HP when you enter a rest site.', 'Flavor': 'This feather appears to be completely indestructible. What bird does this possibly come from?'},
    'Molten Egg': {'Name': 'Molten Egg', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Whenever you add an <keyword>Attack</keyword> card to your deck, it is <keyword>Upgraded</keyword>. ', 'Flavor': 'The egg of a Pheonix. It glows red hot with a simmering lava.'},
    'Toxic Egg': {'Name': 'Toxic Egg', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Whenever you add a <keyword>Skill</keyword> card to your deck, it is <keyword>Upgraded</keyword>. ', 'Flavor': '"What a marvelous discovery! This appears to be the inert egg of some magical creature. Who or what created this?" - Ranwid'},
    'Frozen Egg': {'Name': 'Frozen Egg', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Whenever you add a <keyword>Power</keyword> card to your deck, it is <keyword>Upgraded</keyword>. ', 'Flavor': 'The egg lies inert and frozen, never to hatch'},
    'Gremlin Horn': {'Name': 'Gremlin Horn', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Whenever an enemy dies, gain 1 <keyword>Energy</keyword> and draw 1 card.', 'Flavor': '"Gremlin Nobs are capable of growing until the day they die. Remarkable." - Ranwid'},
    'Horn Cleat': {'Name': 'Horn Cleat', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'At the start of your 2nd trun, gain 14 <keyword>Block</keyword>.', 'Flavor': 'Pleasant to hold in the hand. What was it for?'},
    'Ink Bottle': {'Name': 'Ink Bottle', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Whenever you play 10 cards, draw 1 card.', 'Flavor': 'Once exhausted, it appears to refil itself in a different color.'},
    'Kunai': {'Name': 'Kunai', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Every time you play 3 <keyword>Attacks</keyword> in a single turn, gain 1 <buff>Dexterity</buff>.', 'Flavor': 'A blade favored by assasins for its lethality at range.'},
    'Letter Opener': {'Name': 'Letter Opener', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Every time you play 3 <keyword>Skills</keyword> in a single turn, deal 5 damage to ALL enemies.', 'Flavor': 'Unnaturally sharp.'},
    'Matryoshka': {'Name': 'Matryoshka', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'The next 2 non-boss chests you open contain 2 relics.', 'Flavor': 'A stackable set of dolls. The paint depicts an unknown bird with white eyes and blue feathers.'},
    'Meat on the Bone': {'Name': 'Meat on the Bone', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'If your HP is at 50% or lower at the end of combat, heal 12 HP.', 'Flavor': 'The meat keeps replenishing, never seeming to fully run out.' },
    'Mercury Hourglass': {'Name': 'Mercury Hourglass', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'At the start of your turn, deal 3 damage to ALL enemies.', 'Flavor': 'An enchanted hourglass that endlessly drips.'},
    'Mummified Hand': {'Name': 'Mummified Hand', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Whenever you play a <keyword>Power</keyword> card, a random card in your hand costs 0 that turn.', 'Flavor': 'Frequently twitches, especially when your pulse is high.'},
    'Ornamental Fan': {'Name': 'Ornamental Fan', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Every time you play 3 <keyword>Attacks</keyword> in a single turn, gain 4 <keyword>Block</keyword>.', 'Flavor': 'The fan seems to extend and harden as blood is spilled.'},
    'Pantograph': {'Name': 'Pantograph', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'At the start of boss combats, heal 25 HP.', 'Flavor': '"Solid foundations are not accidental. Tools for planning are a must." - The Architect'},
    'Pear': {'Name': 'Pear', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Raise your Max HP by 10', 'Flavor': 'A common fruit before the Spireblight.'},
    'Question Card': {'Name': 'Question Card', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Future card rewards have 1 additional card to choose from.', 'Flavor': '"Those with more choices minimize the downside to chaos." - Kublai the Great'},
    'Shuriken': {'Name': 'Shuriken', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Every time you play 3 <keyword>Attacks</keyword> in a single turn, gain 1 <buff>Strength</buff>.', 'Flavor': 'Lightweight throwing weapons. Recommend going for the eyes.'},
    'Singing Bowl': {'Name': 'Singing Bowl', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'When adding cards to your deck, you may gain +2 Max HP instead.', 'Flavor': 'This well-used artifact rings out a beautiful melody when struck.'},
    'Strike Dummy': {'Name': 'Strike Dummy', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': "Cards containing <italic>'Strike'</italic> deal 3 additional damage.", 'Flavor': "It's beat up."},
    'Sundial': {'Name': 'Sundial', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Every 3 times you shuffle your draw pile, gain 2 <keyword>Energy</keyword>.', 'Flavor': "'Early man's foolish obsession with time caused them to look to the sky for guidance, hoping for something permanent.' - Zoroth"},
    'The Courier': {'Name': 'The Courier', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'The merchant never runs out of cards, relics, or potions and his prices are reduced by 20%.', 'Flavor': "The merchant's personal pet!"},
    'White Beast Statue': {'Name': 'White Beast Statue', 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Potions always drop after combat.', 'Flavor': 'A small white statue of a creature you have never seen before.'},
    # Class specific uncommon relics
    'Paper Phrog': {'Name': 'Paper Phrog', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Info': 'Enemies with <debuff>Vulnerable</debuff> take 75% more damage rather than 50%.', 'Flavor': 'The paper continuously folds and unfolds into the shape of a small creature.'},
    'Self-Forming Clay': {'Name': 'Self-Forming Clay', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Info': 'Whenever you lose HP in combat, gain 4 <keyword>Block</keyword> next turn.', 'Flavor': '“Most curious! It appears to form itself loosely on my thoughts! Tele-clay?” - Ranwid'},
    'Ninja Scroll': {'Name': 'Ninja Scroll', 'Class': 'Silent', 'Rarity': 'Uncommon', 'Info': 'Start each combat with 3 <bold>Shivs</bold> in hand.', 'Flavor': 'Contains the secrets of assasination.'},
    'Paper Krane': {'Name': 'Paper Krane', 'Class': 'Silent', 'Rarity': 'Uncommon', 'Info': 'Enemies with <debuff>Weak</debuff> deal 40% less damage rather than 25%.', 'Flavor': 'An origami of a creature of a past age.'},
    'Gold-Plated Cables': {'Name': 'Gold-Plated Cables', 'Class': 'Defect', 'Rarity': 'Uncommon', 'Info': 'Your rightmost <keyword>Orb</keyword> triggers its passive an additional time.', 'Flavor': '"Interesting! Even automatons are affected by placebo." - Ranwid'},
    'Symbiotic Virus': {'Name': 'Symbiotic Virus', 'Class': 'Defect', 'Rarity': 'Uncommon', 'Info': 'At the start of each combat, Channel 1 <keyword>Dark</keyword> orb.', 'Flavor': 'A little bit of bad can do a lot of good.'},
    'Duality': {'Name': 'Duality', 'Class': 'Watcher', 'Rarity': 'Uncommon', 'Info': 'Whenever you play an <keyword>Attack</keyword>, gain 1 <buff>Dexterity</buff>.', 'Flavor': '“And the sun was extinguished forever, as if curtains fell before it.” - Zoroth'},
    'Teardrop Locket': {'Name': 'Teardrop Locket', 'Class': 'Watcher', 'Rarity': 'Uncommon', 'Info': 'Start each combat in <keyword>Calm</keyword>.', 'Flavor': 'Its owner blind, its contents unseen.'},
    # Rare relics
    'Bird-Faced Urn': {'Name': 'Bird-Faced Urn', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'Whenever you play a <keyword>Power</keyword> card, heal 2 HP.', 'Flavor': 'The urn shows the crow god Mazaleth looking mischievous.'},
    'Calipers': {'Name': 'Calipers', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'At the start of your turn, lose 15 <keyword>Block</keyword> rather than all of your <keyword>Block</keyword>.', 'Flavor': '"Mechanical precision leads to greatness." - The Architect'},
    "Captain's Wheel": {'Name': "Captain's Wheel", 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'At the start of your 3rd turn, gain 18 <keyword>Block</keyword>.', 'Flavor': 'A wooden trinked carved with delicate precision. A name is carved into it but the language is foreign.'},
    'Dead Branch': {'Name': 'Dead Branch', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'Whenever you <keyword>Exhaust</keyword> a card, add a random card into your hand.', 'Flavor': 'The branch of a tree from a forgotten era.'},
    'Du-Vu Doll': {'Name': 'Du-Vu Doll', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'For each <keyword>Curse</keyword> in your deck, start each comabt with 1 additional <buff>Strength</buff>.', 'Flavor': 'A doll devised to gain strength from malicious energy.'},
    'Fossilized Helix': {'Name': 'Fossilized Helix', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'Prevent the first time you would lose HP in combat.', 'Flavor': 'Seemingly indestrutible, you wonder what kind of creature this belonged to.'},
    'Gambling Chip': {'Name': 'Gambling Chip', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'At the start of each combat, discard any number of cards then draw that many.', 'Flavor': "You see a small inscription on one side. It reads: 'Bear's Lucky Chip!''"},
    'Ginger': {'Name': 'Ginger', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'You can no longer become <debuff>Weakened</debuff>.', 'Flavor': 'A potent tool in many tonics.'},
    'Girya': {'Name': 'Girya', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'You can now gain <buff>Strength</buff> at <keyword>Rest Sites</keyword>. (3 times max)', 'Flavor': 'This Girya is unfathomably heavy. You could train with this to get significantly stronger.'},
    'Ice Cream': {'Name': 'Ice Cream', 'Class': 'Any', 'Rarity': 'Rare', 'Info': '<keyword>Energy</keyword> is now conserved between turns.', 'Flavor': 'Delicious!'},
    'Incense Burner': {'Name': 'Incense Burner', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'Every 6 turns, gain 1 <buff>Intangible</buff>', 'Flavor': 'The smoke imbues the owner with the spirit of the burned.'},
    'Lizard Tail': {'Name': 'Lizard Tail', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'When you would die, heal to 50% of your Max HP instead. (Works once)', 'Flavor': 'A fake tail to trick enemies during combat.'},
    'Mango': {'Name': 'Mango', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'Raise your Max HP by 14.', 'Flavor': 'The most coveted forgotten fruit. Impeccably preserved with no signs of Spireblight.'},
    'Old Coin': {'Name': 'Old Coin', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'Gain 300 Gold.', 'Flavor': 'Unique coins are highly valued for their historical value and rare mettalic composition.'},
    'Peace Pipe': {'Name': 'Peace Pipe', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'You can now remove cards from your deck at Rest Sites.', 'Flavor': 'Clears the mind and cleanses the soul.'},
    'Pocketwatch': {'Name': 'Pocketwatch', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'Whenever you play 3 or less cards during your turn, draw 3 additional cards next turn.', 'Flavor': "The hands seem stuck on the 3 o'clock position."},
    'Prayer Wheel': {'Name': 'Prayer Wheel', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'Normal enemies drop an additional card reward.', 'Flavor': 'The wheel continues to spin, never stopping.'},
    'Shovel': {'Name': 'Shovel', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'You can now Dig for loot at Rest Sites.', 'Flavor': 'The Spire houses all number of relics from past civilizations and powerful adventurers lost to time. Time to go dig them up!'},
    'Stone Calender': {'Name': 'Stone Calender', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'At the end of turn 7, deal 52 damage to ALL enemies.', 'Flavor': 'The passage of time is imperceptible in the Spire.'},
    'Thread and Needle': {'Name': 'Thread and Needle', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'At the start of each combat, gain 4 <buff>Plated Armor</buff>.', 'Flavor': 'Wrapping the magical thread around your body, you feel harder to the touch.'},
    'Torii': {'Name': 'Torii', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'Whenever you would recieve 5 or less unblocked attack damage, reduce it to 1.', 'Flavor': 'Holding the small Torii, you feel a sense of calm and safety drift through your mind.'},
    'Tungsten Rod': {'Name': 'Tungsten Rod', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'When you would lose HP, lose 1 less.', 'Flavor': "It's very very heavy."},
    'Turnip': {'Name': 'Turnip', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'You can no longer become <debuff>Frail</debuff>.', 'Flavor': 'Best with Ginger.'},
    'Unceasing Top': {'Name': 'Unceasing Top', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'When you have no cards in your hand during your turn, draw 1 card.', 'Flavor': 'The top continues to spin effortlessly as if your were in a dream.'},
    'Wing Boots': {'Name': 'Wing Boots', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'You may ignore paths when choosing the next room to travel to up to 3 times.', 'Flavor': 'Stylish.'},
    # Class specific rare relics
    'Champion Belt': {'Name': 'Champion Belt', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Info': 'Whenever you apply <debuff>Vulnerable</debuff>, also apply 1 <debuff>Weak</debuff>.', 'Flavor': 'Only the greatest may wear this belt.'},
    "Charon's Ashes": {'Name': "Charon's Ashes", 'Class': 'Ironclad', 'Rarity': 'Rare', 'Info': 'Whenever you <keyword>Exhaust</keyword> a card, deal 3 damage to ALL enemies.', 'Flavor': 'Charon was said to be the god of rebirth, eternally dying and reviving in a burst of flame.'},
    'Magic Flower': {'Name': 'Magic Flower', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Info': 'Healing is 50% more effective during combat.', 'Flavor': 'A flower long thought extinct, somehow preserved in perfect condition.'},
    'The Specimen': {'Name': 'The Specimen', 'Class': 'Silent', 'Rarity': 'Rare', 'Info': 'Whenever an enemy dies, transfer any <debuff>Poison</debuff> it had to random enemy.', 'Flavor': '"Fascinating! I found a mutated creature demonstrating astounding toxic properties. Storing a sample for later examination." - Ranwid'},
    'Tingsha': {'Name': 'Tingsha', 'Class': 'Silent', 'Rarity': 'Rare', 'Info': 'Whenever you discard a card during your turn, deal 3 damage to random enemy for each card discarded.', 'Flavor': 'The sound this instrument generates appears to be capable of reverberating to painful levels of volume.'},
    'Tough Bandages': {'Name': 'Tough Bandages', 'Class': 'Silent', 'Rarity': 'Rare', 'Info': 'Whenever you discard a card during your turn, gain 3 <keyword>Block</keyword>.', 'Flavor': 'Loss gives strength.'},
    'Emotion Chip': {'Name': 'Emotion Chip', 'Class': 'Defect', 'Rarity': 'Rare', 'Info': 'If you lost HP during your previous turn, trigger the passive ability of ALL <keyword>Orbs</keyword> at the start of your next turn.', 'Flavor': '...<3...?'},
    'Cloak Clasp': {'Name': 'Cloak Clasp', 'Class': 'Watcher', 'Rarity': 'Rare', 'Info': 'At the end of your turn, gain 1 <keyword>Block</keyword> for each card in your hand.', 'Flavor': 'A simple but sturdy design.'},
    'Golden Eye': {'Name': 'Golden Eye', 'Class': 'Watcher', 'Rarity': 'Rare', 'Info': 'Whenever you <keyword>Scry</keyword>, <keyword>Scry</keyword> 2 additional cards.', 'Flavor': 'See into the minds of those nearby, predicting their future moves.'},
    # Shop relics
    'Cauldron': {'Name': 'Cauldron', 'Class': 'Any', 'Rarity': 'Shop', 'Info': 'When obtained, brews 5 random potions.', 'Flavor': 'The merchant is actually a rather skilled ption brewer. Buy 4 get 1 free.'},
    'Chemical X': {'Name': 'Chemical X', 'Class': 'Any', 'Rarity': 'Shop', 'Info': 'Whenever you play an X cost card, its effects are increased by 2.', 'Flavor': 'WARNING: Do not combine with sugar, spice, and everything nice.'},
    'Clockwork Souvenir': {'Name': 'Clockwork Souvenir', 'Class': 'Any', 'Rarity': 'Shop', 'Info': 'At the start of each combat, gain 1 <buff>Artifact</buff>.', 'Flavor': 'So many intricate gears.'},
    'Dolly Mirror': {'Name': 'Dolly Mirror', 'Class': 'Any', 'Rarity': 'Shop', 'Info': 'Upon pick up, obtain an additional copy of a card in your deck.', 'Flavor': 'I look funny in this.'},
    'Frozen Eye': {'Name': 'Frozen Eye', 'Class': 'Any', 'Rarity': 'Shop', 'Info': 'When viewing your draw pile, the cards are now shown in order.', 'Flavor': 'Staring into the eye, you see a glimpse of your future.'},
    'Hand Drill': {'Name': 'Hand Drill', 'Class': 'Any', 'Rarity': 'Shop', 'Info': "Whenever you break an enemy's <keyword>Block</keyword>, apply 2 <debuff>Vulnerable</debuff>.", 'Flavor': 'Spirals are dangerous.'},
    "Lee's Waffle": {'Name': "Lee's Waffle", 'Class': 'Any', 'Rarity': 'Shop', 'Info': 'Raise your Max HP by 7 and heal all of your HP.', 'Flavor': '"Tastiest treat you will find in all the Spire! Baked today just for you."'},
    'Medical Kit': {'Name': 'Medical Kit', 'Class': 'Any', 'Rarity': 'Shop', 'Info': '<status>Status</status> cards can now be played. Playing a <status>Status</status> will <keyword>Exhaust</keyword> the card.', 'Flavor': '"Has everything you need! Anti-itch, anti-burn, anti-venom, and more!"'},
    'Membership Card': {'Name': 'Membership Card', 'Class': 'Any', 'Rarity': 'Shop', 'Info': '50% discout on all products!', 'Flavor': '"Bonus membership option for my most valuable customers!"'},
    'Orange Pellets': {'Name': 'Orange Pellets', 'Class': 'Any', 'Rarity': 'Shop', 'Info': 'Whenever you play a <keyword>Power</keyword>, <keyword>Attack</keyword>, and <keyword>Skill</keyword> in the same turn, remove ALL of your debuffs.', 'Flavor': 'Made from various fungi found throughout the Spire, they will stave off any affliction.'},
    'Orrery': {'Name': 'Orrery', 'Class': 'Any', 'Rarity': 'Shop', 'Info': 'Choose and add 5 to your deck.', 'Flavor': '"Once you understand the universe..." - Zoroth'},
    'Prismatic Shard': {'Name': 'Prismatic Shard', 'Class': 'Any', 'Rarity': 'Shop', 'Info': 'Combat reward screens now contain colorless cards and cards from other colors.', 'Flavor': 'Looking through the shard, you are able to see entirely new perspectives.'},
    'Sling of Courage': {'Name': 'Sling of Courage', 'Class': 'Any', 'Rarity': 'Shop', 'Info': 'Start each <keyword>Elite</keyword> combat with 2 <buff>Strength</buff>.', 'Flavor': 'A handy tool for dealing with particalarly tough opponents.'},
    'Strange Spoon': {'Name': 'Strange Spoon', 'Class': 'Any', 'Rarity': 'Shop', 'Info': 'Cards that <keyword>Exhaust</keyword> will instead discard 50% of the time.', 'Flavor': 'Staring at the spoon, it appears to bend and twist around before your eyes.'},
    'The Abacus': {'Name': 'The Abacus', 'Class': 'Any', 'Rarity': 'Shop', 'Info': 'Gain 6 <keyword>Block</keyword> when you shuffle your draw pile.', 'Flavor': 'One...Two...Three...'},
    'Toolbox': {'Name': 'Toolbox', 'Class': 'Any', 'Rarity': 'Shop', 'Info': 'At the start of each combat, choose 1 of 3 Colorless cards to add to your hand.', 'Flavor': 'A tool for every job.'},
    # Class specific shop relics
    'Brimstone': {'Name': 'Brimstone', 'Class': 'Ironclad', 'Rarity': 'Shop', 'Info': 'At the start of your turn, gain 2 <buff>Strength</buff> and ALL enemies gain 1 <buff>Strength</buff>.', 'Flavor': 'Emanates an infernal heat.'},
    'Twisted Funnel': {'Name': 'Twisted Funnel', 'Class': 'Silent', 'Rarity': 'Shop', 'Info': 'At the start of each combat, apply 4 <debuff>Poison</debuff> to ALL enemies.', 'Flavor': "I wouldn't drink out of it."},
    'Runic Capacitor': {'Name': 'Runic Capacitor', 'Class': 'Defect', 'Rarity': 'Shop', 'Info': 'Start each combat with 3 additional <keyword>Orb</keyword> slots.', 'Flavor': 'More is better.'},
    'Melange': {'Name': 'Melange', 'Class': 'Watcher', 'Rarity': 'Shop', 'Info': 'Whenever you shuffle your draw pile, <keyword>Scry</keyword> 3.', 'Flavor': 'Mysterious sands from an unknown origin, smells of cinnamon.'},
    # Boss relics
    'Astrolabe': {'Name': 'Astrolabe', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Upon pickup, choose and <keyword>Transform</keyword> 3 cards, then <keyword>Upgrade</keyword> them.', 'Flavor': 'A tool to glean inavluable knowledge from the stars.'},
    'Black Star': {'Name': 'Black Star', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Elites now drop 2 relics when defeated.', 'Flavor': 'Originally discovered in the town of the serpent, aside a solitary candle.'},
    'Busted Crown': {'Name': 'Busted Crown', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Gain 1 <keyword>Energy</keyword> at the start of each turn. On card reward screens, you have 2 less cards to choose from.', 'Flavor': "The Champ's crown... or a pale imitation?"},
    'Calling Bell': {'Name': 'Calling Bell', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Obtain a special <keyword>Curse</keyword> and 3 relics.', 'Flavor': 'The dark iron bell rang 3 times when you found it, but now it remains silent.'},
    'Coffee Dripper': {'Name': 'Coffee Dripper', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Gain 1 <keyword>Energy</keyword> at the start of each turn. You can no longer Rest at Rest Sites.', 'Flavor': '"Yes, another cup please. Back to work. Back to work!" - The Architect'},
    'Cursed Key': {'Name': 'Cursed Key', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Gain 1 <keyword>Energy</keyword> at the start of each turn. Whenever you open a non-boss chest, obtain 1 <keyword>Curse</keyword>.', 'Flavor': 'You can feel the malicious energy emanating from the key. Power comes at a price.'},
    'Ectoplasm': {'Name': 'Ectoplasm', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Gain 1 <keyword>Energy</keyword> at the start of each turn. You can no longer obtain Gold.', 'Flavor': 'This blob of slime and energy seems to pulse with life.'},
    'Empty Cage': {'Name': 'Empty Cage', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Upon pickup, remove 2 cards from your deck.', 'Flavor': '"How unusual to cage that which you worship." - Ranwid'},
    'Fusion Hammer': {'Name': 'Fusion Hammer', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Gain 1 <keyword>Energy</keyword> at the start of each turn. You can no longer Smith at <keyword>Rest Sites</keyword>.', 'Flavor': 'Once wielded, the owner can never let go.'},
    "Pandora's Box": {'Name': "Pandora's Box", 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Transform all Strikes and Defends.', 'Flavor': 'You have a bad feeling about opening this.'},
    "Philosopher's Stone": {'Name': "Philosopher's Stone", 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Gain 1 <keyword>Energy</keyword> at the start of each turn. ALL enemies start with 1 <keyword>Strength</keyword>.', 'Flavor': 'Raw energy emanates from the stone, empowering all nearby.'},
    'Runic Dome': {'Name': 'Runic Dome', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Gain 1 <keyword>Energy</keyword> at the start of each turn. You can no longer see enemy intents.', 'Flavor': 'The runes are indecipherable.'},
    'Runic Pyramid': {'Name': 'Runic Pyramid', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'At the end of your turn, you no longer discard your hand.', 'Flavor': 'The runes are indecipherable.'},
    'Sacred Bark': {'Name': 'Sacred Bark', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Double the effectiveness of potions.', 'Flavor': 'A bark rumered to originate from the World Tree.'},
    "Slaver's Collar": {'Name': "Slaver's Collar", 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'During Boss and Elite encounters, gain 1 <keyword>Energy</keyword> at the start of each turn.', 'Flavor': 'Rusty miserable chains.'},
    'Snecko Eye': {'Name': 'Snecko Eye', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Draw 2 additonal cards each turn. You start each combat <debuff>Confused</debuff>.', 'Flavor': 'The eye of a fallen snecko. Much larger than you imagined.'},
    'Sozu': {'Name': 'Sozu', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Gain 1 <keyword>Energy</keyword> at the start of each turn. You can no longer obtain potions.', 'Flavor': 'You notice that magical liquids seem to lose their properties when near this relic.'},
    'Tiny House': {'Name': 'Tiny House', 'Class': 'Any', 'Rarity': 'Boss', 'Info': 'Obtain 1 potion. Gain 50 Gold<. Raise your Max HP by 5. Obtain 1 card. <keyword>Upgrade</keyword> 1 card.', 'Flavor': '"A near-perfect implementation of miniaturization. My finest work to date, but still not adequate." - The Architect'},
    'Velvet Choker': {'Name': 'Velvet Choker', 'Class': 'Any', 'Rarity': 'Boss', 'Info': "Gain 1 <keyword>Energy</keyword> at the start of each turn. You can't play more than 6 cards per turn.", 'Flavor': '"Immense power, but too limited." - Kublai the Great'},
    # Class specific boss relics
    'Black Blood': {'Name': 'Black Blood', 'Class': 'Ironclad', 'Rarity': 'Boss', 'Info': 'Replaces <bold>Burning Blood</bold>. At the end of each combat, heal 12 HP.', 'Flavor': 'The rage grows darker.'},
    'Mark of Pain': {'Name': 'Mark of Pain', 'Class': 'Ironclad', 'Rarity': 'Boss', 'Info': 'Gain 1 <keyword>Energy</keyword> at the start of each turn. Start combat with 2 <keyword>Wounds</keyword> in your draw pile.', 'Flavor': 'This brand was used by the northern tribes to signify warriors who had mastered pain in battle.'},
    'Runic Cube': {'Name': 'Runic Cube', 'Class': 'Ironclad', 'Rarity': 'Boss', 'Info': 'Whenever you lose HP, draw 1 card.', 'Flavor': 'The runes are indecipherable.'},
    'Ring of the Serpent': {'Name': 'Ring of the Serpent', 'Class': 'Silent', 'Rarity': 'Boss', 'Info': 'Replaces <bold>Ring of the Snake</bold>. At the start of each turn, draw 1 additional card.', 'Flavor': 'Your ring has morphed and changed forms.'},
    'Wrist Blade': {'Name': 'Wrist Blade', 'Class': 'Silent', 'Rarity': 'Boss', 'Info': 'Attacks that cost 0 deal 4 additional damage.', 'Flavor': 'Handy for assasinations.'},
    'Hovering Kite': {'Name': 'Hovering Kite', 'Class': 'Silent', 'Rarity': 'Boss', 'Info': 'The first time you discard a card each turn, gain 1 <keyword>Energy</keyword>.', 'Flavor': 'The Kite floats around you in battle, propelled by a mysterious force.'},
    'Frozen Core': {'Name': 'Frozen Core', 'Class': 'Defect', 'Rarity': 'Boss', 'Info': 'Replaces <bold>Cracked Core</bold>. If you end your turn with empty orb slots, Channel 1 <keyword>Frost</keyword> orb.', 'Flavor': 'The crack in your core has been filled with a pulsating cold energy.'},
    'Inserter': {'Name': 'Inserter', 'Class': 'Defect', 'Rarity': 'Boss', 'Info': 'Every 2 turns, gain 1 <keyword>Orb</keyword> slot.', 'Flavor': 'Push. Pull. Stack. Repeat.'},
    'Nuclear Battery': {'Name': 'Nuclear Battery', 'Class': 'Defect', 'Rarity': 'Boss', 'Info': 'At the start of each combat, <keyword>Channel</keyword> 1 <keyword>Plasma</keyword> orb.', 'Flavor': 'Ooooh...'},
    'Holy Water': {'Name': 'Holy Water', 'Class': 'Watcher', 'Rarity': 'Boss', 'Info': 'Replaces <bold>Pure Water</bold>. At the start of combat, add 3 Miracle cards to your hand.', 'Flavor': 'Collected from a time before the Spire.'},
    'Violet Lotus': {'Name': 'Violet Lotus', 'Class': 'Watcher', 'Rarity': 'Boss', 'Info': 'Whenever you exit <keyword>Calm</keyword>, gain an additional <keyword>Energy</keyword>.', 'Flavor': 'The old texts describe that the surface of “mana pools” were littered with these flowers.'},
    # Event relics
    'Bloody Idol': {'Name': 'Bloody Idol', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Forgotten Altar', 'Info': 'Whenever you gain Gold, heal 5 HP.', 'Flavor': 'The idol now weeps a constant stream of blood.'},
    'Cultist Headpiece': {'Name': 'Cultist Headpiece', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Face Trader', 'Info': 'You feel more talkative. CAW! CAAAW', 'Flavor': 'Part of the Flock!'},
    'Enchiridion': {'Name': 'Enchiridion', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Cursed Tome', 'Info': 'At the start of each combat, add a random <keyword>Power</keyword> card to your hand. It costs 0 until the end of your turn.', 'Flavor': 'The legendary journal of an ancient lich.'},
    'Face of Cleric': {'Name': 'Face of Cleric', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Face Trader', 'Info': 'Raise your Max HP by 1 after each combat', 'Flavor': 'Everybody loves Cleric.'},
    'Golden Idol': {'Name': 'Golden Idol', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Golden Idol', 'Info': 'Enemies drop 25% more Gold.', 'Flavor': 'Made of solid gold, you feel richer just holding it.'},
    'Gremlin Visage': {'Name': 'Gremlin Visage', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Face Trader', 'Info': 'Start each combat with 1 <debuff>Weak</debuff>.', 'Flavor': 'Time to run.'},
    'Mark of the Bloom': {'Name': 'Mark of the Bloom', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Mind Bloom', 'Info': 'You can no longer heal.', 'Flavor': 'In the Beyond, thoughts and reality are one.'},
    'Mutagenic Strength': {'Name': 'Mutagenic Strength', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Augmenter', 'Info': 'Start each comabat with 3 <buff>Strength</buff> that is lost at the end of your turn.', 'Flavor': '"The results seem fleeting, triggering when the subject is in danger." - Unknown'},
    "N'loth's Gift": {'Name': "N'loth's Gift", 'Class': 'Any', 'Rarity': 'Event', 'Source': "N'loth", 'Info': 'The next non-boss chest you open is empty.', 'Flavor': "The strange gift from N'loth. Whenever you try and unwrap it, another wrapped box of the same size lies within."},
    "N'loth's Hungry Face": {'Name': "N'loth's Hungry Face", 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Face Trader', 'Info': 'The next non-boss chest you open is empty.', 'Flavor': 'You feel hungry.'},
    'Necronomicon': {'Name': 'Necronomicon', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Necronomicon', 'Info': 'The first <keyword>Attack</keyword> played each turn that has a cost of 2 or more is played twice.',
                     'Flavor': 'Only a fool would try and harness this evil power. At night your dreams are haunted by images of the book devouring your mind.'},
    "Neow's Lament": {'Name': "Neow's Lament", 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Cursed Tome', 'Info': 'Enemies in your first 3 combats have 1 HP.', 'Flavor': 'The blessing of lamentation bestowed by Neow.'},
    "Nilry's Codex": {'Name': "Nilry's Codex", 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Cursed Tome', 'Info': 'At the end of each turn, you can choose 1 of 3 random cards to shuffle into your draw pile.', 'Flavor': "Created by the infamous game master himself. Said to expand one's mind."},
    'Odd Mushroom': {'Name': 'Odd Mushroom', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Hypnotizing Colored Mushrooms', 'Info': 'When <debuff>Vulnerable</debuff>, take 25% more damage rather than 50%.', 'Flavor': '"After consuming trichella parastius I felt larger and less... susceptible." - Ranwid'},
    'Red Mask': {'Name': 'Red Mask', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Masked Bandits or Tome of Lord Red Mask', 'Info': 'At the start of combat, apply 1 <debuff>Weak</debuff> to ALL enemies.', 'Flavor': 'This very stylish-looking mask belongs to the leader of the Red Mask Bandits. Technically that makes you the leader now?'},
    'Spirt Poop': {'Name': 'Spirit Poop', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Bonfire Spirits', 'Info': "It's unpleasant.", 'Flavor': 'The charred remains of your offering to the spirits.'},
    'Ssserpent Head': {'Name': 'Ssserpent Head', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Face Trader', 'Info': 'Whenever you enter a <bold>?</bold> room, gain 50 Gold.', 'Flavor': 'The most fulfilling of lives is that in which you can buy anything!'},
    'Warped Tongs': {'Name': 'Warped Tongs', 'Class': 'Any', 'Rarity': 'Event', 'Source': 'Ominous Forge', 'Info': 'At the start of your turn, <keyword>Upgrade</keyword> a random card in your hand for the rest of combat.', 'Flavor' : 'The cursed tongs emit a strong desire to return to where they were stolen from.'},
    # Circlet can only be obtained once you have gotten all other relics.
    'Circlet': {'Name': 'Circlet', 'Class': 'Any', 'Rarity': 'Special', 'Info': 'Looks pretty.', 'Flavor': 'You ran out of relics to find. Impressive!'}
}
cards = {
    # Ironclad cards
    'Strike': {'Name': 'Strike', 'Damage': 6, 'Energy': 1, 'Rarity': 'Basic', 'Target': 'Single', 'Type': 'Attack', 'Class': 'Ironclad', 'Info': 'Deal Σ6 damage.', 'Effects+': {'Damage': 9, 'Info': 'Deal Σ9 damage.'}, 'Function': use_strike},

    'Defend': {'Name': 'Defend', 'Block': 5, 'Energy': 1, 'Target': 'Yourself', 'Rarity': 'Basic', 'Type': 'Skill', 'Class': 'Ironclad', 'Info': 'Gain Ω5 <keyword>Block</keyword>.', 'Effects+': {'Block': 8, 'Info': 'Gain Ω8 <keyword>Block</keyword>'}, 'Function': use_defend},

    'Bash': {'Name': 'Bash', 'Damage': 8, 'Vulnerable': 2, 'Energy': 2, 'Target': 'Single', 'Rarity': 'Basic', 'Class': 'Ironclad', 'Type': 'Attack', 'Info': 'Deal Σ8 damage. Apply 2 <debuff>Vulnerable</debuff>', 'Effects+': {'Damage': 10, 'Vulnerable': 3, 'Info': 'Deal Σ10 damage. Apply 3 <debuff>Vulnerable</debuff>'}, 'Function': use_bash},

    'Anger': {'Name': 'Anger', 'Damage': 6, 'Energy': 0,  'Target': 'Single', 'Rarity': 'Common', 'Type': 'Attack', 'Class': 'Ironclad', 'Info': 'Deal Σ6 damage. Add a copy of this card to your discard pile.', 'Effects+': {'Damage': 8, 'Info': 'Deal Σ8 damage. Add a copy of this card to your discard pile.'}, 'Function': use_anger},

    'Armaments': {'Name': 'Armaments', 'Target': 'Yourself', 'Energy': 1, 'Rarity': 'Common', 'Type': 'Skill', 'Class': 'Ironclad', 'Info': 'Gain Ω5 <keyword>Block</keyword>. <keyword>Upgrade</keyword> a card in your hand for the rest of combat.',
                  'Effects+': {'Info': 'Gain Ω5 <keyword>Block</keyword>. <keyword>Upgrade</keyword> ALL cards in your hand for the rest of combat.'}, 'Function': use_armaments},

    'Body Slam': {'Name': 'Body Slam', 'Energy': 1, 'Target': 'Single', 'Rarity': 'Common', 'Type': 'Attack', 'Class': 'Ironclad', 'Info': 'Deal damage equal to your <keyword>Block</keyword>(Σ0)', 'Effects+': {'Energy': 0}, 'Function': use_bodyslam},

    'Clash': {'Name': 'Clash', 'Damage': 14, 'Energy': 0, 'Target': 'Single', 'Rarity': 'Common', 'Type': 'Attack', 'Class': 'Ironclad', 'Info': 'Can only be played is every card in your hand is an <keyword>Attack</keyword>. Deal Σ18 damage.',
              'Effects+': {'Damage': 18, 'Info': 'Can only be played if every card in your hand is an <keyword>Attack</keyword>. Deal Σ18 damage.'}, 'Function': use_clash},

    'Cleave': {'Name': 'Cleave', 'Damage': 8, 'Target': 'Any', 'Energy': 1, 'Rarity': 'Common', 'Type': 'Attack', 'Class': 'Ironclad', 'Info': 'Deal Σ8 damage to ALL enemies', 'Effects+': {'Damage': 11, 'Info': 'Deal Σ11 damage to ALL enemies.'}, 'Function': use_cleave},

    'Clothesline': {'Name': 'Clothesline', 'Energy': 2, 'Damage': 12, 'Weak': 2, 'Target': 'Single', 'Rarity': 'Common', 'Type': 'Attack', 'Class': 'Ironclad', 'Info': 'Deal Σ12 damage. Apply 2 <debuff>Weak</debuff>', 'Effects+': {'Damage': 14, 'Weak': 3, 'Info': 'Deal Σ14 damage. Apply 3 <debuff>Weak</debuff>.'}, 'Function': use_clothesline},

    'Flex': {'Name': 'Flex', 'Strength': 2, 'Energy': 0, 'Target': 'Yourself', 'Rarity': 'Common', 'Type': 'Skill', 'Class': 'Ironclad', 'Info': 'Gain 2 <buff>Strength</buff>. At the end of your turn, lose 2 <buff>Strength</buff>',
             'Effects+': {'Strength': 4, 'Info': 'Gain 4 <buff>Strength</buff>. At the end of your turn, lose 4 <buff>Strength</buff>.'}, 'Function': use_flex},

    'Havoc': {'Name': 'Havoc', 'Energy': 1, 'Target': 'Area', 'Rarity': 'Common', 'Type': 'Skill', 'Class': 'Ironclad', 'Info': 'Play the top card of your draw pile and <keyword>Exhaust</keyword> it.', 'Effects+': {'Energy': 0}, 'Function': use_havoc},

    'Headbutt': {'Name': 'Headbutt', 'Damage': 9, 'Energy': 1, 'Target': 'Single', 'Rarity': 'Common', 'Type': 'Attack', 'Class': 'Ironclad', 'Info': 'Deal Σ9 damage. Place a card from your discard pile on top of your draw pile.',
                 'Effects+': {'Damage': 12, 'Info': 'Deal Σ12 damage. Place a card from your discard pile on top of your draw pile.'}, 'Function': use_headbutt},

    'Heavy Blade': {'Name': 'Heavy Blade', 'Damage': 14, 'Strength Multi': 3, 'Energy': 2, 'Target': 'Single', 'Rarity': 'Common', 'Type': 'Attack', 'Class': 'Ironclad', 'Info': 'Deal Σ14 damage. <buff>Strength</buff> affects this card 3 times.',
                    'Effects+': {'Damage': 18, 'Strength Multi': 5, 'Info': 'Deal Σ14 damage. <buff>Strength</buff> affects this card 3 times.'}, 'Function': use_heavyblade},

    'Iron Wave': {'Name': 'Iron Wave', 'Damage': 5, 'Block': 5, 'Energy': 1, 'Target': 'Single', 'Rarity': 'Common', 'Type': 'Attack', 'Class': 'Ironclad', 'Info': 'Gain Ω5 <keyword>Block</keyword>. Deal Σ5 damage.', 'Effects+': {'Damage': 7, 'Block': 7, 'Info': 'Gain Ω7 <keyword>Block</keyword>. Deal Σ7 damage.'}, 'Function': use_ironwave},

    'Perfected Strike': {'Name': 'Perfected Strike', 'Damage Per "Strike"': 2, 'Energy': 2, 'Target': 'Single', 'Rarity': 'Common', 'Type': 'Attack', 'Class': 'Ironclad', 'Info': 'Deal Σ6 damage. Deals 2 additional damage for ALL your cards containing <italic>"Strike"</italic>.',
                         'Effects+': {'Damage Per "Strike"': 3, 'Info': 'Deal Σ6 damage. Deals 3 additional damage for ALL your cards containing <italic>"Strike"</italic>.'}, 'Function': use_perfectedstrike},

    'Pommel Strike': {'Name': 'Pommel Strike', 'Damage': 9, 'Cards': 1, 'Energy': 1, 'Target': 'Single', 'Rarity': 'Common', 'Type': 'Attack', 'Class': 'Ironclad', 'Info': 'Deal Σ9 damage. Draw 1 card.', 'Effects+': {'Damage': 10, 'Cards': 2, 'Info': 'Deal Σ10 damage. Draw 2 cards.'}, 'Function': use_pommelstrike},

    'Shrug it Off': {'Name': 'Shrug it Off', 'Block': 8, 'Cards': 1, 'Energy': 1, 'Rarity': 'Common', 'Target': 'Yourself', 'Type': 'Skill', 'Class': 'Ironclad', 'Info': 'Gain Ω8 <keyword>Block</keyword>. Draw 1 card.', 'Effects+': {'Block': 11, 'Info': 'Gain Ω11 <keyword>Block</keyword>. Draw 1 card.'}, 'Function': use_shrugitoff},

    'Sword Boomerang': {'Name': 'Sword Boomerang', 'Times': 3, 'Target': 'Random', 'Energy': 1, 'Rarity': 'Common', 'Type': 'Attack', 'Class': 'Ironclad', 'Info': 'Deal Σ3 damage to a random enemy 3 times.', 'Effects+': {'Times': 4, 'Info': 'Deal Σ3 damage to a random enemy 4 times.'}, 'Function': use_swordboomerang},

    'Thunderclap': {'Name': 'Thunderclap', 'Damage': 4, 'Target': 'Any', 'Energy': 1, 'Rarity': 'Common', 'Type': 'Attack', 'Class': 'Ironclad', 'Info': 'Deal Σ4 damage and apply 1 <debuff>Vulnerable</debuff> to ALL enemies.',
                    'Effects+': {'Damage': 7, 'Info': 'Deal Σ7 damage and apply 1 <debuff>Vulnerable</debuff> to ALL enemies.'}, 'Function': use_thunderclap},

    'True Grit': {'Name': 'True Grit', 'Class': 'Ironclad', 'Rarity': 'Common', 'Target': 'Yourself', 'Type': 'Skill', 'Block': 7, 'Energy': 1, 'Info': 'Gain Ω7 <keyword>Block</keyword>. <keyword>Exhaust</keyword> a random card in your hand.',
                  'Effects+': {'Block': 9, 'Info': 'Gain Ω9 <keyword>Block</keyword>. <keyword>Exhaust</keyword> a card in your hand.'}, 'Function': use_truegrit},

    'Twin Strike': {'Name': 'Twin Strike', 'Class': 'Ironclad', 'Rarity': 'Common', 'Type': 'Attack', 'Target': 'Single', 'Damage': 5, 'Energy': 1, 'Info': 'Deal Σ5 damage twice.', 'Effects+': {'Damage': 7, 'Info': 'Deal Σ7 damage twice.'}, 'Function': use_twinstrike},

    'Warcry': {'Name': 'Warcry', 'Class': 'Ironclad', 'Rarity': 'Common', 'Target': 'Yourself', 'Type': 'Skill', 'Exhaust': True, 'Cards': 1, 'Energy': 0, 'Info': 'Draw 1 card. Put a card from your hand on top of your draw pile. <keyword>Exhaust</keyword>.',
               'Effects+': {'Cards': 2, 'Info': 'Draw 2 cards. Put a card from your hand on top of your draw pile. <keyword>Exhaust</keyword>.'}, 'Function': use_warcry},

    'Wild Strike': {'Name': 'Wild Strike', 'Class': 'Ironclad', 'Rarity': 'Common', 'Type': 'Attack', 'Target': 'Single', 'Damage': 12, 'Energy': 1, 'Info': 'Deal Σ12 damage. Shuffle a <status>Wound</status> into your draw pile.',
                    'Effects+': {'Damage': 17, 'Info': 'Deal Σ17 damage. Shuffle a <status>Wound</status> into your draw pile.'}, 'Function': use_wildstrike},

    # Uncommon cards
    'Battle Trance': {'Name': 'Battle Trance', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Yourself', 'Cards': 3, 'Energy': 0, 'Info': "Draw 3 cards. You can't draw additional cards this turn.", 'Effects+': {'Cards': 4, 'Info': "Draw 4 cards. You can't draw additional cards this turn."}, 'Function': use_battletrance},

    'Blood for Blood': {'Name': 'Blood for Blood', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Attack', 'Target': 'Single', 'Damage': 18, 'Energy': 4, 'Info': 'Costs 1 less <keyword>Energy</keyword> for each time you lose HP this combat. Deal Σ18 damage.',
                        'Effects+': {'Damage': 22, 'Info': 'Costs 1 less <keyword>Energy</keyword> for each time you lose HP this combat. Deal Σ22 damage.'}, 'Function': use_bloodforblood},

    'Bloodletting': {'Name': 'Bloodletting', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Yourself', 'Energy Gain': 2, 'Energy': 0, 'Info': 'Lose 3 HP. Gain 2 <keyword>Energy</keyword>.', 'Effects+': {'Energy Gain': 3, 'Info': 'Lose 3 HP. Gain 3 <keyword>Energy</keyword>.'}, 'Function': use_bloodletting},

    'Burning Pact': {'Name': 'Burning Pact', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Yourself', 'Cards': 2, 'Energy': 1, 'Info': '<keyword>Exhaust</keyword> 1 card. Draw 2 cards.', 'Effects+': {'Cards': 3, 'Info': '<keyword>Exhaust</keyword> 1 card. Draw 3 cards.'}, 'Function': use_burningpact},

    'Carnage': {'Name': 'Carnage', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Target': 'Single', 'Type': 'Attack', 'Ethereal': True, 'Damage': 20, 'Energy': 2, 'Info': '<keyword>Ethereal.</keyword> Deal Σ20 damage.', 'Effects+': {'Damage': 28, 'Info': '<keyword>Ethereal.</keyword> Deal Σ28 damage.'}, 'Function': use_carnage},

    'Combust': {'Name': 'Combust', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Target': 'Yourself', 'Type': 'Power', 'Combust': 5, 'Energy': 1, 'Info': 'At the end of your turn, lose 1 HP and deal 5 damage to ALL enemies.', 'Effects+': {'Combust': 7, 'Info': 'At the end of your turn, lose 1 HP and deal 7 damage to ALL enemies'}, 'Function': use_combust},

    'Dark Embrace': {'Name': 'Dark Embrace', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Target': 'Yourself', 'Type': 'Power', 'Energy': 2, 'Info': 'Whenever a card is <keyword>Exhausted</keyword>, draw 1 card.', 'Effects+': {'Energy': 1}, 'Function': use_darkembrace},

    'Disarm': {'Name': 'Disarm', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Single', 'Exhaust': True, 'Strength Loss': 2, 'Energy': 1, 'Info': 'Enemy loses 2 <buff>Strength</buff>. <keyword>Exhaust.</keyword>',
               'Effects+': {'Strength Loss': 3, 'Info': 'Enemy loses 3 <buff>Strength</buff>. <keyword>Exhaust</keyword>.'}, 'Function': use_disarm},

    'Dropkick': {'Name': 'Dropkick', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Attack', 'Target': 'Single', 'Damage': 5, 'Energy': 1, 'Info': 'Deal Σ5 damage. If the enemy has <debuff>Vulnerable</debuff>, gain 1 <keyword>Energy</keyword> and draw 1 card.',
                 'Effects+': {'Damage': 8, 'Info': 'Deal Σ8 damage. If the enemy has <debuff>Vulnerable</debuff>, gain 1 <keyword>Energy</keyword> and draw 1 card.'}, 'Function': use_dropkick},

    'Dual Wield': {'Name': 'Dual Wield', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Yourself', 'Copies': 1, 'Energy': 1, 'Info': 'Create a copy of an <keyword>Attack</keyword> or <keyword>Power</keyword> card in your hand.',
                   'Effects+': {'Copies': 2, 'Info': 'Create 2 copies of an <keyword>Attack</keyword> or <keyword>Power</keyword> card in your hand'}, 'Function': use_dualwield},

    'Entrench': {'Name': 'Entrench', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Yourself', 'Energy': 2, 'Info': 'Double your <keyword>Block</keyword>.', 'Effects+': {'Energy': 1}, 'Function': use_entrench},

    'Evolve': {'Name': 'Evolve', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Power', 'Target': 'Yourself', 'Evolve': 1, 'Energy': 1, 'Info': 'Whenever you draw a <status>Status</status> card, draw 1 card.', 'Effects+': {'Evolve': 2, 'Info': 'Whenever you draw a <status>Status</status> cards, draw 2 cards.'}, 'Function': use_evolve},

    'Fire Breathing': {'Name': 'Fire Breathing', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Power', 'Target': 'Yourself', 'Fire Breathing': 6, 'Energy': 1, 'Info': 'Whenever you draw a <status>Status</status> or <keyword>Curse</keyword>, deal 6 damage to ALL enemies.',
                       'Effects+': {'Fire Breathing': 10, 'Info': 'Whenever you draw a <status>Status</status> or <keyword>Curse</keyword> card, deal 10 damage to ALL enemies.'}, 'Function': use_firebreathing},

    'Flame Barrier': {'Name': 'Flame Barrier', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Yourself', 'Block': 12, 'Energy': 2, 'Info': "Gain Ω12 <keyword>Block</keyword>. Whenever you're attacked this turn, deal 4 damage back.",
                      'Effects+': {'Block': 16, 'Info': "Gain Ω16 <keyword>Block</keyword>. Whenever you're attacked this turn, deal 4 damage back."}, 'Function': use_flamebarrier},

    'Ghostly Armor': {'Name': 'Ghostly Armor', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Yourself', 'Ethereal': True, 'Block': 10, 'Energy': 1, 'Info': '<keyword>Ethereal.</keyword> Gain Ω10 <keyword>Block</keyword>.',
                      'Effects+': {'Block': 13, 'Info': '<keyword>Ethereal.</keyword> Gain Ω13 <keyword>Block</keyword>.'}, 'Function': use_ghostlyarmor},

    'Hemokinesis': {'Name': 'Hemokinesis', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Attack', 'Target': 'Single', 'Damage': 15, 'Energy': 1, 'Info': 'Lose 2 HP. Deal Σ15 damage.', 'Effects+': {'Damage': 20, 'Info': 'Lose 2 HP. Deal Σ20 damage.'}, 'Function': use_hemokinesis},

    'Infernal Blade': {'Name': 'Infernal Blade', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Yourself', 'Energy': 1, 'Info': 'Add a random <keyword>Attack</keyword> into your hand. It costs 0 this turn. <keyword>Exhaust.</keyword>', 'Effects+': {'Energy': 0}, 'Function': use_infernalblade},

    'Inflame': {'Name': 'Inflame', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Power', 'Target': 'Yourself', 'Strength': 2, 'Energy': 1, 'Info': 'Gain 2 <buff>Strength</buff>.', 'Effects+': {'Strength': 3, 'Info': 'Gain 3 <buff>Strength</buff>.'}, 'Function': use_inflame},

    'Intimidate': {'Name': 'Intimidate', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Area', 'Exhaust': True, 'Weak': 1, 'Energy': 0, 'Info': 'Apply 1 <debuff>Weak</debuff> to ALL enemies. <keyword>Exhaust</keyword>.',
                   'Effects+': {'Weak': 2, 'Info': 'Apply 2 <debuff>Weak</debuff> to ALL enemies. <keyword>Exhaust</keyword>.'}, 'Function': use_intimidate},

    'Metallicize': {'Name': 'Metallicize', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Power', 'Target': 'Yourself', 'Metallicize': 3, 'Energy': 1, 'Info': 'At the end of your turn, gain 3 <keyword>Block</keyword>.',
                    'Effects+': {'Metallicize': 4, 'Info': 'At the end of your turn, gain 4 <keyword>Block</keyword>.'}, 'Function': use_metallicize},

    'Power Through': {'Name': 'Power Through', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Yourself', 'Block': 15, 'Energy': 1, 'Info': 'Add 2 <status>Wounds</status> to your hand. Gain Ω15 <keyword>Block</keyword>.',
                      'Effects+': {'Block': 20, 'Info': 'Add 2 <status>Wounds</status> to your hand. Gain Ω20 <keyword>Block</keyword>'}, 'Function': use_powerthrough},

    'Pummel': {'Name': 'Pummel', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Attack', 'Target': 'Single', 'Exhaust': True, 'Times': 4, 'Energy': 1, 'Info': 'Deal Σ2 damage 4 times.', 'Effects+': {'Times': 5, 'Info': 'Deal Σ2 damage 5 times.'}, 'Function': use_pummel},

    'Rage': {'Name': 'Rage', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Yourself', 'Rage': 3, 'Energy': 0, 'Info': 'Whenever you play an <keyword>Attack</keyword>, gain 3 <keyword>block</keyword>.',
             'Effects+': {'Rage': 5, 'Info': 'Whenever you play an <keyword>Attack</keyword>, gain 5 <keyword>Block</keyword>.'}, 'Function': use_rage},

    'Rampage': {'Name': 'Rampage', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Attack', 'Target': 'Single', 'Damage+': 5, 'Damage': 8, 'Energy': 1, 'Info': "Deal Σ8 damage. Increase this card's damage by 5 this combat.",
                'Effects+': {'Damage+': 8, 'Info': "Deal Σ8 damage. Increase this card's damage by 8 this combat."}, 'Function': use_rampage},

    'Reckless Charge': {'Name': 'Reckless Charge', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Attack', 'Target': 'Single', 'Damage': 7, 'Energy': 0, 'Info': 'Deal Σ7 damage. Shuffle a <status>Dazed</status> into your draw pile.',
                        'Effects+': {'Damage': 10, 'Info': 'Deal Σ10 damage. Shuffle a <status>Dazed</status> into your draw pile.'}, 'Function': use_recklesscharge},

    'Rupture': {'Name': 'Rupture', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Power', 'Target': 'Yourself', 'Rupture': 1, 'Energy': 1, 'Info': 'Whenever you lose HP from a card, gain 1 <buff>Strength</buff>.',
                'Effects+': {'Rupture': 2, 'Info': 'Whenever you lose HP from a card, gain 2 <buff>Strength</buff>.'}, 'Function': use_rupture},

    'Searing Blow': {'Name': 'Searing Blow', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Attack', 'Target': 'Single', 'Damage': 12, 'Upgrade Count': 0, 'Energy': 2, 'Info': 'Deal Σ12 damage. Can be <keyword>upgraded</keyword> any number of times.', 'Function': use_searingblow},

    'Second Wind': {'Name': 'Second Wind', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Yourself', 'Block Per Card': 5, 'Energy': 1, 'Info': '<keyword>Exhaust</keyword> all non-<keyword>Attack</keyword> cards in your hand and gain 5 <keyword>Block</keyword> for each card <keyword>Exhausted</keyword>.',
                    'Effects+': {'Block Per Card': 7, 'Info': '<keyword>Exhaust</keyword> all non-<keyword>Attack</keyword> cards in your hand and gain 7 <keyword>Block</keyword> for each card <keyword>Exhausted</keyword>.'}, 'Function': use_secondwind},

    'Seeing Red': {'Name': 'Seeing Red', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Yourself', 'Exhaust': True, 'Energy': 1, 'Info': 'Gain 2 <keyword>Energy</keyword>. <keyword>Exhaust</keyword>.', 'Effects+': {'Energy': 0}, 'Function': use_seeingred},

    'Sentinel': {'Name': 'Sentinel', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Yourself', 'Block': 5, 'Energy Gain': 2, 'Energy': 1, 'Info': 'Gain Ω5 <keyword>Block</keyword>. If this card is <keyword>Exhausted</keyword>, gain 2 <keyword>Energy</keyword>',
                 'Effects+': {'Block': 8, 'Energy Gain': 3, 'Info': 'Gain Ω8 <keyword>Block</keyword>. If this card is <keyword>Exhausted</keyword>, gain 3 <keyword>Energy</keyword>.'}, 'Function': use_sentinel},

    'Sever Soul': {'Name': 'Sever Soul', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Attack', 'Target': 'Single', 'Damage': 16, 'Energy': 2, 'Info': '<keyword>Exhaust</keyword> all non-<keyword>Attack</keyword> cards in your hand. Deal Σ16 damage.',
                   'Effects+': {'Damage': 22, 'Info': '<keyword>Exhaust</keyword> all non-<keyword>Attack</keyword> cards in your hand. Deal Σ22 damage.'}, 'Function': use_seversoul},

    'Shockwave': {'Name': 'Shockwave', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Skill', 'Target': 'Area', 'Exhaust': True, 'Weak/Vulnerable': 3, 'Energy': 2, 'Info': 'Apply 3 <debuff>Weak</debuff> and <debuff>Vulnerable</debuff> to ALL enemies. <keyword>Exhaust</keyword>.',
                  'Effects+': {'Weak/Vulnerable': 5, 'Info': 'Apply 5 <debuff>Weak</debuff> and <debuff>Vulnerable</debuff> to ALL enemies. <keyword>Exhaust</keyword>.'}, 'Function': use_shockwave},

    # Ignore Spot Weakness because intent doesn't exist yet

    'Uppercut': {'Name': 'Uppercut', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Attack', 'Target': 'Single', 'Damage': 13, 'Weak/Vulnerable': 1, 'Energy': 2, 'Info': 'Deal Σ13 damage. Apply 1 <debuff>Weak</debuff>. Apply 1 <debuff>Vulnerable</debuff>.',
                 'Effects+': {'Weak/Vulnerable': 2, 'Info': 'Deal Σ13 damage. Apply 2 <debuff>Weak</debuff>. Apply 2 <debuff>Vulnerable</debuff>.'}, 'Function': use_uppercut},

    'Whirlwind': {'Name': 'Whirlwind', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Type': 'Attack', 'Target': 'Area', 'Damage': 5, 'Energy': -1, 'Info': 'Deal Σ5 damage X times.', 'Effects+': {'Damage': 8, 'Info': 'Deal Σ8 damage X times.'}, 'Function': use_whirlwind},

    # Rare Cards
    'Barricade': {'Name': 'Barricade', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Power', 'Target': 'Yourself', 'Energy': 3, 'Info': '<keyword>Block</keyword> is not removed at the start of your turn.', 'Effects+': {'Energy': 2}, 'Function': use_barricade},

    'Berzerk': {'Name': 'Berzerk', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Power', 'Target': 'Yourself', 'Self Vulnerable': 2, 'Energy': 0, 'Info': 'Gain 2 <debuff>Vulnerable</debuff>. At the start of your turn, gain 1 <keyword>Energy</keyword>.',
                'Effects+': {'Self Vulnerable': 1, 'Info': 'Gain 1 <debuff>Vulnerable</debuff>. At the start of your turn, gain 1 <keyword>Energy</keyword>.'}, 'Function': use_berzerk},

    'Bludgeon': {'Name': 'Bludgeon', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Attack', 'Target': 'Single', 'Damage': 32, 'Energy': 3, 'Info': 'Deal Σ32 damage.', 'Effects+': {'Damage': 42, 'Info': 'Deal Σ42 damage.'}, 'Function': use_bludgeon},

    'Brutality': {'Name': 'Brutality', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Power', 'Target': 'Yourself', 'Energy': 0, 'Info': 'At the start of your turn, lose 1 HP and draw 1 card.', 'Effects+': {'Innate': True, 'Info': '<keyword>Innate</keyword>. At the start of your turn, lose 1 HP and draw 1 card'}, 'Function': use_brutality},

    'Corruption': {'Name': 'Corruption', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Power', 'Target': 'Yourself', 'Energy': 3, 'Info': '<keyword>Skills</keyword> cost 0. Whenever you play a <keyword>Skill</keyword>, <keyword>Exhaust</keyword> it.', 'Effects+': {'Energy': 2}, 'Function': use_corruption},

    'Demon Form': {'Name': 'Demon Form', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Power', 'Target': 'Yourself', 'Demon Form': 2, 'Energy': 3, 'Info': 'At the start of your turn, gain 2 <buff>Strength</buff>.', 'Effects+': {'Demon Form': 3, 'Info': 'At the start of your turn, gain 3 <buff>Strength</buff>.'}, 'Function': use_demonform},

    'Double Tap': {'Name': 'Double Tap', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Skill', 'Target': 'Yourself', 'Charges': 1, 'Energy': 1, 'Info': 'This turn, your next <keyword>Attack</keyword> is played twice.', 'Effects+': {'Charges': 2, 'Info': 'This turn, your next 2 <keyword>Attacks</keyword> are played twice'}, 'Function': use_doubletap},

    'Exhume': {'Name': 'Exhume', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Skill', 'Target': 'Yourself', 'Energy': 1, 'Info': 'Put a card from your exhaust pile into your hand. <keyword>Exhaust</keyword>.', 'Effects+': {'Energy': 0}, 'Function': use_exhume},

    'Feed': {'Name': 'Feed', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Attack', 'Target': 'Single', 'Exhaust': True, 'Damage': 10, 'Max HP': 3, 'Energy': 1, 'Info': 'Deal Σ10 damage. If <keyword>Fatal</keyword>, raise your Max HP by 3. <keyword>Exhaust</keyword>.',
             'Effects+': {'Damage': 12, 'Max HP': 4, 'Info': 'Deal Σ12 damage. If <keyword>Fatal</keyword>, raise your Max HP by 4. <keyword>Exhaust</keyword>.'}, 'Function': use_feed},

    'Fiend Fire': {'Name': 'Fiend Fire', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Attack', 'Target': 'Single', 'Energy': 2, 'Exhaust': True, 'Damage': 7, 'Info': '<keyword>Exhaust</keyword> all cards in your hand. Deal Σ7 damage for each <keyword>Exhausted</keyword>. <keyword>Exhaust</keyword>.',
                   'Effects+': {'Damage': 10, 'Info': '<keyword>Exhaust</keyword> all cards in your hand. Deal Σ10 damage for each card <keyword>Exhausted</keyword>. <keyword>Exhaust</keyword>.'}, 'Function': use_fiendfire},

    'Immolate': {'Name': 'Immolate', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Attack', 'Target': 'Area', 'Damage': 21, 'Energy': 2, 'Info': 'Deal Σ21 damage to ALL enemies. Add a <status>Burn</status> to your discard pile',
                 'Effects+': {'Damage': 28, 'Info': 'Deal Σ28 damage to ALL enemies. Add a <status>Burn</status> to your discard pile.'}, 'Function': use_immolate},

    'Impervious': {'Name': 'Impervious', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Skill', 'Target': 'Yourself', 'Block': 30, 'Energy': 2, 'Info': 'Gain Ω30 <keyword>Block</keyword>.', 'Effects+': {'Block': 40, 'Info': 'Gain Ω40 <keyword>Block</keyword>.'}, 'Function': use_impervious},

    'Juggernaut': {'Name': 'Juggernaut', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Power', 'Target': 'Yourself', 'Dmg On Block': 5, 'Energy': 2, 'Info': 'Whenever you gain <keyword>Block</keyword>, deal 5 damage to a random enemy.',
                   'Effects+': {'Dmg On Block': 7, 'Info': 'Whenever you gain <keyword>Block</keyword>, deal 7 damage to a random enemy.'}, 'Function': use_juggernaut},

    'Limit Break': {'Name': 'Limit Break', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Skill', 'Target': 'Yourself', 'Exhaust': True, 'Energy': 1, 'Info': 'Double your <buff>Strength</buff>. <keyword>Exhaust</keyword>.', 'Effects+': {'Exhaust': False}, 'Function': use_limitbreak},

    'Offering': {'Name': 'Offering', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Skill', 'Target': 'Yourself', 'Exhaust': True, 'Cards': 3, 'Energy': 0, 'Info': 'Lose 6 HP. Gain 2 <keyword>Energy</keyword>. Draw 3 cards. <keyword>Exhaust</keyword>.',
                 'Effects+': {'Cards': 5, 'Info': 'Lose 6 HP. Gain 2 <keyword>Exhaust</keyword>. Draw 5 cards. <keyword>Exhaust</keyword>.'}, 'Function': use_offering},

    'Reaper': {'Name': 'Reaper', 'Class': 'Ironclad', 'Rarity': 'Rare', 'Type': 'Attack', 'Target': 'Area', 'Exhaust': True, 'Damage': 4, 'Energy': 2, 'Info': 'Deal 4 damage to ALL enemies. Heal HP equal to unblocked damage. <keyword>Exhaust</keyword>.',
               'Effects+': {'Damage': 5, 'Info': 'Deal 5 damage to ALL enemies. Heal HP equal to unblocked damage. <keyword>Exhaust</keyword>.'}, 'Function': use_reaper},
    # Status cards
    'Slimed': {'Name': 'Slimed', 'Class': PlayerClass.ANY, 'Energy': 1, 'Target': 'Nothing', 'Rarity': 'Common', 'Type': 'Status', 'Info': '<keyword>Exhaust</keyword>'},
    'Burn': {'Name': 'Burn', 'Class': PlayerClass.ANY, 'Playable': False, 'Damage': 2, 'Rarity': 'Common', 'Type': 'Status', 'Info': '<keyword>Unplayable.</keyword> At the end of your turn, take 2 damage.', 'Effects+': {'Damage': 4, 'Info': '<keyword>Unplayable.</keyword> At the end of your turn, take 4 damage.'}},
    'Dazed': {'Name': 'Dazed', 'Class': PlayerClass.ANY, 'Playable': False, 'Ethereal': True, 'Rarity': 'Common', 'Type': 'Status', 'Info': '<keyword>Unplayable. Ethereal.</keyword>'},
    'Wound': {'Name': 'Wound', 'Class': PlayerClass.ANY, 'Playable': False, 'Rarity': 'Common', 'Type': 'Status', 'Info': '<keyword>Unplayable.</keyword>'},
    'Void': {'Name': 'Void', 'Class': PlayerClass.ANY, 'Playable': False, 'Ethereal': True, 'Energy Loss': 1, 'Rarity': 'Common', 'Type': 'Status', 'Info': '<keyword>Unplayable. Ethereal.</keyword> When this card is drawn, lose 1 Energy.'},

    # Curses
    'Regret': {'Name': 'Regret', 'Playable': False, 'Rarity': 'Curse', 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Info': '<keyword>Unplayable</keyword>. At the end of your turn, lose 1 HP for each card in your hand.'},
    "Ascender's Bane": {'Name': "Ascender's Bane", 'Playable': False, 'Ethereal': True, 'Removable': False, 'Rarity': 'Special', 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Info': '<keyword>Unplayable. Ethereal.</keyword> Cannot be removed from your deck'},
    'Clumsy': {'Name': 'Clumsy', 'Playable': False, 'Ethereal': True, 'Rarity': 'Curse', 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Info': '<keyword>Unplayable. Ethereal.</keyword>'},
    'Curse of the Bell': {'Name': 'Curse of the Bell', 'Playable': False, 'Removable': False, 'Rarity': 'Curse', 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Info': '<keyword>Unplayable.</keyword> Cannot be removed from your deck.'},
    'Decay': {'Name': 'Decay', 'Playable': False, 'Damage': 2, 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Rarity': 'Curse', 'Info': '<keyword>Unplayable.</keyword> At the end of your turn, take 2 damage.'},
    'Doubt': {'Name': 'Doubt', 'Playable': False, 'Weak': 1, 'Rarity': 'Curse', 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Info': '<keyword>Unplayable.</keyword> At the end of your turn, gain 1 <debuff>Weak</debuff>.'},
    'Injury': {'Name': 'Injury', 'Playable': False, 'Rarity': 'Curse', 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Info': '<keyword>Unplayable.</keyword>'},
    'Necronomicurse': {'Name': 'Necronomicurse', 'Playable': False, 'Exhaustable': False, 'Rarity': 'Curse', 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Info': '<keyword>Unplayable.</keyword> There is no escape from this <fg 141>Curse</fg 141>.'},
    'Normality': {'Name': 'Normality', 'Playable': False, 'Cards Limit': 3, 'Rarity': 'Curse', 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Info': '<keyword>Unplayable.</keyword> You cannot play more than 3 cards this turn.'},
    'Pain': {'Name': 'Pain', 'Playable': False, 'Damage': 1, 'Rarity': 'Curse', 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Info': '<keyword>Unplayable</keyword>. While in hand, lose 1 HP when other cards are played.'},
    'Parasite': {'Name': 'Parasite', 'Playable': False, 'Max Hp Loss': 3, 'Rarity': 'Curse', 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Info': '<keyword>Unplayable.</keyword> If transformed or removed from your deck, lose 3 Max HP.'},
    'Pride': {'Name': 'Pride', 'Innate': True, 'Exhaust': True, 'Energy': 1, 'Rarity': 'Special', 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Info': '<keyword>Innate.</keyword> At the end of your turn, put a copy of this card on top of your draw pile. <keyword>Exhaust.</keyword>'},
    'Shame': {'Name': 'Shame', 'Playable': False, 'Frail': 1, 'Rarity': 'Curse', 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Info': '<keyword>Unplayable.</keyword> At the end of your turn, gain 1 <red>Frail</red>.'},
    'Writhe': {'Name': 'Writhe', 'Playable': False, 'Innate': True, 'Rarity': 'Curse', 'Class': PlayerClass.ANY, 'Type': 'Curse', 'Info': '<keyword>Unplayable. Innate.</keyword>'},

    # Colorless Cards
    "Bandage Up": {"Name": "Bandage Up", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "Heal 4(6) HP. Exhaust.", "Exhaust": True, "Target": TargetType.YOURSELF, "Function": use_bandageup},
    "Blind": {"Name": "Blind", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "Apply 2 Weak (to ALL enemies).", "Target": TargetType.AREA, "Function": use_blind},
    "Dark Shackles": {"Name": "Dark Shackles", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "Enemy loses 9(15) Strength for the rest of this turn. Exhaust.", "Exhaust": True, "Target": TargetType.ENEMY, "Function": use_darkshackles, "Magic Number": 9},
    "Deep Breath": {"Name": "Deep Breath", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "Shuffle your discard pile into your draw pile. Draw 1(2) card(s).", "Target": TargetType.NOTHING, "Function": use_deepbreath, "Cards": 1},
    # "Discovery": {"Name": "Discovery", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 1, "Info": "Choose 1 of 3 random cards to add to your hand. It costs 0 this turn. Exhaust. (Don't Exhaust.)", "Exhaust": True, "Target": TargetType.YOURSELF, "Function": use_discovery},
    "Dramatic Entrance": {"Name": "Dramatic Entrance", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.ATTACK, "Energy": 0, "Info": "Innate. Deal 8(12) damage to ALL enemies. Exhaust.", "Exhaust": True, "Target": TargetType.AREA, "Function": use_dramaticentrance, "Damage": 8},
    # "Enlightenment": {"Name": "Enlightenment", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "Reduce the cost of cards in your hand to 1 this turn(combat)."},
    # "Finesse": {"Name": "Finesse", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "Gain 2(4) Block. Draw 1 card."},
    # "Flash of Steel": {"Name": "Flash of Steel", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.ATTACK, "Energy": 0, "Info": "Deal 3(6) damage. Draw 1 card."},
    # "Forethought": {"Name": "Forethought", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "Place a card(any number of cards) from your hand on the bottom of your draw pile. It (They) costs 0 until played."},
    # "Good Instincts": {"Name": "Good Instincts", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "Gain 6(9) Block."},
    # "Impatience": {"Name": "Impatience", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "If you have no Attack cards in your hand, draw 2(3) cards."},
    # "Jack Of All Trades": {"Name": "Jack Of All Trades", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "Add 1(2) random Colorless card(s) to your hand. Exhaust.", "Exhaust": True},
    # "Madness": {"Name": "Madness", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 1, "Energy+": 0, "Info": "A random card in your hand costs 0 for the rest of combat. Exhaust.", "Exhaust": True},
    # "Mind Blast": {"Name": "Mind Blast", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.ATTACK, "Energy": 2, "Energy+": 1, "Info": "Innate. Deal damage equal to the number of cards in your draw pile."},
    # "Panacea": {"Name": "Panacea", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "Gain 1(2) Artifact. Exhaust.", "Exhaust": True},
    # "Panic Button": {"Name": "Panic Button", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "Gain 30(40) Block. You cannot gain Block from cards for the next 2 turns. Exhaust.", "Exhaust": True},
    # "Purity": {"Name": "Purity", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "Choose and Exhaust 3(5) cards in your hand. Exhaust.", "Exhaust": True},
    # "Swift Strike": {"Name": "Swift Strike", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.ATTACK, "Energy": 0, "Info": "Deal 7(10) damage."},
    # "Trip": {"Name": "Trip", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.UNCOMMON, "Type": CardType.SKILL, "Energy": 0, "Info": "Apply 2 Vulnerable (to ALL enemies)."},

    "Apotheosis": {"Name": "Apotheosis", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.SKILL, "Energy": 2, "Energy+": 1, "Info": "Upgrade ALL of your cards for the rest of combat. Exhaust.", "Exhaust": True, "Target": TargetType.YOURSELF, "Function": use_apotheosis},
    "Chrysalis": {"Name": "Chrysalis", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.SKILL, "Energy": 2, "Info": "Add 3(5) random Skills into your Draw Pile. They cost 0 this combat. Exhaust.", "Exhaust": True, "Target": TargetType.YOURSELF, "Function": use_chrysalis},
    "Hand of Greed": {"Name": "Hand of Greed", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.ATTACK, "Energy": 2, "Info": "Deal 20(25) damage. If this kills a non-minion enemy, gain 20(25) Gold.", "Damage": 20, "Gold": 20, "Target": TargetType.ENEMY, "Function": use_handofgreed},
    # "Magnetism": {"Name": "Magnetism", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.POWER, "Energy": 2, "Energy+": 1, "Info": "At the start of each turn, add a random colorless card to your hand."},
    "Master Of Strategy": {"Name": "Master Of Strategy", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.SKILL, "Energy": 0, "Info": "Draw 3(4) cards. Exhaust.", "Exhaust": True, "Cards": 3, "Target": TargetType.YOURSELF, "Function": use_masterofstrategy},
    # "Mayhem": {"Name": "Mayhem", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.POWER, "Energy": 2, "Energy+": 1, "Info": "At the start of your turn, play the top card of your draw pile."},
    # "Metamorphosis": {"Name": "Metamorphosis", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.SKILL, "Energy": 2, "Info": "Add 3(5) random Attacks into your Draw Pile. They cost 0 this combat. Exhaust.", "Exhaust": True},
    # "Panache": {"Name": "Panache", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.POWER, "Energy": 0, "Info": "Every time you play 5 cards in a single turn, deal 10(14) damage to ALL enemies."},
    # "Sadistic Nature": {"Name": "Sadistic Nature", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.POWER, "Energy": 0, "Info": "Whenever you apply a Debuff to an enemy, they take 5(7) damage."},
    # "Secret Technique": {"Name": "Secret Technique", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.SKILL, "Energy": 0, "Info": "Choose a Skill from your draw pile and place it into your hand. Exhaust. (Don't Exhaust)", "Exhaust": True},
    # "Secret Weapon": {"Name": "Secret Weapon", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.SKILL, "Energy": 0, "Info": "Choose an Attack from your draw pile and place it into your hand. Exhaust. (Don't Exhaust)", "Exhaust": True},
    # "The Bomb": {"Name": "The Bomb", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.SKILL, "Energy": 2, "Info": "At the end of 3 turns, deal 40(50) damage to ALL enemies."},
    # "Thinking Ahead": {"Name": "Thinking Ahead", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.SKILL, "Energy": 0, "Info": "Draw 2 cards. Place a card from your hand on top of your draw pile. Exhaust. (Don't Exhaust.)", "Exhaust": True},
    # "Transmutation": {"Name": "Transmutation", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.SKILL, "Energy": -1, "Info": "Add X random (Upgraded) colorless cards into your hand. They cost 0 this turn. Exhaust.", "Exhaust": True},
    # "Violence": {"Name": "Violence", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.RARE, "Type": CardType.SKILL, "Energy": 0, "Info": "Place 3(4) random Attack cards from your draw pile into your hand. Exhaust.", "Exhaust": True},
    # "Apparition": {"Name": "Apparition", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.SPECIAL, "Type": CardType.SKILL, "Energy": 1, "Info": "Gain 1 Intangible. Exhaust. Ethereal. (no longer Ethereal.) (Obtained from event: Council of Ghosts).", "Exhaust": True},
    # "Beta": {"Name": "Beta", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.SPECIAL, "Type": CardType.SKILL, "Energy": 2, "Energy+": 1, "Info": "Shuffle an Omega into your draw pile. Exhaust.  (Obtained from Alpha).", "Exhaust": True},
    # "Bite": {"Name": "Bite", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.SPECIAL, "Type": CardType.ATTACK, "Energy": 1, "Info": "Deal 7(8) damage. Heal 2(3) HP. (Obtained from event: Vampires(?))."},
    # "Expunger": {"Name": "Expunger", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.SPECIAL, "Type": CardType.ATTACK, "Energy": 1, "Info": "Deal 9(15) damage X times. (Obtained from Conjure Blade)."},
    # "Insight": {"Name": "Insight", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.SPECIAL, "Type": CardType.SKILL, "Energy": 0, "Info": "Retain. Draw 2(3) cards. Exhaust. (Obtained from Evaluate, Pray and Study).", "Exhaust": True},
    # "J.A.X.": {"Name": "J.A.X.", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.SPECIAL, "Type": CardType.SKILL, "Energy": 0, "Info": "Lose 3 HP.  Gain 2(3) Strength. (Obtained from event: Augmenter)."},
    # "Miracle": {"Name": "Miracle", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.SPECIAL, "Type": CardType.SKILL, "Energy": 0, "Info": "Retain. Gain (2) Energy. Exhaust. (Obtained from Collect, Deus Ex Machina, PureWater-0 Pure Water, and Holy water Holy Water).", "Exhaust": True},
    # "Omega": {"Name": "Omega", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.SPECIAL, "Type": CardType.POWER, "Energy": 3, "Info": "At the end of your turn deal 50(60) damage to ALL enemies. (Obtained from Beta)."},
    # "Ritual Dagger": {"Name": "Ritual Dagger", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.SPECIAL, "Type": CardType.ATTACK, "Energy": 1, "Info": "Deal 15 damage. If this kills an enemy then permanently increase this card's damage by 3(5). Exhaust. (Obtained during event: The Nest)", "Exhaust": True},
    # "Safety": {"Name": "Safety", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.SPECIAL, "Type": CardType.SKILL, "Energy": 1, "Info": "Retain. Gain 12(16) Block. Exhaust. (Obtained from Deceive Reality).", "Exhaust": True},
    # "Shiv": {"Name": "Shiv", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.SPECIAL, "Type": CardType.ATTACK, "Energy": 0, "Info": "Deal 4(6) damage. Exhaust. (Obtained from Blade Dance, Cloak and Dagger, Infinite Blades, Storm of Steel, and NinjaScroll Ninja Scroll).", "Exhaust": True},
    # "Smite": {"Name": "Smite", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.SPECIAL, "Type": CardType.ATTACK, "Energy": 1, "Info": "Retain. Deal 12(16) damage. Exhaust. (Obtained from Carve Reality and Battle Hymn).", "Exhaust": True},
    "Through Violence": {"Name": "Through Violence", "Class": PlayerClass.COLORLESS, "Rarity": Rarity.SPECIAL, "Type": CardType.ATTACK, "Energy": 0, "Info": "Retain. Deal 20(30) damage. Exhaust. (Obtained from Reach Heaven).", "Exhaust": True, "Target": TargetType.ENEMY},
}

sacred_multi: int = 1
def activate_sacred_bark():
    global sacred_multi
    sacred_multi = 2
potions = {
    # Common | All Classes
    'Attack Potion': {'Name': 'Attack Potion', 'Cards': 1 * sacred_multi, 'Card Type': 'Attack', 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Add {"1" if sacred_multi < 2 else "2 copies"} of 3 random <keyword>Attack</keyword> cards to your hand, {"it" if sacred_multi < 2 else "they"} costs 0 this turn'},
    'Power Potion': {'Name': 'Power Potion', 'Cards': 1 * sacred_multi, 'Card Type': 'Power', 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Add {"1" if sacred_multi < 2 else "2 copies"} of 3 random <keyword>Power</keyword> cards to your hand, {"it" if sacred_multi < 2 else "they"} costs 0 this turn'},
    'Skill Potion': {'Name': 'Skill Potion', 'Cards': 1 * sacred_multi, 'Card Type': 'Skill', 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Add {"1" if sacred_multi < 2 else "2 copies"} of 3 random <keyword>Skill</keyword> cards to your hand, {"it" if sacred_multi < 2 else "they"} costs 0 this turn'},
    'Colorless Potion': {'Name': 'Colorless Potion', 'Cards': 1 * sacred_multi, 'Card Type': 'Colorless', 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Choose {"1" if sacred_multi < 2 else "2 copies"} of 3 random Colorless cards to add to your hand, {"it" if sacred_multi < 2 else "they"} costs 0 this turn'},
    'Block Potion': {'Name': 'Block Potion', 'Block': 12 * sacred_multi, 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Gain {12 * sacred_multi} <keyword>Block</keyword>'},
    'Dexterity Potion': {'Name': 'Dexterity Potion', 'Dexterity': 2 * sacred_multi, 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Gain {2 * sacred_multi} <buff>Dexterity</buff>'},
    'Energy Potion': {'Name': 'Energy Potion', 'Energy': 2 * sacred_multi, 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Gain {2 * sacred_multi} <keyword>Energy</keyword>'},
    'Explosive Potion': {'Name': 'Explosive Potion', 'Damage': 10 * sacred_multi, 'Target': 'Any', 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Deal {10 * sacred_multi} damage to ALL enemies'},
    'Fear Potion': {'Name': 'Fear Potion', 'Vulnerable': 3 * sacred_multi, 'Target': 'Enemy', 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Apply {3 * sacred_multi} <debuff>Vulnerable</debuff>'},
    'Fire Potion': {'Name': 'Fire Potion', 'Damage': 20 * sacred_multi, 'Target': 'Enemy', 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Deal {20 * sacred_multi} damage to target enemy'},
    'Flex Potion': {'Name': 'Flex Potion', 'Strength': 5 * sacred_multi, 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Gain {5 * sacred_multi} <buff>Strength</buff>. At the end of your turn lose {5 * sacred_multi} <buff>Strength</buff>'},
    'Speed Potion': {'Name': 'Speed Potion', 'Dexterity': 5 * sacred_multi, 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Gain {5 * sacred_multi} <buff>Dexterity</buff>. At the end of your turn, lose {5 * sacred_multi} <buff>Dexterity</buff>'},
    'Strength Potion': {'Name': 'Strength Potion', 'Strength': 2 * sacred_multi, 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Gain {2 * sacred_multi} <buff>Strength</buff>'},
    'Swift Potion': {'Name': 'Swift Potion', 'Cards': 3 * sacred_multi, 'Class': 'Any', 'Rarity': 'Common', 'Info': 'Draw 3 cards'},
    # Uncommon | All Classes
    'Ancient Potion': {'Name': 'Ancient Potion', 'Artifact': 1 * sacred_multi, 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': f'Gain {1 * sacred_multi} <buff>Artifact</buff>.'},
    'Distilled Chaos': {'Name': 'Distilled Chaos', 'Cards': 3 * sacred_multi, 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': f'Play the top {3 * sacred_multi} cards of your draw pile'},
    'Duplication Potion': {'Name': 'Duplication Potion', 'Cards': 1 * sacred_multi, 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': f'This turn, the next {"card is" if sacred_multi < 2 else "2 cards are"} played twice.'},
    'Essence of Steel': {'Name': 'Essence of Steel', 'Plated Armor': 4 * sacred_multi, 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': f'Gain {4 * sacred_multi} <buff>Plated Armor</buff>'},
    "Gambler's Brew": {'Name': "Gambler's Brew", 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': 'Discard any number of cards, then draw that many'},
    'Liquid Bronze': {'Name': 'Liquid Bronze', 'Thorns': 3 * sacred_multi, 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': f'Gain {3 * sacred_multi} <buff>Thorns</buff>'},
    'Liquid Memories': {'Name': 'Liquid Memories', 'Cards': 1 * sacred_multi, 'Class': 'Any', 'Rarity': 'Uncommon', 'Info': f'Choose {"a card" if sacred_multi < 2 else "2 cards"} in your discard pile and return {"it" if sacred_multi < 2 else "them"} to your hand. {"It" if sacred_multi < 2 else "They"} costs 0 this turn'},
    'Regen Potion': {'Name': 'Regen Potion', 'Regen': 5 * sacred_multi, 'Class': 'Any', 'Rarity': 'Common', 'Info': f'Gain {5 * sacred_multi} <buff>Regeneration</buff>.'},
    # Rare | All Classes
    'Cultist Potion': {'Name': 'Cultist Potion', 'Ritual': 1 * sacred_multi, 'Class': 'Any', 'Rarity': 'Rare', 'Info': f'Gain {1 * sacred_multi} <buff>Ritual</buff>'},
    'Entropic Brew': {'Name': 'Entropic Brew', 'Type': 'Entropic', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'Fill all your empty potion slots with random potions'},
    'Fairy in a Bottle': {'Name': 'Fairy in a Bottle', 'Playable': False, 'Revive Health': 0.3 * sacred_multi, 'Class': 'Any', 'Rarity': 'Rare', 'Info': f'When you would die, heal to {30 * sacred_multi}% of your Max HP instead and discard this potion'},
    'Fruit Juice': {'Name': 'Fruit Juice', 'Playable Everywhere?': True, 'Max Health': 5 * sacred_multi, 'Class': 'Any', 'Rarity': 'Rare', 'Info': f'Gain {5 * sacred_multi} Max HP'},
    'Smoke Bomb': {'Name': 'Smoke Bomb', 'Escape from boss': False, 'Target': 'Nothing', 'Class': 'Any', 'Rarity': 'Rare', 'Info': 'Escape from a non-boss combat. You recieve no rewards.'},
    'Sneko Oil': {'Name': 'Snecko Oil', 'Cards': 5 * sacred_multi, 'Type': 'Snecko', 'Class': 'Any', 'Rarity': 'Rare', 'Info': f'Draw {5 * sacred_multi} cards. Randomize the costs of all cards in your hand for the rest of combat.'},
    # Ironclad Potions
    'Blood Potion': {'Name': 'Blood Potion', 'Health': 0.2 * sacred_multi, 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Info': f'Heal for {20 * sacred_multi}% of your Max HP'},
    'Elixir': {'Name': 'Elixir', 'Class': 'Ironclad', 'Rarity': 'Uncommon', 'Info': 'Exhaust any number of cards in your hand'},
    'Heart of Iron': {'Name': 'Heart of Iron', 'Metallicize': 8 * sacred_multi, 'Class': 'Ironclad', 'Rarity': 'Rare', 'Info': f'Gain {8 * sacred_multi} <buff>Metallicize</buff>'},
    # Silent potion
    'Poison Potion': {'Name': 'Poison Potion', 'Poison': 6 * sacred_multi, 'Target': 'Enemy', 'Class': 'Silent', 'Rarity': 'Common', 'Info': f'Apply {6 * sacred_multi} <debuff>Poison</debuff> to target enemy'},
    # Shiv card doesn't not exist yet
    'Cunning Potion': {'Name': 'Cunning Potion', 'Shivs': 3 * sacred_multi, 'Card': 'placehold', 'Class': 'Silent', 'Rarity': 'Uncommon', 'Info': f'Add {3 * sacred_multi} <keyword>Upgraded</keyword> Shivs to your hand'},
    'Ghost in a Jar': {'Name': 'Ghost in a Jar', 'Intangible': 1 * sacred_multi, 'Class': 'Silent', 'Rarity': 'Rare', 'Info': f'Gain {1 * sacred_multi} <buff>Intangible</buff>.'},
    # Defect Potions
    'Focus Potion': {'Name': 'Focus Potion', 'Focus': 2 * sacred_multi, 'Class': 'Defect', 'Rarity': 'Common', 'Info': f'Gain {2 * sacred_multi} <buff>Focus</buff>'},
    'Potion of Capacity': {'Name': 'Potion of Capacity', 'Orb Slots': 2 * sacred_multi, 'Class': 'Defect', 'Rarity': 'Uncommon', 'Info': f'Gain {2 * sacred_multi} <keyword>Orb</keyword> slots'},
    'Essence of Darkness': {'Name': 'Essence of Darkness', 'Type': 'Dark Essence', 'Class': 'Defect', 'Rarity': 'Rare', 'Info': f'<keyword>Channel</keyword> {1 * sacred_multi} <keyword>Dark</keyword> for each <keyword>Orb</keyword> slot'},
    # Watcher Potions
    'Bottled Miracle': {'Name': 'Bottled Miracle', 'Miracles': 2 * sacred_multi, 'Card': 'placehold', 'Class': 'Watcher', 'Rarity': 'Common', 'Info': f'Add {2 * sacred_multi} Miracles to your hand'},
    'Stance Potion': {'Name': 'Stance Potion', 'Stances': ['Calm', 'Wrath'], 'Class': 'Watcher', 'Rarity': 'Uncommon', 'Info': 'Enter <keyword>Calm</keyword> or <keyword>Wrath</keyword>'},
    'Ambrosia': {'Name': 'Ambrosia', 'Stance': 'Divinity', 'Class': 'Watcher', 'Rarity': 'Rare', 'Info': 'Enter <keyword>Divinity</keyword>'}
}
