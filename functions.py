import numpy as np
from shapely.geometry import Point

def calculate_angle_from_north_projected(center_point, point, crs):
    """
    Calculate angle in projected space for more accurate results
    """
    # Convert points to numpy arrays for easier calculation
    center = np.array([center_point.x, center_point.y])
    pt = np.array([point.x, point.y])
    
    # Calculate vector from center to point
    vector = pt - center
    
    # Calculate angle from north (y-axis)
    angle = np.arctan2(vector[0], vector[1])
    
    # Add 180 degrees (π radians) for rotation
    angle += np.pi
    
    # Normalize angle to [0, 2π]
    if angle < 0:
        angle += 2 * np.pi
    if angle >= 2 * np.pi:
        angle -= 2 * np.pi
        
    return angle

def create_circle_section(center, radius, start_angle, end_angle, num_points = 100):
    """
    Create circle section in projected space
    """
    # Generate points along the arc
    if end_angle < start_angle:
        end_angle += 2 * np.pi
    
    angles = np.linspace(start_angle, end_angle, num_points)
    points = []
    
    for angle in angles:
        x = center.x + radius * np.sin(angle)
        y = center.y + radius * np.cos(angle)
        points.append(Point(x, y))
        
    return points