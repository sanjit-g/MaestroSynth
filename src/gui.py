import tkinter as tk
import math


# ── Layout constants ──────────────────────────────────────────────────────────
CAM_W, CAM_H = 960, 540       # main camera canvas size
WHEEL_SIZE   = 260             # wheel canvas is a square of this many pixels
WHEEL_PAD    = 12              # gap from the top-right corner


class CircleOfFifthsRing:
    """
    Circle-of-fifths overlay widget.

    Layout
    ──────
    • A full-window camera canvas is placed at (0, 0).
    • A compact wheel canvas is overlaid in the top-right corner via place().

    Navigation
    ──────────
    Call update_hand_position(x, y) with raw camera-frame pixel coordinates.
    The x-axis is automatically FLIPPED so that moving your physical hand to
    the RIGHT highlights the RIGHT side of the wheel (cameras are mirrored).
    """

    def __init__(self, root, camera_overlay=False):
        self.root            = root
        self._camera_overlay = camera_overlay
        self._current_photo  = None
        self._cam_image_id   = None

        # ── Colors ────────────────────────────────────────────────────────────
        self.colors = {
            'bg':             '#1e1e1e',
            'ring':           '#444444',
            'note_highlight': '#ffd700',
            'note_default':   '#4a4a4a',
        }

        # ── Notes & quadrants ─────────────────────────────────────────────────
        # Clockwise from 12 o'clock; all flats for consistency.
        self.notes = ['C', 'G', 'D', 'A', 'E', 'B',
                      'Gb', 'Db', 'Ab', 'Eb', 'Bb', 'F']

        self.quadrants = {
            'up':    {'notes': ['C',  'G',  'D'],  'color': '#4287f5', 'start_idx': 0},
            'right': {'notes': ['A',  'E',  'B'],  'color': '#42f54e', 'start_idx': 3},
            'down':  {'notes': ['Gb', 'Db', 'Ab'], 'color': '#f5a442', 'start_idx': 6},
            'left':  {'notes': ['Eb', 'Bb', 'F'],  'color': '#f54242', 'start_idx': 9},
        }

        # ── State ─────────────────────────────────────────────────────────────
        self.current_quadrant = None
        self.current_note     = None
        self.quadrant_objects = {}
        self.note_objects     = {}

        # ── Camera canvas (fills the whole window; resizes with window) ───────
        self.cam_canvas = tk.Canvas(root, width=CAM_W, height=CAM_H,
                                    bg='#000000', highlightthickness=0)
        self.cam_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._display_w, self._display_h = CAM_W, CAM_H

        if self._camera_overlay:
            try:
                from PIL import Image, ImageTk
                import numpy as np
                placeholder = Image.fromarray(
                    np.zeros((CAM_H, CAM_W, 3), dtype=np.uint8))
                self._current_photo = ImageTk.PhotoImage(placeholder)
                self._cam_image_id  = self.cam_canvas.create_image(
                    CAM_W // 2, CAM_H // 2,
                    image=self._current_photo, anchor=tk.CENTER)
            except ImportError:
                self._camera_overlay = False

        # ── Wheel canvas (top-right corner overlay; position updated on resize) ─
        self.canvas = tk.Canvas(root,
                                width=WHEEL_SIZE, height=WHEEL_SIZE,
                                bg=self.colors['bg'],
                                highlightthickness=1,
                                highlightbackground='#555555')
        self._place_wheel(CAM_W, CAM_H)
        self.root.bind("<Configure>", self._on_resize)

        self._build_ring()

        ws = WHEEL_SIZE
        self.center_note_text = self.canvas.create_text(
            ws // 2, ws // 2,
            text='', fill=self.colors['note_highlight'],
            font=('Arial', int(ws * 0.12), 'bold'))

        # Lock indicator: visible when chord is locked (thumbs up)
        self._lock_rect_id = self.canvas.create_rectangle(
            ws // 2 - 42, ws - 28, ws // 2 + 42, ws - 8,
            outline='#ffd700', width=2, state='hidden')
        self._lock_text_id = self.canvas.create_text(
            ws // 2, ws - 18,
            text='LOCKED', fill='#ffd700',
            font=('Arial', 11, 'bold'), state='hidden')
        self._locked = False

    def _place_wheel(self, w, h):
        """Position the wheel at top-right of the given dimensions."""
        wx = w - WHEEL_SIZE - WHEEL_PAD
        self.canvas.place(x=wx, y=WHEEL_PAD)

    def _on_resize(self, event):
        """On window resize: reposition wheel and camera image, store display size."""
        if event.widget != self.root:
            return
        w = max(event.width, WHEEL_SIZE + 2 * WHEEL_PAD)
        h = max(event.height, WHEEL_SIZE + 2 * WHEEL_PAD)
        self._display_w, self._display_h = w, h
        self._place_wheel(w, h)
        if self._camera_overlay and self._cam_image_id is not None:
            self.cam_canvas.coords(self._cam_image_id, w // 2, h // 2)

    # ── Ring construction ─────────────────────────────────────────────────────

    def _build_ring(self):
        ws       = WHEEL_SIZE
        cx = cy  = ws // 2
        outer_r  = int(ws * 0.46)
        inner_r  = int(ws * 0.28)
        ring_mid = (outer_r + inner_r) / 2
        note_r   = int(ws * 0.058)
        hi_r     = int(ws * 0.485)

        for r in (outer_r, inner_r):
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                    outline=self.colors['ring'], width=2)

        for deg in (0, 90, 180, 270):
            rad = math.radians(deg - 90)
            self.canvas.create_line(cx, cy,
                                    cx + outer_r * math.cos(rad),
                                    cy + outer_r * math.sin(rad),
                                    fill=self.colors['ring'], width=1, dash=(2, 3))

        for qname, qdata in self.quadrants.items():
            sa = qdata['start_idx'] * 30 - 90
            ea = sa + 90
            pts = []
            for a in range(sa, ea + 1):
                r = math.radians(a)
                pts.append((cx + hi_r    * math.cos(r),
                             cy + hi_r    * math.sin(r)))
            for a in range(ea, sa - 1, -1):
                r = math.radians(a)
                pts.append((cx + inner_r * math.cos(r),
                             cy + inner_r * math.sin(r)))
            flat = [v for pt in pts for v in pt]
            poly = self.canvas.create_polygon(flat, fill=qdata['color'],
                                              outline='', state='hidden')
            self.quadrant_objects[qname] = poly

        for i, note in enumerate(self.notes):
            angle = math.radians(i * 30 - 90 + 15)
            x = cx + ring_mid * math.cos(angle)
            y = cy + ring_mid * math.sin(angle)
            circ = self.canvas.create_oval(x - note_r, y - note_r,
                                           x + note_r, y + note_r,
                                           fill=self.colors['note_default'],
                                           outline='white', width=1)
            txt  = self.canvas.create_text(x, y, text=note, fill='white',
                                           font=('Arial',
                                                 max(7, int(ws * 0.045)),
                                                 'bold'))
            self.note_objects[note] = {'circle': circ, 'text': txt}

    # ── Public API ────────────────────────────────────────────────────────────

    _NOTE_ALIASES = {
        'F#': 'Gb', 'C#': 'Db', 'G#': 'Ab', 'D#': 'Eb', 'A#': 'Bb',
    }

    def update_hand_position(self, x, y, frame_w=None, frame_h=None):
        """
        Update the wheel from raw camera-frame hand coordinates.

        x, y        – pixel position in the camera frame
        frame_w/h   – frame dimensions; defaults to CAM_W × CAM_H

        The x-axis is flipped internally to correct the camera mirror so that
        physically moving right → right quadrant, left → left quadrant.
        """
        fw = frame_w or CAM_W
        fh = frame_h or CAM_H

        # Flip x to unmirror: moving physically right decreases camera-x,
        # so we negate dx before computing the angle.
        dx = -(x - fw / 2)
        dy =   y - fh / 2

        if math.sqrt(dx * dx + dy * dy) < min(fw, fh) * 0.04:
            return   # dead-zone near centre

        # Clockwise angle from 12 o'clock
        angle = math.degrees(math.atan2(dx, -dy)) % 360

        note_index    = int(angle // 30)
        selected_note = self.notes[note_index]

        quadrant = next(
            (qn for qn, qd in self.quadrants.items()
             if selected_note in qd['notes']),
            None)

        for qn, poly in self.quadrant_objects.items():
            self.canvas.itemconfig(poly,
                                   state='normal' if qn == quadrant else 'hidden')
        self.current_quadrant = quadrant

        if self.current_note and self.current_note != selected_note:
            self._highlight_note(self.current_note, False)
        self._highlight_note(selected_note, True)
        self.current_note = selected_note
        self.canvas.itemconfig(self.center_note_text, text=selected_note)

    def clear_selection(self):
        """Clear all highlights (call when hand leaves frame)."""
        for poly in self.quadrant_objects.values():
            self.canvas.itemconfig(poly, state='hidden')
        if self.current_note:
            self._highlight_note(self.current_note, False)
        self.current_quadrant = None
        self.current_note     = None
        self.canvas.itemconfig(self.center_note_text, text='')

    def update_lock_state(self, locked):
        """
        Show or hide the lock indicator on the wheel.
        Call with True when chord is locked (thumbs up), False when unlocked.
        """
        if locked == self._locked:
            return
        self._locked = locked
        state = 'normal' if locked else 'hidden'
        self.canvas.itemconfig(self._lock_rect_id, state=state)
        self.canvas.itemconfig(self._lock_text_id, state=state)
        self.canvas.configure(highlightbackground='#ffd700' if locked else '#555555')

    def update_from_note(self, note):
        """
        Highlight a note by name (sharp or flat spelling accepted).
        Pass None / '' to clear the selection.
        """
        if not note:
            self.clear_selection()
            return
        note = self._NOTE_ALIASES.get(note, note)
        if note not in self.note_objects:
            return

        idx       = self.notes.index(note)
        theta_rad = math.radians(idx * 30 + 15)
        r         = min(CAM_W, CAM_H) * 0.3
        x = CAM_W / 2 - r * math.sin(theta_rad)
        y = CAM_H / 2 - r * math.cos(theta_rad)
        self.update_hand_position(x, y)

    def update_background(self, cv2_frame):
        """
        Render a BGR OpenCV frame onto the main camera canvas.
        Only active when camera_overlay=True was passed to __init__.
        Resizes frame to current window/canvas size when dynamically resized.
        """
        if not self._camera_overlay or self._cam_image_id is None:
            return
        try:
            from PIL import Image, ImageTk
            import cv2
            w = self.cam_canvas.winfo_width()
            h = self.cam_canvas.winfo_height()
            if w <= 1 or h <= 1:
                w, h = self._display_w, self._display_h
            frame = cv2.resize(cv2_frame, (w, h))
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self._current_photo = ImageTk.PhotoImage(Image.fromarray(rgb))
            self.cam_canvas.itemconfig(self._cam_image_id,
                                       image=self._current_photo)
        except Exception:
            pass

    # ── Internal ──────────────────────────────────────────────────────────────

    def _highlight_note(self, note_name, highlight=True):
        if note_name in self.note_objects:
            color = (self.colors['note_highlight'] if highlight
                     else self.colors['note_default'])
            self.canvas.itemconfig(self.note_objects[note_name]['circle'],
                                   fill=color)


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    root.title('MaestroSynth — move mouse to navigate')
    root.geometry(f'{CAM_W}x{CAM_H}')
    root.resizable(False, False)
    root.configure(bg='#000000')

    app = CircleOfFifthsRing(root)

    # Crosshair at camera-frame centre to aid testing
    cx, cy = CAM_W // 2, CAM_H // 2
    app.cam_canvas.create_line(cx - 30, cy, cx + 30, cy, fill='#444', width=1)
    app.cam_canvas.create_line(cx, cy - 30, cx, cy + 30, fill='#444', width=1)
    app.cam_canvas.create_text(cx + 6, cy - 14, text='centre',
                               fill='#555', font=('Arial', 9))

    # Moving the mouse over the camera area drives the wheel
    app.cam_canvas.bind('<Motion>',
                        lambda e: app.update_hand_position(e.x, e.y))
    app.cam_canvas.bind('<Leave>',
                        lambda e: app.clear_selection())

    root.mainloop()