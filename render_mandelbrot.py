import gint

def render_mandelbrot(it_max=12):
    for py in range(264): # Symmetry: only top half
        c_imag = (py - 264) / 150
        for px in range(320):
            c_real = (px - 200) / 150
            c = complex(c_real, c_imag)
            z = 0
            for i in range(it_max):
                if abs(z) > 2:
                    # Color based on escape time
                    gint.dpixel(px, py, gint.C_RGB(0, i, 0))
                    gint.dpixel(px, 527-py, gint.C_RGB(0, i, 0))
                    break
                z = z*z + c
            else:
                gint.dpixel(px, py, gint.C_RGB(0, 0, 0))
                gint.dpixel(px, 527-py, gint.C_RGB(0, 0, 0))
        if py % 5 == 0: gint.dupdate() # Partial updates for feedback

render_mandelbrot()
gint.getkey()
