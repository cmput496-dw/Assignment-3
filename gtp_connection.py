"""
gtp_connection.py
Module for playing games of Go using GoTextProtocol

Parts of this code were originally based on the gtp module 
in the Deep-Go project by Isaac Henrion and Amos Storkey 
at the University of Edinburgh.
"""
import traceback
from sys import stdin, stdout, stderr
from board_util import GoBoardUtil, BLACK, WHITE, EMPTY, BORDER, PASS, \
                       MAXSIZE, coord_to_point
import numpy as np
import re

POLICY = "random"
STACK = list()
STACK1 = list()

class GtpConnection():

    def __init__(self, go_engine, board, debug_mode = False):
        """
        Manage a GTP connection for a Go-playing engine

        Parameters
        ----------
        go_engine:
            a program that can reply to a set of GTP commandsbelow
        board: 
            Represents the current board state.
        """
        self._debug_mode = debug_mode
        self.go_engine = go_engine
        self.board = board
        self.commands = {
            "protocol_version": self.protocol_version_cmd,
            "quit": self.quit_cmd,
            "name": self.name_cmd,
            "boardsize": self.boardsize_cmd,
            "showboard": self.showboard_cmd,
            "clear_board": self.clear_board_cmd,
            "komi": self.komi_cmd,
            "version": self.version_cmd,
            "known_command": self.known_command_cmd,
            "genmove": self.genmove_cmd,
            "list_commands": self.list_commands_cmd,
            "play": self.play_cmd,
            "legal_moves": self.legal_moves_cmd,
            "gogui-rules_game_id": self.gogui_rules_game_id_cmd,
            "gogui-rules_board_size": self.gogui_rules_board_size_cmd,
            "gogui-rules_legal_moves": self.gogui_rules_legal_moves_cmd,
            "gogui-rules_side_to_move": self.gogui_rules_side_to_move_cmd,
            "gogui-rules_board": self.gogui_rules_board_cmd,
            "gogui-rules_final_result": self.gogui_rules_final_result_cmd,
            "gogui-analyze_commands": self.gogui_analyze_cmd,
            "policy": self.policy_cmd,
            "policy_moves": self.policy_moves
        }

        # used for argument checking
        # values: (required number of arguments, 
        #          error message on argnum failure)
        self.argmap = {
            "boardsize": (1, 'Usage: boardsize INT'),
            "komi": (1, 'Usage: komi FLOAT'),
            "known_command": (1, 'Usage: known_command CMD_NAME'),
            "genmove": (1, 'Usage: genmove {w,b}'),
            "play": (2, 'Usage: play {b,w} MOVE'),
            "legal_moves": (1, 'Usage: legal_moves {w,b}')
        }
    
    def write(self, data):
        stdout.write(data) 

    def flush(self):
        stdout.flush()

    def start_connection(self):
        """
        Start a GTP connection. 
        This function continuously monitors standard input for commands.
        """
        line = stdin.readline()
        while line:
            self.get_cmd(line)
            line = stdin.readline()

    def get_cmd(self, command):
        """
        Parse command string and execute it
        """
        if len(command.strip(' \r\t')) == 0:
            return
        if command[0] == '#':
            return
        # Strip leading numbers from regression tests
        if command[0].isdigit():
            command = re.sub("^\d+", "", command).lstrip()

        elements = command.split()
        if not elements:
            return
        command_name = elements[0]; args = elements[1:]
        if self.has_arg_error(command_name, len(args)):
            return
        if command_name in self.commands:
            try:
                self.commands[command_name](args)
            except Exception as e:
                self.debug_msg("Error executing command {}\n".format(str(e)))
                self.debug_msg("Stack Trace:\n{}\n".
                               format(traceback.format_exc()))
                raise e
        else:
            self.debug_msg("Unknown command: {}\n".format(command_name))
            self.error('Unknown command')
            stdout.flush()

    def has_arg_error(self, cmd, argnum):
        """
        Verify the number of arguments of cmd.
        argnum is the number of parsed arguments
        """
        if cmd in self.argmap and self.argmap[cmd][0] != argnum:
            self.error(self.argmap[cmd][1])
            return True
        return False

    def debug_msg(self, msg):
        """ Write msg to the debug stream """
        if self._debug_mode:
            stderr.write(msg)
            stderr.flush()

    def error(self, error_msg):
        """ Send error msg to stdout """
        stdout.write('? {}\n\n'.format(error_msg))
        stdout.flush()

    def respond(self, response=''):
        """ Send response to stdout """
        stdout.write('= {}\n\n'.format(response))
        stdout.flush()

    def reset(self, size):
        """
        Reset the board to empty board of given size
        """
        self.board.reset(size)

    def board2d(self):
        return str(GoBoardUtil.get_twoD_board(self.board))
        
    def protocol_version_cmd(self, args):
        """ Return the GTP protocol version being used (always 2) """
        self.respond('2')

    def quit_cmd(self, args):
        """ Quit game and exit the GTP interface """
        self.respond()
        exit()

    def name_cmd(self, args):
        """ Return the name of the Go engine """
        self.respond(self.go_engine.name)

    def version_cmd(self, args):
        """ Return the version of the  Go engine """
        self.respond(self.go_engine.version)

    def clear_board_cmd(self, args):
        """ clear the board """
        self.reset(self.board.size)
        self.respond()

    def boardsize_cmd(self, args):
        """
        Reset the game with new boardsize args[0]
        """
        self.reset(int(args[0]))
        self.respond()

    def showboard_cmd(self, args):
        self.respond('\n' + self.board2d())

    def komi_cmd(self, args):
        """
        Set the engine's komi to args[0]
        """
        self.go_engine.komi = float(args[0])
        self.respond()

    def known_command_cmd(self, args):
        """
        Check if command args[0] is known to the GTP interface
        """
        if args[0] in self.commands:
            self.respond("true")
        else:
            self.respond("false")

    def list_commands_cmd(self, args):
        """ list all supported GTP commands """
        self.respond(' '.join(list(self.commands.keys())))

    def legal_moves_cmd(self, args):
        """
        List legal moves for color args[0] in {'b','w'}
        """
        board_color = args[0].lower()
        color = color_to_int(board_color)
        moves = GoBoardUtil.generate_legal_moves(self.board, color)
        gtp_moves = []
        for move in moves:
            coords = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = ' '.join(sorted(gtp_moves))
        self.respond(sorted_moves)

    def play_cmd(self, args):
        """
        play a move args[1] for given color args[0] in {'b','w'}
        """
        try:
            board_color = args[0].lower()
            board_move = args[1]
            if board_color != "b" and board_color !="w":
                self.respond("illegal move: \"{}\" wrong color".format(board_color))
                return
            color = color_to_int(board_color)
            if args[1].lower() == 'pass':
                self.board.play_move(PASS, color)
                self.board.current_player = GoBoardUtil.opponent(color)
                self.respond()
                return
            coord = move_to_coord(args[1], self.board.size)
            if coord:
                move = coord_to_point(coord[0],coord[1], self.board.size)
            else:
                self.error("Error executing move {} converted from {}"
                           .format(move, args[1]))
                return
            if not self.board.play_move_gomoku(move, color):
                self.respond("illegal move: \"{}\" occupied".format(board_move))
                return
            else:
                self.debug_msg("Move: {}\nBoard:\n{}\n".
                                format(board_move, self.board2d()))
            self.respond()
        except Exception as e:
            self.respond('{}'.format(str(e)))

    def genmove_cmd(self, args):
        """
        Generate a move for the color args[0] in {'b', 'w'}, for the game of gomoku.
        """
        board_color = args[0].lower()
        color = color_to_int(board_color)
        game_end, winner = self.board.check_game_end_gomoku()
        if game_end:
            if winner == color:
                self.respond("pass")
            else:
                self.respond("resign")
            return
        moves = GoBoardUtil.generate_legal_moves_gomoku(self.board)


        #IF RANDOM
        if (POLICY == "random"):
            best_move = None
            best_ratio = 0
            for move in moves:
                wins = 0
                if best_move == None:
                    best_move = move
                for i in range(0,10):
                    if random_simulation(self.board.copy(), color, color):
                        wins += 1

                if (wins/10) > best_ratio:
                    best_move = move
                    best_ratio = (wins/10)

        #IF RULES
        elif (POLICY == "rule_based"):
            best_move = None
            best_ratio = 0
            for move in moves:
                temp_board = self.board.copy()
                temp_board.play_move_gomoku(move, color)
                wins = 0
                if best_move == None:
                    best_move = move
                for i in range(0,10):
                    outcome = rules_simulation(temp_board.copy(), color, GoBoardUtil.opponent(color))
                    wins += outcome

                if (wins/10) > best_ratio:
                    best_move = move
                    best_ratio = (wins/10)
            
        
        if best_move == PASS:
            self.respond("pass")
            return
        move_coord = point_to_coord(best_move, self.board.size)
        move_as_string = format_point(move_coord)
        if self.board.is_legal_gomoku(best_move, color):
            self.board.play_move_gomoku(best_move, color)
            self.respond(move_as_string)
        else:
            self.respond("illegal move: {}".format(move_as_string))

    def gogui_rules_game_id_cmd(self, args):
        self.respond("Gomoku")
    
    def gogui_rules_board_size_cmd(self, args):
        self.respond(str(self.board.size))
    
    def legal_moves_cmd(self, args):
        """
            List legal moves for color args[0] in {'b','w'}
            """
        board_color = args[0].lower()
        color = color_to_int(board_color)
        moves = GoBoardUtil.generate_legal_moves(self.board, color)
        gtp_moves = []
        for move in moves:
            coords = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = ' '.join(sorted(gtp_moves))
        self.respond(sorted_moves)

    def gogui_rules_legal_moves_cmd(self, args):
        game_end,_ = self.board.check_game_end_gomoku()
        if game_end:
            self.respond()
            return
        moves = GoBoardUtil.generate_legal_moves_gomoku(self.board)
        gtp_moves = []
        for move in moves:
            coords = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = ' '.join(sorted(gtp_moves))
        self.respond(sorted_moves)
    
    def gogui_rules_side_to_move_cmd(self, args):
        color = "black" if self.board.current_player == BLACK else "white"
        self.respond(color)
    
    def gogui_rules_board_cmd(self, args):
        size = self.board.size
        str = ''
        for row in range(size-1, -1, -1):
            start = self.board.row_start(row + 1)
            for i in range(size):
                point = self.board.board[start + i]
                if point == BLACK:
                    str += 'X'
                elif point == WHITE:
                    str += 'O'
                elif point == EMPTY:
                    str += '.'
                else:
                    assert False
            str += '\n'
        self.respond(str)
    
    def gogui_rules_final_result_cmd(self, args):
        game_end, winner = self.board.check_game_end_gomoku()
        moves = self.board.get_empty_points()
        board_full = (len(moves) == 0)
        if board_full and not game_end:
            self.respond("draw")
            return
        if game_end:
            color = "black" if winner == BLACK else "white"
            self.respond(color)
        else:
            self.respond("unknown")

    def gogui_analyze_cmd(self, args):
        self.respond("pstring/Legal Moves For ToPlay/gogui-rules_legal_moves\n"
                     "pstring/Side to Play/gogui-rules_side_to_move\n"
                     "pstring/Final Result/gogui-rules_final_result\n"
                     "pstring/Board Size/gogui-rules_board_size\n"
                     "pstring/Rules GameID/gogui-rules_game_id\n"
                     "pstring/Show Board/gogui-rules_board\n"
                     )

    def policy_cmd(self,args):
        if args[0] != "random" and args[0] != "rule_based":
            self.respond("unknown policy")
        else:
            global POLICY
            POLICY = args[0]
            self.respond("policy set to " + POLICY)

    def policy_moves(self,args):
        movetype, moves = check_block_win(self.board)

        returnstring = movetype
        move_strings = list()

        #if len(moves) == 0:
            #self.respond("")

        for move in moves:
            move_coord = point_to_coord(move, self.board.size)
            move_as_string = format_point(move_coord)
            move_strings.append(move_as_string)
            
        move_strings.sort()
        for move_string in move_strings:
            string = " " + move_string
            returnstring += string

        if returnstring == "Random":
            returnstring = ""
            
        self.respond(returnstring)
        



