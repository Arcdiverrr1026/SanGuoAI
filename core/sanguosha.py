import random
import uuid
from typing import List, Dict, Any, Optional

# Card types and descriptions
CARD_TYPES = {
    "SHA": {"name": "杀", "type": "basic"},
    "SHAN": {"name": "闪", "type": "basic"},
    "TAO": {"name": "桃", "type": "basic"},
    "WUZHONG": {"name": "无中生有", "type": "scroll"},
    "CHAI": {"name": "过河拆桥", "type": "scroll"},
    "SHUN": {"name": "顺手牵羊", "type": "scroll"},
    "JUEDOU": {"name": "决斗", "type": "scroll"},
    "NANMAN": {"name": "南蛮入侵", "type": "scroll"},
    "WANJIAN": {"name": "万箭齐发", "type": "scroll"},
    "TAOYUAN": {"name": "桃园结义", "type": "scroll"},
    "WUXIE": {"name": "无懈可击", "type": "scroll"},
    "LENGBING": {"name": "诸葛连弩", "type": "equipment", "eq_type": "weapon", "range": 1},
    "QINGGANG": {"name": "青釭剑", "type": "equipment", "eq_type": "weapon", "range": 2},
    "QILIN": {"name": "麒麟弓", "type": "equipment", "eq_type": "weapon", "range": 5},
    "BAGUA": {"name": "八卦阵", "type": "equipment", "eq_type": "armor"},
    "PLUS_HORSE": {"name": "+1马", "type": "equipment", "eq_type": "def_horse"},
    "MINUS_HORSE": {"name": "-1马", "type": "equipment", "eq_type": "off_horse"}
}

SUITS = ["♥", "♦", "♠", "♣"]
CARDS_POOL = []
for card_key, info in CARD_TYPES.items():
    # Populate the deck with typical card proportions
    count = 4
    if card_key in ["SHA"]:
        count = 30
    elif card_key in ["SHAN"]:
        count = 15
    elif card_key in ["TAO"]:
        count = 8
    elif card_key in ["WUXIE"]:
        count = 6
    elif card_key in ["WUZHONG", "CHAI", "SHUN", "JUEDOU", "NANMAN", "WANJIAN"]:
        count = 3
    elif card_key in ["TAOYUAN", "LENGBING", "QINGGANG", "QILIN", "BAGUA", "PLUS_HORSE", "MINUS_HORSE"]:
        count = 2
        
    for _ in range(count):
        suit = random.choice(SUITS)
        value = random.randint(1, 13)
        CARDS_POOL.append({
            "id": str(uuid.uuid4())[:8],
            "key": card_key,
            "name": info["name"],
            "type": info["type"],
            "eq_type": info.get("eq_type"),
            "range": info.get("range"),
            "suit": suit,
            "color": "red" if suit in ["♥", "♦"] else "black",
            "value": value
        })

CHARACTERS = {
    "caocao": {"name": "曹操", "max_hp": 4, "skill": "奸雄", "desc": "受到伤害时，可获得造成伤害的牌"},
    "liubei": {"name": "刘备", "max_hp": 4, "skill": "仁德", "desc": "出牌阶段可将任意牌分给其他玩家，若给出的牌达2张，回复1点体力"},
    "sunquan": {"name": "孙权", "max_hp": 4, "skill": "制衡", "desc": "出牌阶段限一次，可弃置任意牌并摸等量的牌"},
    "guanyu": {"name": "关羽", "max_hp": 4, "skill": "武圣", "desc": "你可以将任意红色牌当【杀】使用或打出"},
    "zhangfei": {"name": "张飞", "max_hp": 4, "skill": "咆哮", "desc": "出牌阶段你可以无限次使用【杀】"},
    "zhaoyun": {"name": "赵云", "max_hp": 4, "skill": "龙胆", "desc": "你可以将【杀】当【闪】、【闪】当【杀】使用或打出"}
}

