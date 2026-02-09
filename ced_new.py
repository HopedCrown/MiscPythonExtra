from gint import *
from io import open
import cinput

# =============================================================================
# CONFIGURATION
# =============================================================================

SCREEN_W = 320
SCREEN_H = 528

# Colors will be loaded from theme
# Default Fallback
COL_BG = C_WHITE
COL_TXT = C_BLACK

# Syntax Highlighting Defaults
COL_KW  = C_BLUE
COL_STR = 0x0480 # Dark Green
COL_COM = 0x7BEF # C_GRAY
COL_NUM = C_RED
COL_OP  = 0xF81F # C_MAGENTA

# Layout
HEADER_H = 40
TEXT_LINE_H = 20
TEXT_MARGIN_X = 5
# Text Y offset within the line (centering correction)
TEXT_Y_OFFSET = 4 

# =============================================================================
# TOKENIZER (Syntax Highlighting)
# =============================================================================

KEYWORDS = {
    "def", "class", "if", "else", "elif", "while", "for", "import", "from", 
    "return", "True", "False", "None", "break", "continue", "pass", "try", 
    "except", "with", "as", "global", "print", "len", "range", "in", "is", 
    "not", "and", "or"
}

def is_digit(char: str) -> bool:
    return "0" <= char <= "9"

def tokenize_line(line: str) -> list:
    """Simple lexer for syntax highlighting."""
    tokens = []
    i = 0
    length = len(line)
    OPERATORS = set("+-*/%=<>!&|^~")
    SEPARATORS = set("()[]{}:,.")
    
    while i < length:
        char = line[i]
        
        if char == "#":
            tokens.append((line[i:], COL_COM))
            break
        elif char in ('"', "'"):
            quote = char
            start = i
            i += 1
            while i < length and line[i] != quote:
                i += 1
            if i < length: i += 1
            tokens.append((line[start:i], COL_STR))
        elif char in OPERATORS or char in SEPARATORS:
            tokens.append((char, COL_OP))
            i += 1
        elif char == " " or char == "\t":
            tokens.append((char, COL_TXT))
            i += 1
        else:
            start = i
            while i < length:
                c = line[i]
                if c in OPERATORS or c in SEPARATORS or c in (" ", "\t", "#", '"', "'"):
                    break
                i += 1
            word = line[start:i]
            if not word: continue
            
            if is_digit(word[0]):
                tokens.append((word, COL_NUM))
            elif word in KEYWORDS:
                tokens.append((word, COL_KW))
            else:
                tokens.append((word, COL_TXT))
    return tokens

# =============================================================================
# EDITOR CLASS
# =============================================================================

