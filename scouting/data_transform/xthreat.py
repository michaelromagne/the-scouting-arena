import pandas as pd
import socceraction.spadl as spadl
import socceraction.xthreat as xthreat


def compute_sequence_id(spadl_events_df: pd.DataFrame) -> pd.DataFrame:
    """Compute the sequence_id column for a game.

    The sequence_id is a unique identifier for a sequence of events in a game.
    When a team loses the ball, the sequence ends and a new one starts.
    """
    spadl_events_df = spadl_events_df.assign(
        previous_team_id=spadl_events_df["team_id"].shift(1)
    )
    spadl_events_df = spadl_events_df.assign(
        lost_ball=spadl_events_df["team_id"] != spadl_events_df["previous_team_id"]
    )

    spadl_events_df["sequence_id"] = spadl_events_df["lost_ball"].cumsum()

    return spadl_events_df


def convert_actions_ltr(spadl_events_df: pd.DataFrame) -> pd.DataFrame:
    """Convert event data in the SPADL format in left-to-right format.

    After this conversion, all actions from both teams go in the same direction.
    This is necesary to compute metrics such as xT (Expected Threat).

    SPADL events need to have the following columns:
    - team_id
    - home_team_id
    - start_x
    - start_y
    - end_x
    - end_y

    Args:
        spadl_events_df (pd.DataFrame): Football events data in the SPADL format.

    Returns:
        pd.DataFrame: Football events data in the SPADL format with left-to-right actions
    """
    df_actions_ltr = spadl.play_left_to_right(
        spadl_events_df, spadl_events_df["home_team_id"]
    )

    df_actions_ltr["end_x"] = df_actions_ltr["end_x"].fillna(df_actions_ltr["start_x"])
    df_actions_ltr["end_y"] = df_actions_ltr["end_y"].fillna(df_actions_ltr["start_y"])

    return df_actions_ltr


def compute_xthreat(spadl_events_df: pd.DataFrame) -> pd.DataFrame:
    """Compute Expected Threat (xT) for a game.

    Expected Threat is a metric that values actions that successfully move the ball
    between two locations on the pitch by computing the difference between the
    long-term probability of scoring on the start and end location of an action.

    Here, we use the Expected Threat implementation from the socceraction package,
    which requires the data to be in SPADL (Soccer Player Action Description Language) format:
    https://socceraction.readthedocs.io/en/latest/index.html

    Args:
        spadl_events_df (pd.DataFrame): Football events data in the SPADL format.

    Returns:
        pd.DataFrame: Actions data with the xT_value column added, in the SPADL format.
    """
    df_actions_ltr = convert_actions_ltr(spadl_events_df)

    xt_model = xthreat.ExpectedThreat(l=16, w=12)
    xt_model.fit(df_actions_ltr)

    df_mov_actions = xthreat.get_successful_move_actions(df_actions_ltr)
    df_mov_actions["xT_value"] = xt_model.rate(df_mov_actions).round(5)

    df_actions_ltr = df_actions_ltr.merge(
        df_mov_actions[["game_id", "action_id", "xT_value"]],
        on=["game_id", "action_id"],
        how="left",
    ).fillna({"xT_value": 0})

    df_actions_ltr = compute_sequence_id(df_actions_ltr)

    return df_actions_ltr