class SgsPlayer:
    def __init__(self, name: str, is_host: bool = False):
        self.name = name
        self.is_host = is_host
        self.character = ""
        self.identity = "" # Lord(主公), Loyalist(忠臣), Rebel(反贼), Defector(内奸)
        self.hp = 0
        self.max_hp = 0
        self.hand_cards = []
        self.weapon = None
        self.armor = None
        self.off_horse = None
        self.def_horse = None
        self.alive = True
        
        # Turn-based flags
        self.slashed_count = 0
        self.rende_given_count = 0
        self.zhiheng_used = False
        
    def to_dict(self, reveal_identity_to: Optional[str] = None) -> Dict[str, Any]:
        """Serialize player state. Hide identity and hand cards if not target player or Lord."""
        show_identity = (
            self.identity == "Lord" or 
            reveal_identity_to == self.name or 
            reveal_identity_to == "all_dead" # Show everyone at game over
        )
        return {
            "name": self.name,
            "is_host": self.is_host,
            "character": self.character,
            "identity": self.identity if show_identity else "???",
            "hp": self.hp,
            "max_hp": self.max_hp,
            "hand_count": len(self.hand_cards),
            "hand_cards": self.hand_cards if reveal_identity_to == self.name else [],
            "weapon": self.weapon,
            "armor": self.armor,
            "off_horse": self.off_horse,
            "def_horse": self.def_horse,
            "alive": self.alive
        }

