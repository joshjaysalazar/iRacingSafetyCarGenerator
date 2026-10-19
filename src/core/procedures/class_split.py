import logging
from heapq import heappush, heappop

from irsdk import TrkLoc

from core.drivers import Driver
from util.generator_utils import driver_positions_from_safety_car

logger = logging.getLogger(__name__)

def get_split_class_commands(drivers: list[Driver], pace_car_idx: int) -> list[str]:
    """ Provide the commands that need to be sent to make sure the cars behind the SC are sorted by their classes.

        Args:
            drivers: The list of Driver objects from the Drivers data model.
            pace_car_idx: The CarIdx of the pacecar (DriverInfo->PaceCarIdx).

        Returns:
            List[str]: The commands to send, in order, to split the classes.
    """
    logger.info(f"Getting split class commands for {len(drivers)} drivers, pace car idx {pace_car_idx}")

    # Get the car positions as seen from the SC, keyed by driver_idx
    pos_from_sc = driver_positions_from_safety_car(drivers, pace_car_idx)
    drivers_by_idx = {driver["driver_idx"]: driver for driver in drivers}

    # Figure out what classes are driving, their est_lap_time to determine the
    # ordering and what drivers belong to each class
    classes = {}
    drivers_to_class = {}
    for driver in drivers:
        idx = driver["driver_idx"]
        if driver["is_pace_car"]:
            logger.debug(f"Skipping driver idx {idx} (pace car)")
            continue
        if driver["track_loc"] == TrkLoc.not_in_world:
            logger.debug(f"Skipping driver idx {idx} #{driver['car_number']} (disconnected)")
            continue

        class_info = classes.get(driver["car_class_id"], { "est_lap_time": 0.0, "drivers": set(), "drivers_ordered": [] })
        class_info["est_lap_time"] = driver["car_class_est_lap_time"]

        # Ignore cars that are currently in the pit for the sorting order
        if not driver["on_pit_road"]:
            class_info["drivers"].add(idx)
        else:
            logger.debug(f"Driver idx {idx} #{driver['car_number']} on pit road, excluding from order check")

        # we are keeping a sorted list of drivers based on their position to be able to send EOL in order
        # Note that we do include anyone in the pit here since they could otherwise end up at the front of their class
        heappush(class_info["drivers_ordered"], (pos_from_sc[idx], idx))
        classes[driver["car_class_id"]] = class_info

        # Keep track of a driver -> class map to easily check if they are out of order
        drivers_to_class[idx] = driver["car_class_id"]

    logger.info(f"Found {len(classes)} classes: {list(classes.keys())}")

    # If there is only one class, skip
    if len(classes) == 1:
        logger.info("Only one class found, no split needed")
        return []

    # Sort by fastest lap time; this returns a list of (CarClassID, { ... }) tuples
    classes_sorted = sorted(classes.items(), key=lambda item: item[1]["est_lap_time"])
    logger.debug(f"Classes sorted by lap time: {[c[0] for c in classes_sorted]}")

    # Check if we need to split the classes by checking for anyone out of order
    pos_and_idx = [(pos, idx) for idx, pos in pos_from_sc.items()]
    pos_and_idx_filtered = [entry for entry in pos_and_idx if entry[0] != -1]
    idx_all_sorted = [entry[1] for entry in sorted(pos_and_idx_filtered, key=lambda item: item[0])]

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
            current_class_drivers.discard(driver)
        # now go through our grid until we have seen all cars in this class
        while len(current_class_drivers) > 0:
            current_car = idx_all_sorted[pos_pointer]

            # Skip the SC, anyone on pit road, and disconnected drivers
            if current_car == pace_car_idx or drivers_by_idx[current_car]["on_pit_road"] or drivers_by_idx[current_car]["track_loc"] == TrkLoc.not_in_world:
                logger.debug(f"Skipping driver idx {current_car} #{drivers_by_idx[current_car]['car_number']} in order check (pace car, on pit road, or disconnected)")
                pos_pointer += 1
                continue

            # if a car is not in the current class, they are out of order
            if current_car not in current_class_drivers:
                logger.debug(f"Driver idx {current_car} #{drivers_by_idx[current_car]['car_number']} (class {drivers_to_class[current_car]}) is out of order in class {current_class}")
                classes_out_of_order.add(drivers_to_class[current_car])
                drivers_out_of_order.add(current_car)
            else:
                logger.debug(f"Driver idx {current_car} #{drivers_by_idx[current_car]['car_number']} is in correct class order")
                current_class_drivers.remove(current_car)

            pos_pointer += 1
        class_pointer += 1

    # No one is out of order!
    if len(classes_out_of_order) == 0:
        logger.info("All classes are in order, no split needed")
        return []

    logger.info(f"Classes out of order: {classes_out_of_order}")

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
                car_number = drivers_by_idx[idx]["car_number"]
                logger.debug(f"Adding EOL command for #{car_number} (class {current_class})")
                commands.append(f"!eol {car_number} Splitting classes")

    logger.debug(f"Total split class commands: {len(commands)}")
    return commands
