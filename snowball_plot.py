import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats

# ----------------------------
# CONFIG
# ----------------------------
INPUT_FILE = "C:\\Users\\bsims\\OneDrive\\Desktop\\vmk\\snowballs\\snowball fight stats.xlsx"  # <-- your Excel file
OUTPUT_HTML = "snowball_scatter_interactive.html"

# Known teams (seed data)
known_reindeer = {"bsims", "SammyxxFairy"}
known_penguin = {"VMKNeec", "Luckymaxer", "Winnie", "BuckyBarnes"}

# Optional: highlight a specific user on hover/search (no special styling in this version)
HIGHLIGHT_USER = "Winnie"  # set to None if you don't care


# ----------------------------
# HELPERS
# ----------------------------
def normalize_user(x: str) -> str:
    """Normalize usernames so matching is consistent."""
    if pd.isna(x):
        return x
    return str(x).strip()


def infer_teams(df: pd.DataFrame, current_teams: dict) -> dict:
    """
    Iteratively infer teams based on: if attacker team known, victim must be opposite; and vice versa.
    Uses conservative rules to avoid random assignments.
    """
    changed = True

    while changed:
        changed = False
        evidence = {}

        for _, row in df.iterrows():
            att = row["Attacker"]
            vic = row["Victim"]

            # If attacker team known -> victim likely opposite
            if att in current_teams and vic not in current_teams:
                att_team = current_teams[att]
                target = "Penguin" if att_team == "Reindeer" else "Reindeer"
                evidence.setdefault(vic, {"Reindeer": 0, "Penguin": 0})
                evidence[vic][target] += 1

            # If victim team known -> attacker likely opposite
            if vic in current_teams and att not in current_teams:
                vic_team = current_teams[vic]
                target = "Penguin" if vic_team == "Reindeer" else "Reindeer"
                evidence.setdefault(att, {"Reindeer": 0, "Penguin": 0})
                evidence[att][target] += 1

        # Apply evidence conservatively
        for user, counts in evidence.items():
            if user in current_teams:
                continue

            r = counts["Reindeer"]
            p = counts["Penguin"]

            # Strong dominance rules
            if r > p * 2 and r > 0:
                current_teams[user] = "Reindeer"
                changed = True
            elif p > r * 2 and p > 0:
                current_teams[user] = "Penguin"
                changed = True
            # One-sided evidence (no contradictions)
            elif r > 0 and p == 0:
                current_teams[user] = "Reindeer"
                changed = True
            elif p > 0 and r == 0:
                current_teams[user] = "Penguin"
                changed = True

    return current_teams


