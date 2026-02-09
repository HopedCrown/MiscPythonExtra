# -----------------------------------------------------------------------------
# Markdown Viewer - Simple MD Parser & Renderer
# Inspired by generic MD parsers and webcalc2.py layout engine
# -----------------------------------------------------------------------------
from gint import *
import time
import cinput

# --- Constants ---
SCREEN_W = 320
SCREEN_H = 528
HEADER_H = 40

# Colors
C_BG_DEFAULT = C_WHITE
C_TEXT_DEFAULT = C_BLACK
C_CODE_BG = 0xDEFB # Light gray/beige
C_HEADER_BORDER = 0x8410 # Gray
C_QUOTE_BAR = 0xC618 # Silver

# Fonts & Layout
FONT_W = 10
FONT_H = 18
LINE_H = 20 # Added line height for better spacing
TEXT_Y_OFFSET = 4 # Vertical offset for text

# --- Data Structures ---

class Style:
    def __init__(self):
        self.block = True # Block vs Inline
        self.margin = [0, 0, 0, 0] # T, R, B, L
        self.padding = [0, 0, 0, 0]
        self.border = [0, 0, 0, 0]
        self.bg_color = -1 # Transparent
        self.border_color = C_BLACK
        self.color = C_TEXT_DEFAULT
        self.font_scale = 1 # Reserved for future
        self.align = 0 # 0=Left, 1=Center, 2=Right
        self.pre = False # Preformatted (code blocks)

class Node:
    def __init__(self, type_name, parent=None):
        self.type = type_name
        self.parent = parent
        self.children = []
        self.spans = [] # For text nodes: list of (text, type/style_id)
        self.style = Style()
        
        # Computed Layout
        self.x = 0
        self.y = 0
        self.w = 0
        self.h = 0
        self.lines = [] # Computed line wrappers

    def add_child(self, child):
        self.children.append(child)
        child.parent = self

# --- Markdown Parser ---

# --- text sanitization ---

def sanitize_text(text):
    # Basic replacement for common unsupported chars
    if not isinstance(text, str): return str(text)
    return text.replace(u'\u2019', "'").replace(u'\u201c', '"').replace(u'\u201d', '"').replace(u'\u2014', '--')

# --- Markdown Parser ---

def parse_inline(text):
    """
    Parses inline markdown: **bold**, `code`, [link](url).
    Returns a list of tuples: (text_content, style_mask, data)
    style_mask: 0=Normal, 1=Bold, 2=Code, 3=Link
    """
    spans = []
    i = 0
    length = len(text)
    
    current_text = ""
    current_style = 0 # 0=Normal
    
    while i < length:
        # Code backtick
        if text[i] == '`':
            if current_text:
                spans.append((current_text, current_style, None))
                current_text = ""
            
            if current_style == 2:
                current_style = 0
            else:
                current_style = 2
            i += 1
            continue
            
        # Bold **
        if text[i:i+2] == '**':
            if current_text:
                spans.append((current_text, current_style, None))
                current_text = ""
            
            if current_style == 1:
                current_style = 0
            else:
                current_style = 1
            i += 2
            continue

        # Link [text](url)
        if text[i] == '[':
            end_bracket = text.find(']', i)
            if end_bracket != -1 and end_bracket + 1 < length and text[end_bracket+1] == '(':
                end_paren = text.find(')', end_bracket + 1)
                if end_paren != -1:
                    if current_text:
                        spans.append((current_text, current_style, None))
                        current_text = ""
                    
                    link_text = text[i+1:end_bracket]
                    link_url = text[end_bracket+2:end_paren]
                    
                    spans.append((link_text, 3, link_url)) # 3 = Link
                    i = end_paren + 1
                    continue
            
        current_text += text[i]
        i += 1

    if current_text:
        spans.append((current_text, current_style, None))
        
    return spans

