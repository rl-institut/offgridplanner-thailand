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

def combine_ent_or_pubs_profiles(all_profiles, enterprises):
    if enterprises is None or enterprises.empty:
        return pd.DataFrame()
    standard_ents = enterprises.query("consumer_type == 'enterprise'")
    common_ent_profile = all_profiles[
        "Enterprise_Large Load_Milling Machine"].copy()  # placeholder copy to keep same format before building up profile
    common_ent_profile *= 0
    if not standard_ents.empty:
        for enterprise_index in standard_ents.index:
            enterprise_type = standard_ents.loc[enterprise_index].consumer_detail.strip()
            column_select_string = "Enterprise_" + enterprise_type
            common_ent_profile += all_profiles[column_select_string]
    public_services = enterprises.query("consumer_type == 'public_service'")
    public_services_profile \
        = all_profiles["Enterprise_Large Load_Milling Machine"].copy()  # placeholder copy to keep same format before building up profile
    public_services_profile *= 0
    if not public_services.empty:
        for public_service_index in public_services.index:
            public_service_type = public_services.loc[public_service_index].consumer_detail.strip()
            column_select_string = "Public Service_" + public_service_type
            public_services_profile += all_profiles[column_select_string]
    large_load_ents = enterprises.query("(custom_specification.notnull()) & (consumer_type == 'enterprise')",
                                        engine='python')
    large_load_profile = all_profiles[
        "Enterprise_Large Load_Milling Machine"].copy()  # placeholder copy to keep same format before building up profile
    large_load_profile *= 0
    if not large_load_ents.empty:
        for enterprise_index in large_load_ents.index:
            large_loads_list = large_load_ents.loc[enterprise_index].custom_specification.split(';')
            # print("large_loads_list:", large_loads_list)
            if large_loads_list[0] != '':
                for load_type_and_count in large_loads_list:
                    load_count = int(load_type_and_count.split("x")[0].strip())
                    load_type = load_type_and_count.split("x")[1].split("(")[0].strip()
                    enterprise_type = large_load_ents.loc[enterprise_index].consumer_detail.strip()
                    column_select_string = "Enterprise_Large Load_" + load_type
                    large_load_profile += (load_count * all_profiles[column_select_string])
    total_non_household_profile = common_ent_profile + public_services_profile + large_load_profile
    return total_non_household_profile


def combine_hh_profiles(all_profiles, num_households, demand_par_dict):
    df_hh_profiles = \
        all_profiles["Household_Distribution_Based_Very Low Consumption"] * float(demand_par_dict["custom_share_1"]) + \
        all_profiles["Household_Distribution_Based_Low Consumption"] * float(demand_par_dict["custom_share_2"]) + \
        all_profiles["Household_Distribution_Based_Middle Consumption"] * float(demand_par_dict["custom_share_3"]) + \
        all_profiles["Household_Distribution_Based_High Consumption"] * float(demand_par_dict["custom_share_4"]) + \
        all_profiles["Household_Distribution_Based_Very High Consumption"] * float(demand_par_dict["custom_share_5"])
    df_hh_profiles *= num_households / 100
    return df_hh_profiles


def calibrate_profiles(df_hh_profile, df_ent_profile, df_pub_profile, calibration_target_value, calibration_option=None):
    calibration_factor = 1
    df_lst = [df_hh_profile, df_ent_profile, df_pub_profile]
    ts = [df for df in df_lst if not df.empty][0].index
    for i, df in enumerate(df_lst):
        if df.empty:
            df_lst[i] = pd.DataFrame(0, index=ts, columns=['value'])
    if calibration_option is not None:
        if calibration_option == "kWh":
            calibration_factor = calibration_target_value / ((df_hh_profile + df_ent_profile + df_pub_profile).sum() / 1000)
        elif calibration_option == "kW":
            calibration_factor = calibration_target_value / ((df_hh_profile + df_ent_profile + df_pub_profile).max() / 1000)
        for i, df in enumerate(df_lst):
            df_lst[i] = df_lst[i] * calibration_factor
    df = pd.concat(df_lst, axis=1)
    df.columns = ['households', 'enterprises', 'public_services']
    return df, calibration_factor
