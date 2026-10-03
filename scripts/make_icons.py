from PIL import Image, ImageDraw

def create_icon(size, filename, bg_color="#0056B3", fg_color="#FFFFFF"):
    img = Image.new("RGB", (size, size), color=bg_color)
    draw = ImageDraw.Draw(img)
    # Simple 'M' or just brain shape placeholder, let's just draw an M
    margin = size * 0.2
    w = size - margin * 2
    
    # M lines
    pts = [
        (margin, size - margin),
        (margin, margin),
        (size/2, size/2),
        (size - margin, margin),
        (size - margin, size - margin)
    ]
    draw.line(pts, fill=fg_color, width=int(size*0.1), joint="curve")
    
    img.save(filename)

if __name__ == "__main__":
    out_dir = "../dashboard/static"
    import os
    os.makedirs(out_dir, exist_ok=True)
    
    create_icon(192, os.path.join(out_dir, "icon-192.png"))
    create_icon(512, os.path.join(out_dir, "icon-512.png"))
    create_icon(180, os.path.join(out_dir, "apple-touch-icon.png"))
    print("Icons generated successfully.")
