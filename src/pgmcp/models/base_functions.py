
from typing import Dict, List

from sqlalchemy_declarative_extensions import Function


functions : List[Function] = []

functions.append(Function("rebuild_element_tree",
    """
    BEGIN
        -- Reset fields
        UPDATE element
        SET "left" = NULL, "right" = NULL, level = 0, children_count = 0;

        -- Recursive CTE for left/right/level assignment
        WITH RECURSIVE tree AS (
            SELECT
                id,
                parent_id,
                1 AS lft,
                2 AS rgt,
                0 AS lvl
            FROM element
            WHERE parent_id IS NULL
            UNION ALL
            SELECT
                e.id,
                e.parent_id,
                t.rgt,
                t.rgt + 1,
                t.lvl + 1
            FROM element e
            JOIN tree t ON e.parent_id = t.id
        )
        UPDATE element e
        SET "left"  = t.lft,
            "right" = t.rgt,
            level   = t.lvl
        FROM tree t
        WHERE e.id = t.id;

        -- Update children_count in bulk
        UPDATE element e
        SET children_count = c.cnt
        FROM (
            SELECT parent_id, COUNT(*) AS cnt
            FROM element
            WHERE parent_id IS NOT NULL
            GROUP BY parent_id
        ) c
        WHERE e.id = c.parent_id;

        -- Reassign position for all siblings, contiguous and deterministic
        WITH sibling_groups AS (
            SELECT
                id,
                parent_id,
                ROW_NUMBER() OVER (PARTITION BY parent_id ORDER BY id) - 1 AS new_position
            FROM element
            WHERE parent_id IS NOT NULL
        )
        UPDATE element e
        SET position = s.new_position
        FROM sibling_groups s
        WHERE e.id = s.id;
    END;
    """,
    language="plpgsql"
))




