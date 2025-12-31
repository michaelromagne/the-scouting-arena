from typing import Tuple

import matplotlib.pyplot as plt
import pandas as pd
from highlight_text import fig_text
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import (
    ArrowStyle,
    Circle,
    FancyArrowPatch,
)
from mplsoccer.pitch import VerticalPitch

from scouting.constants import (
    HEAD_LENGTH,
    HEAD_WIDTH,
    MAX_ALPHA,  # Transparency
    MAX_EDGE_WIDTH,
    MAX_NODE_SIZE,
    MAX_PAIR_COUNT,
    MAX_PAIR_VALUE,
    MAX_PLAYER_COUNT,
    MAX_PLAYER_VALUE,
    MIN_ALPHA,  # Transparency
    MIN_EDGE_WIDTH,
    MIN_NODE_SIZE,
    MIN_PAIR_COUNT,
    MIN_PAIR_VALUE,
    MIN_PLAYER_COUNT,
    MIN_PLAYER_VALUE,
)
from scouting.data_transform.passmaps import change_range

nodes_cmap = LinearSegmentedColormap.from_list(
    "", ["#E15A82", "#EEA934", "#F1CA56", "#DCED69", "#7FF7A8", "#5AE1AC", "#11C0A1"]
)
NODE_CMAP = cm.get_cmap(nodes_cmap)

norm = Normalize(vmin=0, vmax=1)
node_color1 = NODE_CMAP(norm(0))
node_color2 = NODE_CMAP(norm(0.25))
node_color3 = NODE_CMAP(norm(0.5))
node_color4 = NODE_CMAP(norm(0.75))
node_color5 = NODE_CMAP(norm(1))