class SgsGame:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: List[SgsPlayer] = []
        self.deck = []
        self.discard_pile = []
        self.is_started = False
        self.current_player_index = 0
        self.phase = "waiting" # waiting, select_character, normal_turn (drawing, playing, discarding), response_waiting, ended
        
        # Response wait states
        self.response_type = None # "shan" (for slash), "sha" (for nanman/duel), "shan_or_damage" (for wanjian), "wuxie" (for scrolls)
        self.response_source = None # Player who played the triggering card
        self.response_target = None # Player who needs to respond
        self.response_card = None # The card triggering this response
        self.response_target_list = [] # List of targets for AoE cards (e.g. Nanman, Wanjian)
        self.response_card_history = [] # Used for chain Nullification (无懈可击)
        self.duel_turn = None # Used for Duel (决斗) to track who must play Slash next
        
        self.logs = []
        self.winner = ""

    def add_log(self, msg: str):
        self.logs.append(msg)
        if len(self.logs) > 50:
            self.logs.pop(0)

    def join_player(self, name: str) -> bool:
        if self.is_started:
            return False
        if any(p.name == name for p in self.players):
            return True # Rejoining/Refresh
        if len(self.players) >= 8:
            return False
        is_host = len(self.players) == 0
        self.players.append(SgsPlayer(name, is_host))
        self.add_log(f"玩家 【{name}】 加入了房间。")
        return True

    def remove_player(self, name: str):
        # Allow removal if game not started
        if not self.is_started:
            self.players = [p for p in self.players if p.name != name]
            if self.players:
                self.players[0].is_host = True # Reassign host if host left
            self.add_log(f"玩家 【{name}】 离开了房间。")

    def start_game(self) -> bool:
        n = len(self.players)
        if n < 4 or n > 8:
            return False
            
        self.is_started = True
        self.add_log("游戏开始！正在洗牌与分配身份...")
        
        # 1. Distribute identities
        # 4 players: 1 Lord, 1 Loyalist, 1 Rebel, 1 Defector
        # 5 players: 1 Lord, 1 Loyalist, 2 Rebels, 1 Defector
        # 6 players: 1 Lord, 1 Loyalist, 3 Rebels, 1 Defector
        # 7 players: 1 Lord, 2 Loyalists, 3 Rebels, 1 Defector
        # 8 players: 1 Lord, 2 Loyalists, 4 Rebels, 1 Defector
        identities = ["Lord", "Loyalist", "Rebel", "Defector"]
        if n >= 5: identities.append("Rebel")
        if n >= 6: identities.append("Rebel")
        if n >= 7: identities.append("Loyalist")
        if n >= 8: identities.append("Rebel")
        
        random.shuffle(identities)
        for p, iden in zip(self.players, identities):
            p.identity = iden
            p.alive = True
            
        # Find Lord
        lord_idx = next(i for i, p in enumerate(self.players) if p.identity == "Lord")
        self.current_player_index = lord_idx
        self.add_log(f"主公是 【{self.players[lord_idx].name}】！")

        # 2. Select characters automatically or randomly for simplicity
        char_list = list(CHARACTERS.keys())
        random.shuffle(char_list)
        for i, p in enumerate(self.players):
            char_key = char_list[i % len(char_list)]
            p.character = char_key
            p.max_hp = CHARACTERS[char_key]["max_hp"]
            if p.identity == "Lord":
                p.max_hp += 1 # Lord gets extra HP
            p.hp = p.max_hp
            
        # 3. Setup deck
        self.deck = list(CARDS_POOL)
        random.shuffle(self.deck)
        
        # 4. Draw initial cards (Lord draws 5, others 4)
        for p in self.players:
            p.hand_cards = [self.draw_card() for _ in range(5 if p.identity == "Lord" else 4)]
            
        # Start turn
        self.phase = "normal_turn"
        self.start_draw_phase()
        return True

    def draw_card(self):
        if not self.deck:
            self.deck = list(self.discard_pile)
            self.discard_pile = []
            random.shuffle(self.deck)
            if not self.deck: # Out of cards completely
                return None
        return self.deck.pop()

    def start_draw_phase(self):
        p = self.players[self.current_player_index]
        p.slashed_count = 0
        p.rende_given_count = 0
        p.zhiheng_used = False
        
        c1 = self.draw_card()
        c2 = self.draw_card()
        drawn = []
        if c1: 
            p.hand_cards.append(c1)
            drawn.append(c1["name"])
        if c2: 
            p.hand_cards.append(c2)
            drawn.append(c2["name"])
            
        self.add_log(f"【{p.name}】 的回合开始，摸取了：{'、'.join(drawn)}。进入出牌阶段。")

    def end_turn(self):
        self.phase = "normal_turn"
        # Find next alive player
        n = len(self.players)
        for i in range(1, n + 1):
            idx = (self.current_player_index + i) % n
            if self.players[idx].alive:
                self.current_player_index = idx
                break
        self.start_draw_phase()

    def get_player_by_name(self, name: str) -> Optional[SgsPlayer]:
        for p in self.players:
            if p.name == name:
                return p
        return None

    def get_distance(self, from_player: SgsPlayer, to_player: SgsPlayer) -> int:
        """Calculate dynamic distance between two players in the circle (only counting alive players)."""
        alive_players = [p for p in self.players if p.alive]
        if from_player not in alive_players or to_player not in alive_players:
            return 99
            
        idx1 = alive_players.index(from_player)
        idx2 = alive_players.index(to_player)
        
        # Shortest distance in circle
        dist = min(abs(idx1 - idx2), len(alive_players) - abs(idx1 - idx2))
        
        # Apply horse modifiers
        if from_player.off_horse:
            dist -= 1
        if to_player.def_horse:
            dist += 1
            
        return max(1, dist)

    def get_attack_range(self, player: SgsPlayer) -> int:
        if player.weapon:
            return player.weapon.get("range", 1)
        return 1

    def handle_card_play(self, player_name: str, card_id: str, target_name: Optional[str] = None, conversion: Optional[str] = None) -> bool:
        """Handle standard card playing by a player."""
        p = self.get_player_by_name(player_name)
        if not p or not p.alive: return False
        
        # Locate the card in hand
        card = next((c for c in p.hand_cards if c["id"] == card_id), None)
        if not card: return False
        
        # Skill: Guan Yu's "Wusheng" (red card can be used as Slash)
        is_slash = card["key"] == "SHA"
        if conversion == "SHA" and p.character == "guanyu" and card["color"] == "red":
            is_slash = True
            card = dict(card, key="SHA", name="杀（武圣）")
            
        # Skill: Zhao Yun's "Longdan" (Shan can be used as Slash)
        if conversion == "SHA" and p.character == "zhaoyun" and card["key"] == "SHAN":
            is_slash = True
            card = dict(card, key="SHA", name="杀（龙胆）")

        # Verify target distance if needed
        t = self.get_player_by_name(target_name) if target_name else None
        
        # Apply logic per card key
        card_key = card["key"]
        
        if is_slash:
            if not t or not t.alive or t == p:
                return False
            # Check attack range (ignores if user has Blue Steel Sword/青釭剑 against defensive armor, but handles range normally)
            dist = self.get_distance(p, t)
            rng = self.get_attack_range(p)
            if dist > rng:
                self.add_log(f"错误: 目标超出攻击距离！当前距离 {dist}，攻击范围 {rng}")
                return False
                
            # Check if slashed this turn
            if p.slashed_count >= 1 and not (p.weapon and p.weapon["key"] == "LENGBING") and p.character != "zhangfei":
                return False
                
            p.hand_cards = [c for c in p.hand_cards if c["id"] != card_id]
            self.discard_pile.append(card)
            p.slashed_count += 1
            
            # Start response state: wait for Shan
            self.add_log(f"【{p.name}】 对 【{t.name}】 使用了 【{card['name']}】。")
            
            # Check target Armor (Bagua)
            if t.armor and t.armor["key"] == "BAGUA" and not (p.weapon and p.weapon["key"] == "QINGGANG"):
                self.phase = "response_waiting"
                self.response_type = "bagua_judge"
                self.response_source = p
                self.response_target = t
                self.response_card = card
            else:
                self.phase = "response_waiting"
                self.response_type = "shan"
                self.response_source = p
                self.response_target = t
                self.response_card = card

        elif card_key == "TAO":
            if p.hp >= p.max_hp:
                return False
            p.hand_cards = [c for c in p.hand_cards if c["id"] != card_id]
            self.discard_pile.append(card)
            p.hp += 1
            self.add_log(f"【{p.name}】 使用了 【桃】，恢复了 1 点体力。")

        elif card_key == "WUZHONG":
            p.hand_cards = [c for c in p.hand_cards if c["id"] != card_id]
            self.discard_pile.append(card)
            self.add_log(f"【{p.name}】 使用了 【无中生有】。")
            c1 = self.draw_card()
            c2 = self.draw_card()
            if c1: p.hand_cards.append(c1)
            if c2: p.hand_cards.append(c2)

        elif card_key == "CHAI":
            if not t or not t.alive or t == p: return False
            p.hand_cards = [c for c in p.hand_cards if c["id"] != card_id]
            self.discard_pile.append(card)
            self.add_log(f"【{p.name}】 对 【{t.name}】 使用了 【过河拆桥】。")
            self.steal_or_discard_card(t, discard=True)

        elif card_key == "SHUN":
            if not t or not t.alive or t == p: return False
            if self.get_distance(p, t) > 1: return False
            p.hand_cards = [c for c in p.hand_cards if c["id"] != card_id]
            self.discard_pile.append(card)
            self.add_log(f"【{p.name}】 对 【{t.name}】 使用了 【顺手牵羊】。")
            self.steal_or_discard_card(t, receiver=p)

        elif card_key == "JUEDOU":
            if not t or not t.alive or t == p: return False
            p.hand_cards = [c for c in p.hand_cards if c["id"] != card_id]
            self.discard_pile.append(card)
            self.add_log(f"【{p.name}】 对 【{t.name}】 发起了 【决斗】！")
            self.phase = "response_waiting"
            self.response_type = "sha"
            self.response_source = p
            self.response_target = t
            self.response_card = card
            self.duel_turn = t.name

        elif card_key == "NANMAN":
            p.hand_cards = [c for c in p.hand_cards if c["id"] != card_id]
            self.discard_pile.append(card)
            self.add_log(f"【{p.name}】 使用了 【南蛮入侵】！全体除使用本牌外都需要出一张杀。")
            self.response_target_list = [player for player in self.players if player.alive and player != p]
            self.trigger_next_aoe("sha")

        elif card_key == "WANJIAN":
            p.hand_cards = [c for c in p.hand_cards if c["id"] != card_id]
            self.discard_pile.append(card)
            self.add_log(f"【{p.name}】 使用了 【万箭齐发】！全体除使用本牌外都需要出一张闪。")
            self.response_target_list = [player for player in self.players if player.alive and player != p]
            self.trigger_next_aoe("shan")

        elif card_key == "TAOYUAN":
            p.hand_cards = [c for c in p.hand_cards if c["id"] != card_id]
            self.discard_pile.append(card)
            self.add_log(f"【{p.name}】 使用了 【桃园结义】。")
            for player in self.players:
                if player.alive and player.hp < player.max_hp:
                    player.hp += 1
                    self.add_log(f"【{player.name}】 体力回复 1 点。")

        elif card["type"] == "equipment":
            p.hand_cards = [c for c in p.hand_cards if c["id"] != card_id]
            eq_type = card["eq_type"]
            self.add_log(f"【{p.name}】 装备了 【{card['name']}】。")
            if eq_type == "weapon":
                if p.weapon: self.discard_pile.append(p.weapon)
                p.weapon = card
            elif eq_type == "armor":
                if p.armor: self.discard_pile.append(p.armor)
                p.armor = card
            elif eq_type == "def_horse":
                if p.def_horse: self.discard_pile.append(p.def_horse)
                p.def_horse = card
            elif eq_type == "off_horse":
                if p.off_horse: self.discard_pile.append(p.off_horse)
                p.off_horse = card
                
        else:
            return False
            
        return True

    def trigger_next_aoe(self, response_type: str):
        if not self.response_target_list:
            self.phase = "normal_turn"
            return
        next_target = self.response_target_list.pop(0)
        self.phase = "response_waiting"
        self.response_type = response_type
        self.response_target = next_target
        # If wanjian, target might have bagua
        if response_type == "shan" and next_target.armor and next_target.armor["key"] == "BAGUA":
            self.response_type = "bagua_judge"

    def handle_bagua_judge(self, player_name: str) -> bool:
        p = self.get_player_by_name(player_name)
        if not p or not p.alive or self.phase != "response_waiting" or self.response_type != "bagua_judge" or self.response_target != p:
            return False
            
        # Draw a judge card
        judge_card = self.draw_card()
        if not judge_card: return False
        
        self.discard_pile.append(judge_card)
        is_red = judge_card["color"] == "red"
        self.add_log(f"【{p.name}】 的八卦阵判定结果为 【{judge_card['suit']}{judge_card['value']}】 ({'红' if is_red else '黑'})。")
        
        if is_red:
            self.add_log(f"判定成功！八卦阵抵消了该次伤害。")
            # Proceed to end of this resolution
            self.resolve_current_response(negated=True)
        else:
            self.add_log("判定失败！请手动打出【闪】。")
            self.response_type = "shan" # Must play standard shan
        return True

    def resolve_current_response(self, negated: bool):
        """Finalize the current response question (e.g. Shan played or not)."""
        target = self.response_target
        source = self.response_source
        card = self.response_card
        
        if self.response_type in ["shan", "bagua_judge"]:
            if not negated: # Failed to Shan, take damage
                self.apply_damage(target, 1, source, card)
            self.phase = "normal_turn"
            
        elif self.response_type == "sha": # For Duel or Nanman
            if self.response_card["key"] == "JUEDOU":
                if not negated:
                    # Target failed to play Slash, target takes damage
                    self.apply_damage(target, 1, source, card)
                    self.phase = "normal_turn"
                else:
                    # Switch duel turn to source
                    self.duel_turn = source.name
                    self.response_target = source
                    self.response_source = target # source becomes responder
            else: # Nanman
                if not negated:
                    self.apply_damage(target, 1, source, card)
                self.trigger_next_aoe("sha")
                
        elif self.response_type == "shan_or_damage": # Wanjian
            if not negated:
                self.apply_damage(target, 1, source, card)
            self.trigger_next_aoe("shan")

    def apply_damage(self, target: SgsPlayer, damage: int, source: Optional[SgsPlayer] = None, card: Optional[Dict] = None):
        target.hp -= damage
        self.add_log(f"💥 【{target.name}】 受到 {damage} 点伤害，当前体力：{target.hp}/{target.max_hp}。")
        
        # Skill: Cao Cao's "Jianxiong"
        if target.character == "caocao" and card and target.alive:
            target.hand_cards.append(card)
            self.add_log(f"【{target.name}】 动用技能【奸雄】，获得了牌：【{card['name']}】。")
            if card in self.discard_pile:
                self.discard_pile.remove(card)
                
        if target.hp <= 0:
            self.check_dying(target, source)
        else:
            self.check_game_over()

    def check_dying(self, target: SgsPlayer, killer: Optional[SgsPlayer] = None):
        # Allow instant Peach saves if they have it
        peach = next((c for c in target.hand_cards if c["key"] == "TAO"), None)
        if peach:
            target.hand_cards = [c for c in target.hand_cards if c["id"] != peach["id"]]
            self.discard_pile.append(peach)
            target.hp += 1
            self.add_log(f"【{target.name}】 濒死时使用了 【桃】，保住了性命！")
            return
            
        # Target dies
        target.alive = False
        self.add_log(f"☠️ 玩家 【{target.name}】 阵亡了！身份是 【{target.identity}】。")
        
        # Discard all their cards
        for c in target.hand_cards:
            self.discard_pile.append(c)
        target.hand_cards = []
        if target.weapon: self.discard_pile.append(target.weapon)
        if target.armor: self.discard_pile.append(target.armor)
        if target.off_horse: self.discard_pile.append(target.off_horse)
        if target.def_horse: self.discard_pile.append(target.def_horse)
        target.weapon = target.armor = target.off_horse = target.def_horse = None
        
        # Rules: Lord kills Loyalist (discard all Lord's cards)
        if target.identity == "Loyalist" and killer and killer.identity == "Lord":
            self.add_log(f"主公诛杀忠臣！【{killer.name}】 弃置所有手牌与装备。")
            for c in killer.hand_cards:
                self.discard_pile.append(c)
            killer.hand_cards = []
            if killer.weapon: self.discard_pile.append(killer.weapon)
            if killer.armor: self.discard_pile.append(killer.armor)
            if killer.off_horse: self.discard_pile.append(killer.off_horse)
            if killer.def_horse: self.discard_pile.append(killer.def_horse)
            killer.weapon = killer.armor = killer.off_horse = killer.def_horse = None

        # Rules: Kill Rebel (draw 3 cards)
        if target.identity == "Rebel" and killer and killer.alive:
            self.add_log(f"击杀反贼！【{killer.name}】 获得了 3 张赏牌。")
            for _ in range(3):
                c = self.draw_card()
                if c: killer.hand_cards.append(c)

        self.check_game_over()

    def check_game_over(self):
        alive_identities = [p.identity for p in self.players if p.alive]
        lord_alive = "Lord" in alive_identities
        rebel_count = alive_identities.count("Rebel")
        defector_count = alive_identities.count("Defector")
        loyalist_count = alive_identities.count("Loyalist")
        
        if not lord_alive:
            if len(self.players) - len([p for p in self.players if p.alive]) == len(self.players) - 1 and defector_count == 1:
                # Defector won if only Defector remains alive and Lord dies last
                self.winner = "Defector"
                self.phase = "ended"
                self.add_log("游戏结束！【内奸】 获得全场胜利！")
            else:
                self.winner = "Rebel"
                self.phase = "ended"
                self.add_log("游戏结束！【反贼】 成功击杀主公，获得胜利！")
        elif rebel_count == 0 and defector_count == 0:
            self.winner = "Lord"
            self.phase = "ended"
            self.add_log("游戏结束！【主公】及【忠臣】 成功消灭所有反贼与内奸，获得胜利！")

    def handle_response(self, player_name: str, card_id: Optional[str], conversion: Optional[str] = None) -> bool:
        """Handle response when player is asked to play a card (Dodge for Slash, Slash for Duel)."""
        p = self.get_player_by_name(player_name)
        if not p or not p.alive or self.phase != "response_waiting" or self.response_target != p:
            return False
            
        if card_id is None: # Passed/took damage
            self.add_log(f"【{p.name}】 选择不出牌。")
            self.resolve_current_response(negated=False)
            return True
            
        # Verify card
        card = next((c for c in p.hand_cards if c["id"] == card_id), None)
        if not card: return False
        
        # Skill: Zhao Yun's "Longdan" (Slash can be used as Dodge, Dodge as Slash)
        expected_key = "SHAN" if self.response_type == "shan" else "SHA"
        is_match = card["key"] == expected_key
        
        if conversion == expected_key and p.character == "zhaoyun":
            if expected_key == "SHAN" and card["key"] == "SHA":
                is_match = True
                card = dict(card, key="SHAN", name="闪（龙胆）")
            elif expected_key == "SHA" and card["key"] == "SHAN":
                is_match = True
                card = dict(card, key="SHA", name="杀（龙胆）")
                
        # Skill: Guan Yu's "Wusheng" (red card can be used as Slash)
        if conversion == "SHA" and p.character == "guanyu" and card["color"] == "red" and expected_key == "SHA":
            is_match = True
            card = dict(card, key="SHA", name="杀（武圣）")

        if not is_match:
            return False
            
        p.hand_cards = [c for c in p.hand_cards if c["id"] != card_id]
        self.discard_pile.append(card)
        self.add_log(f"【{p.name}】 打出了 【{card['name']}】。")
        self.resolve_current_response(negated=True)
        return True

    def handle_rende(self, player_name: str, card_ids: List[str], target_name: str) -> bool:
        p = self.get_player_by_name(player_name)
        t = self.get_player_by_name(target_name)
        if not p or not p.alive or not t or not t.alive or p == t: return False
        if p.character != "liubei": return False
        
        # Move cards
        for cid in card_ids:
            card = next((c for c in p.hand_cards if c["id"] == cid), None)
            if card:
                p.hand_cards.remove(card)
                t.hand_cards.append(card)
                p.rende_given_count += 1
                
        self.add_log(f"【{p.name}】 发动技能【仁德】，将 {len(card_ids)} 张手牌交给了 【{t.name}】。")
        if p.rende_given_count >= 2 and p.hp < p.max_hp:
            p.hp += 1
            # Reset count to prevent repeated trigger on single card additions
            p.rende_given_count = 0
            self.add_log(f"【{p.name}】 仁德达 2 张牌，回复 1 点体力。")
            
        return True

    def handle_zhiheng(self, player_name: str, card_ids: List[str]) -> bool:
        p = self.get_player_by_name(player_name)
        if not p or not p.alive or p.character != "sunquan" or p.zhiheng_used: return False
        if not card_ids: return False
        
        # Discard chosen cards
        discarded_count = 0
        for cid in card_ids:
            card = next((c for c in p.hand_cards if c["id"] == cid), None)
            if card:
                p.hand_cards.remove(card)
                self.discard_pile.append(card)
                discarded_count += 1
                
        # Draw equal cards
        for _ in range(discarded_count):
            c = self.draw_card()
            if c: p.hand_cards.append(c)
            
        p.zhiheng_used = True
        self.add_log(f"【{p.name}】 发动技能【制衡】，弃置了 {discarded_count} 张手牌，并重新摸了同等数量的牌。")
        return True

    def steal_or_discard_card(self, target: SgsPlayer, receiver: Optional[SgsPlayer] = None, discard: bool = False):
        """Randomly takes or discards one card from the target player (hand, weapon, armor, def_horse, off_horse)."""
        available = []
        if target.hand_cards:
            available.append(("hand", target.hand_cards[0])) # Represent any hand card
        if target.weapon: available.append(("weapon", target.weapon))
        if target.armor: available.append(("armor", target.armor))
        if target.def_horse: available.append(("def_horse", target.def_horse))
        if target.off_horse: available.append(("off_horse", target.off_horse))
        
        if not available: return
        
        target_type, target_card = random.choice(available)
        
        # Remove from target
        if target_type == "hand":
            target_card = random.choice(target.hand_cards)
            target.hand_cards.remove(target_card)
        elif target_type == "weapon":
            target.weapon = None
        elif target_type == "armor":
            target.armor = None
        elif target_type == "def_horse":
            target.def_horse = None
        elif target_type == "off_horse":
            target.off_horse = None
            
        # Give to receiver or discard
        if discard:
            self.discard_pile.append(target_card)
            self.add_log(f"【{target.name}】 被弃置了一张牌：【{target_card['name']}】。")
        elif receiver:
            receiver.hand_cards.append(target_card)
            self.add_log(f"【{receiver.name}】 获得了 【{target.name}】 的一张牌：【{target_card['name']}】。")
