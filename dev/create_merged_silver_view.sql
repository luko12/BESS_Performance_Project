CREATE OR ALTER VIEW merged_delta_view AS
SELECT * 
FROM OPENROWSET(
    BULK 'https://bessstorage.dfs.core.windows.net/datalake/silver/merged_delta/',
    FORMAT = 'DELTA'
) AS rows;