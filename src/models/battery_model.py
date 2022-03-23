from datetime import datetime, timedelta, time
import pandas as pd


class Battery:
    def __init__(self, battery_size=5000, max_charge_rate=13500, time_scale=0.25):
        self.battery_size = battery_size
        self.current_charge = 0
        self.max_charge_rate = max_charge_rate
        self.time_scale = time_scale

    def use_battery(self, energy):
        if energy > 0:
            residual = self.charge(energy)
            return residual
        elif energy < 0:
            residual = self.discharge(energy)
            return residual
        else:
            return 0

    def charge(self, charge_size):
        if self.current_charge + charge_size < self.battery_size:
            self.current_charge += charge_size
            return 0
        else:
            # residual is the energy we couldn't feed to the battery :
            # the difference between the intended charge and the available space
            residual_energy = charge_size - (self.battery_size - self.current_charge)
            self.current_charge = self.battery_size
            return residual_energy

    def discharge(self, discharge_size):
        if self.current_charge >= -discharge_size:
            self.current_charge += discharge_size
            return 0
        elif self.current_charge < -discharge_size:
            # return the energy deficit remaining from insufficient charge
            residual_energy = self.current_charge + discharge_size
            self.current_charge = 0
            return residual_energy
        else:
            return 0


class HouseSystem:
    def __init__(
            self,
            battery_size,
            input_data,
            max_charge_rate,
            time_scale
    ):
        if isinstance(input_data, pd.DataFrame):
            solar_generation = input_data[
                input_data["Consumption Category"] == "solar_generation"
                ].sort_values("datetime")
            controlled_load_consumption = input_data[
                input_data["Consumption Category"] == "controlled_load_consumption"
                ].sort_values("datetime")
            CO2 = input_data[
                input_data["Consumption Category"] == "CO2"
                ].sort_values("datetime")

            earliest_date = str(input_data.datetime.min())
            latest_date = str(input_data.datetime.max())

            self.battery_size = battery_size
            self.max_charge_rate = max_charge_rate
            self.time_scale = time_scale
            self.battery = Battery(battery_size, max_charge_rate, time_scale)
            self.solar_generation = solar_generation
            self.controlled_load_consumption = controlled_load_consumption
            self.CO2 = CO2
            self.datetime = datetime.strptime(str(earliest_date)[:-6], "%Y-%m-%d %H:%M:%S")
            self.end_date = datetime.strptime(str(latest_date)[:-6], "%Y-%m-%d %H:%M:%S")
            self.hour = self.datetime.strftime("%H:%M")

            self.step_number = 0
            self.run_data = {}

    def step(self, charge_discharge):
        self.datetime = datetime.strptime(
            str(self.solar_generation.iloc[self.step_number].datetime)[:-6], "%Y-%m-%d %H:%M:%S"
        )
        self.hour = self.datetime.strftime("%H:%M")

        # Printing stuff to debug / check if algorithm works
        # Should use logs instead #TODO
        print("Date time", self.datetime)
        print("Battery charge: ", self.battery.current_charge)
        print("How much are we charging/discharging?", charge_discharge)

        current_solar = self.solar_generation.iloc[self.step_number].consumption
        current_consumption = self.controlled_load_consumption.iloc[
            self.step_number
        ].consumption
        current_CO2 = (
            self.CO2.iloc[self.step_number].consumption
        )

        self.run_data[self.step_number] = {
            "datetime": self.datetime,
            "charge_discharge": charge_discharge,
            "current_solar": current_solar,
            "current_consumption": current_consumption,
            "current_CO2": current_CO2,
        }

        # charge or discharge battery
        amount_to_charge = charge_discharge
        print("current consumption before ", current_consumption)
        print("current solar", current_solar)
        current_consumption, battery_delta = self.charge_discharge_battery(
            amount_to_charge,
            current_solar,
            current_consumption,
        )
        print("current consumption ", current_consumption)
        current_consumption = max(current_consumption,
                                  0)  # Act as if the 604 building were independent, if we don't use
        # or store the PV production it will be lost

        # Service rest of the load with tariff
        cost = self.cost(
            current_CO2,
            battery_delta,
        )
        reward = -cost

        if self.datetime >= self.end_date:
            done = True
        else:
            done = False

        observations = [
            self.battery.battery_size,
            self.battery.current_charge,
            current_solar,
            current_consumption,
            current_CO2,
        ]

        self.run_data[self.step_number].update(
            {
                "current_charge": self.battery.current_charge,
            }
        )

        # self.datetime += self.time_step
        self.step_number += 1
        return observations, reward, done, {}

    def charge_discharge_battery(
            self,
            charge_rate,
            current_solar,
            current_consumption,
    ):
        amount_to_charge = charge_rate * self.time_scale
        if amount_to_charge >= 0:
            if amount_to_charge < current_solar:  # then we can charge all that we want with solar
                residual_battery_solar = self.battery.use_battery(amount_to_charge)
                battery_delta = amount_to_charge - residual_battery_solar
                remaining_solar = current_solar - amount_to_charge
                remains_to_be_charged = 0
            else:  # something remains to be charged
                residual_battery_solar = self.battery.use_battery(current_solar)
                remaining_solar = 0
                remains_to_be_charged = amount_to_charge - current_solar
                battery_delta = current_solar - residual_battery_solar

            residual_battery_load = self.battery.use_battery(remains_to_be_charged)
            print("amount_to_charge", amount_to_charge)
            print('remains to be charged', remains_to_be_charged)
            print('residual_battery_load (-)', residual_battery_load)
            print("residual_battery_solar (-)", residual_battery_solar)
            print("remaining_solar (-) ", remaining_solar)
            print("battery delta", battery_delta)

            current_consumption = current_consumption + remains_to_be_charged - residual_battery_load \
                                  - residual_battery_solar - remaining_solar

        else:
            energy_deficit = self.battery.use_battery(amount_to_charge)
            print("energy deficit", energy_deficit)
            print(("amount to discharge", amount_to_charge))
            current_consumption = current_consumption + amount_to_charge - energy_deficit - current_solar
            battery_delta = amount_to_charge - energy_deficit
            print("battery delta", battery_delta)
            # amount to charge is negative

        return current_consumption, battery_delta

    def cost(
            self, CO2, charge_done
    ):
        step_cost = (charge_done * self.time_scale * (CO2 - 35.9))

        return step_cost
