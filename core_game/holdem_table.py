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
        response = {'type':'sit_response', 'accepted':True}
        if self.get_player_by_sit(join_request['sit']) != None:
            response['accepted'] = False
            return response
        
        if self.get_player_by_id(join_request['user_id']) != None:
            response['accepted'] = False
            return response
        
        self.add_player(join_request['user_id'], join_request['sit'], join_request['chips'])

        return response
    
    def _process_leave_request(self, leave_request):
        response = {'type':'sit_response', 'accepted':True}
        if self.get_player_by_sit(leave_request['sit']) == None:
            response['accepted'] = False
            return response
        
        if self.get_player_by_id(leave_request['user_id']) == None:
            response['accepted'] = False
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
            return self._process_join_request(sit_request)
    
    def request_handler(self, request: dict) -> dict:
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
        REQUEST_TYPES = ['move_request', 'sit_request']
        assert request in REQUEST_TYPES
        if request['type'] == 'move_request':
            response = self.round.process_game_request(request['data'])
        
        if request['type'] == 'sit_request':
            response =  self.process_sit_request(request['data'])
        
        return response


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