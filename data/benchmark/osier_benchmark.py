"""
This input file shows the State of Illinois and the University of Illinois
as a contained region. We can use this to examine how IL climate policies
influence the energy system planning of UIUC.
"""

# So the database can be saved in the location from which
# the command is called.
import os
import numpy as np
curr_dir = os.path.dirname(__file__)


# Simulation metadata goes here
iteration = "base"
folder = 'data'
scenario_name = 'uniform_lifespan'
start_year = 2050  # the first year optimized by the model
end_year = 2050  # the last year optimized by the model
N_years = 1  # the number of years optimized by the model
N_seasons = 365  # the number of "seasons" in the model
N_hours = 24  # the number of hours in a day
database_filename = f'{folder}/IL_{scenario_name}_{N_seasons}.sqlite'  # where the database will be written


# Optional parameters
reserve_margin = {'IL':0.0}  # fraction of excess capacity to ensure reliability
discount_rate = 0.05  # The discount rate applied globally.

demands_list = []
resources_list = []
emissions_list = []

# Import demand commodities
from pygenesys.commodity.demand import ELC_DEMAND

# Add demand forecast
"""
Illinois' electricity should increase to encompass all parts of the economy
if the State wishes to be truly carbon neutral. An aggressive climate policy
would electrify everything. A limited climate policy would only decarbonize
the electric grid.
"""
ELC_DEMAND.add_demand(region='IL',
                      init_demand=1.87e5,
                      start_year=start_year,
                      end_year=end_year,
                      N_years=N_years,
                      growth_rate=0.01,
                      growth_method='linear')

from pygenesys.data.library import campus_elc_demand

ELC_DEMAND.set_distribution(region='IL',
                            data=campus_elc_demand,
                            n_seasons=N_seasons,
                            n_hours=N_hours,
                            groupby='day',
                            normalize=True)



# Import transmission technologies, set regions, import input commodities
from pygenesys.technology.transmission import TRANSMISSION
from pygenesys.commodity.resource import (electricity,
                                          ethos)
TRANSMISSION.add_regional_data(region='IL',
                               input_comm=electricity,
                               output_comm=ELC_DEMAND,
                               efficiency=1.0,
                               tech_lifetime=1000,)

# Import technologies that generate electricity
from pygenesys.technology.electric import SOLAR_FARM, WIND_FARM, NUCLEAR_CONV
from pygenesys.technology.electric import COAL_CONV, NATGAS_CONV, BIOMASS
from pygenesys.technology.electric import COAL_ADV, NATGAS_ADV, NUCLEAR_ADV
from pygenesys.technology.storage import LI_BATTERY

# Import emissions
from pygenesys.commodity.emissions import co2eq, CO2


# Import capacity factor data
from pygenesys.data.library import solarfarm_data, railsplitter_data
from pygenesys.utils.tsprocess import aggregate

# Calculate the capacity factor distributions
solar_cf = aggregate(solarfarm_data, N_seasons, N_hours, kind='cf', groupby='day')
wind_cf = aggregate(railsplitter_data, N_seasons, N_hours, kind='cf', groupby='day')

years = np.linspace(start_year, end_year, N_years).astype('int')


# Add regional data
import pandas as pd

SOLAR_FARM.add_regional_data(region='IL',
                             input_comm=ethos,
                             output_comm=electricity,
                             efficiency=1.0,
                             tech_lifetime=25,
                             loan_lifetime=10,
                             capacity_factor_tech=solar_cf,
                             emissions={co2eq:4.8e-5},
                             cost_fixed=0.00805,
                             cost_invest=0.6732
                             )
WIND_FARM.add_regional_data(region='IL',
                            input_comm=ethos,
                            output_comm=electricity,
                            efficiency=1.0,
                            tech_lifetime=25,
                            loan_lifetime=10,
                            capacity_factor_tech=wind_cf,
                            emissions={co2eq:1.1e-5},
                            cost_fixed=0.03311,
                            cost_invest=1.1806,)

NUCLEAR_CONV.add_regional_data(region='IL',
                               input_comm=ethos,
                               output_comm=electricity,
                               efficiency=1.0,
                               tech_lifetime=25,
                               loan_lifetime=1,
                               capacity_factor_tech=1.0,
                               emissions={co2eq:1.2e-5},
                               cost_fixed=0.17773741,
                               cost_invest=0.05,
                               cost_variable=0.005811,
                               )

