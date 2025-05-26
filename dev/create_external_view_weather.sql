CREATE OR ALTER VIEW weather_delta_view AS
SELECT * 
FROM OPENROWSET(
    BULK 'https://bessstorage.dfs.core.windows.net/datalake/bronze/weather_delta/',
    FORMAT = 'DELTA'
) AS rows;