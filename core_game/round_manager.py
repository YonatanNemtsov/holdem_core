""" Managing a holdem round object """

from holdem_round import HoldemRound, HoldemRoundPlayer, HoldemRoundStage, HoldemRoundConfig

class HoldemRoundManager:
    """ Utility class for operations on HoldemRound objects, like applying a move, or starting next move etc.
    Note: the methods in this class are duplicated in HoldemRound and it is probably not needed.
    """
    def __init__(self):
        pass
    
    #Todo: make all of these methods static.

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
    
    @staticmethod
    def validate_game_request(game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        assert player.folded == False
        allowed_moves = game.get_allowed_moves(player)
        
        if not request['move'] in allowed_moves['moves']:
            return False
        
        if not game.stage in (HoldemRoundStage.FLOP,HoldemRoundStage.PREFLOP,HoldemRoundStage.RIVER,HoldemRoundStage.TURN):
            print('Move not allowed - game ended.')
            return False

        return HoldemRoundManager.VALIDATE[request['move']](allowed_moves, request)
    
    @staticmethod
    def apply_check(game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        return
    @staticmethod
    def apply_call(game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        game.bets[game.stage].append((player.sit, request['move'], request['call_amount'], request['raise_amount']))
        player.chips -= (request['call_amount']+request['raise_amount'])

    @staticmethod
    def apply_raise(game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        game.bets[game.stage].append((player.sit, request['move'], request['call_amount'], request['raise_amount']))
        player.chips -= (request['call_amount']+request['raise_amount'])

    @staticmethod
    def apply_fold(game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        player.folded = True
    
    APPLY = {
        'check':apply_check,
        'call':apply_call,
        'raise':apply_raise,
        'fold':apply_fold,
    }

    # TODO: should probably be in abstract class
    @staticmethod
    def apply_game_request(game: HoldemRound, player: HoldemRoundPlayer , request: dict):
        
        game.log.append({player.sit: request})
        HoldemRoundManager.APPLY[request['move']](game, player, request)

        if request['move'] == 'raise':
            game.move_queue.extend_due_to_raise(player)
    
    # TODO: should probably be in abstract class
    @staticmethod
    def process_game_request(game: HoldemRound, request: dict) -> None:
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

        player = game.get_player_by_sit(request['sit'])
        if not HoldemRoundManager.validate_game_request(game, player, request):
            print(request['move'] + ' not allowed.')
            return {'type':'move_response', 'accepted':False}
        
        HoldemRoundManager.apply_game_request(game, player, request)
        return {'type':'move_response', 'accepted':True}

def main():
    p1 = HoldemRoundPlayer(1,200)
    p2 = HoldemRoundPlayer(2,200)
    config = HoldemRoundConfig(20,0)
    game = HoldemRound(config,'table', [p1,p2],p1)
    print(game.stage)
    game.start()
    print(game.stage)
    
    HoldemRoundManager.process_game_request(game,{'sit':1,'move':'check', 'call_amount':0, 'raise_amount':0})
    print(game.players)
    game.start_next_move()
    HoldemRoundManager.process_game_request(game,{'sit':2,'move':'raise', 'call_amount':0,'raise_amount':40})
    print(game)
    game.start_next_move()
    print(game)
    
if __name__ == '__main__':
    main()