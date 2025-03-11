from heapq import heappush, heappop

def get_split_class_commands(drivers, car_positions, on_pit_road, pace_car_idx):
    """ Provide the commands that need to be sent to make sure the cars behind the SC are sorted by their classes.
        
        Args:
            drivers: The list of cars as provided by the irSDK DriverInfo->Drivers property.
            car_positions: The list of car positions as provided by the irSDK CarIdxLapDistPct property.
            on_pit_road: The list booleans indicating if cars are on pit road (CarIdxOnPitRoad)
            pace_car_idx: The index of the pacecar in car_positions as provided by the irSDK PaceCarIdx property.

        Returns:
            List[str]: The commands to send, in order, to split the classes.
    """
    # Get the car positions as seen from the SC
    pos_from_sc = positions_from_safety_car(car_positions, pace_car_idx)

    # Figure out what classes are driving, their CarClassEstLapTime to determine the 
    # ordering and what drivers belong to each class
    classes = {}
    drivers_to_class = {}
    for idx, driver in enumerate(drivers):
        if driver["CarIsPaceCar"] == 1 or on_pit_road[idx]:
            continue
        
        class_info = classes.get(driver["CarClassID"], { "est_lap_time": 0.0, "drivers": set(), "drivers_ordered": [] })
        class_info["est_lap_time"] = driver["CarClassEstLapTime"]
        class_info["drivers"].add(idx)
        
        # we are keeping a sorted list of drivers based on their position to be able to send EOL in order
        heappush(class_info["drivers_ordered"], (pos_from_sc[idx], idx)) 
        classes[driver["CarClassID"]] = class_info

        # Keep track of a driver -> class map to easily check if they are out of order
        drivers_to_class[idx] = driver["CarClassID"]
    
    # If there is only one class, skip
    if len(classes) == 1:
        return
    
    # Sort by fastest lap time; this returns a list of (CarClassID, { ... }) tuples 
    classes_sorted = sorted(classes.items(), key=lambda item: item[1]["est_lap_time"])

    # Check if we need to split the classes by checking for anyone out of order
    pos_and_idx = zip(pos_from_sc, list(range(len(pos_from_sc))))
    idx_all_sorted = list(map(lambda tuple: tuple[1], sorted(pos_and_idx, key=lambda item: item[0])))

    class_pointer = 0
    pos_pointer = 0
    classes_out_of_order = set()
    drivers_out_of_order = set() 
    # Go through the classes from fastest to slowest
    while class_pointer < len(classes_sorted):
        current_class = classes_sorted[class_pointer][0]
        current_class_drivers = classes_sorted[class_pointer][1]["drivers"]

        # remove any drivers we have already seen out of order
        for driver in drivers_out_of_order:
            current_class_drivers.remove(driver)
        
        # now go through our grid until we have seen all cars in this class
        while len(current_class_drivers) > 0:
            current_car = idx_all_sorted[pos_pointer]

            # Skip the SC and anyone on pit road
            if current_car == pace_car_idx or on_pit_road[current_car]:
                pos_pointer += 1
                continue

            # if a car is not in the current class, they are out of order
            if current_car not in current_class_drivers:
                classes_out_of_order.add(drivers_to_class[current_car])
                drivers_out_of_order.add(current_car)
            else:
                current_class_drivers.remove(current_car)

            pos_pointer += 1
        class_pointer += 1

    assert pos_pointer == len(idx_all_sorted)

    # No one is out of order!
    if len(classes_out_of_order) == 0:
        return []
    
    commands = []
    add_rest = False
    for c in classes_sorted:
        current_class = c[0]
        if add_rest or current_class in classes_out_of_order:
            # as soon as a class is out of order, then any slower classes also need to be send EOL commands
            add_rest = True 
            drivers_ordered = c[1]["drivers_ordered"]
            while len(drivers_ordered) > 0:
                _, idx = heappop(drivers_ordered)
                car_number = drivers[idx]["CarNumber"]
                commands.append(f"!eol {car_number} Splitting classes")

    return commands

def positions_from_safety_car(car_positions, pace_car_idx):
    """ Get the car positions as seen from the safety car.
        0.0 = SC position
        0.1 = 10% of the track behind the SC
        ...
        
        Args:
            car_positions: The list of car positions as provided by the irSDK CarIdxLapDistPct property.
            pace_car_idx: The index of the pacecar in car_positions as provided by the irSDK PaceCarIdx property.

        Returns:
            List[float]: The car_positions list, offset by the current position of the safety car.
    """
    pace_car_pos = car_positions[pace_car_idx]
    result = []
    for pos in car_positions:
        if pos == pace_car_pos:
            result.append(0.0)
        elif pos < pace_car_pos:
            result.append(pace_car_pos - pos)
        else:
            result.append(pace_car_pos + 1 - pos)
    
    return result