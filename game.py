import math
import random
from copy import copy, deepcopy
from functools import partial
from time import sleep

import game_map
from ansi_tags import ansiprint
from definitions import CombatTier, EncounterType, State
from enemy_catalog import (
    create_act1_boss,
    create_act1_elites,
    create_act1_normal_encounters,
)
from entities import player
from events import choose_event
from helper import active_enemies, combat_turn, ei, gen, potion_dropchance, view
from items import activate_sacred_bark, cards, potions, relics
from message_bus import bus
from shop import Shop

cards['Whirlwind']['Energy'] = player.energy

class Combat:
    def __init__(self, player, tier, gm, all_enemies=None):
        self.bus = bus
        self.player = player
        self.all_enemies = all_enemies if all_enemies else []
        self.active_enemies = list(filter(lambda enemy: enemy.state == State.ALIVE, self.all_enemies))
        self.previous_enemy_state = ()
        self.death_messages = []
        self.tier = tier
        self.game_map = gm
        self.turn = 1

    def main(self) -> None:

        self.start()

        if relics['Preserved Insect'] in player.relics and self.tier == CombatTier.ELITE:
            for enemy in self.active_enemies:
                enemy.health -= round(enemy.health * 0.25)
            ansiprint('<bold>Preserved Insect</bold> <blue>activated</blue>.')
        # Combat automatically ends when all enemies are dead.
        while len(self.active_enemies) > 0:
            player.start_turn()
            for enemy in self.active_enemies:
                enemy.start_turn()
            while True:
                print(f"Turn {self.turn}: ")
                _ = player.draw_cards(True, 1) if len(player.hand) == 0 and relics['Unceasing Top'] in player.relics else None # Assigned to _ so my linter shuts up
                # Shows the player's potions, cards(in hand), amount of cards in discard and draw pile, and shows the status for you and the enemies.
                view.display_ui(player, self.active_enemies)
                print("1-0: Play card, P: Play Potion, M: View Map, D: View Deck, A: View Draw Pile, S: View Discard Pile, X: View Exhaust Pile, E: End Turn, F: View Debuffs and Buffs")
                action = input("> ").lower()
                other_options = {
                    'd': lambda: view.view_piles(player.deck, player), 
                    'a': lambda: view.view_piles(player.draw_pile, player),
                    's': lambda: view.view_piles(player.discard_pile, player), 
                    'x': lambda: view.view_piles(player.exhaust_pile, player),
                    'p': self.play_potion, 
                    'f': lambda: ei.full_view(player, self.active_enemies), 
                    'm': lambda: view.view_map(self.game_map)
                }
                if action.isdigit():
                    option = int(action) - 1
                    if option + 1 in range(len(player.hand) + 1):
                        self.play_card(player.hand[option])
                    else:
                        view.clear()
                        continue
                elif action in other_options:
                    other_options[action]()
                elif action == 'e':
                    view.clear()
                    break
                else:
                    view.clear()
                    continue
                sleep(1)
                view.clear()
            player.end_player_turn()
            for enemy in self.active_enemies:
                enemy.execute_move()
                input('Press enter to continue > ')
                view.clear()
            self.turn += 1

    def end(self, killed_enemies=False, escaped=False, robbed=False):
        global potion_dropchance
        if killed_enemies is True:
            player.in_combat = False
            player.hand.clear()
            player.discard_pile.clear()
            player.draw_pile.clear()
            player.exhaust_pile.clear()
            potion_roll = random.randint(0, 100)
            ansiprint("<green>Combat finished!</green>")
            player.gain_gold(random.randint(10, 20) * 1 if relics['Golden Idol'] not in player.relics else 1.25)
            if potion_roll < potion_dropchance or relics['White Beast Statue'] in player.relics:
                gen.claim_potions(True, 1, player, potions)
                potion_dropchance -= 10
            else:
                potion_dropchance += 10
            for _ in range(int(relics['Prayer Wheel'] in player.relics) + 1):
                gen.card_rewards(self.tier, True, player, cards)
            sleep(1.5)
            view.clear()
        elif escaped is True:
            self.active_enemies.clear()
            print("Escaped...")
            player.in_combat = False
            sleep(0.8)
            print("You recieve nothing.")
            sleep(1.5)
            view.clear()
        elif robbed:
            self.active_enemies.clear()
            print("Robbed...")
            player.in_combat = False
            sleep(0.8)
            print("You recieve nothing.")
            sleep(1.2)
            view.clear()

    def start(self):
        player.in_combat = True
        # Shuffles the player's deck into their draw pile
        player.draw_pile = random.sample(player.deck, len(player.deck))
        if not self.all_enemies:
            act1_normal_encounters  = create_act1_normal_encounters()
            act1_elites = create_act1_elites()
            act1_boss = create_act1_boss()
            encounter_types = {
                CombatTier.NORMAL: act1_normal_encounters,
                CombatTier.ELITE: act1_elites,
                CombatTier.BOSS: act1_boss
            }
            encounter_enemies = encounter_types[self.tier][0]
            self.all_enemies = encounter_enemies

        self.active_enemies = list(filter(lambda enemy: enemy.state == State.ALIVE, self.all_enemies))
        player.start_of_combat_relics(self.tier)
        return act1_boss[0].name

    def play_potion(self):
        if len(player.potions) == 0:
            ansiprint("<red>You have no potions.</red>")
            return
        if relics['Sacred Bark'] in player.relics:
            activate_sacred_bark()
        view.view_potions(player.potions, player.max_potions)
        raise NotImplementedError

    def play_card(self, card):
        while True:
            # Prevents the player from using a card that they don't have enough energy for.
            energy_cost = card.get("Energy", float('inf')) if card.get("Energy", float('inf')) != -1 else player.energy
            if energy_cost > player.energy:
                ansiprint("<red>You don't have enough energy to use this card.</red>")
                sleep(1)
                view.clear()
                return
            if player.choker_cards_played == 6:
                ansiprint("You have already played 6 cards this turn!")
                sleep(1)
                view.clear()
                return
            if card.get("Target") == 'Single' and len(self.active_enemies) > 1:
                try:
                    target = int(input("Choose an enemy to target > ")) - 1
                    _ = self.active_enemies[target]
                except (IndexError, ValueError):
                    ansiprint(f"\u001b[1A\u001b[100D<red>You have to enter a number between 1 and {len(self.active_enemies)}</red>", end='')
                    sleep(1)
                    print("\u001b[2K\u001b[100D", end='')
                    continue
            elif len(self.active_enemies) == 1:
                target = 0
            else:
                target = 0
            player.use_card(card, self.active_enemies[target], False, player.hand)
            break

    def update(self):
        self.state_check()
        self.previous_enemy_state = tuple(enemy.state for enemy in self.all_enemies)
        self.self.active_enemies = list(filter(lambda enemy: enemy.state == State.ALIVE, self.all_enemies))

    def state_check(self):
        current_states = tuple(enemy.state for enemy in self.all_enemies)

        for i in range(max(1, len(self.all_enemies) - 1)):
            if self.previous_enemy_state[i] != current_states[i]:
                self.death_messages.append(current_states[i])

