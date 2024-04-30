
# The shop contains:
# 5 Colored cards:
#  - 2 Attack cards, 2 skill cards, and 1 Power card
#    - Common: 45-55 Gold
#    - Uncommon: 68-82 Gold
#    - Rare: 135-165 Gold
#  - One card is always on sale by 50%
# 2 Colorless Cards:
# - uncommmon on the left (81-99)
# - Rare on the right (162-198)
# Relics:
# Shop Relic on the right:
#   Common: 143 - 157 Gold
#   Uncommon: 238 - 262 Gold
#   Rare: 285 - 315 Gold
#   Shop: 143 - 157 Gold
# Potions:
# Common: 48 - 52 Gold
# Uncommon: 72 - 78 Gold
# Rare: 95 - 105 Gold
# Card Removal Service
# Can only be used once per shop.
# Costs 75 Gold initially, increases cost by 25 Gold every time it is used at any shop.
# Woo.... lots of stuff to do here.

import random
import time

from ansi_tags import ansiprint
from definitions import CardCategory, PlayerClass, Rarity
from helper import Displayer
from items import cards, potions, relics


# Helper functions for displaying cards, potions, and relics.
# These really should be inside the classes for those items
#------------------------------------------------------------
def card_pretty_string(card, valid):
  if valid:
    changed_energy = 'light-red' if not card.get('Changed Energy') else 'green'
    return f"<{card['Rarity'].lower()}>{card['Name']}</{card['Rarity'].lower()}> | <{card['Type'].lower()}>{card['Type']}</{card['Type'].lower()}> | <{changed_energy}>{card.get('Energy', 'Unplayable')}{' Energy' if card.get('Energy') is not None else ''}</{changed_energy}> | <yellow>{card['Info']}</yellow>".replace('Σ', '').replace('Ω', '')
  else:
    return f"<light-black>{card['Name']} | {card['Type']} | {card.get('Energy', 'Unplayable')}{' Energy' if card.get('Energy') else ''} | {card['Info']}</light-black>".replace('Σ', '').replace('Ω', '')

def relic_pretty_string(relic, valid):
  if valid:
    name_colors = {
      'Starter': 'starter',
      'Common': 'white',
      'Uncommon': 'uncommon',
      'Rare': 'rare',
      'Event': 'event',
      'Shop': 'rare',
      'Boss': 'rare',
      'Special': 'rare'}
    return f"<{name_colors[relic['Rarity']]}>{relic['Name']}</{name_colors[relic['Rarity']]}> | {relic['Class']} | <yellow>{relic['Info']}</yellow> | <dark-blue><italic>{relic['Flavor']}</italic></dark-blue>"
  else:
    return f"<light-black>{relic['Name']} | {relic['Class']} | {relic['Info']} | {relic['Flavor']}</light-black>"

def potion_pretty_string(potion, valid):
  if valid:
    class_colors = {'Ironclad': 'red', 'Silent': 'dark-green', 'Defect': 'true-blue', 'Watcher': 'watcher-purple', 'Any': 'white'}
    rarity_colors = {'Common': 'white', 'Uncommon': 'uncommon', 'Rare': 'rare'}
    chosen_class_color = class_colors[potion['Class']]
    chosen_rarity_color = rarity_colors[potion['Rarity']]
    return f"<{chosen_rarity_color}>{potion['Name']}</{chosen_rarity_color}> | <{chosen_class_color}>{potion['Class']}</{chosen_class_color}> | <yellow>{potion['Info']}</yellow>"
  else:
    return f"<light-black>{potion['Name']} | {potion['Class']} | {potion['Info']}</light-black>"

def determine_item_category(item) -> CardCategory:
  # A massive hack to try to figure out if we've got a card, potion, or relic
  try:
    name = item['Name']
  except KeyError as e:
    raise KeyError(f'The following item has no Name: {item}') from e
  card_names = [c['Name'] for c in cards.values()]
  potion_names = [p['Name'] for p in potions.values()]
  relic_names = [r['Name'] for r in relics.values()]
  if name in card_names:
    return CardCategory.CARD
  elif name in potion_names:
    return CardCategory.POTION
  elif name in relic_names:
    return CardCategory.RELIC
  else:
    raise ValueError(f"Item {item} not found in any category")

