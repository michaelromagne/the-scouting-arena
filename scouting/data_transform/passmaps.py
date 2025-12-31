import pandas as pd


def change_range(value, old_range, new_range):
    """Normalize a range of values."""
    new_value = ((value - old_range[0]) / (old_range[1] - old_range[0])) * (
        new_range[1] - new_range[0]
    ) + new_range[0]

    if new_value >= new_range[1]:
        return new_range[1]
    elif new_value <= new_range[0]:
        return new_range[0]
    else:
        return new_value


def filter_on_time_window(
    df: pd.DataFrame,
    start_minute: int,
    end_minute: int,
    subbed_off_times: dict | None = None,
    subbed_on_times: dict | None = None,
) -> pd.DataFrame:
    """Filter dataframe based on time window and exclude players after they were subbed off.

    Args:
        df: DataFrame to filter
        start_minute: Start minute of the time window
        end_minute: End minute of the time window
        subbed_off_times: Dict mapping player IDs to their substitution off minute
        subbed_on_times: Dict mapping player IDs to their substitution on minute

    Returns:
        Filtered DataFrame
    """
    # Convert event times to minutes from start
    time_mask = (df["minute"] >= start_minute) & (df["minute"] < end_minute)

    if subbed_off_times or subbed_on_times:
        # Create mask for players based on substitutions at each event's time
        player_masks = []
        for _, row in df[time_mask].iterrows():
            player_id = row["player_id"]
            include_player = True

            # Check if player was subbed off before this event
            if subbed_off_times and (
                player_id in subbed_off_times
                and row["minute"] >= subbed_off_times[player_id]
            ):
                include_player = False

            # Check if player was not yet subbed on at this event
            if subbed_on_times and (
                player_id in subbed_on_times
                and row["minute"] < subbed_on_times[player_id]
            ):
                include_player = False

            player_masks.append(include_player)

        return df[time_mask][player_masks]

    return df[time_mask]


def get_substitutes_and_red_card_minutes(
    cards_and_subs_df: pd.DataFrame, team_id: int, team_data: pd.DataFrame
) -> tuple[list, dict, dict]:
    """Get minutes of red cards and substitutions, and dict of subbed off players with their exit times.

    Args:
        cards_and_subs_df: DataFrame containing cards and substitutions
        team_id: ID of the team to analyze
        team_data: DataFrame containing team event data

    Returns:
        tuple containing:
        - list of minutes when substitutions or red cards occurred
        - dict mapping player IDs to their substitution minute
        - dict mapping player IDs to their substitution minute
    """
    team_cards_and_subs = cards_and_subs_df[cards_and_subs_df["team_id"] == team_id]

    # Get red card minutes
    red_card_minutes = set(
        team_cards_and_subs[
            team_cards_and_subs["card_type"].isin(["SecondYellow", "Red"])
        ]["minute"]
    )

    # Get substitution minutes
    sub_events = team_cards_and_subs[
        team_cards_and_subs["type_name"] == "SubstitutionOn"
    ]
    sub_minutes = set(sub_events["minute"])

    # Get players that were subbed off with their exit times
    subbed_off_events = team_cards_and_subs[
        team_cards_and_subs["type_name"] == "SubstitutionOff"
    ]
    subbed_off_times = dict(
        zip(subbed_off_events["player_id"], subbed_off_events["minute"])
    )

    # Same with subbed on
    subbed_on_events = team_cards_and_subs[
        team_cards_and_subs["type_name"] == "SubstitutionOn"
    ]
    subbed_on_times = dict(
        zip(subbed_on_events["player_id"], subbed_on_events["minute"])
    )

    max_minute = team_data["minute"].max()

    all_subs_and_red_card_minutes = sub_minutes.union(red_card_minutes)
    all_subs_and_red_card_minutes.add(max_minute)

    return (
        sorted(list(all_subs_and_red_card_minutes)),
        subbed_off_times,
        subbed_on_times,
    )


def get_passes_df(team_data: pd.DataFrame):
    passes_df = team_data[team_data["type_name"] == "pass"].reset_index(drop=True)
    passes_df["player_id"] = passes_df["player_id"].astype("Int64")
    passes_df = passes_df.dropna(subset=["player_id"])
    passes_df["pass_recipient_name"] = passes_df["player"].shift(-1)
    passes_df = passes_df.dropna(subset=["pass_recipient_name"])
    return passes_df


