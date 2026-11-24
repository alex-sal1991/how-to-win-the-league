DROP TABLE IF EXISTS gold.match_diff;

CREATE TABLE gold.match_diff AS
SELECT
    match_id, league, season, start_time, round,
    home_team_id, home_team, away_team_id, away_team,
    home_goals, away_goals, result,

    -- outcomes (0/1) for the logistic regression
    (result = 'H')::int AS home_win,
    (result = 'D')::int AS draw,
    (result = 'A')::int AS away_win,

    -- home minus away: positive = home team had more
    home_ball_possession - away_ball_possession      AS possession_diff,
    home_shots_total     - away_shots_total          AS shots_diff,
    home_shots_on_target - away_shots_on_target      AS shots_on_target_diff,
    ROUND(home_shots_on_target::numeric / NULLIF(home_shots_total, 0)
        - away_shots_on_target::numeric / NULLIF(away_shots_total, 0), 3)
                                                     AS shot_accuracy_diff,
    home_corner_kicks    - away_corner_kicks         AS corners_diff,
    home_fouls           - away_fouls                AS fouls_diff
FROM silver.matches
WHERE phase = 'regular season';

ALTER TABLE gold.match_diff ADD PRIMARY KEY (match_id);