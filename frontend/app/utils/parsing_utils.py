import re

def svg_path_to_vtk_polydata(path_str, z_slice):
    """
    Convertit un path SVG (M x,y L x,y Z) issu de plotly en coordonnées 3D pour VTK.
    """
    points = []
    # Find pairs of coordinates following 'M' or 'L' commands
    matches = re.findall(r'[ML]\s*([\d\.-]+),([\d\.-]+)', path_str)
    
    for x_str, y_str in matches:
        x = float(x_str)
        y = float(y_str)
        points.extend([x, y, z_slice])
        
    num_points = len(matches)
    # Format VTK poly
    polys = [num_points] + list(range(num_points))
    
    return points, polys
