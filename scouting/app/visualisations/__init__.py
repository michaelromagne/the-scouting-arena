"""
Visualizations package for the scouting application.

This package contains modular visualization components organized by business scope:
- filtering: Core filtering and data processing functionality
- player_comparison: Comprehensive player comparison tools (radar charts, scatter plots, similarity analysis)
- player_profiles: Individual player displays and statistics
- quantile_analysis: Position and season-based percentile analysis
- charts: General chart and plot components
- category_analysis: Top players by category and specialized analyses
"""

from .category_analysis import (
    display_category,
    display_penalty_takers,
    display_player_statistics,
)
from .charts import (
    create_bar_chart,
    create_category_tooltip,
    create_penalty_takers_tooltip,
    get_column_tooltips,
    plot_tsne_player,
)
from .filtering import (
    FilterState,
    create_position_filter_ui,
    filter_and_process_data,
    filter_data,
    get_players_candidates,
    process_dataframe,
)
from .player_comparison import (
    create_comparison_plot,
    create_statistics_selector,
    display_similarity_score,
    get_available_statistics,
    get_single_player_radar,
    get_stat_definition,
    plot_two_players_radar_comparison,
)
from .player_profiles import display_player_profile
from .quantile_analysis import (
    create_barplot,
    plot_best_and_worst_quantiles,
)

__all__ = [
    # Filtering
    "FilterState",
    "filter_data",
    "filter_and_process_data",
    "get_players_candidates",
    "process_dataframe",
    "create_position_filter_ui",
    # Player comparison
    "create_comparison_plot",
    "create_statistics_selector",
    "display_similarity_score",
    "get_available_statistics",
    "get_single_player_radar",
    "get_stat_definition",
    "plot_two_players_radar_comparison",
    # Player profiles
    "display_player_profile",
    # Quantile analysis
    "create_barplot",
    "plot_best_and_worst_quantiles",
    # Charts
    "create_bar_chart",
    "create_category_tooltip",
    "create_penalty_takers_tooltip",
    "get_column_tooltips",
    "plot_tsne_player",
    # Category analysis
    "display_category",
    "display_penalty_takers",
    "display_player_statistics",
]
