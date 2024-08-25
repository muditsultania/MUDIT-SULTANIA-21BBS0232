from flask import Flask, render_template
from flask_socketio import SocketIO, send, emit
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Keep track of the game state
game_state = {
    'board': [
        ['P2', 'H2b', '', 'H1b', 'P2'],
        ['', '', '', '', ''],
        ['', '', '', '', ''],
        ['', '', '', '', ''],
        ['P1', 'H1a', '', 'H2a', 'P1']
    ],
    'turn': 'player1'
}



def is_valid_move(player, start, end):
    piece = game_state['board'][start[0]][start[1]]
    target_piece = game_state['board'][end[0]][end[1]]
    print(f"Validating move for piece {piece} by {player}")
    print(f"Target piece at {end}: {target_piece}")

    # Define the pieces for each player
    player1_pieces = ['P1', 'H1a', 'H2a']
    player2_pieces = ['P2', 'H1b', 'H2b']

    # Check if the piece is valid for the player
    if not piece or (player == 'player1' and piece not in player1_pieces) or (player == 'player2' and piece not in player2_pieces):
        print("Invalid move: Empty cell or opponent's piece selected")
        return False

    # Check if the target cell contains a piece of the same team
    if (player == 'player1' and target_piece in player1_pieces) or (player == 'player2' and target_piece in player2_pieces):
        print("Invalid move: Cannot capture your own piece")
        return False

    dx = end[0] - start[0]
    dy = end[1] - start[1]

    if piece[0] == 'P':  # Pawn movement
        # Pawns can move one block in any direction
        if abs(dx) <= 1 and abs(dy) <= 1 and (dx != 0 or dy != 0):
            return True

    elif piece.startswith('H1a') or piece.startswith('H1b'):  # Hero1 (2 blocks in any direction except diagonal)
        # Hero1 can move 2 blocks in horizontal or vertical directions but not diagonally
        if (abs(dx) == 2 and dy == 0) or (dx == 0 and abs(dy) == 2):
            return True

    elif piece.startswith('H2a') or piece.startswith('H2b'):  # Hero2 (2 blocks diagonally)
        # Hero2 can move 2 blocks diagonally and capture any pieces in its path
        if abs(dx) == 2 and abs(dy) == 2:
            return True

    print("Invalid move: Does not follow piece movement rules")
    return False



def is_path_clear(player, start, end):
    """Checks if the path between start and end is clear for Hero1 and Hero2 and identifies opponent pieces."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]

    # For Hero1, check if the path between start and end is clear
    if abs(dx) == 2 and dy == 0:
        x = start[0] + (dx // 2)
        piece_in_path = game_state['board'][x][start[1]]
        if piece_in_path != '' and is_opponent_piece(player, piece_in_path):
            return (x, start[1])  # Return the coordinates of the opponent's piece in the path

    elif dx == 0 and abs(dy) == 2:
        y = start[1] + (dy // 2)
        piece_in_path = game_state['board'][start[0]][y]
        if piece_in_path != '' and is_opponent_piece(player, piece_in_path):
            return (start[0], y)  # Return the coordinates of the opponent's piece in the path

    # For Hero2, check the diagonal path between start and end
    if abs(dx) == abs(dy):
        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1
        x, y = start[0] + step_x, start[1] + step_y

        while x != end[0] and y != end[1]:
            piece_in_path = game_state['board'][x][y]
            if piece_in_path != '' and is_opponent_piece(player, piece_in_path):
                return (x, y)  # Return the coordinates of the opponent's piece in the path
            x += step_x
            y += step_y

    return None  # Path is clear, or no opponent piece in the path

def is_opponent_piece(player, piece):
    """Check if a given piece belongs to the opponent."""
    player1_pieces = ['P1', 'H1a', 'H2a']
    player2_pieces = ['P2', 'H1b', 'H2b']
    
    if player == 'player1' and piece in player2_pieces:
        return True
    if player == 'player2' and piece in player1_pieces:
        return True
    return False

def check_game_over():
    """Checks if a player has won the game by counting the remaining pieces."""
    player1_pieces = player2_pieces = 0

    for row in game_state['board']:
        for piece in row:
            if piece in ['P1', 'H1a', 'H2a']:
                player1_pieces += 1
            elif piece in ['P2', 'H1b', 'H2b']:
                player2_pieces += 1

    # If player 1 has no pieces left, player 2 wins
    if player1_pieces == 0:
        return 'player2'

    # If player 2 has no pieces left, player 1 wins
    if player2_pieces == 0:
        return 'player1'

    # If both players still have pieces, no one has won yet
    return None

@socketio.on('connect')
def handle_connect():
    """Handles a new client connection and sends the initial game state."""
    emit('game_state', game_state)

@socketio.on('move')
def handle_move(data):
    """Handles a move request from a player."""
    start = data['start']
    end = data['end']
    player = data['player']

    print(f"Received move from {player}: {start} -> {end}")
    print(f"Current turn: {game_state['turn']}")

    # Check if the move is valid
    if player == game_state['turn'] and is_valid_move(player, start, end):
        print(f"Move is valid. Moving piece from {start} to {end}")
        
        piece = game_state['board'][start[0]][start[1]]
        
        # Check if there's an opponent piece in the path that should be killed
        piece_in_path = is_path_clear(player, start, end)
        if piece_in_path:
            print(f"Killing opponent piece at {piece_in_path}")
            game_state['board'][piece_in_path[0]][piece_in_path[1]] = ''  # Remove the opponent piece in the path

        # Move the piece on the board
        game_state['board'][start[0]][start[1]] = ''
        game_state['board'][end[0]][end[1]] = piece

        # Check if the game is over
        winner = check_game_over()
        if winner:
            emit('game_over', {'winner': winner}, broadcast=True)
            return

        # Switch turn
        game_state['turn'] = 'player2' if player == 'player1' else 'player1'
        emit('game_state', game_state, broadcast=True)
    else:
        print("Invalid move attempted")
        emit('invalid_move', {'message': 'Invalid move, please try again'}, broadcast=False)
        emit('game_state', game_state, broadcast=True)  # Refresh the board after an invalid move


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
