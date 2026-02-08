from gint import *
import random
import math

# Config
G_SIZE = 300
G_X, G_Y = 10, 70
BLOCK = 20
EPOCHS_PER_FRAME = 50   # Aggressive batching
MAX_EPOCHS = 5000       # Target 5000 epochs (Soft limit)
GAIN = 3.0              # Sharpness of sigmoid
SEED = 42               # Initial Seed

# Global State
random.seed(SEED)

# Math Helpers (Float LUT)
LUT_RES = 50
LUT_RANGE = 8.0
LUT_SIZE = int(2 * LUT_RANGE * LUT_RES)
SIGMOID_LUT = [0.0] * LUT_SIZE

dclear(C_WHITE)
dtext(10, 10, C_BLACK, "Building Float LUT...")
dupdate()

for i in range(LUT_SIZE):
    x = -LUT_RANGE + (i / LUT_RES)
    try:
        val = 1.0 / (1.0 + math.exp(-x * GAIN))
    except:
        val = 0.0 if x < 0 else 1.0
    SIGMOID_LUT[i] = val

def fast_sigmoid(x):
    if x <= -LUT_RANGE: return 0.0
    if x >= LUT_RANGE: return 1.0
    idx = int((x + LUT_RANGE) * LUT_RES)
    return SIGMOID_LUT[idx]

# Neural Network Globals
LR = 0.8
data = []
w_h = []
b_h = []
w_o = []
b_o = 0.0

def reset_network(new_seed):
    global data, w_h, b_h, w_o, b_o, SEED
    SEED = new_seed
    random.seed(SEED)
    
    # Regenerate Data
    data = []
    for _ in range(30):
        data.append(([random.uniform(0.1, 0.4), random.uniform(0.1, 0.4)], 0.0))
        data.append(([random.uniform(0.6, 0.9), random.uniform(0.6, 0.9)], 0.0))
        data.append(([random.uniform(0.6, 0.9), random.uniform(0.1, 0.4)], 1.0))
        data.append(([random.uniform(0.1, 0.4), random.uniform(0.6, 0.9)], 1.0))

    # Reset Weights (Aggressive Init)
    w_h = [[random.uniform(-2.5, 2.5) for _ in range(2)] for _ in range(4)]
    b_h = [random.uniform(-2.5, 2.5) for _ in range(4)]
    w_o = [random.uniform(-2.5, 2.5) for _ in range(4)]
    b_o = random.uniform(-2.5, 2.5)

# Initial Setup
reset_network(SEED)

# Save / Load Logic (CSV)
# You can open and modify that from the Spreadsheet app
MODEL_FILE = "pocket_nn.csv"

def save_model():
    try:
        with open(MODEL_FILE, "w") as f:
            # Header with Seed
            f.write(f"#SEED: {SEED}\n")
            # Flatten lists to CSV lines
            # w_h (flat list of 8 floats)
            flat_wh = [x for row in w_h for x in row]
            f.write(",".join(["{:.6f}".format(x) for x in flat_wh]) + "\n")
            # b_h
            f.write(",".join(["{:.6f}".format(x) for x in b_h]) + "\n")
            # w_o
            f.write(",".join(["{:.6f}".format(x) for x in w_o]) + "\n")
            # b_o
            f.write("{:.6f}\n".format(b_o))
        return True
    except:
        return False

def load_model():
    global w_h, b_h, w_o, b_o, SEED
    try:
        with open(MODEL_FILE, "r") as f:
            lines = f.readlines()
            # Parse Header
            header = lines[0].strip()
            if header.startswith("#SEED:"):
                SEED = int(header.split(":")[1].strip())
                random.seed(SEED)
            
            # Helper to parse CSV line
            def parse_csv(line): return [float(x) for x in line.strip().split(",")]

            # w_h
            vals_wh = parse_csv(lines[1])
            for r in range(4):
                for c in range(2):
                    w_h[r][c] = vals_wh[r*2 + c]
            
            # b_h
            b_h = parse_csv(lines[2])
            
            # w_o
            w_o = parse_csv(lines[3])
            
            # b_o
            b_o = float(lines[4].strip())
            
        return True
    except:
        return False

