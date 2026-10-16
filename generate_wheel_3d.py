import build123d as bd

def build_crane_wheel():
    # Basic Parameters (mm)
    outer_tread_dia = 300.0
    r_tread = outer_tread_dia / 2.0  # 150.0 mm

    flange_dia = 330.0
    r_flange = flange_dia / 2.0      # 165.0 mm

    total_width = 90.0               # 90.0 mm
    flange_width = 15.0              # 15.0 mm each flange

    hub_dia = 100.0
    r_hub = hub_dia / 2.0            # 50.0 mm

    bore_dia = 50.0
    r_bore = bore_dia / 2.0          # 25.0 mm

    web_thickness = 30.0             # 30.0 mm
    web_recess = (total_width - web_thickness) / 2.0  # 30.0 mm on each side
    rim_thickness = 25.0             # rim inner radius = 125.0 mm
    r_rim_inner = r_tread - rim_thickness # 125.0 mm

    # Keyway parameters GOST 23360-78 (for d=50mm: b=14mm, t2=3.8mm)
    key_width = 14.0
    key_depth = 3.8                  # depth into hub bore

    z_half = total_width / 2.0        # 45.0 mm

    profile_pts = [
        (r_bore, -z_half),
        (r_hub, -z_half),
        (r_hub, -z_half + web_recess),
        (r_rim_inner, -z_half + web_recess),
        (r_rim_inner, -z_half),
        (r_flange, -z_half),
        (r_flange, -z_half + flange_width),
        (r_tread, -z_half + flange_width),
        (r_tread, z_half - flange_width),
        (r_flange, z_half - flange_width),
        (r_flange, z_half),
        (r_rim_inner, z_half),
        (r_rim_inner, z_half - web_recess),
        (r_hub, z_half - web_recess),
        (r_hub, z_half),
        (r_bore, z_half),
        (r_bore, -z_half),
    ]

    with bd.BuildPart() as wheel_part:
        with bd.BuildSketch(bd.Plane.XZ) as sketch:
            with bd.BuildLine():
                bd.Polyline(*profile_pts)
            bd.make_face()
        bd.revolve(axis=bd.Axis.Z)

        # Add keyway cut along Z axis
        with bd.BuildSketch(bd.Plane.XY) as key_sketch:
            with bd.Locations((0, r_bore + key_depth / 2.0)):
                bd.Rectangle(key_width, key_depth + 1.0)
        bd.extrude(amount=total_width + 10.0, both=True, mode=bd.Mode.SUBTRACT)

    return wheel_part.part

if __name__ == "__main__":
    wheel = build_crane_wheel()
    bd.export_step(wheel, "crane_wheel.step")
    bd.export_stl(wheel, "crane_wheel.stl")
    print("Exported crane_wheel.step and crane_wheel.stl successfully.")
