
def positions_from_safety_car(car_positions, pace_car_idx):
    """ Get the car positions as seen from the safety car.
        0.0 = SC position
        0.1 = 10% of the track behind the SC
        ...
        
        Args:
            car_positions: The list of car positions as provided by the irSDK CarIdxLapDistPct property.
            pace_car_idx: The index of the pacecar in car_positions as provided by the irSDK DriverInfo->PaceCarIdx property.

        Returns:
            List[float]: The car_positions list, offset by the current position of the safety car.
    """
    normalize_positions = [n % 1 if n >= 0 else n for n in car_positions]
    pace_car_pos = normalize_positions[pace_car_idx]
    result = []
    for idx, pos in enumerate(normalize_positions):
        if idx == pace_car_idx:
            result.append(0.0)
        elif pos == -1:
            result.append(-1)
        elif pos < pace_car_pos:
            result.append(pace_car_pos - pos)
        else:
            result.append(pace_car_pos + 1 - pos)
    
    return result