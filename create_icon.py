#!/usr/bin/env python3
"""
create_icon.py - Generate CadOwl icon in Walmart colors

Creates a professional-looking icon with an owl + CAD theme
"""

import struct
import zlib
from pathlib import Path

# Walmart colors
BLUE = (0, 83, 226)        # #0053e2
SPARK = (255, 194, 32)     # #ffc220
WHITE = (255, 255, 255)
DARK = (30, 30, 30)

def create_ico_file(output_path: Path, sizes: list = [16, 32, 48, 64, 128, 256]):
    """Create a .ico file with multiple sizes."""
    
    images = []
    for size in sizes:
        png_data = create_owl_png(size)
        images.append((size, png_data))
    
    # ICO file format
    # Header: 2 bytes reserved, 2 bytes type (1=ico), 2 bytes count
    ico_data = bytearray()
    ico_data.extend(struct.pack('<HHH', 0, 1, len(images)))
    
    # Calculate offsets
    header_size = 6 + (16 * len(images))
    offset = header_size
    
    # Directory entries
    for size, png_data in images:
        width = size if size < 256 else 0
        height = size if size < 256 else 0
        ico_data.extend(struct.pack('<BBBBHHII',
            width,           # Width
            height,          # Height
            0,               # Color palette
            0,               # Reserved
            1,               # Color planes
            32,              # Bits per pixel
            len(png_data),   # Size of image data
            offset           # Offset to image data
        ))
        offset += len(png_data)
    
    # Image data
    for size, png_data in images:
        ico_data.extend(png_data)
    
    with open(output_path, 'wb') as f:
        f.write(ico_data)
    
    print(f"[OK] Created icon: {output_path}")
    return output_path


def create_owl_png(size: int) -> bytes:
    """Create a PNG image of an owl icon."""
    
    # Create RGBA pixel data
    pixels = []
    center = size // 2
    
    for y in range(size):
        row = []
        for x in range(size):
            # Distance from center
            dx = x - center
            dy = y - center
            dist = (dx*dx + dy*dy) ** 0.5
            radius = size * 0.45
            
            # Background circle (Walmart Blue)
            if dist <= radius:
                # Inside the circle - create owl face
                rel_x = dx / radius  # -1 to 1
                rel_y = dy / radius  # -1 to 1
                
                # Owl body (blue background)
                r, g, b = BLUE
                a = 255
                
                # Owl eyes (two white circles with dark pupils)
                eye_y = -0.15
                eye_radius = 0.25
                pupil_radius = 0.12
                
                # Left eye
                left_eye_x = -0.32
                left_dist = ((rel_x - left_eye_x)**2 + (rel_y - eye_y)**2) ** 0.5
                
                # Right eye  
                right_eye_x = 0.32
                right_dist = ((rel_x - right_eye_x)**2 + (rel_y - eye_y)**2) ** 0.5
                
                if left_dist < eye_radius or right_dist < eye_radius:
                    # White of eye
                    r, g, b = WHITE
                    
                    # Pupils (dark)
                    if left_dist < pupil_radius or right_dist < pupil_radius:
                        r, g, b = DARK
                
                # Owl beak (Walmart Spark yellow) - triangle pointing down
                beak_top = 0.1
                beak_bottom = 0.4
                if rel_y > beak_top and rel_y < beak_bottom:
                    beak_width = 0.2 * (1 - (rel_y - beak_top) / (beak_bottom - beak_top))
                    if abs(rel_x) < beak_width:
                        r, g, b = SPARK
                
                # Ear tufts (triangles at top)
                if rel_y < -0.5:
                    tuft_y = -rel_y - 0.5
                    left_tuft = rel_x < -0.2 and rel_x > -0.5 and tuft_y > abs(rel_x + 0.35) * 1.5
                    right_tuft = rel_x > 0.2 and rel_x < 0.5 and tuft_y > abs(rel_x - 0.35) * 1.5
                    if left_tuft or right_tuft:
                        # Darker blue for tufts
                        r, g, b = (0, 60, 180)
                
                row.append((r, g, b, a))
            else:
                # Outside circle - transparent
                row.append((0, 0, 0, 0))
        
        pixels.append(row)
    
    return encode_png(pixels, size, size)


def encode_png(pixels: list, width: int, height: int) -> bytes:
    """Encode pixel data as PNG."""
    
    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        crc = zlib.crc32(chunk) & 0xffffffff
        return struct.pack('>I', len(data)) + chunk + struct.pack('>I', crc)
    
    # PNG signature
    png = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    png += make_chunk(b'IHDR', ihdr_data)
    
    # IDAT chunk (image data)
    raw_data = b''
    for row in pixels:
        raw_data += b'\x00'  # Filter type: None
        for r, g, b, a in row:
            raw_data += bytes([r, g, b, a])
    
    compressed = zlib.compress(raw_data, 9)
    png += make_chunk(b'IDAT', compressed)
    
    # IEND chunk
    png += make_chunk(b'IEND', b'')
    
    return png


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    icon_path = script_dir / "cadowl.ico"
    create_ico_file(icon_path)
    print(f"\nIcon created at: {icon_path}")
    print("Run CREATE_SHORTCUT.bat to update your desktop shortcut!")
