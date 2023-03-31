# Holdem game core classes

from time import sleep
import itertools
from enum import Enum
from dataclasses import dataclass, field
import random
import deuces.deuces as hand_ranker

class CardDeck(list):
    suites = ['h','d','c','s']
    ranks = ['2','3','4','5','6','7','8','9','T','J','Q','K','A']
    def __init__(self):
        super().__init__(p[0]+p[1] for p in itertools.product(self.ranks,self.suites))
        self.shuffle()
    
    def shuffle(self):
        random.shuffle(self)

class BettingPots:
    def __init__(self):
        self.pots = dict()
    
@dataclass
class HoldemRoundPlayer:
    """ Represents a player for a single round (or hand) of a Texas Hold'em game """
    sit: int
    chips: int
    cards: list = field(default_factory=list,repr=False)
    folded: bool = field(default=False,repr=False)

    def __post_init__(self):
        self.validate_player()

    def validate_player(self):
        assert(
            all((
                isinstance(self.sit, int),
                isinstance(self.cards, list),
                isinstance(self.chips, int),
                isinstance(self.folded, bool),
            ))
        )

        assert(10 > self.sit > 0)
        assert(self.chips >= 0)

class PlayerQueue:
    def __init__(self,player_order: list[HoldemRoundPlayer]):
        self.player_order = player_order
        self.queue = player_order.copy()
    
    def get(self):
        return self.queue.pop(0)
    
    def put(self,player):
        self.queue.append(player)

    def __len__(self):
        return len(self.queue)
    def __repr__(self):
        return self.queue.__repr__()
    
    def extend_due_to_raise(self,player):
        for p in self.player_order[self.player_order.index(player)+1:] + self.player_order[:self.player_order.index(player)]:
            if not p.folded and not p in self.queue:
                self.put(p)
    
    def remake_due_to_new_betting_round(self):
        self.queue = []
        for p in self.player_order:
            if not p.folded:
                self.put(p)

@dataclass
class HoldemRoundConfig:
    small_blind: int
    ante: int

class HoldemRoundStage(Enum):
    NOT_STARTED = 'not started'
    PREFLOP = 'preflop'
    FLOP = 'flop'
    TURN = 'turn'
    RIVER = 'river'
    SHOWDOWN = 'showdown'
    NO_SHOWDOWN = 'no showdown'
    ENDED = 'ended'

