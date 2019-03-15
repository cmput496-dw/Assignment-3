#Simulation-based player for Gomoku

from gtp_connection import GtpConnection
from board_util import GoBoardUtil
from simple_board import SimpleGoBoard

class Gomoku3():
    numSims = 10

    def name(self):
        return "Simulation Player ({0} sim.)".format(self.numSimulations)

    def genmove(self):
        assert not self.check_game_end_gomoku()
        moves = GoBoardUtil.generate_legal_moves_gomoku(self.board)
        numMoves = len(moves)
        score = [0] * numMoves
        for i in range(numMoves):
            move = moves[i]
            score[i] = self.simulate(self.board, move)
        #print(score)
        bestIndex = score.index(max(score))
        best = moves[bestIndex]
        #print("Best move:", best, "score", score[best])
        assert best in GoBoardUtil.generate_legal_moves_gomoku(self.board)
        return best

    def simulate(self, state, move):
        stats = [0] * 3
        state.play(move)
        moveNr = state.moveNumber()
        for _ in range(self.numSimulations):
            winner, _ = state.simulate()
            stats[winner] += 1
            state.resetToMoveNumber(moveNr)
        assert sum(stats) == self.numSimulations
        assert moveNr == state.moveNumber()
        state.undoMove()
        eval = (stats[BLACK] + 0.5 * stats[EMPTY]) / self.numSimulations
        if state.toPlay == WHITE:
            eval = 1 - eval
        return eval