def add_details(
    fig,
    ax_n,
    game_result: str,
    subtitle: str,
    team_name: str,
    start_minute: int | str,
    end_minute: int | str,
):
    """Add plot annotations.

    Args:
        fig (matplotlib.figure.Figure): Figure object.
        ax_n (matplotlib.axes._axes.Axes): Axes object.
        game_result (str): Game result. Example: "Salzburg 0 - 4 Brest".
        subtitle (str): Subtitle. Example: "Champions League | 2024-10-01".
        team_name (str): Team name for this passmap.
        start_minute (int): Start minute for the passmap.
        end_minute (int): End minute for the passmap.
    """

    # Add text annotations
    head_length, head_width = 0.3, 0.05
    ax_n.annotate(
        text="",
        xy=(102, 58),
        xytext=(102, 43),
        zorder=2,
        ha="center",
        arrowprops=dict(
            arrowstyle=f"->, head_length={head_length}, head_width={head_width}",
            color="#7c7c7c",
            lw=0.5,
        ),
    )
    ax_n.annotate(
        text="Attack",
        xy=(104, 48),
        zorder=2,
        ha="center",
        color="#7c7c7c",
        rotation=90,
        size=5,
    )

    font = "serif"
    fig_text(
        x=0.5,
        y=0.90,
        s=f"Passing network for {game_result}",
        weight="bold",
        va="bottom",
        ha="center",
        fontsize=10,
        font=font,
        color="black",
    )

    # Additional Annotations
    fig_text(
        x=0.5,
        y=0.875,
        s=f"{subtitle}",
        va="bottom",
        ha="center",
        fontsize=6,
        font=font,
        color="black",
    )

    start_minute = (
        f"90'+{start_minute % 90}'" if int(start_minute) > 90 else f"{start_minute}'"
    )
    end_minute = (
        f"90'+{int(end_minute % 90)}'" if int(end_minute) > 90 else f"{end_minute}'"
    )
    fig_text(
        x=0.5,
        y=0.82,
        s=f"{team_name} - Passes from {start_minute} to {end_minute}",
        weight="bold",
        va="bottom",
        ha="center",
        fontsize=8,
        font=font,
        color="#7c7c7c",
    )

    # Add legends for the different metrics and values
    legend_annotations = [
        (0.14, 0.14, "Pass count between"),
        (0.38, 0.14, "Pass value between (OP xT)"),
        (0.61, 0.14, "Player pass count"),
        (0.84, 0.14, "Player pass value (OP xT)"),
        (0.41, 0.038, "Low"),
        (0.6, 0.038, "High"),
        (0.13, 0.07, "5 to 16+"),
        (0.37, 0.07, "0 to 0.09+"),
        (0.61, 0.07, "1 to 88+"),
        (0.84, 0.07, "0.01 to 0.36+"),
    ]

    for x, y, text in legend_annotations:
        fig_text(
            x=x,
            y=y,
            s=text,
            va="bottom",
            ha="center",
            fontsize=6,
            font=font,
            color="black",
        )

    # Draw legend elements
    head_length = 20
    head_width = 20

    x0 = 135
    y0 = 195
    dx = 60
    dy = 120
    shift_x = 70

    x1 = 640
    x2 = 1280
    y2 = 240
    shift_x2 = 70
    radius = 20

    x3 = 1730
    shift_x3 = 100

    color = "black"

    style = ArrowStyle("->", head_length=5, head_width=3)

    arrow1 = FancyArrowPatch(
        (x0, y0), (x0 + dx, y0 + dy), lw=0.5, arrowstyle=style, color=color
    )
    arrow2 = FancyArrowPatch(
        (x0 + shift_x, y0),
        (x0 + dx + shift_x, y0 + dy),
        lw=1.5,
        arrowstyle=style,
        color=color,
    )
    arrow3 = FancyArrowPatch(
        (x0 + 2 * shift_x, y0),
        (x0 + dx + 2 * shift_x, y0 + dy),
        lw=2.5,
        arrowstyle=style,
        color=color,
    )

    arrow4 = FancyArrowPatch(
        (x1, y0), (x1 + dx, y0 + dy), lw=2.5, arrowstyle=style, color=node_color1
    )
    arrow5 = FancyArrowPatch(
        (x1 + shift_x, y0),
        (x1 + dx + shift_x, y0 + dy),
        lw=2.5,
        arrowstyle=style,
        color=node_color2,
    )
    arrow6 = FancyArrowPatch(
        (x1 + 2 * shift_x, y0),
        (x1 + dx + 2 * shift_x, y0 + dy),
        lw=2.5,
        arrowstyle=style,
        color=node_color3,
    )
    arrow7 = FancyArrowPatch(
        (x1 + 3 * shift_x, y0),
        (x1 + dx + 3 * shift_x, y0 + dy),
        lw=2.5,
        arrowstyle=style,
        color=node_color4,
    )
    arrow8 = FancyArrowPatch(
        (x1 + 4 * shift_x, y0),
        (x1 + dx + 4 * shift_x, y0 + dy),
        lw=2.5,
        arrowstyle=style,
        color=node_color5,
    )

    circle1 = Circle(xy=(x2, y2), radius=radius, edgecolor="black", fill=False)
    circle2 = Circle(
        xy=(x2 + shift_x2, y2), radius=radius * 1.5, edgecolor="black", fill=False
    )
    circle3 = Circle(
        xy=(x2 + 2.3 * shift_x2, y2), radius=radius * 2, edgecolor="black", fill=False
    )

    circle4 = Circle(xy=(x3, y2), radius=radius * 2, color=node_color1)
    circle5 = Circle(xy=(x3 + shift_x3, y2), radius=radius * 2, color=node_color2)
    circle6 = Circle(xy=(x3 + 2 * shift_x3, y2), radius=radius * 2, color=node_color3)
    circle7 = Circle(xy=(x3 + 3 * shift_x3, y2), radius=radius * 2, color=node_color4)
    circle8 = Circle(xy=(x3 + 4 * shift_x3, y2), radius=radius * 2, color=node_color5)

    fig.patches.extend([arrow1, arrow2, arrow3])
    fig.patches.extend([arrow4, arrow5, arrow6, arrow7, arrow8])
    fig.patches.extend([circle1, circle2, circle3])
    fig.patches.extend([circle4, circle5, circle6, circle7, circle8])

    x4 = 935
    y4 = 90
    dx = 350

    arrow9 = FancyArrowPatch(
        (x4, y4), (x4 + dx, y4), lw=1, arrowstyle=style, color="black"
    )

    fig.patches.extend([arrow9])

    # Adjust the layout for better spacing
    plt.tight_layout()
    plt.subplots_adjust(wspace=0.1, hspace=0, bottom=0.1)


def plot_pitch() -> Tuple[plt.Figure, plt.Axes, VerticalPitch]:
    plt.style.use("fivethirtyeight")
    pitch = VerticalPitch(
        pitch_type="uefa",
        line_color="#7c7c7c",
        goal_type="box",
        linewidth=0.5,
        pad_bottom=20,
        pad_top=20,
    )
    fig, ax = plt.subplots(figsize=(6, 6), dpi=400)
    pitch.draw(ax=ax, constrained_layout=False, tight_layout=False)
    return fig, ax, pitch


