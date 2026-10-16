import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
import numpy as np
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def draw_dimension_arrow(ax, x1, y1, x2, y2, text="", text_pos="above", text_offset=2, arrow_size=3):
    # Extension lines / dimension line
    dx = x2 - x1
    dy = y2 - y1
    dist = np.hypot(dx, dy)
    if dist == 0:
        return

    ux, uy = dx / dist, dy / dist

    # Draw main dimension line
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle="<->", color="black", lw=0.8, mutation_scale=arrow_size*3)
    )

    # Draw text
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0

    # Angle calculation for rotated text
    angle = np.degrees(np.arctan2(dy, dx))
    if angle > 90:
        angle -= 180
    elif angle < -90:
        angle += 180

    # Offset perpendicular to dimension line
    nx, ny = -uy, ux
    tx = mx + nx * text_offset
    ty = my + ny * text_offset

    ax.text(tx, ty, text, fontsize=8, family='sans-serif', ha='center', va='center', rotation=angle)

def build_pdf_drawing():
    # Dimensions in mm
    # Figure setup for A3 (420 x 297 mm)
    fig = plt.figure(figsize=(16.54, 11.69), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 420)
    ax.set_ylim(0, 297)
    ax.axis('off')

    # Outer Border & GOST Frame (Left margin 20mm, others 5mm)
    ax.add_patch(mpatches.Rectangle((0, 0), 420, 297, fill=False, edgecolor='black', linewidth=1.5))
    ax.add_patch(mpatches.Rectangle((20, 5), 395, 287, fill=False, edgecolor='black', linewidth=1.5))

    # Title block GOST 2.104-68 (185 x 55 mm in bottom right corner: x=230 to 415, y=5 to 60)
    tb_x, tb_y = 230, 5
    tb_w, tb_h = 185, 55
    ax.add_patch(mpatches.Rectangle((tb_x, tb_y), tb_w, tb_h, fill=False, edgecolor='black', linewidth=1.2))

    # Title Block Grid Lines
    ax.plot([tb_x, tb_x + tb_w], [tb_y + 15, tb_y + 15], 'k-', lw=0.8)
    ax.plot([tb_x, tb_x + tb_w], [tb_y + 35, tb_y + 35], 'k-', lw=0.8)
    ax.plot([tb_x, tb_x + 65], [tb_y + 20, tb_y + 20], 'k-', lw=0.5)
    ax.plot([tb_x, tb_x + 65], [tb_y + 25, tb_y + 25], 'k-', lw=0.5)
    ax.plot([tb_x, tb_x + 65], [tb_y + 30, tb_y + 30], 'k-', lw=0.5)
    ax.plot([tb_x, tb_x + 65], [tb_y + 40, tb_y + 40], 'k-', lw=0.5)
    ax.plot([tb_x, tb_x + 65], [tb_y + 45, tb_y + 45], 'k-', lw=0.5)
    ax.plot([tb_x, tb_x + 65], [tb_y + 50, tb_y + 50], 'k-', lw=0.5)

    ax.plot([tb_x + 7, tb_x + 7], [tb_y + 15, tb_y + tb_h], 'k-', lw=0.5)
    ax.plot([tb_x + 17, tb_x + 17], [tb_y + 15, tb_y + tb_h], 'k-', lw=0.5)
    ax.plot([tb_x + 27, tb_x + 27], [tb_y + 15, tb_y + tb_h], 'k-', lw=0.5)
    ax.plot([tb_x + 42, tb_x + 42], [tb_y + 15, tb_y + tb_h], 'k-', lw=0.5)
    ax.plot([tb_x + 57, tb_x + 57], [tb_y + 15, tb_y + tb_h], 'k-', lw=0.5)
    ax.plot([tb_x + 65, tb_x + 65], [tb_y, tb_y + tb_h], 'k-', lw=1.0)

    ax.plot([tb_x + 135, tb_x + 135], [tb_y + 15, tb_y + 35], 'k-', lw=0.5)
    ax.plot([tb_x + 150, tb_x + 150], [tb_y + 15, tb_y + 35], 'k-', lw=0.5)
    ax.plot([tb_x + 167, tb_x + 167], [tb_y + 15, tb_y + 35], 'k-', lw=0.5)

    # Title Block Texts
    ax.text(tb_x + 2, tb_y + 51, "Изм.", fontsize=6, family='sans-serif')
    ax.text(tb_x + 8, tb_y + 51, "Лист", fontsize=6, family='sans-serif')
    ax.text(tb_x + 18, tb_y + 51, "№ докум.", fontsize=6, family='sans-serif')
    ax.text(tb_x + 43, tb_y + 51, "Подп.", fontsize=6, family='sans-serif')
    ax.text(tb_x + 58, tb_y + 51, "Дата", fontsize=6, family='sans-serif')

    ax.text(tb_x + 2, tb_y + 46, "Разраб.", fontsize=6, family='sans-serif')
    ax.text(tb_x + 2, tb_y + 41, "Пров.", fontsize=6, family='sans-serif')
    ax.text(tb_x + 2, tb_y + 31, "Т.контр.", fontsize=6, family='sans-serif')
    ax.text(tb_x + 2, tb_y + 21, "Н.контр.", fontsize=6, family='sans-serif')
    ax.text(tb_x + 2, tb_y + 16, "Утв.", fontsize=6, family='sans-serif')

    ax.text(tb_x + 18, tb_y + 46, "Иванов", fontsize=7, family='sans-serif')
    ax.text(tb_x + 18, tb_y + 41, "Петров", fontsize=7, family='sans-serif')

    ax.text(tb_x + 70, tb_y + 42, "КР-300.00.001", fontsize=12, fontweight='bold', family='sans-serif')
    ax.text(tb_x + 70, tb_y + 22, "Колесо крановое\nдвухободчатое", fontsize=11, fontweight='bold', family='sans-serif')
    ax.text(tb_x + 70, tb_y + 5, "Сталь 65Г ГОСТ 14959-2016", fontsize=9, family='sans-serif')

    ax.text(tb_x + 137, tb_y + 30, "Масса", fontsize=6, family='sans-serif')
    ax.text(tb_x + 152, tb_y + 30, "Масштаб", fontsize=6, family='sans-serif')
    ax.text(tb_x + 137, tb_y + 20, "45 кг", fontsize=8, family='sans-serif')
    ax.text(tb_x + 154, tb_y + 20, "1:2", fontsize=8, family='sans-serif')

    ax.text(tb_x + 170, tb_y + 30, "Лист 1", fontsize=6, family='sans-serif')
    ax.text(tb_x + 170, tb_y + 20, "Листов 1", fontsize=6, family='sans-serif')

    # -------------------------------------------------------------
    # VIEW 1: FRONT CROSS-SECTION (A-A)
    # Scale 1:2 -> dimensions scaled by 0.5 in drawing units (mm)
    # Center of View 1 at (X=110, Y=175)
    # -------------------------------------------------------------
    cx1, cy1 = 110, 175
    s = 0.5 # Scale 1:2

    # Dimensions in real mm
    r_bore = 25.0
    r_hub = 50.0
    r_rim_in = 125.0
    r_tread = 150.0
    r_flange = 165.0

    w_total = 90.0
    w_flange = 15.0
    w_web = 30.0
    recess = (w_total - w_web) / 2.0 # 30.0

    # Scaled profile relative to center (cx1, cy1)
    top_poly = [
        (-w_total/2*s, r_bore*s),
        (w_total/2*s, r_bore*s),
        (w_total/2*s, r_hub*s),
        ((w_total/2 - recess)*s, r_hub*s),
        ((w_total/2 - recess)*s, r_rim_in*s),
        (w_total/2*s, r_rim_in*s),
        (w_total/2*s, r_flange*s),
        ((w_total/2 - w_flange)*s, r_flange*s),
        ((w_total/2 - w_flange)*s, r_tread*s),
        ((-w_total/2 + w_flange)*s, r_tread*s),
        ((-w_total/2 + w_flange)*s, r_flange*s),
        (-w_total/2*s, r_flange*s),
        (-w_total/2*s, r_rim_in*s),
        ((-w_total/2 + recess)*s, r_rim_in*s),
        ((-w_total/2 + recess)*s, r_hub*s),
        (-w_total/2*s, r_hub*s),
    ]

    bottom_poly = [(x, -y) for (x, y) in top_poly]

    top_poly_abs = [(cx1 + x, cy1 + y) for (x, y) in top_poly]
    bottom_poly_abs = [(cx1 + x, cy1 + y) for (x, y) in bottom_poly]

    top_patch = mpatches.Polygon(top_poly_abs, closed=True, facecolor='none', edgecolor='black', linewidth=1.2, hatch='///')
    bottom_patch = mpatches.Polygon(bottom_poly_abs, closed=True, facecolor='none', edgecolor='black', linewidth=1.2, hatch='///')
    ax.add_patch(top_patch)
    ax.add_patch(bottom_patch)

    # Centerline for View 1
    ax.plot([cx1 - w_total*s - 15, cx1 + w_total*s + 15], [cy1, cy1], 'k-.', lw=0.6)
    ax.plot([cx1, cx1], [cy1 - r_flange*s - 15, cy1 + r_flange*s + 15], 'k-.', lw=0.6)

    ax.text(cx1, cy1 + r_flange*s + 20, "Разрез А-А (1:2)", fontsize=10, fontweight='bold', ha='center')

    # Dimension Lines View 1
    y_dim_w = cy1 - r_flange*s - 12
    ax.plot([cx1 - w_total/2*s, cx1 - w_total/2*s], [cy1 - r_flange*s - 2, y_dim_w - 3], 'k-', lw=0.5)
    ax.plot([cx1 + w_total/2*s, cx1 + w_total/2*s], [cy1 - r_flange*s - 2, y_dim_w - 3], 'k-', lw=0.5)
    draw_dimension_arrow(ax, cx1 - w_total/2*s, y_dim_w, cx1 + w_total/2*s, y_dim_w, text="90", text_offset=3)

    y_dim_tr = cy1 + r_flange*s + 8
    ax.plot([cx1 - (w_total/2 - w_flange)*s, cx1 - (w_total/2 - w_flange)*s], [cy1 + r_tread*s + 2, y_dim_tr + 3], 'k-', lw=0.5)
    ax.plot([cx1 + (w_total/2 - w_flange)*s, cx1 + (w_total/2 - w_flange)*s], [cy1 + r_tread*s + 2, y_dim_tr + 3], 'k-', lw=0.5)
    draw_dimension_arrow(ax, cx1 - (w_total/2 - w_flange)*s, y_dim_tr, cx1 + (w_total/2 - w_flange)*s, y_dim_tr, text="60", text_offset=3)

    x_dim_d50 = cx1 + w_total/2*s + 10
    ax.plot([cx1 + w_total/2*s, x_dim_d50 + 5], [cy1 + r_bore*s, cy1 + r_bore*s], 'k-', lw=0.5)
    ax.plot([cx1 + w_total/2*s, x_dim_d50 + 5], [cy1 - r_bore*s, cy1 - r_bore*s], 'k-', lw=0.5)
    draw_dimension_arrow(ax, x_dim_d50, cy1 - r_bore*s, x_dim_d50, cy1 + r_bore*s, text="Ø50 H7", text_offset=4)

    x_dim_d100 = cx1 + w_total/2*s + 25
    ax.plot([cx1 + w_total/2*s, x_dim_d100 + 5], [cy1 + r_hub*s, cy1 + r_hub*s], 'k-', lw=0.5)
    ax.plot([cx1 + w_total/2*s, x_dim_d100 + 5], [cy1 - r_hub*s, cy1 - r_hub*s], 'k-', lw=0.5)
    draw_dimension_arrow(ax, x_dim_d100, cy1 - r_hub*s, x_dim_d100, cy1 + r_hub*s, text="Ø100", text_offset=4)

    x_dim_d300 = cx1 - w_total/2*s - 15
    ax.plot([cx1 - w_total/2*s, x_dim_d300 - 5], [cy1 + r_tread*s, cy1 + r_tread*s], 'k-', lw=0.5)
    ax.plot([cx1 - w_total/2*s, x_dim_d300 - 5], [cy1 - r_tread*s, cy1 - r_tread*s], 'k-', lw=0.5)
    draw_dimension_arrow(ax, x_dim_d300, cy1 - r_tread*s, x_dim_d300, cy1 + r_tread*s, text="Ø300", text_offset=-4)

    x_dim_d330 = cx1 - w_total/2*s - 30
    ax.plot([cx1 - w_total/2*s, x_dim_d330 - 5], [cy1 + r_flange*s, cy1 + r_flange*s], 'k-', lw=0.5)
    ax.plot([cx1 - w_total/2*s, x_dim_d330 - 5], [cy1 - r_flange*s, cy1 - r_flange*s], 'k-', lw=0.5)
    draw_dimension_arrow(ax, x_dim_d330, cy1 - r_flange*s, x_dim_d330, cy1 + r_flange*s, text="Ø330", text_offset=-4)

    # -------------------------------------------------------------
    # VIEW 2: SIDE VIEW WITH KEYWAY
    # -------------------------------------------------------------
    cx2, cy2 = 285, 175

    c_flange = mpatches.Circle((cx2, cy2), r_flange*s, fill=False, edgecolor='black', linewidth=1.2)
    c_tread = mpatches.Circle((cx2, cy2), r_tread*s, fill=False, edgecolor='black', linewidth=1.0, linestyle='--')
    c_rim_in = mpatches.Circle((cx2, cy2), r_rim_in*s, fill=False, edgecolor='black', linewidth=0.8)
    c_hub = mpatches.Circle((cx2, cy2), r_hub*s, fill=False, edgecolor='black', linewidth=1.0)

    ax.add_patch(c_flange)
    ax.add_patch(c_tread)
    ax.add_patch(c_rim_in)
    ax.add_patch(c_hub)

    b_key = 14.0 * s
    t2_key = 3.8 * s
    r_b = r_bore * s

    y_key_top = cy2 + r_b + t2_key
    x_key_l = cx2 - b_key / 2.0
    x_key_r = cx2 + b_key / 2.0
    y_key_bot = cy2 + np.sqrt(max(0, r_b**2 - (b_key/2.0)**2))

    ax.plot([x_key_l, x_key_r], [y_key_top, y_key_top], 'k-', lw=1.2)
    ax.plot([x_key_l, x_key_l], [y_key_bot, y_key_top], 'k-', lw=1.2)
    ax.plot([x_key_r, x_key_r], [y_key_bot, y_key_top], 'k-', lw=1.2)

    theta1 = np.degrees(np.arctan2(y_key_bot - cy2, x_key_r - cx2))
    theta2 = np.degrees(np.arctan2(y_key_bot - cy2, x_key_l - cx2))
    arc_bore = mpatches.Arc((cx2, cy2), 2*r_b, 2*r_b, angle=0, theta1=theta1, theta2=360+theta2, edgecolor='black', linewidth=1.2)
    ax.add_patch(arc_bore)

    ax.plot([cx2 - r_flange*s - 15, cx2 + r_flange*s + 15], [cy2, cy2], 'k-.', lw=0.6)
    ax.plot([cx2, cx2], [cy2 - r_flange*s - 15, cy2 + r_flange*s + 15], 'k-.', lw=0.6)

    ax.text(cx2, cy2 + r_flange*s + 20, "Вид Б", fontsize=10, fontweight='bold', ha='center')

    ax.plot([x_key_l, x_key_l], [y_key_top + 2, y_key_top + 12], 'k-', lw=0.5)
    ax.plot([x_key_r, x_key_r], [y_key_top + 2, y_key_top + 12], 'k-', lw=0.5)
    draw_dimension_arrow(ax, x_key_l, y_key_top + 8, x_key_r, y_key_top + 8, text="14 Js9", text_offset=3)

    x_dim_k_h = cx2 + r_hub*s + 15
    ax.plot([cx2, x_dim_k_h + 3], [cy2 - r_b, cy2 - r_b], 'k-', lw=0.5)
    ax.plot([x_key_r, x_dim_k_h + 3], [y_key_top, y_key_top], 'k-', lw=0.5)
    draw_dimension_arrow(ax, x_dim_k_h, cy2 - r_b, x_dim_k_h, y_key_top, text="53.8 +0.2", text_offset=4)

    ax.plot([cx2 - r_flange*s - 10, cx2 + r_flange*s + 10], [cy2, cy2], 'k-', lw=2.0)
    ax.annotate("", xy=(cx2 - r_flange*s - 5, cy2 + 8), xytext=(cx2 - r_flange*s - 5, cy2), arrowprops=dict(arrowstyle="->", lw=1.5, color='black'))
    ax.annotate("", xy=(cx2 + r_flange*s + 5, cy2 + 8), xytext=(cx2 + r_flange*s + 5, cy2), arrowprops=dict(arrowstyle="->", lw=1.5, color='black'))
    ax.text(cx2 - r_flange*s - 10, cy2 + 10, "А", fontsize=11, fontweight='bold')
    ax.text(cx2 + r_flange*s + 10, cy2 + 10, "А", fontsize=11, fontweight='bold')

    # -------------------------------------------------------------
    # VIEW 3: ISOMETRIC 3D PREVIEW
    # -------------------------------------------------------------
    ax_3d = fig.add_axes([0.06, 0.22, 0.25, 0.30], projection='3d')
    ax_3d.set_facecolor('none')

    u = np.linspace(0, 2 * np.pi, 40)
    z_len = np.linspace(-45, 45, 20)
    U, Z = np.meshgrid(u, z_len)

    X_tread = 150 * np.cos(U)
    Y_tread = 150 * np.sin(U)
    ax_3d.plot_surface(X_tread, Y_tread, Z, color='lightblue', alpha=0.6, edgecolor='gray', linewidth=0.2)

    z_f1 = np.linspace(30, 45, 5)
    U_f, Z_f1 = np.meshgrid(u, z_f1)
    X_f1 = 165 * np.cos(U_f)
    Y_f1 = 165 * np.sin(U_f)
    ax_3d.plot_surface(X_f1, Y_f1, Z_f1, color='steelblue', alpha=0.7)

    Z_f2 = np.linspace(-45, -30, 5)
    U_f, Z_f2 = np.meshgrid(u, Z_f2)
    X_f2 = 165 * np.cos(U_f)
    Y_f2 = 165 * np.sin(U_f)
    ax_3d.plot_surface(X_f2, Y_f2, Z_f2, color='steelblue', alpha=0.7)

    X_hub = 50 * np.cos(U)
    Y_hub = 50 * np.sin(U)
    ax_3d.plot_surface(X_hub, Y_hub, Z, color='darkgray', alpha=0.8)

    ax_3d.set_axis_off()
    ax_3d.view_init(elev=25, azim=-45)

    ax.text(80, 120, "Наглядное 3D-изображение", fontsize=9, fontweight='bold', ha='center')

    # -------------------------------------------------------------
    # TECHNICAL REQUIREMENTS
    # -------------------------------------------------------------
    tech_req = (
        "Технические требования:\n"
        "1. *Размеры для справок.\n"
        "2. Твердость поверхности катания и внутренних поверхностей реборд: HRC 32...38.\n"
        "3. Материал: Сталь 65Г ГОСТ 14959-2016 (допускается Литье 55L ГОСТ 977-88).\n"
        "4. Шпоночный паз по ГОСТ 23360-78 (ширина 14 мм, глубина 3.8 мм).\n"
        "5. Радиальное биение поверхности катания не более 0.15 мм.\n"
        "6. Неуказанные предельные отклонения размеров: H14, h14, ±IT14/2."
    )
    ax.text(230, 80, tech_req, fontsize=8, family='sans-serif', va='bottom')

    plt.savefig("crane_wheel_drawing.png", dpi=300, bbox_inches='tight')
    plt.savefig("crane_wheel_drawing.pdf", dpi=300, bbox_inches='tight')
    print("Generated crane_wheel_drawing.pdf and crane_wheel_drawing.png successfully.")

if __name__ == "__main__":
    build_pdf_drawing()
