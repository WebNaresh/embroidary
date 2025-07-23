from svgpathtools import svg2paths
import pyembroidery
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import numpy as np
# import cairosvg  # Not available on Windows
from PIL import Image, ImageDraw
import io
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path as MPLPath

def convert_svg_to_dst_bitmap(svg_file="complex.svg", output_file="output.dst", scale=1.0):
    """
    Convert SVG to DST using bitmap rendering approach
    """
    try:
        # Load SVG paths
        paths, attributes = svg2paths(svg_file)
        if not paths:
            return False

        # Create a high-resolution bitmap
        width, height = 800, 800
        dpi = 100

        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(width/dpi, height/dpi), dpi=dpi)
        ax.set_xlim(0, 1179)  # SVG viewBox width
        ax.set_ylim(0, 1524)  # SVG viewBox height
        ax.set_aspect('equal')
        ax.axis('off')

        # Convert SVG path to matplotlib path and fill it
        for i, path in enumerate(paths):
            attr = attributes[i]
            fill_color = attr.get('fill', 'none')

            if fill_color and fill_color != 'none':
                # Sample points from the SVG path
                samples = max(int(path.length() / 2.0), 100)
                vertices = []
                codes = []

                for j in range(samples + 1):
                    t = j / samples
                    point = path.point(t)
                    x = point.real
                    y = 1524 - point.imag  # Flip Y coordinate
                    vertices.append([x, y])
                    codes.append(MPLPath.LINETO if j > 0 else MPLPath.MOVETO)

                # Close the path
                if len(vertices) > 2:
                    codes[-1] = MPLPath.CLOSEPOLY

                    # Create matplotlib path
                    mpl_path = MPLPath(vertices, codes)
                    patch = patches.PathPatch(mpl_path, facecolor='blue', edgecolor='none')
                    ax.add_patch(patch)

        # Render to bitmap
        plt.tight_layout(pad=0)
        fig.canvas.draw()

        # Convert to PIL image
        buf = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        buf = buf.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        image = Image.fromarray(buf)
        plt.close(fig)

        # Create embroidery pattern from bitmap
        pattern = pyembroidery.EmbPattern()

        # Add thread color
        pattern.color_change()
        thread_info = {
            "hex": "#047AE1",
            "description": "SVG Fill Blue",
            "brand": "SVG",
            "catalog_number": "001F",
            "weight": "40",
            "color": 0x047AE1
        }
        pattern.add_thread(thread_info)

        # Scan bitmap for filled areas
        img_width, img_height = image.size
        fill_spacing = 3  # Spacing between scan lines
        total_stitches = 0
        fill_lines = 0

        # Center coordinates
        center_x = img_width / 2
        center_y = img_height / 2

        for y in range(0, img_height, fill_spacing):
            line_segments = []
            start_x = None

            for x in range(img_width):
                pixel = image.getpixel((x, y))
                # Check if pixel is blue (filled area)
                r, g, b = pixel
                is_blue = (b > 150 and r < 100 and g < 100)  # Blue pixel detection

                if is_blue:
                    if start_x is None:
                        start_x = x
                else:
                    if start_x is not None:
                        # End of filled segment
                        if x - start_x > 5:  # Minimum segment width
                            line_segments.append((start_x, x))
                        start_x = None

            # Handle segment that goes to edge
            if start_x is not None and img_width - start_x > 5:
                line_segments.append((start_x, img_width))

            # Create stitches for each segment
            for start_x, end_x in line_segments:
                # Convert to embroidery coordinates
                stitch_start_x = (start_x - center_x) * scale * 0.8
                stitch_end_x = (end_x - center_x) * scale * 0.8
                stitch_y = (y - center_y) * scale * 0.8

                pattern.move_abs(stitch_start_x, stitch_y)
                pattern.stitch_abs(stitch_end_x, stitch_y)
                fill_lines += 1
                total_stitches += 1

        # End pattern
        pattern.end()

        # Write DST file
        pyembroidery.write_dst(pattern, output_file, {"write_colors": True})

        print(f"✓ Bitmap Fill Success! Created {output_file}")
        print(f"  Total stitches: {total_stitches}")
        print(f"  Fill lines: {fill_lines}")
        print(f"  Bitmap size: {img_width} x {img_height}")

        return True

    except Exception as e:
        print(f"✗ Bitmap Fill Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def convert_svg_to_dst_manual(svg_file="complex.svg", output_file="output.dst", scale=1.0):
    """
    Convert SVG to DST using manual fill areas for the N logo
    """
    try:
        # Create embroidery pattern
        pattern = pyembroidery.EmbPattern()

        # Add thread color (blue from SVG)
        pattern.color_change()
        thread_info = {
            "hex": "#047AE1",
            "description": "SVG Fill Blue",
            "brand": "SVG",
            "catalog_number": "001F",
            "weight": "40",
            "color": 0x047AE1
        }
        pattern.add_thread(thread_info)

        # Manual fill areas based on the N logo structure
        # These coordinates are approximated from the SVG path analysis

        # Scale factor to match the SVG coordinate system
        svg_scale = scale * 0.6

        # Define the filled rectangles that make up the "N" logo
        fill_areas = [
            # Top-left vertical bar
            {"x1": -300, "y1": -400, "x2": -200, "y2": -100},
            # Top-right horizontal bar
            {"x1": 100, "y1": -400, "x2": 300, "y2": -300},
            # Middle diagonal section (upper)
            {"x1": -200, "y1": -200, "x2": 100, "y2": -100},
            # Middle diagonal section (lower)
            {"x1": -100, "y1": 0, "x2": 200, "y2": 100},
            # Bottom-left section
            {"x1": -300, "y1": 200, "x2": -100, "y2": 400},
            # Bottom-right horizontal bar
            {"x1": 200, "y1": 300, "x2": 300, "y2": 400}
        ]

        total_stitches = 0
        fill_lines = 0
        fill_spacing = 2.0

        # Fill each area with horizontal lines
        for area in fill_areas:
            x1, y1, x2, y2 = area["x1"], area["y1"], area["x2"], area["y2"]

            # Scale coordinates
            x1 *= svg_scale
            x2 *= svg_scale
            y1 *= svg_scale
            y2 *= svg_scale

            # Ensure proper ordering
            if x1 > x2:
                x1, x2 = x2, x1
            if y1 > y2:
                y1, y2 = y2, y1

            # Create horizontal fill lines
            y = y1 + fill_spacing
            while y < y2:
                pattern.move_abs(x1, y)
                pattern.stitch_abs(x2, y)
                fill_lines += 1
                total_stitches += 1
                y += fill_spacing

        # End pattern
        pattern.end()

        # Write DST file
        pyembroidery.write_dst(pattern, output_file, {"write_colors": True})

        print(f"✓ Manual Fill Success! Created {output_file}")
        print(f"  Total stitches: {total_stitches}")
        print(f"  Fill lines: {fill_lines}")
        print(f"  Fill areas: {len(fill_areas)}")

        return True

    except Exception as e:
        print(f"✗ Manual Fill Error: {e}")
        return False

def convert_svg_to_dst(svg_file="complex.svg", output_file="output.dst", step_size=3.0, scale=1.0):
    """
    Convert SVG file to DST embroidery format

    Args:
        svg_file: Input SVG file path
        output_file: Output DST file path
        step_size: Distance between stitches in SVG units (smaller = more detail)
        scale: Scale factor (1.0 = same size, 0.5 = half size)
    """

    try:
        # Load SVG paths (svgpathtools automatically applies transforms)
        paths, attributes = svg2paths(svg_file)
        print(f"✓ Loaded {svg_file}: {len(paths)} paths found")

        if not paths:
            print("⚠ No paths found in SVG")
            return False

        # Extract colors from SVG attributes
        def extract_color(attr_dict):
            """Extract color from SVG attributes - prioritize stroke over fill"""
            # Check stroke first (outline color)
            if 'stroke' in attr_dict:
                color = attr_dict['stroke']
                if color and color != 'none':
                    return color
            # Then check fill (interior color)
            if 'fill' in attr_dict:
                color = attr_dict['fill']
                if color and color != 'none':
                    return color
            return 'black'  # default color

        def parse_hex_color(color_str):
            """Convert hex color string to integer"""
            if color_str.startswith('#'):
                try:
                    return int(color_str[1:], 16)
                except ValueError:
                    return 0x000000
            return 0x000000

        # Map colors to accurate embroidery thread colors (matching CSS/SVG standard colors)
        color_map = {
            'black': 0x000000,      # Pure black
            'red': 0xFF0000,        # Pure red
            'green': 0x008000,      # Standard green (not lime)
            'blue': 0x0000FF,       # Pure blue
            'purple': 0x800080,     # Standard purple
            'pink': 0xFFC0CB,       # Light pink
            'orange': 0xFFA500,     # Standard orange
            'cyan': 0x00FFFF,       # Pure cyan/aqua
            'brown': 0xA52A2A,      # Standard brown
            'magenta': 0xFF00FF,    # Pure magenta/fuchsia
            'darkgreen': 0x006400,  # Dark green
            'navy': 0x000080,       # Navy blue
            'gold': 0xFFD700        # Standard gold
        }

        print("Colors found:")
        for i, attr in enumerate(attributes):
            stroke_color = attr.get('stroke', 'none')
            fill_color = attr.get('fill', 'none')
            selected_color = extract_color(attr)

            if selected_color.startswith('#'):
                hex_color = parse_hex_color(selected_color)
            else:
                hex_color = color_map.get(selected_color, 0x000000)

            print(f"  Path {i+1}: stroke={stroke_color}, fill={fill_color} -> using {selected_color} (#{hex_color:06X})")
        print()

        # Create embroidery pattern
        pattern = pyembroidery.EmbPattern()
        total_stitches = 0

        # Try to get actual SVG dimensions from viewBox or width/height
        # For this SVG: viewBox="0 0 1871 2208"
        svg_width = 1871  # Default, could be extracted from SVG
        svg_height = 2208

        # Center coordinates for the SVG canvas
        center_x = svg_width / 2
        center_y = svg_height / 2

        print(f"  SVG canvas: {svg_width} x {svg_height}")
        print(f"  Center: ({center_x}, {center_y})")

        # Process each path with both stroke and fill colors
        for i, path in enumerate(paths):
            path_length = path.length()
            if path_length == 0:
                continue

            attr = attributes[i]
            stroke_color = attr.get('stroke', 'none')
            fill_color = attr.get('fill', 'none')

            # Process fill using concentric layers approach
            if fill_color and fill_color != 'none':
                print(f"  Path {i+1} FILL: {fill_color}")

                if fill_color.startswith('#'):
                    fill_embroidery_color = parse_hex_color(fill_color)
                else:
                    fill_embroidery_color = color_map.get(fill_color, 0x000000)

                # Add fill color
                pattern.color_change()
                fill_thread_info = {
                    "hex": f"#{fill_embroidery_color:06X}",
                    "description": f"Fill {fill_color}",
                    "brand": "SVG",
                    "catalog_number": f"{i+1:03d}F",
                    "weight": "40",
                    "color": fill_embroidery_color
                }
                pattern.add_thread(fill_thread_info)

                # Create path points for fill
                fill_samples = max(int(path_length / step_size), 20)
                fill_points = []
                for j in range(fill_samples + 1):
                    t = j / fill_samples
                    point = path.point(t)
                    x = (point.real - center_x) * scale
                    y = (point.imag - center_y) * scale
                    fill_points.append((x, y))

                # Create simple dense fill - just outline with multiple passes
                if fill_points:
                    # Create multiple concentric layers for fill effect
                    fill_layers = 8
                    layer_offset = 3.0  # Distance between layers
                    fill_lines = 0

                    for layer in range(fill_layers):
                        # Calculate inward offset for this layer
                        offset = layer * layer_offset

                        # Create offset points (simple approach)
                        layer_points = []
                        center_x = sum(p[0] for p in fill_points) / len(fill_points)
                        center_y = sum(p[1] for p in fill_points) / len(fill_points)

                        for x, y in fill_points:
                            # Move point toward center
                            dx = center_x - x
                            dy = center_y - y
                            length = (dx*dx + dy*dy)**0.5
                            if length > offset:
                                factor = offset / length
                                new_x = x + dx * factor
                                new_y = y + dy * factor
                                layer_points.append((new_x, new_y))

                        # Only create layer if we have enough points
                        if len(layer_points) > 3:
                            pattern.move_abs(layer_points[0][0], layer_points[0][1])
                            for x, y in layer_points[1:]:
                                pattern.stitch_abs(x, y)
                                total_stitches += 1
                            fill_lines += 1

                    print(f"    Fill: {fill_lines} concentric fill layers")

            # Process stroke (outline)
            if stroke_color and stroke_color != 'none':
                print(f"  Path {i+1} STROKE: {stroke_color}")

                if stroke_color.startswith('#'):
                    stroke_embroidery_color = parse_hex_color(stroke_color)
                else:
                    stroke_embroidery_color = color_map.get(stroke_color, 0x000000)

                # Add stroke color
                pattern.color_change()
                stroke_thread_info = {
                    "hex": f"#{stroke_embroidery_color:06X}",
                    "description": f"Stroke {stroke_color}",
                    "brand": "SVG",
                    "catalog_number": f"{i+1:03d}S",
                    "weight": "40",
                    "color": stroke_embroidery_color
                }
                pattern.add_thread(stroke_thread_info)

                # Create stroke stitches (outline)
                stroke_samples = max(int(path_length / step_size), 2)
                stroke_points = []

                for j in range(stroke_samples + 1):
                    t = j / stroke_samples
                    point = path.point(t)
                    x = (point.real - center_x) * scale
                    y = (point.imag - center_y) * scale
                    stroke_points.append((x, y))

                if stroke_points:
                    pattern.move_abs(stroke_points[0][0], stroke_points[0][1])
                    for x, y in stroke_points[1:]:
                        pattern.stitch_abs(x, y)
                        total_stitches += 1
                    print(f"    Stroke: {len(stroke_points)} stitches")

        # End pattern
        pattern.end()

        # Write embroidery file with enhanced color support
        file_ext = output_file.lower().split('.')[-1]

        # Set pattern metadata for better color support
        pattern.extras["name"] = "SVG Conversion"
        pattern.extras["author"] = "SVG to Embroidery Converter"

        if file_ext == 'pes':
            pyembroidery.write_pes(pattern, output_file)
        elif file_ext == 'jef':
            pyembroidery.write_jef(pattern, output_file)
        elif file_ext == 'exp':
            pyembroidery.write_exp(pattern, output_file)
        else:
            # Enhanced DST writing with color information
            pyembroidery.write_dst(pattern, output_file, {"write_colors": True})

        # Show results
        bounds = pattern.bounds()
        stroke_colors = set()
        for attr in attributes:
            if attr.get('stroke') and attr.get('stroke') != 'none':
                stroke_colors.add(attr.get('stroke'))

        print(f"✓ Success! Created {output_file}")
        print(f"  Total stitches: {total_stitches}")
        print(f"  Stroke colors: {len(stroke_colors)} ({', '.join(sorted(stroke_colors))})")
        print(f"  Size: {bounds[2]-bounds[0]:.1f} x {bounds[3]-bounds[1]:.1f} units")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

# Main execution
if __name__ == "__main__":
    print("=== SVG to DST Converter - Automatic Fill ===\n")

    # Use the improved path-based approach with better fill algorithm
    print("Converting SVG to DST with automatic fill...")
    success = convert_svg_to_dst("complex_design.svg", "logo_auto_fill.dst", step_size=2.0, scale=0.6)

    if success:
        print("\n✓ Auto-fill DST file created!")
        print("File: logo_auto_fill.dst")
        print("\nThis uses the most advanced algorithm available.")
        print("For complex logos like this, the result may need fine-tuning")
        print("in professional embroidery software.")
    else:
        print("✗ Auto-fill failed")