def point_to_coord(point, boardsize):
    """
    Transform point given as board array index 
    to (row, col) coordinate representation.
    Special case: PASS is not transformed
    """
    if point == PASS:
        return PASS
    else:
        NS = boardsize + 1
        return divmod(point, NS)

def format_point(move):
    """
    Return move coordinates as a string such as 'a1', or 'pass'.
    """
    column_letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    #column_letters = "abcdefghjklmnopqrstuvwxyz"
    if move == PASS:
        return "pass"
    row, col = move
    if not 0 <= row < MAXSIZE or not 0 <= col < MAXSIZE:
        raise ValueError
    return column_letters[col - 1]+ str(row) 
    
def move_to_coord(point_str, board_size):
    """
    Convert a string point_str representing a point, as specified by GTP,
    to a pair of coordinates (row, col) in range 1 .. board_size.
    Raises ValueError if point_str is invalid
    """
    if not 2 <= board_size <= MAXSIZE:
        raise ValueError("board_size out of range")
    s = point_str.lower()
    if s == "pass":
        return PASS
    try:
        col_c = s[0]
        if (not "a" <= col_c <= "z") or col_c == "i":
            raise ValueError
        col = ord(col_c) - ord("a")
        if col_c < "i":
            col += 1
        row = int(s[1:])
        if row < 1:
            raise ValueError
    except (IndexError, ValueError):
        raise ValueError("illegal move: \"{}\" wrong coordinate".format(s))
    if not (col <= board_size and row <= board_size):
        raise ValueError("illegal move: \"{}\" wrong coordinate".format(s))
    return row, col

