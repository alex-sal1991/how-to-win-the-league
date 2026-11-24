DROP TABLE IF EXISTS gold.team_season;

CREATE TABLE gold.team_season AS
WITH agg AS (
    SELECT
        league, season, team_id,
        MAX(team)                              AS team,
        COUNT(*)                               AS played,
        SUM((outcome = 'W')::int)              AS wins,
        SUM((outcome = 'D')::int)              AS draws,
        SUM((outcome = 'L')::int)              AS losses,
        SUM(goals_for)::int                         AS goals_for,
        SUM(goals_against)::int                     AS goals_against,
        SUM(goals_for) - SUM(goals_against)::int    AS goal_diff,
        SUM(points)                            AS points,
        ROUND(AVG(possession), 1)              AS avg_possession,
        SUM(shots)                             AS shots,
        SUM(shots_against)                     AS shots_against,
        SUM(shots_on_target)                   AS shots_on_target,
        SUM(shots_on_target_against)           AS shots_on_target_against
    FROM gold.team_match
    WHERE phase = 'regular season'
    GROUP BY league, season, team_id
)
SELECT
    *,
    RANK() OVER (PARTITION BY league, season
                 ORDER BY points DESC, goal_diff DESC, goals_for DESC) AS position
FROM agg;

ALTER TABLE gold.team_season ADD PRIMARY KEY (league, season, team_id);