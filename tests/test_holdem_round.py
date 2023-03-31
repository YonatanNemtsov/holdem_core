import unittest
import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))

from holdem_round import (
    HoldemRoundPlayer,
    HoldemRound,
    HoldemRoundConfig,
    HoldemRoundStage,
)


    

class TestValidateSetup(unittest.TestCase):
    def test2(self):
        p1 = HoldemRoundPlayer(1,1000,[])
        p2 = HoldemRoundPlayer(2,500,[])
        config = HoldemRoundConfig(5,0)
        game = HoldemRound(config,[p1,p2],p1)
        game.stage = HoldemRoundStage.FLOP
        self.assertRaises(Exception,game.validate_game_setup)
    
    def test_one_player_setupt_raise_exception(self):
        p1 = HoldemRoundPlayer(1,1000,[])
        config = HoldemRoundConfig(5,0)
        game = HoldemRound(config,[p1],p1)
        self.assertRaises(Exception, game.validate_game_setup)

class TestCards(unittest.TestCase):
    def test_deal_cards1(self):
        p1 = HoldemRoundPlayer(1,1000,[])
        p2 = HoldemRoundPlayer(2,500,[])
        config = HoldemRoundConfig(5,0)
        game = HoldemRound(config,[p1,p2],p1)
        game.deal_cards()
        print(p1.cards,p2.cards)
        self.assertEqual(len(p1.cards),2)

class TestStartRound(unittest.TestCase):
    def test_start_round1(self):
        p1 = HoldemRoundPlayer(1,1000,[])
        p2 = HoldemRoundPlayer(2,500,[])
        config = HoldemRoundConfig(5,0)
        game = HoldemRound(config,[p1,p2],p1)
        game.start_round()
        self.assertEqual(game.stage,HoldemRoundStage.PREFLOP)
    
    def test_start_round2(self):
        p1 = HoldemRoundPlayer(1,1000,[])
        p2 = HoldemRoundPlayer(2,500,[])
        config = HoldemRoundConfig(5,0)
        game = HoldemRound(config,[p1,p2],p1)
        game.stage = HoldemRoundStage.PREFLOP
        self.assertRaises(Exception, game.start_round)

class TestValidateRequests(unittest.TestCase):
    pass

class TestPlayerQueue(unittest.TestCase):
    pass

class TestCompleteGame(unittest.TestCase):
    def test_game_with_showdown(self):
        pass
    
if __name__ == '__main__':
    unittest.main()