# Training Core
def train_step():
    global b_o
    sample = random.choice(data)
    inputs, target = sample
    i1, i2 = inputs
    
    # Forward (Unrolled)
    s0 = b_h[0] + i1 * w_h[0][0] + i2 * w_h[0][1]; h0 = fast_sigmoid(s0)
    s1 = b_h[1] + i1 * w_h[1][0] + i2 * w_h[1][1]; h1 = fast_sigmoid(s1)
    s2 = b_h[2] + i1 * w_h[2][0] + i2 * w_h[2][1]; h2 = fast_sigmoid(s2)
    s3 = b_h[3] + i1 * w_h[3][0] + i2 * w_h[3][1]; h3 = fast_sigmoid(s3)
    
    s_o = b_o + h0*w_o[0] + h1*w_o[1] + h2*w_o[2] + h3*w_o[3]
    pred = fast_sigmoid(s_o)
    
    # Backward
    error = pred - target
    out_delta = error * (pred * (1.0 - pred)) * GAIN
    
    # Updates (Unrolled)
    # N0
    grad0 = out_delta * h0
    h_delta0 = (out_delta * w_o[0]) * (h0 * (1.0 - h0)) * GAIN
    w_o[0] -= LR * grad0
    w_h[0][0] -= LR * h_delta0 * i1; w_h[0][1] -= LR * h_delta0 * i2
    b_h[0] -= LR * h_delta0
    # N1
    grad1 = out_delta * h1
    h_delta1 = (out_delta * w_o[1]) * (h1 * (1.0 - h1)) * GAIN
    w_o[1] -= LR * grad1
    w_h[1][0] -= LR * h_delta1 * i1; w_h[1][1] -= LR * h_delta1 * i2
    b_h[1] -= LR * h_delta1
    # N2
    grad2 = out_delta * h2
    h_delta2 = (out_delta * w_o[2]) * (h2 * (1.0 - h2)) * GAIN
    w_o[2] -= LR * grad2
    w_h[2][0] -= LR * h_delta2 * i1; w_h[2][1] -= LR * h_delta2 * i2
    b_h[2] -= LR * h_delta2
    # N3
    grad3 = out_delta * h3
    h_delta3 = (out_delta * w_o[3]) * (h3 * (1.0 - h3)) * GAIN
    w_o[3] -= LR * grad3
    w_h[3][0] -= LR * h_delta3 * i1; w_h[3][1] -= LR * h_delta3 * i2
    b_h[3] -= LR * h_delta3
    
    b_o -= LR * out_delta
    return abs(error)

def forward_viz(i1, i2):
    h0 = fast_sigmoid(b_h[0] + i1 * w_h[0][0] + i2 * w_h[0][1])
    h1 = fast_sigmoid(b_h[1] + i1 * w_h[1][0] + i2 * w_h[1][1])
    h2 = fast_sigmoid(b_h[2] + i1 * w_h[2][0] + i2 * w_h[2][1])
    h3 = fast_sigmoid(b_h[3] + i1 * w_h[3][0] + i2 * w_h[3][1])
    return fast_sigmoid(b_o + h0*w_o[0] + h1*w_o[1] + h2*w_o[2] + h3*w_o[3])

# UI Helpers
NUM_KEYS = {
    KEY_0: '0', KEY_1: '1', KEY_2: '2', KEY_3: '3', KEY_4: '4',
    KEY_5: '5', KEY_6: '6', KEY_7: '7', KEY_8: '8', KEY_9: '9'
}

def input_seed_ui():
    s = str(SEED)
    while True:
        dclear(C_WHITE)
        dtext(10, 10, C_BLACK, "Set Random Seed:")
        drect(10, 30, 200, 55, C_BLACK)
        drect(11, 31, 199, 54, C_WHITE)
        dtext(15, 35, C_BLACK, s + "_")
        dtext(10, 70, C_BLACK, "[EXE] Confirm  [DEL] Back")
        dupdate()
        
        k = getkey()
        if k.key == KEY_EXE:
            if len(s) > 0: return int(s)
            return SEED
        elif k.key == KEY_DEL:
            s = s[:-1]
        elif k.key in NUM_KEYS:
            if len(s) < 9: s += NUM_KEYS[k.key]