def calculate_median_positions(passes_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate the median starting positions for each player."""
    positions = passes_df.groupby("player").agg(
        {"start_x": "median", "start_y": "median"}
    )
    positions.columns = ["x", "y"]
    positions.index = positions.index.astype(str)
    # Swap x and y for plot purpose (vertical pitches)
    positions["x"], positions["y"] = positions["y"], positions["x"]
    return positions


def get_player_stats(
    passes_df: pd.DataFrame,
    passes_df_suc: pd.DataFrame,
    passes_df_suc_short: pd.DataFrame,
    player_positions: pd.DataFrame,
) -> pd.DataFrame:
    # Count passes for each player
    player_pass_count_all = (
        passes_df.groupby("player")
        .agg({"player_id": "count"})
        .rename(columns={"player_id": "num_passes_all"})
    )
    player_pass_count_suc = (
        passes_df_suc.groupby("player")
        .agg({"player_id": "count"})
        .rename(columns={"player_id": "num_passes_suc"})
    )
    player_pass_count_suc_short = (
        passes_df_suc_short.groupby("player")
        .agg({"player_id": "count"})
        .rename(columns={"player_id": "num_passes_suc_short"})
    )
    player_pass_count = player_pass_count_all.join(
        [player_pass_count_suc, player_pass_count_suc_short]
    )
    # Calculate pass value (xT_value) for each player
    player_pass_value_suc = (
        passes_df_suc.groupby("player")
        .agg({"xT_value": "sum"})
        .round(3)
        .rename(columns={"xT_value": "pass_value_suc"})
    )
    player_pass_value_suc_short = (
        passes_df_suc_short.groupby("player")
        .agg({"xT_value": "sum"})
        .round(3)
        .rename(columns={"xT_value": "pass_value_suc_short"})
    )
    player_pass_value = player_pass_value_suc.join(player_pass_value_suc_short)
    # Merge player stats and positions --> To plot nodes
    player_stats = pd.merge(
        player_pass_count, player_pass_value, left_index=True, right_index=True
    )
    player_stats = pd.merge(
        player_stats, player_positions, left_index=True, right_index=True
    )

    return player_stats


def get_pair_stats(
    passes_df: pd.DataFrame,
    passes_df_suc: pd.DataFrame,
    passes_df_suc_short: pd.DataFrame,
    min_passes: int,
) -> pd.DataFrame:
    # Create pair keys for passes
    passes_df.loc[:, "pair_key"] = passes_df.apply(
        lambda x: "_".join([str(x["player"]), str(x["pass_recipient_name"])]), axis=1
    )
    passes_df_suc.loc[:, "pair_key"] = passes_df_suc.apply(
        lambda x: "_".join([str(x["player"]), str(x["pass_recipient_name"])]), axis=1
    )
    passes_df_suc_short.loc[:, "pair_key"] = passes_df_suc_short.apply(
        lambda x: "_".join([str(x["player"]), str(x["pass_recipient_name"])]), axis=1
    )
    # Count passes between pairs
    pair_pass_count_all = (
        passes_df.groupby("pair_key")
        .agg({"player_id": "count"})
        .rename(columns={"player_id": "num_passes_all"})
    )
    pair_pass_count_suc = (
        passes_df_suc.groupby("pair_key")
        .agg({"player_id": "count"})
        .rename(columns={"player_id": "num_passes_suc"})
    )
    pair_pass_count_suc_short = (
        passes_df_suc_short.groupby("pair_key")
        .agg({"player_id": "count"})
        .rename(columns={"player_id": "num_passes_suc_short"})
    )
    pair_pass_count = pair_pass_count_all.join(
        [pair_pass_count_suc, pair_pass_count_suc_short]
    )
    # Calculate pass value (xT_value) between pairs
    pair_pass_value_suc = (
        passes_df_suc.groupby("pair_key")
        .agg({"xT_value": "sum"})
        .round(3)
        .rename(columns={"xT_value": "pass_value_suc"})
    )
    pair_pass_value_suc_short = (
        passes_df_suc_short.groupby("pair_key")
        .agg({"xT_value": "sum"})
        .round(3)
        .rename(columns={"xT_value": "pass_value_suc_short"})
    )
    pair_pass_value = pair_pass_value_suc.join(pair_pass_value_suc_short)
    # Merge pair stats --> To plot edges
    pair_stats = pd.merge(
        pair_pass_count, pair_pass_value, left_index=True, right_index=True
    )
    pair_stats = pair_stats.sort_values("num_passes_suc", ascending=False)
    pair_stats_filtered = pair_stats[pair_stats["num_passes_suc"] >= min_passes]

    return pair_stats_filtered