def color_to_int(c):
    """convert character to the appropriate integer code"""
    color_to_int = {"b": BLACK , "w": WHITE, "e": EMPTY, 
                    "BORDER": BORDER}
    return color_to_int[c]

#################################################################################
#Check Wins
################################################################################
def check_wins(board):
    game_end, winner = self.board.check_game_end_gomoku()

    color = board.current_player
    original_board = board.copy


#################################################################################
#Check Block Win
################################################################################
def check_block_win(board, color=None):

    if color == None:
        color = board.current_player
    original_board = board.copy()
    moves = GoBoardUtil.generate_legal_moves_gomoku(board)
    
    win_moves = list()
    block_win_moves = list()
    open_four_moves = list()
    block_open_four_moves = list()

    returned_move_list = list()

    # initially set all switches to false
    found_win = False
    found_block_win = False
    found_open_four = False
    found_block_open_four = False

    # check to see how many situations exist beforehand
    original_block_situations = original_board.check_block_win_gomoku(color)
    original_open_situations = original_board.check_open_four_gomoku(color)
    original_block_open_situations = original_board.check_block_open_four_gomoku(color)
        
    for move in moves:

        board_copy = board.copy()
        #STACK.append(board_copy.copy())
        save(board)
        board_copy.play_move_gomoku(move, color)

        # If win, update win
        game_end, winner = board_copy.check_game_end_gomoku()
        if (game_end):
            win_moves.append(move)
            found_win = True
        
        # If blockwin, update blockwin
        if (not found_win):
            check_block_situations = board_copy.check_block_win_gomoku(color)
            if(check_block_situations < original_block_situations):
                block_win_moves.append(move)
                found_block_win = True

        #open four
        if (not found_win and not found_block_win):
            check_open_situations = board_copy.check_open_four_gomoku(color)
            if(check_open_situations > original_open_situations):
                open_four_moves.append(move)
                found_open_four = True
            

        #block open four
        if (not found_win and not found_block_win and not found_open_four):
            check_block_open_situations = board_copy.check_block_open_four_gomoku(color)
            if (check_block_open_situations < original_block_open_situations):
                block_open_four_moves.append(move)
                found_block_open_four = True

        board = undo()

    
    if (found_win):
        returnstring = "Win"
        returned_move_list = win_moves

    elif (found_block_win):
        returnstring = "BlockWin"
        returned_move_list = block_win_moves
        
    elif (found_open_four):
        returnstring = "OpenFour"
        returned_move_list = open_four_moves

    elif (found_block_open_four):
        returnstring = "BlockOpenFour"
        returned_move_list = block_open_four_moves

    else:
        returnstring = "Random"
        returned_move_list = moves
            
    return returnstring, returned_move_list


def save(board):
    STACK.append(board.copy())

def undo():
    return STACK.pop()



def random_simulation(board, original_color, color):

    #check base case
    game_end, winner = board.check_game_end_gomoku()
    if game_end:
        if winner == original_color:
            return True
    move = GoBoardUtil.generate_random_move_gomoku(board)
    if move == PASS:
        return False
    
    #save to stack
    STACK.append(board.copy())
    
    #play move
    board.play_move_gomoku(move, color)
    status = random_simulation(board.copy(), original_color, GoBoardUtil.opponent(color))

    #pop from stack
    board = STACK.pop()

    return status


def rules_simulation(board, original_color, color):

    #check base case
    game_end, winner = board.check_game_end_gomoku()
    if game_end:
        if winner == original_color:
            return 1
        else:
            return 0
    #if board is empty, return Loss
    string, moves = check_block_win(board.copy(), color)
    if len(moves) == 0:
        return 0.5

    move = moves.pop()
    
    if move == PASS:
        return 0.5
    
    #save to stack
    #STACK1.append(board.copy())
    
    #play move
    board.play_move_gomoku(move, color)
    status = rules_simulation(board, original_color, GoBoardUtil.opponent(color))

    #pop from stack
    #board = STACK1.pop()

    return status