def category_to_pretty_string(item, valid):
  category = determine_item_category(item)
  if category == CardCategory.CARD:
    return card_pretty_string(item, valid)
  elif category == CardCategory.POTION:
    return potion_pretty_string(item, valid)
  elif category == CardCategory.RELIC:
    return relic_pretty_string(item, valid)
  else:
    raise ValueError(f"Category {category} not understood.")
#------------------------------------------------------------

class SellableItem():
    '''A class to represent an item that can be sold in the shop. This is a wrapper around the actual item, and includes a price.'''
    def __init__(self, item, price=None, discount=0.0):
        self.item = item
        self.item_category = determine_item_category(item)
        if price is not None:
          self.price = price
        else:
          self.price = self.set_price()
        self.discount = discount

    def __repr__(self):
        return f"Sellable({self.item['Name']})"

    def invalid_string(self):
        pretty_string = category_to_pretty_string(self.item, valid=False)
        return f"<light-black>{self.price:3d} Gold</light-black> : {pretty_string}"

    def valid_string(self):
        pretty_string = category_to_pretty_string(self.item, valid=True)
        full_string = f"<yellow>{self.price:3d} Gold</yellow> : {pretty_string}"
        return full_string

    def set_price(self) -> int:
        '''Set the price of the item based on its rarity.'''
        assert "Rarity" in self.item, f"Item {self.item} has no rarity."
        assert "Class" in self.item, f"Item {self.item} has no class."
        if self.item_category == CardCategory.CARD and self.item["Class"] != PlayerClass.COLORLESS:
            if self.item["Rarity"] in (Rarity.BASIC, Rarity.COMMON, Rarity.STARTER):
                return random.randint(45, 55)
            elif self.item["Rarity"] == Rarity.UNCOMMON:
                return random.randint(68, 82)
            elif self.item["Rarity"] == Rarity.RARE:
                return random.randint(135, 165)
            else:
                raise ValueError(f"Cannot determine price. Unexpected rarity for card: {self.item['Rarity']}")

        elif self.item_category == CardCategory.CARD and self.item["Class"] == PlayerClass.COLORLESS:
            if self.item["Rarity"] == Rarity.UNCOMMON:
                return random.randint(81, 99)
            elif self.item["Rarity"] == Rarity.RARE:
                return random.randint(162, 198)
            else:
                raise ValueError(f"Cannot determine colorless card price.Unexpected rarity for colorless card: {self.item['Rarity']}")

        elif self.item_category == CardCategory.POTION:
          if self.item["Rarity"] == Rarity.COMMON:
              return random.randint(48, 52)
          elif self.item["Rarity"] == Rarity.UNCOMMON:
              return random.randint(72, 78)
          elif self.item["Rarity"] == Rarity.RARE:
              return random.randint(95, 105)
          else:
              raise ValueError(f"Unexpected rarity for potion: {self.item['Rarity']}")

        elif self.item_category == CardCategory.RELIC:
          if self.item["Rarity"] in (Rarity.COMMON, Rarity.STARTER):
              return random.randint(143, 157)
          elif self.item["Rarity"] == Rarity.UNCOMMON:
              return random.randint(238, 262)
          elif self.item["Rarity"] == Rarity.RARE:
              return random.randint(285, 315)
          elif self.item["Rarity"] == Rarity.SHOP:
              return random.randint(143, 157)
          else:
              raise ValueError(f"Unexpected rarity for relic: {self.item['Rarity']}")

        else:
            raise ValueError(f"Unable to set price -- Item category not understood: {self.item_category}")

