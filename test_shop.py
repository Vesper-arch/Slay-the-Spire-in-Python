# test the shop
import pytest

import entities
import items
from ansi_tags import ansiprint
from shop import SellableItem, Shop


class TestSellableItems():
  def test_colored_cards(self):
    '''See that we can make sellable items out of all cards and that they display correctly'''
    all_sellable_cards = list(items.cards.values())
    all_sellable_cards = [card for card in all_sellable_cards if card["Type"] in ("Attack", "Skill", "Power") and
                          card["Rarity"] not in ("Special", "Boss") and
                          card['Class'] != 'Colorless']
    for card in all_sellable_cards:
      sellable = SellableItem(card)
      ansiprint(sellable.valid_string())
      ansiprint(sellable.invalid_string())
      # Lets also check that the gold values are within the expected ranges
      # Common: 45 - 55 Gold
      # Uncommon: 68 - 82 Gold
      # Rare: 135 - 165 Gold
      if card["Rarity"] == "Common":
        assert 45 <= sellable.price <= 55
      elif card["Rarity"] == "Uncommon":
        assert 68 <= sellable.price <= 82
      elif card["Rarity"] == "Rare":
        assert 135 <= sellable.price <= 165

  def test_colorless_cards(self):
    all_sellable_cards = list(items.cards.values())
    all_sellable_cards = [card for card in all_sellable_cards if card["Type"] in ("Attack", "Skill", "Power") and
                          card["Rarity"] not in ("Special", "Boss") and
                          card['Class'] == 'Colorless']
    for card in all_sellable_cards:
      sellable = SellableItem(card)
      ansiprint(sellable.valid_string())
      ansiprint(sellable.invalid_string())
      # Lets also check that the gold values are within the expected ranges
      # - uncommmon  (81-99)
      # - Rare (162-198)
      if card["Rarity"] == "Uncommon":
        assert 81 <= sellable.price <= 99
      elif card["Rarity"] == "Rare":
        assert 162 <= sellable.price <= 198

  def test_potions(self):
    '''See that we can make sellable items out of all potions and that they display correctly'''
    all_sellable_potions = list(items.potions.values())
    for potion in all_sellable_potions:
      sellable = SellableItem(potion)
      ansiprint(sellable.valid_string())
      ansiprint(sellable.invalid_string())
      # Lets also check that the gold values are within the expected ranges
      # Common: 48 - 52 Gold
      # Uncommon: 72 - 78 Gold
      # Rare: 95 - 105 Gold
      if potion["Rarity"] == "Common":
        assert 48 <= sellable.price <= 52
      elif potion["Rarity"] == "Uncommon":
        assert 72 <= sellable.price <= 78
      elif potion["Rarity"] == "Rare":
        assert 95 <= sellable.price <= 105

  def test_relics(self):
    '''See that we can make sellable items out of all relics and that they display correctly'''
    all_sellable_relics = list(items.relics.values())
    all_sellable_relics = [relic for relic in all_sellable_relics if relic["Rarity"] not in ("Event", "Special", "Boss")]
    for relic in all_sellable_relics:
      sellable = SellableItem(relic)
      ansiprint(sellable.valid_string())
      ansiprint(sellable.invalid_string())
      # Lets also check that the gold values are within the expected ranges
      # Common: 143 - 157 Gold
      # Uncommon: 238 - 262 Gold
      # Rare: 285 - 315 Gold
      # Shop: 143 - 157 Gold
      if relic["Rarity"] == "Common":
        assert 143 <= sellable.price <= 157
      elif relic["Rarity"] == "Uncommon":
        assert 238 <= sellable.price <= 262
      elif relic["Rarity"] == "Rare":
        assert 285 <= sellable.price <= 315
      elif relic["Rarity"] == "Shop":
        assert 143 <= sellable.price <= 157

def test_buying_a_card(monkeypatch):
  player = entities.create_player()
  cards = [SellableItem(items.cards[x]) for x in ("Strike","Body Slam","Heavy Blade","Warcry")]
  shop = Shop(player, cards)
  responses = iter(['1', '\n', 'e'])
  with monkeypatch.context() as m:
    m.setattr('builtins.input', lambda *a, **kw: next(responses))
    shop.loop()

@pytest.mark.skip("Manual test requires user input.")
def test_buying_cards_MANUAL():
  player = entities.create_player()
  shop = Shop(player)
  shop.loop()