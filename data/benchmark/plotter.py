import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import (MultipleLocator, AutoMinorLocator)
import pygenesys as pg
plt.style.use('ggplot')
plt.rcParams['figure.figsize'] = (12,9)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['savefig.dpi'] = 400
plt.rcParams['savefig.bbox'] = 'tight'

N_hours = 24


elc_colors = {'ELC_EX':'tab:brown',
              'IMP_ELC':'tab:brown',
              'BIOMASS':'tab:brown',
              'ABBOTT_TB':'tab:red',
              'ABBOTT':'tab:red',
              'NUCLEAR_THM':'tab:green',
              'NUCLEAR_TB':'tab:green',
              'LI_BATTERY':'dimgray',
              'SOLAR_FARM':'yellow',
              'WIND_FARM':'tab:blue',
              'COAL_CONV':'k',
              'COAL_ADV':'firebrick',
              'NATGAS_ADV':'tab:orange',
              'NATGAS_CONV':'tan',
              'NUCLEAR_ADV':'tab:green',
              'NUCLEAR_CONV':'lightblue',
              'CWS':'tab:purple',
              'CW_STORAGE':'tab:pink'}


def get_periods(db_conn):
    """
    This function returns a list of simulated
    years.
    """

    command = "SELECT * FROM time_periods WHERE flag is 'f'"

    cur = db_conn.cursor()
    cur.execute(command)
    periods = [y[0] for y in cur.fetchall()]

    return periods[:-1]


def sorted_flow_out(unsorted_data, N_hours=24):
    """
    This function returns sorted data.

    The unsorted data should be a list of tuples
    where the tuples are ('time_day', 'vflow_out').

    There may be duplicate time slices for different vintages
    of a technology! Why? Who knows.
    """

    sorted_data = np.zeros(N_hours)

    for tup in unsorted_data:
        hour = int(tup[0].strip('H'))
        sorted_data[hour-1] = float(tup[1])

    return sorted_data


def sorted_years(unsorted_data, periods):
    """
    This function sorts data given for each period.

    The unsorted data should be a list of tuples
    where the tuples are ('t_periods', 'value').

    Parameters
    ----------
    unsorted_data : list
        A list of tuples
    periods : list
        The list of periods in the simulation.
    """

    sorted_data = unsorted_data

    sorted_data.sort(key = lambda y: int(y[0]))


    return sorted_data


def get_regions(db_conn):
    """
    This function returns the regions in the simulation.
    """

    cur = db_conn.cursor()
    command = "SELECT regions FROM regions"

    cur.execute(command)
    regions = cur.fetchall()
    regions = [r[0] for r in regions]

    return regions


def get_seasons(db_conn):
    """
    This function returns a list of simulated
    seasons.
    """

    command = "SELECT t_season FROM time_season"

    cur = db_conn.cursor()
    cur.execute(command)
    seasons = [s[0] for s in cur.fetchall()]

    return seasons


def get_regional_techs(db_conn, outcomm, region):
    """
    This function returns a list of technologies
    in a given sector.
    """

    cur = db_conn.cursor()

    if type(outcomm) == list:
        command = (f"SELECT tech FROM Output_VFlow_Out WHERE regions LIKE '%{region}' "
                   f"AND (output_comm IS '{outcomm[0]}' OR output_comm IS '{outcomm[1]}')" )
    else:
        command = (f"SELECT tech FROM Output_VFlow_Out WHERE regions LIKE '%{region}' "
                   f"AND output_comm IS '{outcomm}' ")


    cur.execute(command)

    regional_techs = np.unique([t[0] for t in cur.fetchall()])

    return regional_techs


