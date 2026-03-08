# Gantt, Table, and Kanban Operations

The MCP server now supports view-aware operations for Vikunja projects.

## 1) List project views

Tool: `vikunja_list_project_views`

Input example:

```json
{
  "project_id": 11
}
```

## 2) Read tasks through a specific view

Tool: `vikunja_get_view_tasks`

Table example:

```json
{
  "project_id": 11,
  "view_kind": "table",
  "limit": 100
}
```

Gantt example:

```json
{
  "project_id": 11,
  "view_kind": "gantt",
  "limit": 100
}
```

Kanban example:

```json
{
  "project_id": 11,
  "view_kind": "kanban",
  "limit": 100
}
```

## 3) Move a task between Kanban buckets

Tool: `vikunja_move_task_to_bucket`

```json
{
  "project_id": 11,
  "view_id": 44,
  "task_id": 132,
  "bucket_title": "Doing"
}
```

## 4) Reorder task position in table/kanban

Tool: `vikunja_move_task_position`

```json
{
  "task_id": 132,
  "project_view_id": 44,
  "position": 16384.0
}
```

## 5) Move a task on Gantt timeline

Tool: `vikunja_update_task`

```json
{
  "task_id": 132,
  "start_date": "2026-03-08T18:27:19Z",
  "end_date": "2026-03-11T18:27:19Z",
  "due_date": "2026-03-11T18:27:19Z"
}
```
