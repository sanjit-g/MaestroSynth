import tkinter as tk
import math

class CircleOfFifthsRing:
    def __init__(self, root):
        self.root = root
        
        # Colors
        self.colors = {
            'bg': '#1e1e1e',
            'ring': '#333333',
            'text': '#ffffff',
            'center_bg': '#2d2d2d',
            'quadrants': {
                'up': '#4287f5',     # Blue
                'right': '#42f54e',   # Green
                'down': '#f5a442',    # Orange
                'left': '#f54242'      # Red
            },
            'note_highlight': '#ffd700',  # Gold
            'note_default': '#4a4a4a'
        }
        
        # Notes in circle of fifths order (clockwise from top)
        self.notes = ['C', 'G', 'D', 'A', 'E', 'B', 
                      'F#', 'C#', 'G#', 'D#', 'A#', 'F']
        
        # Quadrant mapping
        self.quadrants = {
            'up': {'notes': ['C', 'G', 'D'], 'color': '#4287f5', 'start_idx': 0},
            'right': {'notes': ['A', 'E', 'B'], 'color': '#42f54e', 'start_idx': 3},
            'down': {'notes': ['F#', 'C#', 'G#'], 'color': '#f5a442', 'start_idx': 6},
            'left': {'notes': ['D#', 'A#', 'F'], 'color': '#f54242', 'start_idx': 9}
        }
        
        # Hand movement to note position mapping
        self.hand_to_position = {
            'left': 0,    # First note in quadrant
            'up': 1,      # Second note in quadrant
            'right': 2    # Third note in quadrant
        }
        
        # Current state
        self.current_quadrant = None
        self.current_note = None
        self.quadrant_objects = {}  # Store canvas objects for quadrants
        self.note_objects = {}       # Store canvas objects for notes
        
        # Setup canvas
        self.canvas = tk.Canvas(root, width=600, height=600, 
                                bg=self.colors['bg'], highlightthickness=0)
        self.canvas.pack(pady=20)
        
        # Create the ring
        self.create_ring()
        
        # Center display for selected note
        self.center_display = tk.Label(root, text="", 
                                       font=('Arial', 24, 'bold'),
                                       fg=self.colors['note_highlight'],
                                       bg=self.colors['bg'])
        self.center_display.pack(pady=10)
        
    def create_ring(self):
        """Create the circle of fifths ring with quadrants"""
        center_x, center_y = 300, 300
        outer_radius = 250
        inner_radius = 150  # Creates a ring instead of full circle
        