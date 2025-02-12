def get_demand_timeseries(nodes, custom_demand_parameters, all_profiles=None, df_only=True):
    num_households = len(nodes[
                             (nodes['consumer_type'] == 'household')
                             & (nodes['is_connected'] == True)
                         ].index)
    calibration_target_value, calibration_option = get_calibration_target(custom_demand_parameters)
    if all_profiles is None:
        all_profiles = pd.read_parquet(path=config.FULL_PATH_PROFILES, engine="pyarrow")
    df_hh_profile = combine_hh_profiles(all_profiles,
                                        num_households=num_households,
                                        demand_par_dict=custom_demand_parameters)
    enterprise_nodes = nodes[(nodes['consumer_type'] == 'enterprise') & (nodes['is_connected'] == True)]
    public_service_nodes = nodes[(nodes['consumer_type'] == 'public_service') & (nodes['is_connected'] == True)]
    df_ent_profile = combine_ent_or_pubs_profiles(all_profiles, enterprise_nodes)
    df_pub_profile = combine_ent_or_pubs_profiles(all_profiles, public_service_nodes)
    df, calibration_factor = calibrate_profiles(df_hh_profile,
                                                df_ent_profile,
                                                df_pub_profile,
                                                calibration_target_value,
                                                calibration_option)
    if df_only:
        return df / 1000
    else:
        return df / 1000, calibration_target_value, calibration_option, calibration_factor

def get_calibration_target(demand_par_dict):
    if demand_par_dict['maximum_peak_load'] is not None:
        value = float(demand_par_dict['maximum_peak_load'])
        calibration_option = 'kW'
    elif demand_par_dict['average_daily_energy'] is not None:
        value = float(demand_par_dict['average_daily_energy'])
        calibration_option = 'kWh'
    else:
        value = 1
        calibration_option = None
    return value, calibration_option
