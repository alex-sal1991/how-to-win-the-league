DROP TABLE IF EXISTS gold.team_match;

CREATE TABLE gold.team_match AS
SELECT
    match_id, league, season, start_time, round, phase,
    TRUE                     AS is_home,
    home_team_id             AS team_id,
    home_team                AS team,
    away_team_id             AS opponent_id,
    away_team                AS opponent,
    home_goals               AS goals_for,
    away_goals               AS goals_against,
    CASE result WHEN 'H' THEN 'W' WHEN 'D' THEN 'D' ELSE 'L' END AS outcome,
    CASE result WHEN 'H' THEN 3   WHEN 'D' THEN 1   ELSE 0   END AS points,
    home_ball_possession     AS possession,
    home_shots_total         AS shots,
    away_shots_total         AS shots_against,
    home_shots_on_target     AS shots_on_target,
    away_shots_on_target     AS shots_on_target_against,
    home_corner_kicks        AS corners,
    away_corner_kicks        AS corners_against,
    home_fouls               AS fouls,
    away_fouls               AS fouls_against,
    home_yellow_cards        AS yellow_cards,
    home_yellow_red_cards    AS yellow_red_cards,
    home_red_cards           AS red_cards
FROM silver.matches

UNION ALL

SELECT
    match_id, league, season, start_time, round, phase,
    FALSE,
    away_team_id, away_team,
    home_team_id, home_team,
    away_goals, home_goals,
    CASE result WHEN 'A' THEN 'W' WHEN 'D' THEN 'D' ELSE 'L' END,
    CASE result WHEN 'A' THEN 3   WHEN 'D' THEN 1   ELSE 0   END,
    away_ball_possession,
    away_shots_total,          home_shots_total,
    away_shots_on_target,      home_shots_on_target,
    away_corner_kicks,         home_corner_kicks,
    away_fouls,                home_fouls,
    away_yellow_cards,
    away_yellow_red_cards,
    away_red_cards
FROM silver.matches;

ALTER TABLE gold.team_match ADD PRIMARY KEY (match_id, team_id);