class Editor:
    def __init__(self):
        self.lines = [""]
        self.filename = "untitled.py"
        
        # Theme State
        self.current_theme_name = 'light'
        self.theme = cinput.get_theme(self.current_theme_name)
        self.update_colors()
        
        # Settings
        self.word_wrap = False
        
        # Cursor & Viewport
        self.cy = 0
        self.cx = 0
        self.vy = 0
        
        # Instantiate the Keyboard Widget from cinput
        self.keyboard = cinput.Keyboard(theme=self.current_theme_name, layout='qwerty')
        self.keyboard.visible = False 
        
        self.msg = "Welcome to CED"
        self.msg_timer = 100

    def update_colors(self):
        global COL_BG, COL_TXT, COL_KW, COL_STR, COL_COM, COL_NUM, COL_OP
        t = self.theme
        COL_BG = t['modal_bg']
        COL_TXT = t['txt']
        # Adjust syntax colors based on brightness if needed
        if self.current_theme_name == 'dark':
            COL_KW  = 0x4C7F # Light Blue
            COL_STR = 0x8666 # Light Green
            COL_OP  = 0xF81F # Magenta
        else:
            COL_KW  = C_BLUE
            COL_STR = 0x0480
            COL_OP  = 0xF81F

    def switch_theme(self):
        themes = ['light', 'dark', 'grey']
        try:
            idx = themes.index(self.current_theme_name)
        except: idx = 0
        new_name = themes[(idx + 1) % len(themes)]
        
        self.current_theme_name = new_name
        self.theme = cinput.get_theme(new_name)
        self.update_colors()
        
        # Re-init keyboard with new theme
        vis = self.keyboard.visible
        self.keyboard = cinput.Keyboard(theme=new_name, layout='qwerty')
        self.keyboard.visible = vis

    # --- Cursor Management ---
    
    def clamp_cursor(self):
        if self.cy < 0: self.cy = 0
        if self.cy >= len(self.lines): self.cy = len(self.lines) - 1
        
        line_len = len(self.lines[self.cy])
        if self.cx < 0: self.cx = 0
        if self.cx > line_len: self.cx = line_len

    def get_wrapped_line_info(self, line):
        """
        Calculates wrapping for a single logical line.
        Returns (num_visual_lines, cursor_visual_row)
        cursor_visual_row is -1 if not calculating for cursor.
        """
        
        if not self.word_wrap:
            # If not wrapping, every logical line is 1 visual line.
            # Cursor is always on row 0.
            return 1, 0
        
        tokens = tokenize_line(line)
        cur_x = TEXT_MARGIN_X
        visual_lines = 1
        cursor_row = -1
        
        # Cursor tracking
        char_count = 0
        found_cursor = False
        
        # Check start of line cursor
        if self.cx == 0: found_cursor = True; cursor_row = 0

        for text, color in tokens:
            t_w, _ = dsize(text, None)
            
            # Wrap check
            if cur_x + t_w > SCREEN_W - 5:
                visual_lines += 1
                cur_x = TEXT_MARGIN_X
            
            # Cursor tracking
            if not found_cursor:
                # Is cursor inside this token?
                # range is char_count+1 to char_count+len
                if self.cx > char_count and self.cx <= char_count + len(text):
                    cursor_row = visual_lines - 1
                    found_cursor = True
            
            cur_x += t_w
            char_count += len(text)
            
        if not found_cursor and self.cx == char_count:
            cursor_row = visual_lines - 1
            
        return visual_lines, cursor_row

    def scroll_to_cursor(self):
        kb_h = 260 if self.keyboard.visible else 0
        view_h = SCREEN_H - HEADER_H - kb_h
        
        # 1. Logic for moving UP (easy)
        if self.cy < self.vy:
            self.vy = self.cy
            return

        # 2. Logic for moving DOWN with Wrap support
        # We assume vy is correct start, we simulate drawing to see if cy is on screen.
        
        # Safety break for huge files
        if self.cy > self.vy + 100:
            self.vy = self.cy - 5
        
        while True:
            current_visual_h = 0
            cursor_is_visible = False
            
            # Simulate rendering from vy
            for i in range(self.vy, len(self.lines)):
                if not self.word_wrap:
                    # Simple mode
                    line_h = TEXT_LINE_H
                    if i == self.cy:
                        # Check if bottom of cursor is in view
                        if current_visual_h + line_h <= view_h:
                            cursor_is_visible = True
                else:
                    # Wrapped mode
                    vis_lines, cur_row = self.get_wrapped_line_info(self.lines[i])
                    line_h = vis_lines * TEXT_LINE_H
                    
                    if i == self.cy:
                        # Cursor is on 'cur_row' (0-indexed) of this logical line
                        # Calc Y of the bottom of that visual row relative to screen top
                        cursor_bottom = current_visual_h + (cur_row + 1) * TEXT_LINE_H
                        if cursor_bottom <= view_h:
                            cursor_is_visible = True
                
                current_visual_h += line_h
                
                # Optimization: If we passed the cursor logic line, stop
                if i > self.cy: break
                # If we filled the screen and haven't reached cursor, definitely invisible
                if current_visual_h > view_h and i < self.cy: break
                if i == self.cy: break

            if cursor_is_visible:
                break
            else:
                # Scroll down
                self.vy += 1
                if self.vy > self.cy: self.vy = self.cy; break

    # --- File Operations (Using cinput Dialogs) ---

    def do_menu(self):
        # Use the List Picker for a menu
        wrap_status = "On" if self.word_wrap else "Off"
        opts = [
            "New", 
            "Save", 
            "Save As...", 
            "Open...", 
            f"Word Wrap: {wrap_status}",
            "Theme: " + self.current_theme_name, 
            "Quit"
        ]
        choice = cinput.pick(opts, "Menu", theme=self.current_theme_name)
        
        if choice == "New":
            self.lines = [""]
            self.filename = "untitled.py"
            self.cy = 0; self.cx = 0
        elif choice == "Save":
            self.save_file()
        elif choice == "Save As...":
            self.save_as_dialog()
        elif choice == "Open...":
            self.load_file_dialog()
        elif choice and choice.startswith("Word Wrap"):
            self.word_wrap = not self.word_wrap
        elif choice and choice.startswith("Theme"):
            self.switch_theme()
        elif choice == "Quit":
            return "QUIT"
        return None

    def load_file_dialog(self):
        fname = cinput.input("File to open:", theme=self.current_theme_name)
        if fname:
            self.load_file(fname)

    def save_as_dialog(self):
        fname = cinput.input("Save as:", theme=self.current_theme_name)
        if fname:
            self.save_file(fname)

    def load_file(self, filename):
        try:
            with open(filename, "r") as f:
                content = f.read()
                self.lines = content.replace("\r\n", "\n").split("\n")
                if not self.lines: self.lines = [""]
            self.filename = filename
            self.msg = "Loaded " + filename
            self.cy = 0; self.cx = 0
        except:
            self.msg = "Error loading " + filename
        self.msg_timer = 60

    def save_file(self, target_name=None):
        target = target_name if target_name else self.filename
        if target == "untitled.py":
            target = cinput.input("Save as:", theme=self.current_theme_name)
            if not target: return 
        
        try:
            with open(target, "w") as f:
                f.write("\n".join(self.lines))
            self.filename = target
            self.msg = "Saved " + target
        except:
            self.msg = "Error saving file"
        self.msg_timer = 60

    # --- Text Editing ---

    def insert_char(self, char):
        self.clamp_cursor()
        line = self.lines[self.cy]
        self.lines[self.cy] = line[:self.cx] + char + line[self.cx:]
        self.cx += 1
        self.clamp_cursor()

    def delete_char(self):
        self.clamp_cursor()
        if self.cx > 0:
            line = self.lines[self.cy]
            self.lines[self.cy] = line[:self.cx-1] + line[self.cx:]
            self.cx -= 1
        elif self.cy > 0:
            curr = self.lines.pop(self.cy)
            self.cy -= 1
            self.cx = len(self.lines[self.cy])
            self.lines[self.cy] += curr
        self.clamp_cursor()

    def new_line(self):
        self.clamp_cursor()
        line = self.lines[self.cy]
        rem = line[self.cx:]
        self.lines[self.cy] = line[:self.cx]
        self.cy += 1
        self.lines.insert(self.cy, rem)
        self.cx = 0
        self.clamp_cursor()

    # --- Drawing ---

    def get_cursor_rect(self, line, cx):
        """
        Returns (x, relative_y_offset) for the cursor at index cx.
        """
        tokens = tokenize_line(line)
        cur_x = TEXT_MARGIN_X
        cur_y = 0
        char_count = 0
        
        # Handle start of line
        if cx == 0:
            return cur_x, cur_y

        for text, color in tokens:
            t_w, _ = dsize(text, None)
            
            # Check Wrap
            if self.word_wrap and cur_x + t_w > SCREEN_W - 5:
                cur_y += TEXT_LINE_H
                cur_x = TEXT_MARGIN_X
            
            # Is cursor in this token?
            # Range is inclusive of start, exclusive of end, 
            # BUT cursor can be at the very end of the token.
            token_len = len(text)
            
            if cx >= char_count and cx <= char_count + token_len:
                # Calculate local offset
                local_off = cx - char_count
                
                # Measure width up to cursor within this token
                # Using dsize on the substring is safer than drsize for exact measurement
                sub_w, _ = dsize(text[:local_off], None)
                
                return cur_x + sub_w, cur_y
            
            cur_x += t_w
            char_count += token_len
            
        # Fallback: End of line
        return cur_x, cur_y

    def get_cx_from_px(self, line, target_x, target_visual_row):
        """
        Maps a pixel X coordinate within a specific visual row back to a char index.
        Unified logic for both Wrap and Non-Wrap modes.
        """
        tokens = tokenize_line(line)
        
        cur_x = TEXT_MARGIN_X
        cur_vis_row = 0
        char_count = 0
        
        # If the line is empty, return 0
        if not tokens: return 0

        for text, color in tokens:
            t_w, _ = dsize(text, None)
            
            # --- UNIFIED WRAP LOGIC ---
            # Only wrap if enabled AND we hit the edge
            if self.word_wrap and cur_x + t_w > SCREEN_W - 5:
                # If the click was on the row we just finished
                if cur_vis_row == target_visual_row:
                    # User clicked past the end of the content on this row
                    return char_count
                
                cur_vis_row += 1
                cur_x = TEXT_MARGIN_X

            # --- HIT TEST ---
            if cur_vis_row == target_visual_row:
                # We are on the correct row. 
                # Does the click fall within this token's width?
                # OR is it the last token and the click is to the right?
                
                # Check if target_x is 'covered' by this token or before it
                if target_x < cur_x + t_w:
                    rel_x = target_x - cur_x
                    if rel_x < 0: rel_x = 0 # Safety for margin clicks
                    
                    # Use drsize for pixel-perfect char detection
                    # drsize returns (offset_in_bytes/chars, width_in_pixels)
                    offset, fit_w = drsize(text, None, rel_x)
                    
                    # 'offset' is how many chars fit in rel_x.
                    # Check if we should snap to the next char (nearest neighbor)
                    if offset < len(text):
                        char_w, _ = dsize(text[offset], None)
                        # If we are past the midpoint of the char, pick next
                        if rel_x > fit_w + (char_w // 2):
                            offset += 1
                            
                    return char_count + offset

            cur_x += t_w
            char_count += len(text)

        # If we exhausted the loop, return the end of the line
        return char_count

    def get_cx_from_px_linear(self, line, target_x):
        # Deprecated by get_cx_from_px handling both
        pass

    def draw_icon_menu(self, x, y, col):
        for i in range(3):
            drect(x, y + 4 + i*5, x + 18, y + 5 + i*5, col)

    def draw_icon_kbd(self, x, y, col):
        drect_border(x, y+2, x+22, y+16, C_NONE, 1, col)
        for r in range(2):
            for c in range(3):
                px = x + 3 + c*6
                py = y + 5 + r*5
                drect(px, py, px+3, py+2, col)

    def draw_indentation_guides(self, line, x, y):
        # Count leading spaces
        spaces = 0
        for char in line:
            if char == ' ': spaces += 1
            else: break
        
        # Guide color (subtle)
        guide_col = 0xCE59 if self.current_theme_name == 'light' else 0x4208
        
        space_w, _ = dsize(' ', None)
        
        # Draw horizontal lines for every 4 spaces
        # Width of 4 spaces
        block_w = space_w * 4
        
        for t in range(spaces // 4):
            guide_x = x + t * block_w
            # Draw horizontal bar at bottom of line height
            drect(guide_x, y + TEXT_LINE_H - 2, guide_x + block_w - 2, y + TEXT_LINE_H - 1, guide_col)

    def draw_text_content(self, view_h):
        # Clip
        dwindow_set(0, HEADER_H, SCREEN_W, SCREEN_H)
        
        current_screen_y = HEADER_H + 6 
        max_y = HEADER_H + view_h
        
        for i in range(self.vy, len(self.lines)):
            if current_screen_y >= max_y: break
            
            line = self.lines[i]
            tokens = tokenize_line(line)
            
            # Draw Indentation Guides (Always on the first visual row of the line)
            self.draw_indentation_guides(line, TEXT_MARGIN_X, current_screen_y)

            # Draw Cursor if it's on this line
            if i == self.cy:
                # Calculate relative cursor pos
                c_x, c_y_off = self.get_cursor_rect(line, self.cx)
                
                # Draw cursor rect (Absolute position)
                cursor_screen_y = current_screen_y + c_y_off
                
                # Only draw if cursor is visible within the viewport
                if cursor_screen_y < max_y:
                    drect(c_x, cursor_screen_y, c_x + 2, cursor_screen_y + TEXT_LINE_H - 2, COL_TXT)

            # --- UNIFIED DRAWING LOOP ---
            cur_x = TEXT_MARGIN_X
            line_start_y = current_screen_y # Remember where this logical line started
            
            for text, color in tokens:
                t_w, _ = dsize(text, None)
                
                # Wrap Logic
                if self.word_wrap and cur_x + t_w > SCREEN_W - 5:
                    current_screen_y += TEXT_LINE_H
                    cur_x = TEXT_MARGIN_X
                    if current_screen_y >= max_y: break # Stop drawing if off screen
                
                # Optimization: In non-wrap mode, if X is way off screen, skip dtext
                if not self.word_wrap and cur_x > SCREEN_W:
                    # We continue the loop to track cx correctly, but don't draw
                    pass 
                else:
                    dtext(cur_x, current_screen_y + TEXT_Y_OFFSET, color, text)
                
                cur_x += t_w
            
            current_screen_y += TEXT_LINE_H
            
        dwindow_set(0, 0, SCREEN_W, SCREEN_H) # Reset clip

    def draw(self):
        t = self.theme
        dclear(COL_BG)
        
        # 1. Material Header
        header_col = t['accent']
        header_txt = t['txt_acc']
        
        drect(0, 0, SCREEN_W, HEADER_H, header_col)
        
        # Left Icon: Menu (x=10)
        self.draw_icon_menu(10, 10, header_txt)
        
        # Right Icon: Keyboard Toggle (x=SCREEN_W-35)
        kbd_x = SCREEN_W - 35
        if not self.keyboard.visible:
            self.draw_icon_kbd(kbd_x, 10, header_txt)
        else:
            self.draw_icon_kbd(kbd_x, 10, header_txt)
            drect(kbd_x, 22, kbd_x + 22, 23, header_txt) 
            
        # Title (Centered)
        title = self.filename + ("*" if False else "") 
        dtext_opt(SCREEN_W//2, HEADER_H//2, header_txt, C_NONE, DTEXT_CENTER, DTEXT_MIDDLE, title, -1)

        # 2. Text Area
        # Determine visible area height based on keyboard
        kb_h = 260 if self.keyboard.visible else 0
        view_h = SCREEN_H - HEADER_H - kb_h
        
        # Draw Content
        self.draw_text_content(view_h)

        # 3. Message Overlay
        if self.msg_timer > 0:
            self.msg_timer -= 1
            dtext(10, SCREEN_H - kb_h - 20, C_RED, self.msg)

        # 4. Keyboard
        self.keyboard.draw()
        
        dupdate()

# =============================================================================
# MAIN LOOP
# =============================================================================

def main():
    editor = Editor()
    clearevents()
    
    running = True
    
    # Touch latch for buttons
    touch_latched = False
    
    while running:
        editor.draw()
        
        cleareventflips()
        
        events = []
        ev = pollevent()
        while ev.type != KEYEV_NONE:
            events.append(ev)
            ev = pollevent()
            
        for e in events:
            # Shortcuts
            if e.type == KEYEV_DOWN:
                if e.key == KEY_MENU or e.key == KEY_F1:
                    res = editor.do_menu()
                    if res == "QUIT": running = False
                    clearevents()
                    break
                
                elif e.key == KEY_EXIT or e.key == KEY_KBD: 
                    editor.keyboard.visible = not editor.keyboard.visible
                
                # Nav (Logical Lines)
                elif e.key == KEY_UP: 
                    editor.cy -= 1; editor.clamp_cursor()
                    editor.scroll_to_cursor()
                elif e.key == KEY_DOWN: 
                    editor.cy += 1; editor.clamp_cursor()
                    editor.scroll_to_cursor()
                elif e.key == KEY_LEFT: 
                    editor.cx -= 1; editor.clamp_cursor()
                elif e.key == KEY_RIGHT: 
                    editor.cx += 1; editor.clamp_cursor()
                
                # Editing
                elif e.key == KEY_EXE: editor.new_line()
                elif e.key == KEY_DEL: editor.delete_char()

            # Touch Logic - Only process ONCE per press
            if e.type == KEYEV_TOUCH_UP:
                touch_latched = False
                editor.keyboard.last_key = None 
            
            elif e.type == KEYEV_TOUCH_DOWN:
                if not touch_latched:
                    # Mark as latched immediately
                    touch_latched = True
                    
                    # Header Interaction
                    if e.y < HEADER_H:
                        if e.x < 40: 
                            if editor.do_menu() == "QUIT": running = False
                        elif e.x > SCREEN_W - 40:
                            editor.keyboard.visible = not editor.keyboard.visible
                    
                    # Text Area Interaction (Wrap Aware)
                    elif not editor.keyboard.visible or e.y < editor.keyboard.y:
                        rel_y = e.y - (HEADER_H + 6) # Account for padding
                        
                        # We need to find which visual line this corresponds to
                        # Iterate visual lines from top
                        current_visual_y = 0
                        found_logic_row = -1
                        found_visual_row_offset = 0
                        
                        for i in range(editor.vy, len(editor.lines)):
                            line = editor.lines[i]
                            if not editor.word_wrap:
                                line_h = TEXT_LINE_H
                                if rel_y >= current_visual_y and rel_y < current_visual_y + line_h:
                                    found_logic_row = i
                                    found_visual_row_offset = 0
                                    break
                            else:
                                vis_lines, _ = editor.get_wrapped_line_info(line)
                                line_h = vis_lines * TEXT_LINE_H
                                if rel_y >= current_visual_y and rel_y < current_visual_y + line_h:
                                    found_logic_row = i
                                    found_visual_row_offset = (rel_y - current_visual_y) // TEXT_LINE_H
                                    break
                            current_visual_y += line_h
                        
                        if found_logic_row != -1:
                            editor.cy = found_logic_row
                            editor.cx = editor.get_cx_from_px(editor.lines[found_logic_row], e.x, found_visual_row_offset)
                            editor.clamp_cursor()
                    
                    # Keyboard Interaction
                    elif editor.keyboard.visible:
                        res = editor.keyboard.update(e)
                        if res:
                            if res == "ENTER": editor.new_line()
                            elif res == "BACKSPACE": editor.delete_char()
                            elif res == "CAPS": pass
                            elif len(res) == 1: editor.insert_char(res)

main()
