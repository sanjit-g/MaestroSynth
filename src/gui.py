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
        
        # Center display for selected note (ON CANVAS, at center)
        self.center_note_text = self.canvas.create_text(
        300, 300,                     # x, y = center of 600x600 canvas
        text="C",
        fill='white',
    font=('Arial', 32, 'bold')
)
        # Center display for selected note
        #self.center_display = tk.Label(root, text="", 
        #                               font=('Arial', 24, 'bold'),
         #                              fg=self.colors['note_highlight'],
         #                              bg=self.colors['bg'])
        #self.center_display.pack(pady=10)
        
    def create_ring(self):
        """Create the circle of fifths ring with quadrants"""
        center_x, center_y = 300, 300
        outer_radius = 250
        inner_radius = 150  # Creates a ring instead of full circle
        note_radius = 30
        second_outer_radius = 290
        
        # Draw the ring background (dark circle)
        self.canvas.create_oval(center_x-outer_radius, center_y-outer_radius,
                                center_x+outer_radius, center_y+outer_radius,
                                outline=self.colors['ring'], width=2)
        self.canvas.create_oval(center_x-inner_radius, center_y-inner_radius,
                                center_x+inner_radius, center_y+inner_radius,
                                outline=self.colors['ring'], width=2)
        
        # Draw quadrant dividers (lines from center to outer edge)
        for angle in [0, 90, 180, 270]:
            rad = math.radians(angle - 90)  # -90 so 0 degrees is at top
            x = center_x + outer_radius * math.cos(rad)
            y = center_y + outer_radius * math.sin(rad)
            self.canvas.create_line(center_x, center_y, x, y,
                                   fill=self.colors['ring'], width=1, dash=(2,4))
        
        # Create invisible quadrant highlights (will be colored when active)
        for quad_name, quad_data in self.quadrants.items():
            # Calculate quadrant angle range
            start_angle = quad_data['start_idx'] * 30 - 90  # -90 so C is at top
            end_angle = start_angle + 90
            
            # Create quadrant highlight polygon
            points = []
            # Arc from inner to second outer radius
            for angle in range(start_angle, end_angle + 1):
                rad = math.radians(angle)
                x = center_x + second_outer_radius * math.cos(rad)
                y = center_y + second_outer_radius * math.sin(rad)
                points.append((x, y))
            for angle in range(end_angle, start_angle - 1, -1):
                rad = math.radians(angle)
                x = center_x + inner_radius * math.cos(rad)
                y = center_y + inner_radius * math.sin(rad)
                points.append((x, y))
            
            # Flatten points list for canvas
            flat_points = []
            for point in points:
                flat_points.extend(point)
            
            # Create polygon (invisible by default)
            poly = self.canvas.create_polygon(flat_points,
                                             fill=quad_data['color'],
                                             #stipple='gray75',  # Creates transparency effect
                                             outline='',
                                             state='hidden')  # Hidden by default
            self.quadrant_objects[quad_name] = poly
        
        # Draw notes
        for i, note in enumerate(self.notes):
            angle = math.radians(i * 30 - 90 + 15)  # -90 so C is at top
            x = center_x + ((outer_radius + inner_radius) / 2) * math.cos(angle)
            y = center_y + ((outer_radius + inner_radius) / 2) * math.sin(angle)
            
            # Note background circle
            circle = self.canvas.create_oval(x-note_radius, y-note_radius,
                                            x+note_radius, y+note_radius,
                                            fill=self.colors['note_default'],
                                            outline='white', width=1)
            
            # Note text
            text = self.canvas.create_text(x, y, text=note,
                                          fill='white',
                                          font=('Arial', 14, 'bold'))
            
            self.note_objects[note] = {'circle': circle, 'text': text}
    
    # ========== PUBLIC METHODS FOR TEAM INTEGRATION ==========
    
    def update_thumb(self, thumb_direction):
        """Call this when thumb direction changes"""
        # Hide all quadrant highlights
        for quad_name, poly in self.quadrant_objects.items():
            self.canvas.itemconfig(poly, state='hidden')
        
        # Show selected quadrant highlight
        if thumb_direction in self.quadrant_objects:
            self.canvas.itemconfig(self.quadrant_objects[thumb_direction],
                                  state='normal')
            self.current_quadrant = thumb_direction
            
            # Reset note highlight when quadrant changes
            if self.current_note:
                self.highlight_note(self.current_note, False)
                self.current_note = None
                self.center_display.config(text="")
    
    def update_hand(self, hand_movement):
        """Call this when hand movement changes"""
        if not self.current_quadrant:
            return  # No quadrant selected yet
        
        if hand_movement in self.hand_to_position:
            # Get the note from current quadrant
            position = self.hand_to_position[hand_movement]
            quadrant_notes = self.quadrants[self.current_quadrant]['notes']
            
            if position < len(quadrant_notes):
                selected_note = quadrant_notes[position]
                
                # Update highlights
                if self.current_note:
                    self.highlight_note(self.current_note, False)
                
                self.highlight_note(selected_note, True)
                self.current_note = selected_note
                self.center_display.config(text=selected_note)
    
    def highlight_note(self, note_name, highlight=True):
        """Helper to highlight/unhighlight a note"""
        if note_name in self.note_objects:
            color = self.colors['note_highlight'] if highlight else self.colors['note_default']
            self.canvas.itemconfig(self.note_objects[note_name]['circle'],
                                  fill=color)
    
    def update_gesture(self, thumb_direction, hand_movement):
        """Combined update for both gestures"""
        self.update_thumb(thumb_direction)
        # Small delay to ensure visual separation (optional)
        self.root.after(50, lambda: self.update_hand(hand_movement))

# Test the GUI
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Circle of Fifths Ring")
    root.configure(bg='#1e1e1e')
    
    app = CircleOfFifthsRing(root)
    
    # Simple test buttons
    test_frame = tk.Frame(root, bg='#1e1e1e')
    test_frame.pack(pady=10)
    
    tk.Label(test_frame, text="Test Controls:", fg='white', bg='#1e1e1e').pack()
    
    thumb_frame = tk.Frame(test_frame, bg='#1e1e1e')
    thumb_frame.pack()
    for thumb in ['up', 'right', 'down', 'left']:
        btn = tk.Button(thumb_frame, text=f"Thumb {thumb}",
                       command=lambda t=thumb: app.update_thumb(t))
        btn.pack(side=tk.LEFT, padx=2)
    
    hand_frame = tk.Frame(test_frame, bg='#1e1e1e')
    hand_frame.pack(pady=5)
    for hand in ['left', 'up', 'right']:
        btn = tk.Button(hand_frame, text=f"Hand {hand}",
                       command=lambda h=hand: app.update_hand(h))
        btn.pack(side=tk.LEFT, padx=2)
    
    root.mainloop()



