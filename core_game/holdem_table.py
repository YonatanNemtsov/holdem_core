from dataclasses import dataclass, field

if __name__ == '__main__':
    from holdem_round import (
        HoldemRound,
        HoldemRoundConfig,
        HoldemRoundPlayer,
        HoldemRoundStage,
    )
    
else:
    from .holdem_round import (
        HoldemRound,
        HoldemRoundConfig,
        HoldemRoundPlayer,
        HoldemRoundStage,
    )

@dataclass
class HoldemTablePlayer:
    id: str
    table_id: str
    sit: int
    chips: int
    active: bool = True
    round_player: HoldemRoundPlayer = None
    def __post_init__(self):
        self.round_player = self.make_round_player()

    def make_round_player(self):
        if self.round_player != None:
            self.sync_chips()
        self.round_player = HoldemRoundPlayer(self.sit,self.chips)

    def sync_chips(self):
        self.chips = self.round_player.chips
    
@dataclass
class HoldemTableConfig:
    small_blind: int
    ante: int
    min_buyin: int
    max_buyin: int
    num_of_sits: int

class HoldemTable:
    """ Represents a poker table.
    This object includes the interface for sit requests, and game move requests,
    recieved from a user, and for general controll of a poker table, like starting a hand
    """

    # TODO: "players" Should probably be a dict {'sit':player}...
    def __init__(self, table_id: str, config: HoldemTableConfig):
        self.table_id: str = table_id
        self.config: HoldemTableConfig = config
        self.players: list[HoldemTablePlayer] = []
        self.dealer: HoldemTablePlayer = None
        self.round: HoldemRound = None
    
    def add_player(self, player_id: str, sit: int, chips: int):
        """ Creates a new HoldemTablePlayer object and adds it to self.players """
        assert self.get_player_by_sit(sit) == None
        assert self.get_player_by_id(player_id) == None

        player = HoldemTablePlayer(player_id, self.table_id, sit, chips)

        if len(self.players) == 0:
            self.dealer = player

        self.players.append(player)
    
    def remove_player(self, player: HoldemTablePlayer):
        self.players.remove(player)
        del player

    async def _validate_start_new_round(self):
        pass

    def start_new_round(self):
        if len(self.players) < 2:
            print("HoldemTable.start_new_round: can't start with less than two players")
            return
        
        if (self.round != None):
            if self.round.stage != HoldemRoundStage.ENDED:
                print("HoldemTable.start_new_round: can't start, round is ongoing")
                return
        
        config = HoldemRoundConfig(self.config.small_blind, self.config.ante)
        for player in self.players:
            player.make_round_player()
        
        # TODO: change first_to_move to dealer.
        round = HoldemRound(config,[player.round_player for player in self.players], first_to_move=self.dealer.round_player)
        self.round = round
        
            
    def get_player_by_id(self, player_id: str) -> HoldemTablePlayer:
        for player in self.players:
            if player.id == player_id:
                return player
    
    def get_player_by_sit(self, sit: int) -> HoldemTablePlayer:
        for player in self.players:
            if player.sit == sit:
                return player
                
    
    def _process_join_request(self, join_request):
        response = {'type':'sit_response', 'success':True}
        if self.get_player_by_sit(join_request['sit']) != None:
            response['success'] = False
            return response
        
        if self.get_player_by_id(join_request['user_id']) != None:
            response['success'] = False
            return response
        
        self.add_player(join_request['user_id'], join_request['sit'], join_request['chips'])

        return response
    

    #TODO: needs to be written with full functionality.
    def _process_leave_request(self, leave_request):
        
        response = {'type':'sit_response', 'success':True}
        if self.get_player_by_sit(leave_request['sit']) == None:
            response['success'] = False
            return response
        
        if self.get_player_by_id(leave_request['user_id']) == None:
            response['success'] = False
            return response
        
        self.remove_player(self.get_player_by_id(leave_request['user_id']))
        
        return response

    def process_sit_request(self, sit_request: dict):
        """ handles sit requests.
        sit_request has the form:
        {
            'user_id': str,
            'table_id': str,
            'type': str, # either 'join' or 'leave'
            'sit': int,
            'chips': int,
        }
        """
        
        if sit_request['type'] == 'join':
            return self._process_join_request(sit_request)
        
        if sit_request['type'] == 'leave':
            return self._process_leave_request(sit_request)
        
    #TODO: refactor
    def request_handler(self, request: dict) -> dict:
        print(request)
        """ handles the following types of events:
        sit_request,
        game_request

        the structure of a request:
        {
            'type': str,
            'user_id',
            'data': {
                ...
            }
        }
        """
        REQUEST_TYPES = ['move_request', 'sit_request', 'table_view_request']
        assert request['type'] in REQUEST_TYPES

        if request['type'] == 'move_request':
            if self.round == None:
                response = {'type': 'move_response','success': False}
            else:
                response = self.round.process_game_request(request['data'])
        
        if request['type'] == 'sit_request':
            response =  self.process_sit_request(request['data'])
        
        if request['type'] == 'table_view_request':
            player = self.get_player_by_id(request['data']['user_id'])
            response = self.get_table_view(player)

        return response
    
    def get_table_view(self, player: HoldemTablePlayer = None) -> dict:

        shared_data = {
                'players': [
                    {'user_id': p.id, 'sit': p.sit, 'chips': p.chips, 'active': p.active}
                    for p in self.players],
        }

        if self.round != None:
            last_moves = {}
            for p in self.round.players:
                last_move = self.round.get_last_move(p)
                if last_move != {}:
                    last_moves[p.sit] = last_move
            players = []
            for p in self.players:
                if p.round_player != None:
                    players.append({'user_id': p.id, 'sit': p.sit, 'chips': p.round_player.chips, 'active': p.active, 'in_hand':True, 'folded': p.round_player.folded})
                else:
                    players.append({'user_id': p.id, 'sit': p.sit, 'chips': p.chips, 'active': p.active, 'in_hand': False})
            shared_data = {
                'players': players,
                'community_cards': self.round.community_cards,
                'pots': [pot['pot'] for pot in self.round.pots.values()],
                'bets': self.round.bets,
                'stage': self.round.stage.value,
                'last_moves': last_moves,
                'to_move': self.round.to_move.sit
            }

        personal_data = {}
        if player != None:
            if player.round_player != None:
                personal_data = {'id': player.id, 'sit': player.sit, 'cards': player.round_player.cards, 'allowed_moves': self.round.get_allowed_moves(player.round_player)}


        view = {
            'type': 'table_view_update',
            'data': {
                'personal_data': personal_data,
                'shared_data': shared_data,
            }
        }
        return view

def main():
    config = HoldemTableConfig(20,0,100,1000,9)
    table = HoldemTable('table_1',config)
    table.add_player('p1',1,200)
    table.add_player('p2',2,200)
    table.process_sit_request(
        {
        'user_id': 'p3',
        'table_id': 'table_1',
        'type': 'join',
        'sit': 3,
        'chips': 300
        }
    )
    print(table.players[0])
    table.start_new_round()
    table.start_new_round()
    print(table.round)
    table.round.start()
    print(table.round)

if __name__ == '__main__':
    main()