class Shop():
    def __init__(self, player, items=None):
      self.player = player
      if items is None:
        self.items = self.initialize_items()
      else:
        self.items = items

    def split_by_category(self, sellables:list[SellableItem]=None) -> dict[CardCategory, list[SellableItem]]:
      if sellables is None:
        sellables = self.items
      ret = {
        CardCategory.CARD: [],
        CardCategory.POTION: [],
        CardCategory.RELIC: []
      }
      for sellable in sellables:
        ret[determine_item_category(sellable.item)].append(sellable)
      return ret

    def initialize_items(self) -> list[SellableItem]:
      return self.initialize_cards() + self.initialize_relics() + self.initialize_potions()

    def initialize_relics(self):
      items = []
      all_relics = list(relics.values())
      shop_relics = [r for r in all_relics if r["Rarity"] == Rarity.SHOP]
      if len(shop_relics) >= 1:
        items.extend(random.sample(shop_relics, 1))
      return [SellableItem(item) for item in items]

    def initialize_potions(self):
      items = []
      all_potions = list(potions.values())
      sellable_potions = [p for p in all_potions if p["Rarity"] in (Rarity.COMMON, Rarity.UNCOMMON, Rarity.RARE)]
      if len(sellable_potions) >= 2:
        items.extend(random.sample(sellable_potions, 2))
      return [SellableItem(item) for item in items]

    def initialize_cards(self):
      items = []
      all_cards = list(cards.values())
      attack_cards = [c for c in all_cards if c["Type"] == "Attack" and c["Class"] != "Colorless"]
      skill_cards = [c for c in all_cards if c["Type"] == "Skill" and c["Class"] != "Colorless"]
      power_cards = [c for c in all_cards if c["Type"] == "Power" and c["Class"] != "Colorless"]
      if len(attack_cards) >= 2:
        items.extend(random.sample(attack_cards, 2))
      if len(skill_cards) >= 2:
        items.extend(random.sample(skill_cards, 2))
      if len(power_cards) >= 1:
        items.extend(random.sample(power_cards, 1))

      colorless_cards = [c for c in all_cards if "Class" in c and c["Class"] == "Colorless"]
      colorless_uncommon = [c for c in colorless_cards if c["Rarity"] == Rarity.UNCOMMON]
      colorless_rare = [c for c in colorless_cards if c["Rarity"] == Rarity.RARE]
      if len(colorless_uncommon) >= 1:
        items.extend(random.sample(colorless_uncommon, 1))
      if len(colorless_rare) >= 1:
        items.extend(random.sample(colorless_rare, 1))
      return [SellableItem(item) for item in items]

    def loop(self):
      while True:
        ansiprint(f"Welcome to the shop! You have {self.player.gold} gold.")
        choice = Displayer().list_input(
          input_string="Buy something?",
          choices=self.items,
          displayer=self.display,
          validator=self.validator,
          extra_allowables=['e'])
        if choice == 'e':
          break
        self.buy(choice)

    def buy(self, choice):
      self.player.gold -= self.items[choice].price
      self.player.deck.append(self.items[choice].item)
      ansiprint(f"<bold>You bought {self.items[choice].item['Name']} for {self.items[choice].price} gold</bold>.")
      time.sleep(0.5)
      input("Press Enter to continue...")

    def validator(self, item):
      return item.price <= self.player.gold

    def display(self, items, validator):
      organized = self.split_by_category()
      ansiprint("<bold>CARDS</bold>")
      for idx, item in enumerate(organized[CardCategory.CARD]):
        if validator(item):
          ansiprint(f"{idx+1}: {item.valid_string()}")
        else:
          ansiprint(f"{idx+1}: {item.invalid_string()}")

      ansiprint("<bold>POTIONS</bold>")
      for idx, item in enumerate(organized[CardCategory.POTION]):
        if validator(item):
          ansiprint(f"{idx+1+len(organized[CardCategory.CARD])}: {item.valid_string()}")
        else:
          ansiprint(f"{idx+1+len(organized[CardCategory.CARD])}: {item.invalid_string()}")

      ansiprint("<bold>RELICS</bold>")
      for idx, item in enumerate(organized[CardCategory.RELIC]):
        if validator(item):
          ansiprint(f"{idx+1+len(organized[CardCategory.CARD])+len(organized[CardCategory.POTION])}: {item.valid_string()}")
        else:
          ansiprint(f"{idx+1+len(organized[CardCategory.CARD])+len(organized[CardCategory.POTION])}: {item.invalid_string()}")

      ansiprint("<bold>SERVICES</bold>")
      ansiprint("r: Card REMOVAL Service (tbd)")
      ansiprint("")
      ansiprint("e: Exit Shop")