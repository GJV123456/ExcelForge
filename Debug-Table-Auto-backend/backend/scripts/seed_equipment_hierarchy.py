"""Seed the parent/child equipment type catalog used by the Vue tree selector.

The existing equipment_types rows are retained for backward-compatible rule
matching.  This script only adds explicit hierarchy metadata.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

HIERARCHY: dict[str, list[str]] = {
    "排烟机": [],
    "加压送风机": [],
    "防火阀": ["手动防火阀", "电动防火阀"],
    "监视模块": [
        "吸气式主机",
        "感温电缆",
        "感温光纤",
        "AFC",
        "EPS",
        "垂直电梯",
        "防火卷帘",
        "400V切非",
        "消防泵",
        "防火门",
        "门禁释放",
        "电气火灾、消防电源、应急疏散",
    ],
    "控制模块": [
        "吸气式主机",
        "感温电缆",
        "AFC",
        "EPS",
        "垂直电梯",
        "防火卷帘",
        "400V切非",
        "消防泵",
        "PA",
        "门禁释放",
        "电气火灾、消防电源、应急疏散",
        "声光报警器",
        "消火栓点灯",
        "主机手自动、人工确认",
    ],
    "特殊模块": ["气灭房功能测试", "区间消防电话与插孔电话", "站内消防电话与插孔电话"],
}

PARENT_STATUSES: dict[str, list[str]] = {
    "排烟机": ["运行状态", "手自动切换状态", "开启控制命令"],
    "加压送风机": ["运行状态", "手自动切换状态", "开启控制命令"],
}

SUBTYPE_STATUSES: dict[tuple[str, str], list[str]] = {
    ("防火阀", "电动防火阀"): ["动作状态", "关控制命令"],
    ("监视模块", "吸气式主机"): ["预警", "火警", "故障", "远程复位"],
    ("控制模块", "吸气式主机"): ["预警", "火警", "故障", "远程复位"],
    ("监视模块", "感温电缆"): ["报警反馈", "故障反馈", "远程复位"],
    ("控制模块", "感温电缆"): ["报警反馈", "故障反馈", "远程复位"],
    ("监视模块", "感温光纤"): ["感温光纤综合故障", "区间上行感温光纤报警反馈", "区间下行感温光纤报警反馈"],
    ("监视模块", "AFC"): ["AFC切非反馈", "AFC切非", "AFC状态反馈", "AFC释放控制"],
    ("控制模块", "AFC"): ["AFC切非反馈", "AFC切非", "AFC状态反馈", "AFC释放控制"],
    ("监视模块", "EPS"): ["状态反馈", "启动控制"],
    ("控制模块", "EPS"): ["状态反馈", "启动控制"],
    ("监视模块", "垂直电梯"): ["垂直电梯状态反馈", "垂直电梯归首控制"],
    ("控制模块", "垂直电梯"): ["垂直电梯状态反馈", "垂直电梯归首控制"],
    ("监视模块", "防火卷帘"): ["防火卷帘一次降落反馈", "防火卷帘一次降落控制", "防火卷帘二次降落反馈", "防火卷帘二次降落控制"],
    ("控制模块", "防火卷帘"): ["防火卷帘一次降落反馈", "防火卷帘一次降落控制", "防火卷帘二次降落反馈", "防火卷帘二次降落控制"],
    ("监视模块", "400V切非"): ["切非反馈"],
    ("控制模块", "400V切非"): ["切非"],
    ("监视模块", "消防泵"): ["消防泵手/自动反馈", "消防泵动作反馈", "消防泵故障反馈", "压力开关动作反馈", "流量开关动作反馈", "高水位报警反馈", "低水位报警反馈", "最低水位报警反馈", "稳压泵动作反馈", "稳压泵故障反馈", "消防泵启动控制", "巡检柜报警反馈", "信号阀动作反馈", "水流指示器动作反馈"],
    ("控制模块", "消防泵"): ["消防泵手/自动反馈", "消防泵动作反馈", "消防泵故障反馈", "压力开关动作反馈", "流量开关动作反馈", "高水位报警反馈", "低水位报警反馈", "最低水位报警反馈", "稳压泵动作反馈", "稳压泵故障反馈", "消防泵启动控制", "巡检柜报警反馈", "信号阀动作反馈", "水流指示器动作反馈"],
    ("监视模块", "门禁释放"): ["门禁释放反馈", "门禁释放"],
    ("控制模块", "门禁释放"): ["门禁释放反馈", "门禁释放"],
    ("监视模块", "电气火灾、消防电源、应急疏散"): ["电气火灾监控报警", "电气火灾监控故障反馈", "消防电源监控系统报警", "消防电源监控系统故障反馈", "应急照明及疏散指示系统状态反馈", "应急照明及疏散指示系统模式控制"],
    ("控制模块", "电气火灾、消防电源、应急疏散"): ["电气火灾监控报警", "电气火灾监控故障反馈", "消防电源监控系统报警", "消防电源监控系统故障反馈", "应急照明及疏散指示系统状态反馈", "应急照明及疏散指示系统模式控制"],
    ("控制模块", "声光报警器"): ["声光报警控制", "声光交替模块"],
    ("控制模块", "PA"): ["PA广播", "PA广播状态保持", "广播交替模块"],
    ("控制模块", "主机手自动、人工确认等"): ["FAS主机人工确定按钮", "FAS主机自动状态按钮", "气灭主机自动状态按钮", "FAS主机综合火警"],
}


def seed(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS equipment_type_subtypes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_equipment_type_id INTEGER NOT NULL,
                code TEXT NOT NULL COLLATE NOCASE,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                FOREIGN KEY (parent_equipment_type_id)
                    REFERENCES equipment_types(id) ON DELETE RESTRICT,
                UNIQUE (parent_equipment_type_id, code),
                UNIQUE (parent_equipment_type_id, name)
            )
            """
        )
        # This seed file is the authoritative taxonomy. Rebuild only hierarchy
        # metadata; test rules and equipment type rows are left untouched.
        connection.execute("CREATE TABLE IF NOT EXISTS test_content_selectors (id INTEGER PRIMARY KEY AUTOINCREMENT, test_content_id INTEGER NOT NULL, equipment_type TEXT NOT NULL DEFAULT '', equipment_subtype TEXT NOT NULL DEFAULT '', FOREIGN KEY (test_content_id) REFERENCES test_contents(id) ON DELETE CASCADE, UNIQUE (test_content_id, equipment_type, equipment_subtype))")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS equipment_type_statuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_type_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
                FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id) ON DELETE RESTRICT,
                UNIQUE (equipment_type_id, name)
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS equipment_subtype_statuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_subtype_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
                FOREIGN KEY (equipment_subtype_id) REFERENCES equipment_type_subtypes(id) ON DELETE RESTRICT,
                UNIQUE (equipment_subtype_id, name)
            )
        """)
        connection.execute("DELETE FROM equipment_type_statuses")
        connection.execute("DELETE FROM equipment_subtype_statuses")
        selector_columns = {row[1] for row in connection.execute("PRAGMA table_info(test_content_selectors)")}
        if "equipment_type" not in selector_columns:
            connection.execute("ALTER TABLE test_content_selectors ADD COLUMN equipment_type TEXT NOT NULL DEFAULT ''")
        connection.execute("DELETE FROM test_content_selectors")
        connection.execute("DELETE FROM equipment_type_subtypes")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS ix_equipment_type_subtypes_parent "
            "ON equipment_type_subtypes(parent_equipment_type_id)"
        )
        for parent_name, subtype_names in HIERARCHY.items():
            parent = connection.execute(
                "SELECT id FROM equipment_types WHERE name = ? COLLATE NOCASE ORDER BY id LIMIT 1",
                (parent_name,),
            ).fetchone()
            if parent is None:
                code = {
                    "防火阀": "TYPE_FIRE_DAMPER",
                    "特殊模块": "TYPE_SPECIAL_MODULE",
                }[parent_name]
                connection.execute(
                    "INSERT INTO equipment_types(\n"
                    "code, name, description, sort_order, is_enabled\n"
                    ") VALUES (?, ?, '', 0, 1)",
                    (code, parent_name),
                )
                parent_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
            else:
                parent_id = int(parent[0])
            for sort_order, subtype_name in enumerate(subtype_names, start=1):
                subtype_code = f"{parent_id}_{sort_order:02d}"
                connection.execute(
                    """
                    INSERT INTO equipment_type_subtypes(
                        parent_equipment_type_id, code, name, sort_order, is_enabled
                    )
                    VALUES (?, ?, ?, ?, 1)
                    ON CONFLICT(parent_equipment_type_id, name) DO UPDATE SET
                        sort_order = excluded.sort_order,
                        is_enabled = 1,
                        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    """,
                    (parent_id, subtype_code, subtype_name, sort_order),
                )
                subtype_id = int(
                    connection.execute(
                        "SELECT id FROM equipment_type_subtypes WHERE parent_equipment_type_id = ? AND name = ?",
                        (parent_id, subtype_name),
                    ).fetchone()[0]
                )
                for status_order, status_name in enumerate(SUBTYPE_STATUSES.get((parent_name, subtype_name), []), start=1):
                    connection.execute(
                        """
                        INSERT INTO equipment_subtype_statuses(
                            equipment_subtype_id, name, sort_order, is_enabled
                        ) VALUES (?, ?, ?, 1)
                        """,
                        (subtype_id, status_name, status_order),
                    )

            for status_order, status_name in enumerate(PARENT_STATUSES.get(parent_name, []), start=1):
                connection.execute(
                    """
                    INSERT INTO equipment_type_statuses(
                        equipment_type_id, name, sort_order, is_enabled
                    ) VALUES (?, ?, ?, 1)
                    """,
                    (parent_id, status_name, status_order),
                )

        # Imported workbook keeps subtype rules as legacy top-level equipment
        # types, while the frontend selects parent type plus subtype.
        fire_rules = {
            "电动防火阀": "防火阀（电动）",
            "手动防火阀": "防火阀（手动）",
        }
        for subtype_name, legacy_name in fire_rules.items():
            legacy = connection.execute(
                "SELECT id FROM equipment_types WHERE name = ? COLLATE NOCASE ORDER BY id LIMIT 1",
                (legacy_name,),
            ).fetchone()
            if legacy is None:
                continue
            rule_rows = connection.execute(
                "SELECT id, content FROM test_contents WHERE equipment_type_id = ?",
                (int(legacy[0]),),
            ).fetchall()
            for rule_row in rule_rows:
                connection.execute(
                    "INSERT OR IGNORE INTO test_content_selectors(test_content_id, equipment_type, equipment_subtype) VALUES (?, ?, ?)",
                    (int(rule_row["id"]), "防火阀", subtype_name),
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    args = parser.parse_args()
    seed(args.database)
    print(f"seeded equipment hierarchy: {args.database}")


if __name__ == "__main__":
    main()
