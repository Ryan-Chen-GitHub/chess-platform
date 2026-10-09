import io

import chess.pgn

# Sample Game
# [bracketed lines are "headers"]
# 1. while numbered lines are the chess move list (this example is Scholar's mate)
PGN = """
[Event "Test Game"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0
"""

# Turns text --> Game object that holds header & moves.
# Also lets us look up players by name
game = chess.pgn.read_game(io.StringIO(PGN))
print(game.headers["White"], "vs", game.headers["Black"])

# Creates a starting chess board, and converts all the moves into chess notation
# Before actually "moving" it in the program & checks for Checkmate
board = game.board()
for move in game.mainline_moves():
    print(board.san(move))
    board.push(move)

print("Checkmate:", board.is_checkmate())