# ----------------------------
# MAIN
# ----------------------------
def main():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Could not find input file: {INPUT_FILE}")

    df = pd.read_excel(INPUT_FILE)

    # Validate expected columns
    required_cols = {"Attacker", "Victim", "Time"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in Excel file: {missing}. Found columns: {list(df.columns)}")

    # Normalize usernames (critical for correct joins/counts)
    df["Attacker"] = df["Attacker"].apply(normalize_user)
    df["Victim"] = df["Victim"].apply(normalize_user)
    df["Time"] = pd.to_datetime(df["Time"])

    # Seed teams
    user_teams = {u: "Reindeer" for u in known_reindeer}
    user_teams.update({u: "Penguin" for u in known_penguin})

    # Infer teams
    solid_teams = infer_teams(df, user_teams.copy())

    # --- Build stats ---
    attacks_made = df["Attacker"].value_counts().rename("Attacks Made")
    attacks_received = df["Victim"].value_counts().rename("Attacks Received")

    stats_df = pd.concat([attacks_made, attacks_received], axis=1).fillna(0).reset_index()
    stats_df = stats_df.rename(columns={"index": "User"})
    stats_df["Team"] = stats_df["User"].apply(lambda u: solid_teams.get(u, "Unknown"))

    # Drop Unknowns
    stats_df = stats_df[stats_df["Team"] != "Unknown"].copy()

    # Optional: add a flag column for highlighting
    if HIGHLIGHT_USER:
        stats_df["Highlight"] = stats_df["User"].str.contains(HIGHLIGHT_USER, regex=False)
    else:
        stats_df["Highlight"] = False

    # Build plot with team-specific trendlines
    fig = px.scatter(
        stats_df,
        x="Attacks Made",
        y="Attacks Received",
        color="Team",
        hover_name="User",
        hover_data={"Attacks Made": True, "Attacks Received": True, "Team": True},
        title="Snowball Fight: Attacks Made vs. Received (Interactive)",
        trendline="ols",
        color_discrete_map={
            "Reindeer": "red",
            "Penguin": "blue",
        },
    )

    # Set marker size
    fig.update_traces(marker_size=8, selector=dict(mode='markers'))

    # Add overall trendline for everyone
    x_all = stats_df["Attacks Made"].values
    y_all = stats_df["Attacks Received"].values
    slope, intercept, r_value, p_value, std_err = stats.linregress(x_all, y_all)

    x_line = np.array([x_all.min(), x_all.max()])
    y_line = slope * x_line + intercept

    fig.add_trace(go.Scatter(
        x=x_line,
        y=y_line,
        mode='lines',
        name=f'Overall Trend (R²={r_value**2:.3f})',
        line=dict(color='green', width=3, dash='dash'),
        hoverinfo='name',
    ))

    # Layout polish
    fig.update_layout(
        xaxis_title="Attacks Made",
        yaxis_title="Attacks Received",
        legend_title="Team",
        hovermode="closest",
    )

    # Save with custom HTML/JS for search functionality
    html_content = fig.to_html(include_plotlyjs=True, full_html=True)

    # Inject custom search box and JavaScript
    search_widget = """
    <style>
        .search-container {
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 1000;
            background: white;
            padding: 10px 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            font-family: Arial, sans-serif;
        }
        .search-container input {
            padding: 8px 12px;
            font-size: 14px;
            border: 1px solid #ccc;
            border-radius: 4px;
            width: 200px;
        }
        .search-container input:focus {
            outline: none;
            border-color: #007bff;
        }
        .search-container label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            font-size: 12px;
            color: #333;
        }
        .search-container .hint {
            font-size: 11px;
            color: #666;
            margin-top: 5px;
        }
    </style>
    <div class="search-container">
        <label>🔍 Highlight User</label>
        <input type="text" id="userSearch" placeholder="Enter username..." oninput="highlightUser(this.value)">
        <div class="hint">Type to highlight a user on the plot</div>
    </div>
    <script>
        function highlightUser(searchTerm) {
            var gd = document.querySelector('.plotly-graph-div');
            if (!gd || !gd.data) return;

            var updateSizes = [];
            var updateOpacities = [];

            searchTerm = searchTerm.toLowerCase().trim();

            for (var i = 0; i < gd.data.length; i++) {
                var trace = gd.data[i];
                // Skip trendlines (they don't have customdata/hovertext in the same way)
                if (trace.mode === 'lines' || !trace.hovertext) {
                    updateSizes.push(null);
                    updateOpacities.push(null);
                    continue;
                }

                var sizes = [];
                var opacities = [];
                var hoverTexts = trace.hovertext || [];

                for (var j = 0; j < hoverTexts.length; j++) {
                    var username = hoverTexts[j].toLowerCase();
                    if (searchTerm === '') {
                        // Reset to default
                        sizes.push(8);
                        opacities.push(1);
                    } else if (username.includes(searchTerm)) {
                        // Highlight match
                        sizes.push(20);
                        opacities.push(1);
                    } else {
                        // Dim non-matches
                        sizes.push(8);
                        opacities.push(0.2);
                    }
                }

                updateSizes.push(sizes);
                updateOpacities.push(opacities);
            }

            // Build update object
            var update = {'marker.size': [], 'marker.opacity': []};
            for (var i = 0; i < gd.data.length; i++) {
                if (updateSizes[i] !== null) {
                    update['marker.size'].push(updateSizes[i]);
                    update['marker.opacity'].push(updateOpacities[i]);
                } else {
                    update['marker.size'].push(undefined);
                    update['marker.opacity'].push(undefined);
                }
            }

            Plotly.restyle(gd, update);
        }
    </script>
    """

    # Insert the widget right after <body>
    html_content = html_content.replace("<body>", "<body>" + search_widget)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Saved: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
