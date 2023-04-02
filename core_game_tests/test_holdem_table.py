import unittest
import sys
import os

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from core_game.holdem_round import (
    HoldemRoundPlayer,
    HoldemRound,
    HoldemRoundConfig,
    HoldemRoundStage,
)

from core_game.holdem_table import validate_request





class TestValidateRequest(unittest.TestCase):
    def test1(self):
        p1 = HoldemRoundPlayer(1,1000,[])
        p2 = HoldemRoundPlayer(2,500,[])
        config = HoldemRoundConfig(5,0)
        game = HoldemRound(config,[p1,p2],p1)
        request = {'type':'check'}
        self.assertEqual(validate_request(game,p1,request),False)
        self.assertEqual(validate_request(game,p2,request),False)
        
        game.start_round()
        self.assertEqual(validate_request(game,p1,request),True)
        self.assertEqual(validate_request(game,p2,request),False)

if __name__ == '__main__':
    unittest.main()