def rest_site():
    """
    Actions:
    Rest: Heal for 30% of you max hp(rounded down)
    Upgrade: Upgrade 1 card in your deck(Cards can only be upgraded once unless stated otherwise)*
    Lift: Permanently gain 1 Strength(Requires Girya, can only be used 3 times in a run)*
    Toke: Remove 1 card from your deck(Requires Peace Pipe)*
    Dig: Obtain 1 random Relic(Requires Shovel)*
    Recall: Obtain the Ruby Key(Max 1 use, availible in normal runs when Act 4 is unlocked)*
    **Not finished
    """
    valid_inputs = ['rest', 'smith']
    if relics['Ancient Tea Set'] in player.relics and not player.ancient_tea_set:
        player.ancient_tea_set = True
        ansiprint('<bold>Ancient Tea Set activated</bold>')
    while True:
        ansiprint(player)
        ansiprint("You come across a <green>Rest Site</green>")
        if relics['Eternal Feather'] in player.relics:
            player.health_actions(len(player.deck) // 5 * 3, "Heal")
        sleep(1)
        ansiprint(f"<bold>[Rest]</bold> <green>Heal for 30% of your <light-blue>Max HP</light-blue>({math.floor(player.max_health * 0.30 + 15 if relics['Regal Pillow'] in player.relics else 0)})</green> \n<bold>[Smith]</bold> <green><keyword>Upgrade</keyword> a card in your deck</green> ")
        ansiprint("+15 from <bold>Regal Pillow</bold>\n" if relics['Regal Pillow'] in player.relics else '', end='')
        relic_actions = {'Girya': ('lift', "<bold>[Lift]</bold> <green>Gain 1 <light-cyan>Strength</light-cyan></green>"),
            'Peace Pipe': ('toke', "<bold>[Toke]</bold> <green>Remove a card from your deck</green>"),
            'Shovel': ('dig', "<bold>[Dig]</bold> <green>Obtain a relic</green>")}
        for relic_name, (action, message) in relic_actions.items():
            if relics[relic_name] in player.relics:
                valid_inputs.append(action)
                ansiprint(message, end='')
        action = input('> ').lower()
        if action not in valid_inputs:
            ansiprint("<red>Valid Inputs: " + valid_inputs + "</red>")
            sleep(1.5)
            view.clear()
            continue
        if action == 'rest':
            if relics['Coffee Dripper'] in player.relics:
                ansiprint("<red>You cannot rest because of </red><bold>Coffee Dripper</bold>.")
                sleep(1)
                view.clear()
                continue
            # heal_amount is equal to 30% of the player's max health rounded down.
            heal_amount = math.floor(player.max_health * 0.30)
            if relics['Regal Pillow'] in player.relics:
                heal_amount += 15
            sleep(1)
            view.clear()
            player.health_actions(heal_amount, "Heal")
            if relics['Dream Catcher'] in player.relics:
                ansiprint('<bold><italic>Dreaming...</italic></bold>')
                gen.card_rewards(CombatTier.NORMAL, True, player, cards)
            break
        if action == 'smith':
            if relics['Fusion Hammer'] in player.relics:
                ansiprint("<red>You cannot smith because of <bold>Fusion Hammer</bold>.</red>")
                sleep(1.5)
                view.clear()
                continue
            upgrade_card = view.list_input('What card do you want to upgrade?', player.deck, view.view_piles, lambda card: not card.get("Upgraded") and (card['Type'] not in ("Status", "Curse") or card['Name'] == 'Burn'), "That card is not upgradeable.")
            player.deck[upgrade_card] = player.card_actions(player.deck[upgrade_card], 'Upgrade', cards)
            break
        if action == 'lift':
            if player.girya_charges > 0:
                ei.apply_effect(player, 'Strength', 1)
                player.girya_charges -= 1
                if player.girya_charges == 0:
                    ansiprint('<bold>Girya</bold> is depleted')
                break
            ansiprint('You cannot use <bold>Girya</bold> anymore')
            sleep(1.5)
            view.clear()
            continue
        if action == 'toke':
            option = view.list_input('What card would you like to remove? > ', player.deck, view.view_piles, lambda card: card.get("Removable") is False, "That card is not removable.")
            player.deck[option] = player.card_actions(player.deck[option], 'Remove', cards)
            break
        if action == 'dig':
            gen.claim_relics(False, player, 1, relics, None, False)
            break
    while True:
        ansiprint("<bold>[View Deck]</bold> or <bold>[Leave]</bold>")
        option = input("> ").lower()
        if option == 'view deck':
            view.view_piles(player.deck)
            input("Press enter to leave > ")
            sleep(0.5)
            view.clear()
            break
        if option == 'leave':
            sleep(1)
            view.clear()
            break
        print("Invalid input")
        sleep(1.5)
        view.clear()

def unknown(game_map) -> None:
    # Chances
    normal_combat: float = 0.1
    treasure_room: float = 0.02
    merchant: float = 0.03
    # Event chance is equal to 1 minus all the previous chances
    random_number = random.random()

    if random_number < treasure_room:
        treasure_room = 0.02
        normal_combat += 0.1
        merchant += 0.03
    elif random_number < merchant:
        merchant = 0.03
        treasure_room += 0.02
        normal_combat += 0.1
    elif random_number < normal_combat:
        normal_combat = 0.1
        treasure_room += 0.02
        merchant += 0.03
        Combat(player, CombatTier.NORMAL, game_map).main()
    else:
        ansiprint(player)
        chosen_event = choose_event()
        chosen_event()

def play(encounter: EncounterType, gm: game_map.GameMap):
    if encounter.type == EncounterType.START:
        pass
    elif encounter.type == EncounterType.REST_SITE:
        return rest_site()
    elif encounter.type == EncounterType.UNKNOWN:
        return unknown(game_map)
    elif encounter.type == EncounterType.BOSS:
        return Combat(player, CombatTier.BOSS, gm).main()
    elif encounter.type == EncounterType.ELITE:
        return Combat(player, CombatTier.ELITE, gm).main()
    elif encounter.type == EncounterType.NORMAL:
        return Combat(player, CombatTier.NORMAL, gm).main()
    elif encounter.type == EncounterType.SHOP:
        return Shop(player).loop()
    else:
        raise game_map.MapError(f"Encounter type {encounter} is not valid.")

def main(seed=None):
    if seed is not None:
        random.seed(seed)
    gm = game_map.create_first_map()
    gm.pretty_print()
    for encounter in gm:
        play(encounter, gm)
        player.floors += 1
        gm.pretty_print()
