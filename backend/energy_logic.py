from config import *

def decide_energy_flow(solar_kw, demand_kw, soc):
    battery_energy = soc * BATTERY_CAPACITY_KWH
    grid_import = 0
    battery_charge = 0
    battery_discharge = 0

    if solar_kw >= demand_kw:
        surplus = solar_kw - demand_kw
        battery_charge = min(
            surplus,
            MAX_CHARGE_KW,
            BATTERY_CAPACITY_KWH - battery_energy
        )
        source = "SOLAR → LOAD + BATTERY"

    else:
        deficit = demand_kw - solar_kw
        battery_discharge = min(
            deficit,
            MAX_DISCHARGE_KW,
            battery_energy
        )

        if battery_discharge > 0:
            source = "SOLAR + BATTERY → LOAD"
        else:
            grid_import = deficit
            source = "GRID → LOAD"

    battery_energy += battery_charge * BATTERY_EFFICIENCY
    battery_energy -= battery_discharge / BATTERY_EFFICIENCY

    new_soc = battery_energy / BATTERY_CAPACITY_KWH
    new_soc = max(0, min(1, new_soc))

    return {
        "source": source,
        "grid_import_kw": round(grid_import, 2),
        "battery_charge_kw": round(battery_charge, 2),
        "battery_discharge_kw": round(battery_discharge, 2),
        "soc": round(new_soc * 100, 1)
    }