def run():
    epoch = 0
    avg_loss = 1.0
    msg = "Paused ([5] to resume)"
    paused = True  # Start paused!
    ignore_limit = False
    
    # Force initial draw
    redraw_needed = True
    
    while True:
        # Logic: Update
        if not paused:
            if epoch < MAX_EPOCHS or ignore_limit:
                loss_sum = 0
                # Train a batch
                for _ in range(EPOCHS_PER_FRAME):
                    loss_sum += train_step()
                
                avg_loss = loss_sum / EPOCHS_PER_FRAME
                epoch += EPOCHS_PER_FRAME
                redraw_needed = True
            else:
                paused = True # Auto-pause at limit
                msg = "Done! ([DEL] to quit)"
                redraw_needed = True

        # Logic: Draw
        if redraw_needed:
            dclear(C_WHITE)
            
            # Header
            title = "PocketNN"
            if paused: 
                if epoch >= MAX_EPOCHS and not ignore_limit: title += " (DONE)"
                else: title += " (PAUSED)"
            else: title += " (RUNNING)"
            dtext(10, 5, C_BLACK, title)
            dtext(200, 5, C_BLACK, f"Seed: {SEED}")
            
            dtext(10, 20, C_BLACK, f"Epoch: {epoch}" + ("" if ignore_limit else f"/{MAX_EPOCHS}"))
            dtext(200, 20, C_BLACK, f"Loss: {int(avg_loss*100)}%")
            
            
            # Controls Bar
            dtext(10, 35, C_BLACK, "[5] Play/Pause")
            dtext(200, 35, C_BLACK, "[=] Seed")
            dtext(10, 50, C_BLACK, "[7] Save [9] Load")
            if msg: dtext(10, 480, C_BLUE, msg)

            # Draw Heatmap
            for y in range(0, G_SIZE, BLOCK):
                norm_y = y / G_SIZE
                for x in range(0, G_SIZE, BLOCK):
                    norm_x = x / G_SIZE
                    p = forward_viz(norm_x, norm_y)
                    r = int(31 * (1.0 - p))
                    b = int(31 * p)
                    g = int(10 * (1.0 - abs(p - 0.5) * 2))
                    drect(G_X+x, G_Y+y, G_X+x+BLOCK, G_Y+y+BLOCK, C_RGB(r, g, b))

            # Draw Data
            for inputs, target in data:
                px = G_X + int(inputs[0] * G_SIZE)
                py = G_Y + int(inputs[1] * G_SIZE)
                col = C_WHITE if target < 0.5 else C_BLACK
                drect(px-2, py-2, px+2, py+2, col)
                
            dupdate()
            redraw_needed = False
        
        # Logic: Input
        key_code = 0
        
        if paused:
            # When paused, we BLOCK to save battery/CPU.
            # This waits indefinitely for a key press.
            k = getkey()
            if k.type == KEYEV_DOWN:
                key_code = k.key
        else:
            # When running, we POLL the queue.
            # We drain the queue to ensure we catch any key press happened during calculation.
            while True:
                ev = pollevent()
                if ev.type == KEYEV_NONE: 
                    break # Queue empty
                if ev.type == KEYEV_DOWN:
                    key_code = ev.key
                    # Optional: Break early if a command key is found to ensure it's handled immediately?
                    # For now, last key wins is okay, or we can handle specific priority keys.
                    if key_code in [KEY_5, KEY_EXIT, KEY_DEL, KEY_7, KEY_9, KEY_EQUALS]:
                        break 
        
        # Dispatch
        if key_code == KEY_DEL or key_code == KEY_EXIT:
            return
        
        if key_code == KEY_5:
            paused = not paused
            if not paused: 
                msg = ""
                # If we were at the limit and hit play, we enable free run
                if epoch >= MAX_EPOCHS:
                    ignore_limit = True 
            else:
                msg = "Paused ([5] to resume)"
            redraw_needed = True
            
        if key_code == KEY_EQUALS:
            new_s = input_seed_ui()
            reset_network(new_s)
            epoch = 0
            paused = True # Auto-pause on reset
            ignore_limit = False
            msg = "Reseeded!"
            redraw_needed = True
            
        if key_code == KEY_7:
            dtext(10, 480, C_BLACK, "Saving...")
            dupdate()
            if save_model(): msg = "Saved CSV!"
            else: msg = "Error Saving"
            redraw_needed = True
            
        if key_code == KEY_9:
            dtext(10, 480, C_BLACK, "Loading...")
            dupdate()
            if load_model(): 
                # epoch = 0 # Epoch count is not in CSV, reset makes sense OR keep?
                # Usually better to reset context if we don't know the epoch.
                # But you might want to continue training.
                msg = "Loaded CSV!"
                redraw_needed = True
            else: 
                msg = "Error Loading"
                redraw_needed = True

run()