@dataclass
class HoldemRound:
    """Main class that represents the state of a Holdem round (or hand)."""
    config: HoldemRoundConfig
    table_name: str
    players: list[HoldemRoundPlayer]
    first_to_move: HoldemRoundPlayer
    
    stage: HoldemRoundStage = HoldemRoundStage.NOT_STARTED
    log: list = field(default_factory=list) 
    bets: dict = field(default_factory=lambda: { # each bet is represented as (sit, bet_type, call_amount, raise_amount)
        HoldemRoundStage.PREFLOP:[],
        HoldemRoundStage.FLOP:[],
        HoldemRoundStage.TURN:[],
        HoldemRoundStage.RIVER:[]
    }, repr=False)

    winners: dict[HoldemRoundPlayer:int] = field(default_factory=dict, repr=False)
    community_cards: list[str] = field(default_factory=list)
    pots: dict = field(default_factory=dict)
    move_queue: PlayerQueue = field(init=False, repr=False)
    to_move: HoldemRoundPlayer = field(init=False)
    deck: CardDeck = field(init=False, repr=False)

    def __post_init__(self):
        self.players = sorted(self.players,key=lambda p:p.sit)
        move_order = self.players[self.players.index(self.first_to_move):] +  self.players[:self.players.index(self.first_to_move)]
        self.move_queue = PlayerQueue(move_order)
        self.to_move = None
    
    def get_allowed_moves(self, player: HoldemRoundPlayer) -> list[str]:
        return ('fold', 'call', 'check', 'raise')
    
    def get_player_total_bet_in_stage(self, player: HoldemRoundPlayer, stage: HoldemRoundStage) -> int:
        return  sum([0]+[bet[2]+bet[3] for bet in self.bets[stage] if bet[0]==player.sit])
    
    def get_player_total_bet(self,player: HoldemRoundPlayer) -> int:
        return sum([self.get_player_total_bet_in_stage(player,stage) for stage in self.bets.keys()])
    
    def get_call_amount(self, player: HoldemRoundPlayer) -> int:
        biggest_total_bet_in_stage = max([self.get_player_total_bet_in_stage(p,self.stage) for p in self.players])
        player_total_bet_in_stage = self.get_player_total_bet_in_stage(player, self.stage)
        return min(player.chips, biggest_total_bet_in_stage - player_total_bet_in_stage)
    
    def get_largest_raise_in_stage(self, stage: HoldemRoundStage):
        return max(bet[3] for bet in self.bets[stage])
    
    def get_min_raise_amount(self) -> int:
        return max(2*self.config.small_blind, self.get_largest_raise_in_stage(self.stage))
    
    def get_min_total_bet(self, player: HoldemRoundPlayer) -> int:
        return self.get_call_amount(player) + self.get_min_raise_amount()
    
    def make_pots(self):
        """
        create self.pots from self.bets

        self.pots = {
            bet_rank: {
                'pot': (bet_rank(n) - bet_rank(n-1)) * num_of_players_in_bet_rank
                'players':[player1, player2, ...]

            }
            
        }
        
        """
        ordered_total_bets = sorted([(p, self.get_player_total_bet(p)) for p in self.players], key=lambda x:x[1])
        pots = dict()
        bet_rank = 0
        for count,(player,bet) in enumerate(ordered_total_bets):
            if bet > bet_rank:
                pots[bet] = {'pot':(bet-bet_rank) * (len(ordered_total_bets) - count),'players':[]}
                bet_rank = bet
            for bet_rank in pots:
                pots[bet_rank]['players'].append(player)
        self.pots = pots
    
    def determine_pots_winners(self) -> list[HoldemRoundPlayer]:
        assert self.stage in (HoldemRoundStage.NO_SHOWDOWN,HoldemRoundStage.SHOWDOWN)
        not_folded_players = [p for p in self.players if not p.folded]
        if len(not_folded_players) == 1:
            return [not_folded_players[0]]
        
        evaluator = hand_ranker.Evaluator()
        for bet_rank in self.pots:
            hand_ranks = dict()
            for p in self.pots[bet_rank]['players']:
                if p.folded:
                    continue

                player_cards = [hand_ranker.Card.new(c) for c in p.cards]
                community_cards = [hand_ranker.Card.new(c) for c in self.community_cards]
                
                hand_ranks[p.sit] = evaluator.evaluate(player_cards, community_cards)
        
            self.winners[bet_rank] = [sit for sit in  hand_ranks if sit == min(hand_ranks, key=hand_ranks.get)] # todo: use filter instead
    def distribute_pot_of_rank(self,rank: int):
        pass

    def distribute_pots(self):
        assert self.stage in (HoldemRoundStage.NO_SHOWDOWN,HoldemRoundStage.SHOWDOWN)
        assert len(self.winners)>0
        
        for player in self.players:
            for bet_rank in self.winners:
                if player.sit in self.winners[bet_rank]:
                    player.chips += self.pots[bet_rank]['pot']//len(self.winners[bet_rank])

        self.pots = dict()


    def deal_cards(self):
        self.deck = CardDeck()
        for player in self.players:
            player.cards = [self.deck.pop(),self.deck.pop()]
    
    def validate_game_setup(self):
        if self.stage is not HoldemRoundStage.NOT_STARTED:
            raise Exception("Game already started!")
        if len(self.players) <= 1:
            raise Exception("Can't start game with less than two players!")
    
    def start(self):
        self.validate_game_setup()
        self.deal_cards()
        self.stage = HoldemRoundStage.PREFLOP
        self.to_move = self.move_queue.get()
        print(self.to_move)
    
    # refactor: start_showdown(), start_flop(), etc...
    def start_next_stage(self):
        print('next stage starting...')
        if 1 == len([p for p in self.players if not p.folded]):
                if self.stage in [HoldemRoundStage.PREFLOP, HoldemRoundStage.FLOP, HoldemRoundStage.TURN, HoldemRoundStage.RIVER]:
                    self.stage = HoldemRoundStage.NO_SHOWDOWN
        
        elif self.stage == HoldemRoundStage.PREFLOP:
            self.move_queue.remake_due_to_new_betting_round()
            self.community_cards += [self.deck.pop() for i in range(3)]
            self.to_move = self.move_queue.get()
            self.stage = HoldemRoundStage.FLOP
        
        elif self.stage == HoldemRoundStage.FLOP:
            self.move_queue.remake_due_to_new_betting_round()
            self.community_cards += [self.deck.pop()]
            self.to_move = self.move_queue.get()
            self.stage = HoldemRoundStage.TURN
        
        elif self.stage == HoldemRoundStage.TURN:
            self.move_queue.remake_due_to_new_betting_round()
            self.community_cards += [self.deck.pop()]
            self.to_move = self.move_queue.get()
            self.stage = HoldemRoundStage.RIVER
        
        elif self.stage == HoldemRoundStage.RIVER:
            self.stage = HoldemRoundStage.SHOWDOWN
        
        elif self.stage in (HoldemRoundStage.SHOWDOWN,HoldemRoundStage.NO_SHOWDOWN):
            self.stage = HoldemRoundStage.ENDED
        return
    
    def start_next_move(self):
        if len(self.move_queue) == 0:
            self.start_next_stage()
        else:
            self.to_move = self.move_queue.get()
    
    def print_round_state(self):
        print(f' stage: {self.stage},\n to move: {self.to_move},\n queue: {self.move_queue},\n bets: {self.bets}')

def main():
    player1 = HoldemRoundPlayer(sit=1, chips=1000)
    player2 = HoldemRoundPlayer(sit=2, chips=100)
    player3 = HoldemRoundPlayer(sit=3, chips=100, cards=[])

    config = HoldemRoundConfig(10,0)
    game = HoldemRound(config, 'table', [player1,player2,player3], player1)
    game.start()
    game.bets[game.stage].append((1,'raise',0,20))
    game.start_next_move()
    game.bets[game.stage].append((2,'call',20,0))
    game.start_next_move()
    player3.folded = True
    game.start_next_move()
    game.print_round_state()
    game.bets[game.stage].append((1,'raise',0,20))
    game.move_queue.extend_due_to_raise(player1)
    game.start_next_move()
    game.bets[game.stage].append((2,'raise',20,20))
    game.move_queue.extend_due_to_raise(player2)
    game.start_next_move()
    game.bets[game.stage].append((1,'call',20,0))
    game.make_pots()
    game.start_next_move()
    game.print_round_state()
    game.start_next_move()
    game.start_next_move()
    game.print_round_state()
    game.start_next_move()
    game.start_next_move()
    game.print_round_state()
    game.make_pots()
    game.determine_pots_winners()
    print(game.winners,game.community_cards,player1.cards,player2.cards)
    game.distribute_pots()
    print(player1.chips,player2.chips)
if __name__ == '__main__':
    main()