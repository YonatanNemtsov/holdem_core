"""Holdem game core classes"""

from time import sleep
import itertools
from enum import Enum
from dataclasses import dataclass, field
import random

if __name__ == '__main__':
    from deuces import deuces as hand_ranker
else:
    from .deuces import deuces as hand_ranker
    
class CardDeck(list):
    suites = ['h','d','c','s']
    ranks = ['2','3','4','5','6','7','8','9','T','J','Q','K','A']
    def __init__(self):
        super().__init__(p[0]+p[1] for p in itertools.product(self.ranks,self.suites))
        self.shuffle()
    
    def shuffle(self):
        random.shuffle(self)

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
        assert(self.chips > 0)

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
    players: list[HoldemRoundPlayer]
    first_to_move: HoldemRoundPlayer
    
    stage: HoldemRoundStage = HoldemRoundStage.NOT_STARTED
    log: list = field(default_factory=list) 
    bets: dict = field(default_factory=lambda: { # each bet is represented as (sit, bet_type, call_amount, raise_amount)
        HoldemRoundStage.PREFLOP.value:[],
        HoldemRoundStage.FLOP.value:[],
        HoldemRoundStage.TURN.value:[],
        HoldemRoundStage.RIVER.value:[]
    }, repr=False)

    winners: dict[HoldemRoundPlayer:int] = field(default_factory=dict, repr=False) # of the form {winner: amount}
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
    
    def get_player_by_sit(self, sit: int) -> HoldemRoundPlayer:
        for p in self.players:
            if p.sit == sit:
                return p
        return None 
    

    def get_allowed_moves(self, player: HoldemRoundPlayer) -> dict:
        """ Returns the allowed moves of player, output of the form:
        
        {
            moves: list[move_names...],
            call_amount: int
            min_raise_amount: int
            max_raise_amount: int
        }

        for check, fold min_amount = max_amount = None
        """
        allowed_moves = {'moves': [], 'call_amount': 0, 'min_raise_amount': 0, 'max_raise_amount': 0}
        if not self.stage in (HoldemRoundStage.FLOP,HoldemRoundStage.PREFLOP,HoldemRoundStage.RIVER,HoldemRoundStage.TURN):
            return allowed_moves
        

        
        if self.to_move != player:
            return allowed_moves
        
        if player.chips == 0:
            allowed_moves['moves'].append('check')
            return allowed_moves
        
        non_all_in_players = len([p for p in self.players if not p.chips==0])
        if all((non_all_in_players == 1, self.get_call_amount(player) == 0)):
            allowed_moves['moves'].append('check')
            return allowed_moves
        
        if player.folded:
            return allowed_moves
        
        allowed_moves['moves'].append('fold')
        
        call_amount = self.get_call_amount(player)
        if call_amount > 0:
            allowed_moves['moves'].append('call')
            allowed_moves['call_amount'] = call_amount
        else:
            allowed_moves['moves'].append('check')
        
        min_raise_amount = self.get_min_raise_amount(player)
        if min_raise_amount > 0:
            allowed_moves['moves'].append('raise')
            allowed_moves['min_raise_amount'] = min_raise_amount
            allowed_moves['max_raise_amount'] = self.get_max_raise_amount(player)
        
        return allowed_moves



    
    def get_player_total_bet_in_stage(self, player: HoldemRoundPlayer, stage: HoldemRoundStage) -> int:
        return  sum([0]+[bet[2]+bet[3] for bet in self.bets[stage] if bet[0]==player.sit])
    
    def get_player_total_bet(self,player: HoldemRoundPlayer) -> int:
        return sum([self.get_player_total_bet_in_stage(player,stage) for stage in self.bets.keys()])
    
    def get_call_amount(self, player: HoldemRoundPlayer) -> int:
        """ returns the amount a player has to call to continue hand. """
        biggest_total_bet_in_stage = max([self.get_player_total_bet_in_stage(p,self.stage.value) for p in self.players])
        player_total_bet_in_stage = self.get_player_total_bet_in_stage(player, self.stage.value)
        return min(player.chips, biggest_total_bet_in_stage - player_total_bet_in_stage)
    
    def get_largest_raise_in_stage(self, stage: HoldemRoundStage):
        return max([0] +[bet[3] for bet in self.bets[stage]])
    
    def is_betting_open(self):
        raised_amount = 0
        betting_open = True
        for bet in self.bets[self.stage.value]:
            if bet[0] == 'raise':
                if bet[3] >= raised_amount:
                    raised_amount = bet[3]
                    betting_open = True
                else:
                    betting_open = False
        return betting_open

    def get_max_raise_amount(self, player: HoldemRoundPlayer) -> int:
        """ Returns the maximal amount a player can raise. Returns 0 if betting is closed."""
        if not self.is_betting_open():
            return 0
        
        return player.chips - self.get_call_amount(player)
    
    def get_min_raise_amount(self, player: HoldemRoundPlayer) -> int:
        """ returns minimal amount of chips a player is allowed to raise. returns 0 if raise is not allowed. """
        max_raise_amount = self.get_max_raise_amount(player)
        return min(max_raise_amount, max(2*self.config.small_blind, self.get_largest_raise_in_stage(self.stage.value)))
    
    def get_min_total_bet(self, player: HoldemRoundPlayer) -> int:
        return self.get_call_amount(player) + self.get_min_raise_amount()
    
    @staticmethod
    def join_pots(pots: dict) -> dict:
        
        if len(pots) == 1:
            return pots
        
        new_pots = {}
        bet_ranks = list(reversed(sorted(pots.keys())))
        bet_rank = bet_ranks[0]
        for br in bet_ranks[1:]:
            print(br)
            if len([p.sit for p in pots[br]['players']]) == len([p.sit for p in pots[bet_rank]['players']]):
                print(10)
                new_bet_rank = br + bet_rank
                new_pot = pots[br]['pot'] + pots[bet_rank]['pot']
                new_pots[new_bet_rank] = {'pot': new_pot, 'players':pots[br]['players']}
                bet_rank = new_bet_rank
            else:
                bet_rank = br
        return new_pots

    def make_pots(self):
        """
        create self.pots from self.bets

        self.pots = {
            bet_rank: {
                'pot': (bet_rank(n) - bet_rank(n-1)) * num_of_players_in_bet_rank
                'players':[player1, player2, ...]

            }
            
        }

        Thus one player can win several pots of different "bet_ranks".
        
        """
        ordered_total_bets = sorted([(p, self.get_player_total_bet(p)) for p in self.players], key=lambda x:x[1])
        pots = dict()
        bet_rank = 0
        for count,(player,bet) in enumerate(ordered_total_bets):
            if bet > bet_rank:
                pots[bet] = {'pot':(bet-bet_rank) * (len(ordered_total_bets) - count),'players':[]}
                bet_rank = bet
            for bet_rank in pots:
                if not player.folded:
                    pots[bet_rank]['players'].append(player)

        new_pots = self.join_pots(pots)

        self.pots = new_pots
        print(new_pots)
    
    def determine_pots_winners(self) -> None:
        assert self.stage in (HoldemRoundStage.NO_SHOWDOWN,HoldemRoundStage.SHOWDOWN)
        not_folded_players = [p for p in self.players if not p.folded]

        if len(not_folded_players) == 1:
            assert self.stage == HoldemRoundStage.NO_SHOWDOWN
            for bet_rank in self.pots:
                self.winners[bet_rank] = [not_folded_players[0].sit]
            return
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
            print(self.winners)

    def distribute_pot_of_rank(self,rank: int):
        pass

    def distribute_pots(self):
        assert self.stage in (HoldemRoundStage.NO_SHOWDOWN, HoldemRoundStage.SHOWDOWN)
        assert len(self.winners) > 0
        
        for player in self.players:
            for bet_rank in self.winners:
                if player.sit in self.winners[bet_rank]:
                    player.chips += self.pots[bet_rank]['pot']//len(self.winners[bet_rank])

        self.pots = dict()


    def deal_cards(self):
        self.deck = CardDeck()
        for player in self.players:
            player.cards = [self.deck.pop(),self.deck.pop()]
    
    def post_blinds(self):
        sb_player = self.move_queue.player_order[-2]
        bb_player = self.move_queue.player_order[-1]
        #print(sb_player.sit, bb_player.sit)
        sb_player.chips -= min(sb_player.chips, self.config.small_blind)
        bb_player.chips -= min(bb_player.chips, 2*self.config.small_blind)
        self.bets['preflop'].append((sb_player.sit, 'raise', 0, self.config.small_blind))
        self.bets['preflop'].append((bb_player.sit, 'raise', self.config.small_blind, self.config.small_blind))
        self.log.append(
            {
                'action': 'sb',
                'call_amount': 0,
                'raise_amount': self.config.small_blind, 
                'sit': sb_player.sit, 
                'stage': 'preflop'
                }
        )
        self.log.append(
            {
                'action': 'bb',
                'call_amount': self.config.small_blind,
                'raise_amount': self.config.small_blind, 
                'sit': bb_player.sit, 
                'stage': 'preflop'
                }
        )

    def validate_game_setup(self):
        if self.stage is not HoldemRoundStage.NOT_STARTED:
            raise Exception("Game already started!")
        if len(self.players) <= 1:
            raise Exception("Can't start game with less than two players!")
    
    def start(self):
        self.validate_game_setup()
        self.deal_cards()
        self.post_blinds()
        self.stage = HoldemRoundStage.PREFLOP
        self.to_move = self.move_queue.get()

        #print(self.to_move)
    
    # TODO: refactor: start_showdown(), start_flop(), etc...
    def start_next_stage(self):
        print('next stage starting...')
        if len([p for p in self.players if not p.folded]) == 1:
                if self.stage in [HoldemRoundStage.PREFLOP, HoldemRoundStage.FLOP, HoldemRoundStage.TURN, HoldemRoundStage.RIVER]:
                    self.stage = HoldemRoundStage.NO_SHOWDOWN
                elif self.stage == HoldemRoundStage.NO_SHOWDOWN:
                    self.stage = HoldemRoundStage.ENDED
        
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

    def get_last_move(self, player: HoldemRoundPlayer):
        last_move = {}
        for event in self.log:
            if event['sit'] == player.sit and event['stage'] == self.stage.value:
                last_move = event.copy()
                
        return last_move

    #TODO: make this better. Currently not in use.
    def get_round_view(self, player: HoldemRoundPlayer = None):
        view = {
            'personal_info': {
                'sit':player.sit if player else -1,
                'player_cards': player.cards if player else -1,
            },

            'shared_info': {
                'players': [p.sit for p in  self.players],
            }
            
        }
        
        return view
    
    def get_hand_rank_name(self, player: HoldemRoundPlayer):
        evaluator = hand_ranker.Evaluator()

        player_cards = [hand_ranker.Card.new(c) for c in player.cards]
        community_cards = [hand_ranker.Card.new(c) for c in self.community_cards]
        
        rank = evaluator.evaluate(player_cards, community_cards)
        print(evaluator.table)
        hand_name = evaluator.class_to_string(evaluator.get_rank_class(rank))
        return hand_name
    
    """ Game Requests Handlers """

    @staticmethod
    def is_valid_check(allowed_moves: dict, request: dict):
        return True
    
    @staticmethod
    def is_valid_call(allowed_moves: dict, request: dict):
        if allowed_moves['call_amount'] != request['call_amount']:
            return False
        if request['raise_amount'] != 0:
            return False
        
        return True
    
    @staticmethod
    def is_valid_raise(allowed_moves: dict, request: dict):
        if allowed_moves['call_amount'] != request['call_amount']:
            return False
        if request['raise_amount'] > allowed_moves['max_raise_amount']:
            return False
        if request['raise_amount'] < allowed_moves['min_raise_amount']:
            return False
        
        return True
    
    @staticmethod
    def is_valid_fold(allowed_moves: dict, request: dict):
        return True
    
    VALIDATE = {
        'check':is_valid_check,
        'call':is_valid_call,
        'raise':is_valid_raise,
        'fold':is_valid_fold,
    }
    
    def validate_game_request(self, player: HoldemRoundPlayer, request: dict):
        allowed_moves = self.get_allowed_moves(player)
        
        if not request['action'] in allowed_moves['moves']:
            return False
        
        if not self.stage in (HoldemRoundStage.FLOP,HoldemRoundStage.PREFLOP,HoldemRoundStage.RIVER,HoldemRoundStage.TURN):
            print('Move not allowed - game ended.')
            return False

        return self.VALIDATE[request['action']](allowed_moves, request)
    

    def apply_check(self, player: HoldemRoundPlayer, request: dict):
        return
    
    def apply_call(self, player: HoldemRoundPlayer, request: dict):
        self.bets[self.stage.value].append((player.sit, request['action'], request['call_amount'], request['raise_amount']))
        player.chips -= (request['call_amount']+request['raise_amount'])

    def apply_raise(self, player: HoldemRoundPlayer, request: dict):
        self.bets[self.stage.value].append((player.sit, request['action'], request['call_amount'], request['raise_amount']))
        player.chips -= (request['call_amount']+request['raise_amount'])

    def apply_fold(self, player: HoldemRoundPlayer, request: dict):
        player.folded = True
    
    APPLY = {
        'check':apply_check,
        'call':apply_call,
        'raise':apply_raise,
        'fold':apply_fold,
    }

    # TODO: should probably be in abstract class

    def apply_game_request(self, player: HoldemRoundPlayer , request: dict):
        log_record = request.copy()
        log_record.update({'stage': self.stage.value})
        self.log.append(log_record)
        self.APPLY[request['action']](self, player, request)

        if request['action'] == 'raise':
            self.move_queue.extend_due_to_raise(player)

    # TODO: should probably be in abstract class

    def process_game_request(self, request: dict) -> None:
        """
        Main function interface for game requests.

        Requests should be of the form:
        {
            'sit': int, # sit of player
            'type': str, # one of 'fold','raise','check','call'
            'call_amount': int, # present if call or raise
            'raise_amount': int, # presest if call or raise
        }

        """

        player = self.get_player_by_sit(request['sit'])
        if not self.validate_game_request(player, request):
            print(request['action'] + ' not allowed.')
            return {'type':'move_response', 'success':False}
        
        self.apply_game_request(player, request)
        return {'type':'move_response', 'success':True}

def main():
    player1 = HoldemRoundPlayer(sit=1, chips=1000)
    player2 = HoldemRoundPlayer(sit=2, chips=100)
    player3 = HoldemRoundPlayer(sit=3, chips=100, cards=[])

    config = HoldemRoundConfig(10,0)
    game = HoldemRound(config, [player1,player2,player3], player1)
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
    print(game.get_allowed_moves(player1))
    res = game.process_game_request({
        'sit':1,
        'move':'raise',
        'call_amount':0,
        'raise_amount':100,
        }
    
    )
    print(res)
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
    print(game.get_player_by_sit(4))
    print(game.get_hand_rank_name(player1))

if __name__ == '__main__':
    main()