def parse_markdown(md_text):
    root = Node('root')
    root.style.padding = [10, 5, 10, 5]
    
    lines = md_text.replace('\r\n', '\n').split('\n')
    
    i = 0
    n_lines = len(lines)
    
    while i < n_lines:
        line = lines[i]
        stripped = line.strip()
        
        # 1. Empty lines
        if not stripped:
            i += 1
            continue
            
        # 2. Syntax Checking
        
        # Headers
        if stripped.startswith('#'):
            level = 0
            for char in stripped:
                if char == '#': level += 1
                else: break
            
            content = stripped[level:].strip()
            
            node = Node('header', root)
            node.style.block = True
            node.style.margin = [10 if level == 1 else 15, 0, 10, 0]
            node.style.font_scale = 1 
            
            if level <= 2:
                node.style.border = [0, 0, 2, 0] # Bottom border
                node.style.padding = [0, 0, 5, 0]
                node.style.bg_color = C_WHITE
            
            node.spans = parse_inline(content)
            root.add_child(node)
            i += 1
            continue
            
        # Horizontal Rule
        if stripped.startswith('---'):
            node = Node('hr', root)
            node.style.margin = [10, 0, 10, 0]
            node.style.h = 2
            node.style.bg_color = C_BLACK
            root.add_child(node)
            i += 1
            continue
            
        # Block Quotes
        if stripped.startswith('> '):
            quote_text = stripped[2:].strip()
            i += 1
            while i < n_lines:
                next_line = lines[i].strip()
                if not next_line: break
                if any(next_line.startswith(x) for x in ['#', '-', '```', '---']): break
                
                # Check for > continuation or lazy continuation
                if next_line.startswith('> '):
                    quote_text += " " + next_line[2:].strip()
                else:
                    quote_text += " " + next_line
                i += 1
            
            node = Node('blockquote', root)
            node.style.margin = [5, 0, 5, 0]
            node.style.padding = [5, 5, 5, 10]
            node.style.border = [0, 0, 0, 2] # Left border
            node.style.bg_color = 0xEF5D # Light Gray
            node.style.border_color = C_QUOTE_BAR # Silver
            
            node.spans = parse_inline(quote_text)
            root.add_child(node)
            continue

        # Code Blocks
        if stripped.startswith('```'):
            code_lines = []
            i += 1
            while i < n_lines:
                if lines[i].strip().startswith('```'):
                    i += 1
                    break
                code_lines.append(lines[i]) # Preserve indentation
                i += 1
            
            node = Node('code_block', root)
            node.style.pre = True
            node.style.bg_color = C_CODE_BG
            node.style.color = C_BLACK # Black Text for code blocks
            node.style.padding = [5, 5, 5, 5]
            node.style.margin = [5, 0, 5, 0]
            node.style.border = [1, 1, 1, 1]
            # Use default border color (Black) for code blocks
            
            full_code = "\n".join(code_lines)
            node.spans = [(full_code, 2, None)] # Style 2 = Code
            
            root.add_child(node)
            continue
            
        # List Items
        if stripped.startswith('- '):
            content = stripped[2:].strip()
            node = Node('list_item', root)
            node.style.margin = [2, 0, 2, 5] 
            node.style.padding = [0, 0, 0, 12] # Indent content for bullet
            
            # No bullet in text, drawn manually
            node.spans = parse_inline(content)
            root.add_child(node)
            i += 1
            continue
            
        # Paragraphs
        para_text = stripped
        i += 1
        while i < n_lines:
            next_line = lines[i].strip()
            if not next_line: break
            if any(next_line.startswith(x) for x in ['#', '-', '```', '---', '>']): break
            
            para_text += " " + next_line
            i += 1
            
        node = Node('paragraph', root)
        node.style.margin = [0, 0, 8, 0]
        node.spans = parse_inline(para_text)
        root.add_child(node)
        
    return root

# --- Layout Engine ---

def get_wrapped_lines(spans, max_width, is_pre=False):
    """
    Wraps text spans into lines using dsize logic.
    """
    lines = []
    
    if is_pre:
        # Code block: Sanitized, allow wrap per line.
        raw_text = sanitize_text(spans[0][0])
        style = spans[0][1]
        data = spans[0][2]
        
        # Split by hard newlines
        hard_lines = raw_text.split('\n')
        for hl in hard_lines:
            if not hl: 
                # Empty line -> add empty line
                lines.append([]) 
                continue
            
            # Recursively wrap each hard line
            # Treat as normal text (is_pre=False)
            wrapped_subs = get_wrapped_lines([(hl, style, data)], max_width, False)
            if not wrapped_subs: lines.append([])
            else: lines.extend(wrapped_subs)
            
        return lines

    # Normal Wrapping
    current_line = [] 
    current_w = 0
    space_w, _ = dsize(" ", None)
    
    for text, style, data in spans:
        clean_text = sanitize_text(text)
        words = clean_text.split(' ')
        
        for idx, word in enumerate(words):
            if not word: continue 
            
            word_w, _ = dsize(word, None)
            
            # Determine space before this word
            add_space = False
            if idx > 0 or (current_w > 0 and current_line and not current_line[-1][0].endswith(" ")):
                add_space = True
            
            space_w_curr = space_w if add_space else 0

            # Wrap if overflows
            if current_w + space_w_curr + word_w > max_width and current_w > 0:
                lines.append(current_line)
                current_line = []
                current_w = 0
                space_w_curr = 0 
            
            # Append content
            prefix = " " if space_w_curr else ""
            current_line.append((prefix + word, style, data))
            current_w += space_w_curr + word_w
            
    if current_line:
        lines.append(current_line)
        
    return lines

