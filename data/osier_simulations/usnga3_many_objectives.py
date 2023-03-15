from osier import *
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sb
import functools
from sklearn.preprocessing import normalize
from pymoo.core.problem import Problem
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.algorithms.moo.unsga3 import UNSGA3
from pymoo.termination import get_termination
from pymoo.optimize import minimize
from pymoo.termination.ftol import MultiObjectiveSpaceTermination
from pymoo.visualization.scatter import Scatter
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PolynomialMutation
from pymoo.termination.robust import RobustTermination
from pymoo.core.parameters import set_params, hierarchical

from pygenesys.utils.tsprocess import aggregate
from unyt import kW, MW, GW, hour, unyt_array

from tech_library import *

from copy import deepcopy
import time
import dill

print("Modules imported...")

# # Import solar, wind, demand
n_hours = 24
n_days = 2
N = n_hours*n_days
scale = 1
total_demand = 187e3 * n_days/365 * GW

wdf = pd.read_csv('../../../2021-dotson-ms/data/railsplitter_data.csv', 
                  usecols=['time', 'kw'], 
                  index_col='time', 
                  parse_dates=True)
# wdf = wdf[wdf.index.year == 2017][:N]/scale
sdf = pd.read_csv('../../../2021-dotson-ms/data/solarfarm_data.csv', 
                  usecols=['time', 'kw'],
                  index_col='time', 
                  parse_dates=True)
# sdf = sdf[sdf.index.year == 2017][:N]/scale
ddf = pd.read_csv('../../../2021-dotson-ms/data/uiuc_demand_data.csv',
                  usecols=['time', 'kw'],
                  index_col='time',
                  parse_dates=True)
# ddf = ddf[ddf.index.year == 2017][:N]/scale

ddf = aggregate(ddf,
                N_seasons=365,
                N_hours=n_hours,
                kind='demand',
                groupby='day')
sdf = aggregate(sdf,
                N_seasons=365,
                N_hours=n_hours,
                kind='cf',
                groupby='day')
wdf = aggregate(wdf,
                N_seasons=365,
                N_hours=n_hours,
                kind='cf',
                groupby='day')


ddf = ddf.flatten()[:N]
ddf = ddf/ddf.sum() * total_demand
sdf = sdf.flatten()[:N]*1*GW
wdf = wdf.flatten()[:N]*1*GW

print("Demand, solar, and wind curves processed...")

techs = [nuclear, 
         nuclear_adv,
         natural_gas,
         natural_gas_adv,
         coal,
         coal_adv,
         biomass,
         battery,
         solar,
         wind
         ]

with open("../2022-12-31-techset.pkl", "rb") as file:
    techs = dill.load(file)

# percent renewable energy 

def percent_nonrenewable(technology_list, solved_dispatch_model):
    """
    Calculates the percentage of non-renewable energy as a fraction of
    total energy produced. If we want to maximize the percent 
    renewable energy, then we should minimize the energy produced
    by everything else.
    """
    
    all_nonre = get_tech_names([t for t in techs
                              if not (t.renewable)
                              and not hasattr(t, 'storage_duration')])
    all_nonstorage = get_tech_names([t for t in techs
                              if not hasattr(t, 'storage_duration')])
    non_renewable_energy = solved_dispatch_model.results[all_nonre].sum().sum()
    non_storage_energy = solved_dispatch_model.results[all_nonstorage].sum().sum()

    fraction_non_re = non_renewable_energy/non_storage_energy

    return fraction_non_re

# objs = [total_cost, 
# functools.partial(annual_emission, 
#                     emission='lifecycle_co2_rate'), 
# percent_nonrenewable]

objs = [total_cost, 
functools.partial(annual_co2, 
                  emission='lifecycle_co2_rate'),
        # annualized_capital_cost
        ]

from osier.models.capacity_expansion import CapacityExpansion
problem = CapacityExpansion(technology_list=techs,
                            objectives=objs,
                            demand=ddf,
                            solar=sdf,
                            wind=wdf,
                            power_units=GW,
                            allow_blackout=False,
                            verbosity=10)

print("Problem initialized... ")

# # Repair Operator

from pymoo.core.repair import Repair

class PortfolioRepair(Repair):

    def _do(self, problem, X, **kwargs):
        # zero out small numbers
        # make sure the portfolio equals one
        X = X/X.sum(axis=1, keepdims=True)
        X[X<1e-2] = 0
        X = X/X.sum(axis=1, keepdims=True)
        I = np.eye(problem.n_var, problem.n_var) * problem.capacity_credit
        X = ((X.T)/(I@X.T).sum(axis=0, keepdims=True)).T      
        return X

# class CapacityCredit(Repair):

#     def _do(self, problem, X, **kwargs):
#         # zero out small numbers
#         # make sure the portfolio equals one
        
#         C = problem.capacity_credit
# #         print("CAPACITY REQUIREMENT\n",C)
# #         print("INITIAL \n",X)
#         X = X/X.sum(axis=1, keepdims=True)
# #         print("NORMALIZATION\n",X)
#         X[X<1e-2] = 0
# #         print("REMOVE SMALL NUMBERS\n",X)
#         X = X/C
# #         print("DIVIDE BY CAPACITY CREDIT\n",X)
#         X = np.around(X, 3)
# #         print(X)
#         return X


with open('../2022-12-10-optimal_hyperparams_UNSGA3.pkl', 'rb') as file:
    hyperparams = dill.load(file)

from pymoo.util.ref_dirs import get_reference_directions
from pymoo.visualization.scatter import Scatter

n_pop = 100
ref_dirs = get_reference_directions("energy", 
                                    problem.n_obj, 
                                    n_pop, 
                                    seed=1)

print("Reference directions generated... ")

algorithm = UNSGA3(
    ref_dirs=ref_dirs,
    sampling=FloatRandomSampling(),
    crossover=SBX(prob=0.9, eta=15),
    mutation=PolynomialMutation(eta=50),
    eliminate_duplicates=True,
    repair = PortfolioRepair()
)
set_params(algorithm, hierarchical(hyperparams))
# termination = RobustTermination(
#     MultiObjectiveSpaceTermination(tol=1e-2, n_skip=20), period=10)
termination = get_termination("n_gen", 5)

print("Algorithm Initialized! Begin optimization:")

start = time.perf_counter()
res = minimize(problem,
               algorithm,
               termination,
               pf=False,
               seed=5,
               save_history=True,
               verbose=True)
end = time.perf_counter()

F = res.F
X = res.X


print("Simulation took", res.exec_time/3600, " hours")

save = False

if save:
    with open("../2023-03-12-USNGA3-results.pkl", "wb+") as file:
        dill.dump(res, file)

    with open("../2023-03-12-optimal_hyperparams.pkl", "wb") as hp:
        dill.dump(hyperparams, hp)
    with open("../2023-03-12-optimal_objective_F.pkl", "wb") as obj_F:
        dill.dump(F, obj_F)
    with open("../2023-03-12-optimal_design_X.pkl", "wb") as des_X:
        dill.dump(X, des_X)
    with open("../2023-03-12-techset.pkl", "wb") as ts:
        dill.dump(techs, ts)

    print("Simulation results saved!")

with open("../2023-03-13-DEBUGGING.pkl", "wb+") as file:
        dill.dump(res, file)