def plot_nodes(
    ax: plt.Axes,
    player_stats: pd.DataFrame,
    short_period: bool = False,
) -> None:
    """Plot nodes representing players.

    If you want to plot passmaps only for sub periods of a game,
    you may prefer to get stats on short time window.
    """
    num_passes_var = "num_passes_suc_short" if short_period else "num_passes_suc"
    pass_value_var = "pass_value_suc_short" if short_period else "pass_value_suc"
    for player, stats in player_stats.iterrows():
        marker_size = change_range(
            stats[num_passes_var],
            (MIN_PLAYER_COUNT, MAX_PLAYER_COUNT),
            (MIN_NODE_SIZE, MAX_NODE_SIZE),
        )
        norm = Normalize(vmin=MIN_PLAYER_VALUE, vmax=MAX_PLAYER_VALUE)
        node_color = NODE_CMAP(norm(stats[pass_value_var]))

        ax.plot(
            stats["x"],
            stats["y"],
            ".",
            markersize=marker_size + 2,
            zorder=4,
            color="white",
        )
        ax.plot(
            stats["x"],
            stats["y"],
            ".",
            color=node_color,
            markersize=marker_size,
            zorder=5,
        )

        var_ = (
            " ".join(str(player).split(" ")[1:])
            if len(str(player).split(" ")) > 1
            else str(player)
        )
        ax.annotate(
            var_,
            xy=(stats["x"], stats["y"] + 4 if stats["y"] > 48 else stats["y"] - 4),
            ha="center",
            va="center",
            zorder=7,
            fontsize=5,
            color="black",
            font="serif",
            weight="heavy",
        )

        player_stats.loc[str(player), "marker_size"] = marker_size


def plot_edges(
    ax: plt.Axes,
    player_stats: pd.DataFrame,
    pair_stats_filtered: pd.DataFrame,
    short_period: bool = False,
) -> None:
    """Plot edges representing passes between players.

    If you want to plot passmaps only for sub periods of a game,
    you may prefer to get stats on short time window.
    """
    num_passes_var = "num_passes_suc_short" if short_period else "num_passes_suc"
    pass_value_var = "pass_value_suc_short" if short_period else "pass_value_suc"
    for pair_key, pair_stats in pair_stats_filtered.iterrows():
        player1, player2 = pair_key.split("_")

        player1_x = player_stats.loc[player1]["x"]
        player1_y = player_stats.loc[player1]["y"]
        player2_x = player_stats.loc[player2]["x"]
        player2_y = player_stats.loc[player2]["y"]

        num_passes = pair_stats[num_passes_var]
        pass_value = pair_stats[pass_value_var]

        line_width = change_range(
            num_passes,
            (MIN_PAIR_COUNT, MAX_PAIR_COUNT),
            (MIN_EDGE_WIDTH, MAX_EDGE_WIDTH),
        )
        alpha = change_range(
            pass_value, (MIN_PLAYER_VALUE, MAX_PLAYER_VALUE), (MIN_ALPHA, MAX_ALPHA)
        )

        norm = Normalize(vmin=MIN_PAIR_VALUE, vmax=MAX_PAIR_VALUE)
        edge_cmap = cm.get_cmap(nodes_cmap)
        edge_color = edge_cmap(norm(pass_value))

        dx, dy = player2_x - player1_x, player2_y - player1_y
        rel = 55 / 105
        shift_x, shift_y = 1.5, 1.5 * rel

        slope = round(
            abs(
                (player2_y - player1_y) * 105 / 100 / (player2_x - player1_x) * 68 / 100
            ),
            1,
        )

        if slope > 0.5:
            if dy > 0:
                xy = (player1_x + dx + shift_x, player1_y + dy)
                xytext = (player1_x + shift_x, player1_y)
            else:
                xy = (player1_x + dx - shift_x, player1_y + dy)
                xytext = (player1_x - shift_x, player1_y)
        elif 0 <= slope <= 0.5:
            if dx > 0:
                xy = (player1_x + dx, player1_y + dy - shift_y)
                xytext = (player1_x, player1_y - shift_y)
            else:
                xy = (player1_x + dx, player1_y + dy + shift_y)
                xytext = (player1_x, player1_y + shift_y)

        ax.annotate(
            "",
            xy=xy,
            xytext=xytext,
            zorder=2,
            arrowprops=dict(
                arrowstyle=f"->, head_length={HEAD_LENGTH}, head_width={HEAD_WIDTH}",
                color=tuple([alpha if n == 3 else i for n, i in enumerate(edge_color)]),
                lw=line_width,
                shrinkB=player_stats.loc[player2, "marker_size"] / 5,
            ),
        )
