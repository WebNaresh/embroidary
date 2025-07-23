from svgpathtools import svg2paths
import pyembroidery
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import numpy as np

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

                # Create even-odd fill using winding number algorithm
                if fill_points:
                    def winding_number(point_x, point_y, polygon_points):
                        """Calculate winding number for even-odd fill rule"""
                        wn = 0
                        n = len(polygon_points)

                        for i in range(n):
                            x1, y1 = polygon_points[i]
                            x2, y2 = polygon_points[(i + 1) % n]

                            if y1 <= point_y:
                                if y2 > point_y:  # upward crossing
                                    if is_left(x1, y1, x2, y2, point_x, point_y) > 0:
                                        wn += 1
                            else:
                                if y2 <= point_y:  # downward crossing
                                    if is_left(x1, y1, x2, y2, point_x, point_y) < 0:
                                        wn -= 1
                        return wn

                    def is_left(x1, y1, x2, y2, px, py):
                        """Test if point is left|on|right of line"""
                        return ((x2 - x1) * (py - y1) - (px - x1) * (y2 - y1))

                    def point_in_polygon_evenodd(x, y, polygon_points):
                        """Even-odd fill rule: odd winding number = inside"""
                        wn = winding_number(x, y, polygon_points)
                        return (wn % 2) == 1

                    # Get bounding box
                    min_x = min(p[0] for p in fill_points)
                    max_x = max(p[0] for p in fill_points)
                    min_y = min(p[1] for p in fill_points)
                    max_y = max(p[1] for p in fill_points)

                    # Create horizontal fill lines with even-odd rule
                    fill_spacing = 1.0  # Dense spacing for quality fill
                    stitch_spacing = 1.5  # Spacing between stitches on each line
                    fill_lines = 0

                    y = min_y + fill_spacing
                    while y < max_y:
                        # Find all points on this horizontal line that are inside using even-odd rule
                        line_points = []

                        x = min_x
                        while x <= max_x:
                            if point_in_polygon_evenodd(x, y, fill_points):
                                line_points.append(x)
                            x += stitch_spacing

                        # Group consecutive points into line segments
                        if line_points:
                            segments = []
                            start = line_points[0]
                            end = line_points[0]

                            for i in range(1, len(line_points)):
                                if line_points[i] - line_points[i-1] <= stitch_spacing * 1.5:
                                    end = line_points[i]
                                else:
                                    if end - start > 2.0:  # Only create segments that are wide enough
                                        segments.append((start, end))
                                    start = line_points[i]
                                    end = line_points[i]

                            # Add the last segment
                            if end - start > 2.0:
                                segments.append((start, end))

                            # Stitch each segment
                            for start_x, end_x in segments:
                                pattern.move_abs(start_x, y)
                                pattern.stitch_abs(end_x, y)
                                fill_lines += 1
                                total_stitches += 1

                        y += fill_spacing

                    # Add clean outline on top
                    if fill_points:
                        pattern.move_abs(fill_points[0][0], fill_points[0][1])
                        for x, y in fill_points[1:]:
                            pattern.stitch_abs(x, y)
                            total_stitches += 1

                    print(f"    Fill: {fill_lines} even-odd fill lines + outline")

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
    print("=== SVG to DST Converter - With Fill Support ===\n")

    # Create filled DST file
    print("Converting SVG to DST with fill...")
    convert_svg_to_dst("complex_design.svg", "logo_filled.dst", step_size=3.0, scale=0.6)

    print("\n✓ Filled DST file created!")