def get_hourly_data(db_conn, region, season, year, technology, scenario=None):
    """
    This function returns the hourly data for a particular
    year, season, and technology.
    """
    if scenario is None:
        command = (f"SELECT t_day, SUM(vflow_out), tech "
                   f"FROM Output_VFlow_Out "
                   f"WHERE tech IS '{technology}' "
                   f"AND t_season IS '{season}' "
                   f"AND t_periods IS {year} "
                   f"AND regions LIKE '%{region}' "
                   f"GROUP BY Output_VFlow_Out.t_day")
    else:
        command = (f"SELECT t_day, SUM(vflow_out), tech "
                   f"FROM Output_VFlow_Out "
                   f"WHERE tech IS '{technology}' "
                   f"AND t_season IS '{season}' "
                   f"AND t_periods IS {year} "
                   f"AND regions LIKE '%{region}' "
                   f"AND scenario LIKE '%{scenario}' "
                   f"GROUP BY Output_VFlow_Out.t_day")
    cur = db_conn.cursor()
    cur.execute(command)

    hourly_data = cur.fetchall()
    hourly_data = sorted_flow_out(hourly_data)

    if (technology == 'LI_BATTERY') or (technology == 'CW_STORAGE'):
        command = (f"SELECT t_day, SUM(vflow_in), tech "
           f"FROM Output_VFlow_In "
           f"WHERE tech IS '{technology}' "
           f"AND t_season IS '{season}' "
           f"AND t_periods IS {year} "
           f"AND regions LIKE '%{region}' "
           f"GROUP BY Output_VFlow_In.t_day")

        cur.execute(command)
        stored = cur.fetchall()
        stored = sorted_flow_out(stored)
        hourly_data = hourly_data #- stored

    return hourly_data



def get_load_profile(db_conn, region, season, year, outcomm, scenario=None):

    tech_list = get_regional_techs(db_conn, outcomm, region)
    if (region == 'UIUC') and (outcomm=='ELC'):
        tech_list = ['ABBOTT_TB','IMP_ELC', 'NUCLEAR_TB', 'WIND_FARM', 'SOLAR_FARM' , 'LI_BATTERY']
    elif (region == 'IL') and (outcomm=='ELC'):
        tech_list = ['COAL_CONV',  'NUCLEAR_CONV', 'NUCLEAR_ADV',
                     'BIOMASS','NATGAS_CONV','NATGAS_ADV',
                     'WIND_FARM', 'SOLAR_FARM', 'LI_BATTERY']


    load_profile = {}

    for tech in tech_list:
        data = get_hourly_data(db_conn, region, season, year, tech, scenario)
        load_profile[tech] = data
#     print(load_profile)
    return list(load_profile.keys()), list(load_profile.values())


def get_demand_curve(db_conn, season, region, comm="ELC_DEMAND", scenario=None):
    """
    This function returns the demand curve for a particular season.
    """

    if scenario == None:
        command = (f"SELECT time_of_day_name, dds FROM DemandSpecificDistribution "
                  f"WHERE season_name IS '{season}' "
                  f"AND demand_name IS '{comm}' "
                  f"AND regions IS '{region}' ")
    else:
        command = (f"SELECT time_of_day_name, dds FROM DemandSpecificDistribution "
                  f"WHERE season_name IS '{season}' "
                  f"AND demand_name IS '{comm}' "
                  f"AND regions IS '{region}' "
                  f"AND scenario IS '{scenario}' ")

    cur = db_conn.cursor()
    data = cur.execute(command)

    demand_data = cur.fetchall()
    demand_data = sorted_flow_out(demand_data)
    return demand_data


def get_demand_value(db_conn, region, period, comm="ELC_DEMAND"):
    """
    This function returns the demand value for a particular period.
    """

    command = (f"SELECT demand FROM Demand "
               f"WHERE demand_comm IS '{comm}' "
               f"AND periods IS {period} "
               f"AND regions LIKE '{region}' ")
    cur = db_conn.cursor()
    data = cur.execute(command)

    demand = cur.fetchall()[0][0]

    return demand



def plot_electricity_profiles(db_conn, region, outcomm, colors=elc_colors, N_hours=24, scenario=None):
    """
    This function plots all of the load profiles
    for a particular sector.
    """

    seasons = get_seasons(db_conn)
    periods = get_periods(db_conn)
    all_techs = get_regional_techs(db_conn, outcomm, region)

    fig, ax = plt.subplots(nrows=len(periods), ncols=1, sharex=True, figsize=(10, 20))

    axes = []

    for i,year in enumerate(periods):
