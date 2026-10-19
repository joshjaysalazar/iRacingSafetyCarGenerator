
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

def driver_positions_from_safety_car(drivers, pace_car_idx):
    """ Get each driver's position as seen from the safety car, keyed by driver_idx.

        The Drivers data model only holds the cars listed in DriverInfo, so a driver's place in
        that list is not its CarIdx (e.g. 16 cars at CarIdx 0-15 and the pace car at CarIdx 62).
        This puts each lap distance back at its CarIdx before offsetting it from the safety car.

        Args:
            drivers: The list of Driver objects from the Drivers data model.
            pace_car_idx: The CarIdx of the pacecar as provided by the irSDK DriverInfo->PaceCarIdx property.

        Returns:
            dict[int, float]: The position behind the safety car (see positions_from_safety_car) per driver_idx.
    """
    car_positions = [-1] * (max(driver["driver_idx"] for driver in drivers) + 1)
    for driver in drivers:
        car_positions[driver["driver_idx"]] = driver["lap_distance"]

    relative_to_sc = positions_from_safety_car(car_positions, pace_car_idx)
    return {driver["driver_idx"]: relative_to_sc[driver["driver_idx"]] for driver in drivers}