NUCLEAR_ADV.add_regional_data(region='IL',
                               input_comm=ethos,
                               output_comm=electricity,
                               efficiency=1.0,
                               tech_lifetime=25,
                               loan_lifetime=10,
                               capacity_factor_tech=1.0,
                               emissions={co2eq:1.2e-5},
                               ramp_up=0.25,
                               ramp_down=0.25,
                               cost_fixed=0.11899,
                               cost_invest=4.9164,
                               cost_variable=0.009158,
                               )

import collections, functools, operator

NATGAS_CONV.add_regional_data(region='IL',
                             input_comm=ethos,
                             output_comm=electricity,
                             efficiency=1.0,
                             tech_lifetime=25,
                             loan_lifetime=25,
                             capacity_factor_tech=1.0,
                             emissions={co2eq:4.9e-4, CO2:1.81e-4},
                             ramp_up=1.0,
                             ramp_down=1.0,
                             cost_fixed=0.0111934,
                             cost_invest=0.95958,
                             cost_variable=0.022387
                             )
NATGAS_ADV.add_regional_data(region='IL',
                             input_comm=ethos,
                             output_comm=electricity,
                             efficiency=1.0,
                             tech_lifetime=25,
                             loan_lifetime=25,
                             capacity_factor_tech=1.0,
                             emissions={co2eq:1.7e-4, CO2:1.81e-5},
                             ramp_up=1.0,
                             ramp_down=1.0,
                             cost_fixed=0.02699,
                             cost_invest=1.8910,
                             cost_variable=0.027475
                             )
COAL_CONV.add_regional_data(region='IL',
                             input_comm=ethos,
                             output_comm=electricity,
                             efficiency=1.0,
                             tech_lifetime=25,
                             loan_lifetime=25,
                             capacity_factor_tech=1.0,
                             emissions={co2eq:8.2e-4, CO2:3.2595e-4},
                             ramp_up=0.5,
                             ramp_down=0.5,
                             cost_fixed=0.0407033,
                             cost_invest=1.000,
                             cost_variable=0.021369
                             )

COAL_ADV.add_regional_data(region='IL',
                             input_comm=ethos,
                             output_comm=electricity,
                             efficiency=1.0,
                             tech_lifetime=25,
                             loan_lifetime=25,
                             capacity_factor_tech=1.0,
                             emissions={co2eq:2.2e-4, CO2:3.2595e-5},
                             ramp_up=0.5,
                             ramp_down=0.5,
                             cost_fixed=0.05824,
                             cost_invest=4.9246,
                             cost_variable=0.0366329
                             )

BIOMASS.add_regional_data(region='IL',
                          input_comm=ethos,
                          output_comm=electricity,
                          efficiency=1.0,
                          tech_lifetime=25,
                          loan_lifetime=25,
                          capacity_factor_tech=1.0,
                          emissions={co2eq:2.3e-4},
                          cost_fixed=0.123,
                          cost_invest=3.436,
                          cost_variable=0.047,
                          )

LI_BATTERY.add_regional_data(region='IL',
                             input_comm=electricity,
                             output_comm=electricity,
                             efficiency=0.85,
                             capacity_factor_tech=1.0,
                             tech_lifetime=25,
                             loan_lifetime=5,
                             emissions={co2eq:2.32e-5},
                             cost_invest=0.613,
                             cost_fixed=0.01532,
                             storage_duration=4)

# 2050 carbon limits

if scenario_name == "CC50":
    print('Applying constraints carbon neutral by 2050')
    CO2.add_regional_limit(region='IL',
                           limits={2025:52.34375,
                                   2030:41.875,
                                   2035:31.40625,
                                   2040:20.9375,
                                   2045:10.46875,
                                   2050:0.0})

# 2030 carbon limits
elif scenario_name == "CC30":
    print('Applying constraints carbon neutral by 2030')
    CO2.add_regional_limit(region='IL',
                           limits={2025:27.917,
                                   2030:0.0,
                                   2035:0.0,
                                   2040:0.0,
                                   2045:0.0,
                                   2050:0.0,})

else:
    print('No carbon limits -- Business as usual')

demands_list = [ELC_DEMAND]
resources_list = [electricity, ethos]
emissions_list = [co2eq, CO2]

if __name__ == "__main__":
    import numpy as np
    import matplotlib.pyplot as plt


    print(ELC_DEMAND.distribution)
    plt.plot(ELC_DEMAND.distribution['IL'])
    plt.show()