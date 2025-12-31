from itertools import cycle

import pandas as pd
from mplsoccer import Pitch

cycol = cycle("brcm")


def plot_events_on_pitch(events_df: pd.DataFrame, pitch_type: str = "uefa"):
    """Plot events of a game on a football pitch."""
    pitch = Pitch(pitch_type=pitch_type, pitch_color="grass", line_color="white")
    fig, ax = pitch.draw(figsize=(10, 6))

    team_ids = events_df["team_id"].unique().tolist()
    team_colors = {team_id: next(cycol) for team_id in team_ids}

    for i, row in events_df.iterrows():
        color = team_colors.get(row["team_id"], "black")

        if row["type_name"] in ("shot", "pass", "cross"):
            pitch.arrows(
                row["start_x"],
                row["start_y"],
                row["end_x"],
                row["end_y"],
                width=2,
                headwidth=10,
                headlength=10,
                color=color,
                ax=ax,
            )

        else:
            pitch.lines(
                row["start_x"],
                row["start_y"],
                row["end_x"],
                row["end_y"],
                lw=2,
                color=color,
                ax=ax,
            )

        if row["result_name"] == "fail":
            ax.scatter(
                row["end_x"],
                row["end_y"],
                color="black",
                marker="x",
                s=100,
                label="Fail",
            )

        if "shot" in row["type_name"] and row["result_name"] == "success":
            ax.scatter(
                row["end_x"],
                row["end_y"],
                color="orange",
                marker="*",
                s=200,
                label="Goal",
            )

        # if i > 0 and events_df.iloc[i - 1]['result_name'] == 'fail':
        #     ax.scatter(row['start_x'], row['start_y'], color='black', marker='o', s=100, label='New Action Start')
