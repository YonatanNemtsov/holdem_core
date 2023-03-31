from holdem_round import HoldemRound, HoldemRoundPlayer, HoldemRoundStage, HoldemRoundConfig

class HoldemRoundManager:
    def __init__(self):
        pass

    def is_valid_check(self, game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        return True

    def is_valid_call(self, game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        return True

    def is_valid_raise(self, game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        return True

    def is_valid_fold(self, game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        return True

    VALIDATE = {
        'check':is_valid_check,
        'call':is_valid_call,
        'check':is_valid_raise,
        'fold':is_valid_fold,
    }

    def validate_game_request(self, game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        if not game.to_move == player:
            print(f" Not {player}'s turn ")
            return False
        if not game.stage in (HoldemRoundStage.FLOP,HoldemRoundStage.PREFLOP,HoldemRoundStage.RIVER,HoldemRoundStage.TURN):
            print('Move not allowed')
            return False
        
        return self.VALIDATE[request['type']](self, game,player,request)

    def apply_check(game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        pass

    def apply_call(game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        game.bets[game.stage].append((player.sit, request['type'], request['call_amount'], request['raise_amount']))
        player.chips -= request['amount']

    def apply_raise(game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        game.bets[game.stage].append((player.sit, request['type'], request['call_amount'], request['raise_amount']))
        player.chips -= request['amount']

    def apply_fold(game: HoldemRound, player: HoldemRoundPlayer, request: dict):
        player.folded = True

    APPLY = {
        'check':apply_check,
        'call':apply_call,
        'raise':apply_raise,
        'fold':apply_fold,
    }

    def apply_game_request(self, game: HoldemRound, player: HoldemRoundPlayer , request: dict):
        
        game.log.append({player.sit: request})
        self.APPLY[request['type']](game, player, request)

        if request['type'] == 'raise':
            game.move_queue.extend_due_to_raise(player)

    def process_game_request(self, game: HoldemRound, player: HoldemRoundPlayer, request: dict) -> None:
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
        if not self.validate_game_request(game, player, request):
            print('move not allowed.')
            return
        
        self.apply_game_request(game, player, request)

def main():
    p1 = HoldemRoundPlayer(1,200)
    p2 = HoldemRoundPlayer(2,200)
    config = HoldemRoundConfig(20,0)
    game = HoldemRound(config,'table', [p1,p2],p1)
    print(game.stage)
    game.start()
    manager = HoldemRoundManager()
    manager.process_game_request(game,p1,{'sit':1,'type':'check'})
    print(game.players)

if __name__ == '__main__':
    main()