def resolve_layout(node, container_w):
    s = node.style
    
    # Margins/Padding
    avail_w = container_w - s.margin[1] - s.margin[3] - s.border[1] - s.border[3]
    content_w = avail_w - s.padding[1] - s.padding[3]
    
    node.w = container_w 
    
    # Children or Content?
    current_h = s.padding[0] + s.border[0]
    
    if node.spans:
        # It's a text/leaf node
        lines = get_wrapped_lines(node.spans, content_w, s.pre)
        node.lines = lines
        text_h = len(lines) * LINE_H 
        current_h += text_h
    else:
        # Container
        for child in node.children:
            resolve_layout(child, content_w)
            
            child.x = s.margin[3] + s.border[3] + child.style.margin[3] + s.padding[3]
            child.y = current_h + child.style.margin[0]
            
            current_h += child.h + child.style.margin[0] + child.style.margin[2]
            
    node.h = current_h + s.padding[2] + s.border[2]

# --- Rendering ---

def draw_node(node, abs_x, abs_y, scroll_y, hotspots=None):
    screen_x = abs_x + node.x
    screen_y = abs_y + node.y - scroll_y
    
    # Cull
    if screen_y > SCREEN_H or screen_y + node.h < HEADER_H:
         return 

    s = node.style
    
    # Background
    bb_w = node.w - s.margin[1] - s.margin[3]
    if s.bg_color != -1:
        drect(screen_x, screen_y, screen_x + bb_w, screen_y + node.h, s.bg_color)
        
    # Borders
    
    # Top
    if s.border[0] > 0:
        drect(screen_x, screen_y, screen_x + bb_w, screen_y + s.border[0], s.border_color)
        
    # Right
    if s.border[1] > 0:
        drect(screen_x + bb_w - s.border[1], screen_y, screen_x + bb_w, screen_y + node.h, s.border_color)

    # Bottom
    if s.border[2] > 0: 
        by = screen_y + node.h - s.border[2]
        drect(screen_x, by, screen_x + bb_w, screen_y + node.h, s.border_color)
        
    # Left
    if s.border[3] > 0:
        drect(screen_x, screen_y, screen_x + s.border[3], screen_y + node.h, s.border_color)

    # Bullet for List Items
    if node.type == 'list_item':
        # Draw bullet centered on first line (circle radius 2)
        bx = screen_x + 6
        by = screen_y + s.padding[0] + s.border[0] + (LINE_H // 2)
        dcircle(bx, by, 2, C_BLACK, 1)

    # Text Content
    if node.lines:
        txt_y = screen_y + s.padding[0] + s.border[0]
        txt_x_start = screen_x + s.padding[3] + s.border[3]
        
        for line in node.lines:
            curr_x = txt_x_start
            
            if txt_y + LINE_H > HEADER_H and txt_y < SCREEN_H:
                for text, style_id, style_data in line:
                    col = s.color
                    t_w, _ = dsize(text, None)
                    
                    # Style modifications
                    if style_id == 2 and not s.pre: # Inline Code Highlight ONLY
                         drect(curr_x + 1, txt_y + 1, curr_x + t_w, txt_y + LINE_H - 3, 0xCE79) 
                    elif style_id == 1: # Bold
                         dtext(curr_x+1, txt_y + TEXT_Y_OFFSET, col, text)
                    elif style_id == 3: # Link
                         col = C_BLUE
                         dline(curr_x, txt_y + LINE_H - 2, curr_x + t_w, txt_y + LINE_H - 2, C_BLUE)
                         if hotspots is not None:
                             hotspots.append(((curr_x, txt_y, t_w, LINE_H), style_data))
                    
                    dtext(curr_x, txt_y + TEXT_Y_OFFSET, col, text)
                    curr_x += t_w
            
            txt_y += LINE_H

    # Children
    for child in node.children:
        draw_node(child, screen_x, screen_y, 0, hotspots)

# --- App Shell ---

# ... imports ...
import cinput

# ... existing code ...

# --- App Shell & IO ---

def draw_icon_menu(x, y, col):
    for i in range(3):
        drect(x, y + 4 + i*5, x + 18, y + 5 + i*5, col)

def draw_header(title):
    drect(0, 0, SCREEN_W, HEADER_H, 0x8410) # Gray header
    # dtext(10, 12, C_WHITE, title)
    # Menu Icon
    # draw_icon_menu(10, 10, C_WHITE) # If we want icon, need to shift title
    # Let's shift title and draw icon
    drect(0, 0, 40, HEADER_H, 0x8410) # Clear area
    draw_icon_menu(10, 10, C_WHITE)
    dtext(50, 16, C_WHITE, title)
    
    drect(0, HEADER_H, SCREEN_W, HEADER_H+2, C_BLACK) # Separator

def do_menu(current_file):
    opts = [
        "Open...",
        "Quit"
    ]
    choice = cinput.pick(opts, "Menu")
    
    if choice == "Open...":
        fname = cinput.input("File to open:")
        if fname: return fname
    elif choice == "Quit":
        return "QUIT"
    
    return None

def main():
    # Initial Load
    path = "1.md"
    dom = None
    
    def load(fname):
        nonlocal dom, path
        try:
            with open(fname, "r", encoding="utf-8") as f:
                content = f.read()
            # Parse
            dclear(C_WHITE)
            dtext(10, 200, C_BLACK, "Parsing...")
            dupdate()
            dom = parse_markdown(content)
            resolve_layout(dom, SCREEN_W)
            path = fname
        except Exception:
            # Fallback error
            dom = parse_markdown(f"# Error\nCould not load {fname}")
            resolve_layout(dom, SCREEN_W)
            path = fname

    load(path)
    
    scroll_y = 0
    running = True
    touch_latched = False
    
    clearevents()
    
    while running:
        dclear(C_WHITE)
        
        # Max Scroll Update
        max_scroll = max(0, dom.h - (SCREEN_H - HEADER_H))
        
        # Hotspots
        hotspots = []
        
        # Draw Document
        draw_node(dom, 0, HEADER_H + 5, scroll_y, hotspots)
        
        # Draw Header
        draw_header(path)
        
        # Scrollbar
        if dom.h > (SCREEN_H - HEADER_H):
            view_h = SCREEN_H - HEADER_H
            sb_h = max(20, int((view_h / dom.h) * view_h))
            sb_y = HEADER_H + int((scroll_y / dom.h) * view_h)
            drect(SCREEN_W-5, sb_y, SCREEN_W, sb_y+sb_h, 0x8410)
        
        dupdate()
        
        # Events
        cleareventflips()
        events = []
        ev = pollevent()
        while ev.type != KEYEV_NONE:
            events.append(ev)
            ev = pollevent()
            
        for e in events:
            if e.type == KEYEV_DOWN:
                if e.key == KEY_EXIT:
                    running = False
                elif e.key == KEY_UP:
                    scroll_y = max(0, scroll_y - 40)
                elif e.key == KEY_DOWN:
                    scroll_y = min(max_scroll, scroll_y + 40)
                elif e.key == KEY_MENU or e.key == KEY_F1:
                    res = do_menu(path)
                    if res == "QUIT": running = False
                    elif res: 
                        load(res)
                        scroll_y = 0
                    clearevents()
            
            elif e.type == KEYEV_TOUCH_UP:
                touch_latched = False
                
            elif e.type == KEYEV_TOUCH_DOWN:
                if not touch_latched:
                    touch_latched = True
                    # Header Click
                    if e.y < HEADER_H:
                        if e.x < 50: # Menu area
                            res = do_menu(path)
                            if res == "QUIT": running = False
                            elif res: 
                                load(res)
                                scroll_y = 0
                            clearevents()
                    else:
                        # Check Link Hotspots
                        clicked_link = False
                        for (hx, hy, hw, hh), link_url in hotspots:
                            if e.x >= hx and e.x <= hx + hw and e.y >= hy and e.y <= hy + hh:
                                if link_url:
                                    load(link_url)
                                    scroll_y = 0
                                    clicked_link = True
                                    clearevents()
                                    break
                                    
                        if not clicked_link:
                            # Drag scroll? 
                            pass

    print("Done")

if __name__ == "__main__":
    main()