#         dmd = get_demand_value(conn, period=year, comm='CW_DEMAND', region='UIUC')
        for j, s in enumerate(seasons):
            techs, activity = get_load_profile(db_conn, region, s, year, outcomm, scenario)
            sec_colors = [elc_colors[tech] for tech in techs]
            hours = np.arange(0,N_hours,1)+j*N_hours+1
            ax[i].xaxis.set_minor_locator(AutoMinorLocator())
            d1 = ax[i].stackplot(hours, activity, labels=techs, colors=sec_colors, baseline='zero')
            ax[i].tick_params(which='minor', length=4, color='r')
            ax[i].set_ylabel(f'Generation [GWh] : {year}')
            axes.append(d1)
#             ax[i].set_ylim(0,16)
#             ax[i].set_xlim(/,100)

    fig.legend(axes, labels=techs, loc='right',bbox_to_anchor=(1.3, 0.75), fontsize=21)
#     fig.legend(axes, labels=all_techs)
    plt.subplots_adjust(right=0.9)
#     plt.legend()
    plt.show()

    return


def get_annual_capacity(db_conn, region, outcomm, scenario=None):
    """
    Retrieves the annual capacity of each technology.
    """

    periods = get_periods(db_conn)
    all_techs = get_regional_techs(db_conn, outcomm, region)

    cur = db_conn.cursor()

    cap_dict = {}
    for tech in all_techs:
        if scenario == None:
            command = (f"SELECT t_periods, capacity "
                       f"FROM Output_CapacityByPeriodAndTech "
                       f"WHERE tech IS '{tech}' "
                       f"AND regions LIKE '%{region}' "
                       f"ORDER BY Output_CapacityByPeriodAndTech.t_periods")
        else:
            command = (f"SELECT t_periods, capacity "
                       f"FROM Output_CapacityByPeriodAndTech "
                       f"WHERE tech IS '{tech}' "
                       f"AND regions LIKE '%{region}' "
                       f"AND scenario LIKE '%{scenario}' "
                       f"ORDER BY Output_CapacityByPeriodAndTech.t_periods")
        cur.execute(command)
        cap_tech = cur.fetchall()

        diff = np.diff(periods).astype('int')[0]
        first_year = int(min(periods))

        caps = np.zeros(len(periods))
        for i, tup in enumerate(cap_tech):
            year = tup[0]
            cap = tup[1]
            j = int((year-first_year)/diff)
            caps[j] = cap
        cap_dict[tech] = caps
    cap_dict['year'] = periods

    cap_df = pd.DataFrame(cap_dict)
    cap_df.set_index('year', inplace=True)
    return cap_df


def get_annual_generation(db_conn, region, outcomm, scenario=None):
    """
    Retrieves the annual generation of each technology.
    """

    periods = get_periods(db_conn)
    all_techs = get_regional_techs(db_conn, outcomm, region)

    cur = db_conn.cursor()

    cap_dict = {}
    for tech in all_techs:
        if scenario == None:
            command = (f"SELECT t_periods, SUM(vflow_out), tech "
                           f"FROM Output_VFlow_Out "
                           f"WHERE tech IS '{tech}' "
                           f"AND regions LIKE '%{region}' "
                           f"GROUP BY Output_VFlow_Out.t_periods")
        else:
            command = (f"SELECT t_periods, SUM(vflow_out), tech "
                           f"FROM Output_VFlow_Out "
                           f"WHERE tech IS '{tech}' "
                           f"AND regions LIKE '%{region}' "
                           f"AND scenario LIKE '%{scenario}' "
                           f"GROUP BY Output_VFlow_Out.t_periods")
        cur.execute(command)
        cap_tech = cur.fetchall()

        diff = np.diff(periods).astype('int')[0]
        first_year = int(min(periods))

        caps = np.zeros(len(periods))
        for i, tup in enumerate(cap_tech):
            year = tup[0]
            cap = tup[1]
            j = int((year-first_year)/diff)
            caps[j] = cap
        cap_dict[tech] = caps
    cap_dict['year'] = periods

    cap_df = pd.DataFrame(cap_dict)
    cap_df.set_index('year', inplace=True)
    return cap_df