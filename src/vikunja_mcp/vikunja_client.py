"""Thin typed client for Vikunja REST API."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from vikunja_mcp.errors import (
    VikunjaAuthError,
    VikunjaConflictError,
    VikunjaNotFoundError,
    VikunjaUnexpectedError,
    VikunjaValidationError,
)

logger = logging.getLogger(__name__)


class VikunjaClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        verify_ssl: bool = True,
        max_page_size: int = 100,
        max_fetch_tasks: int = 500,
    ):
        self.base_url = base_url.rstrip("/")
        self.max_page_size = max(1, max_page_size)
        self.max_fetch_tasks = max(1, max_fetch_tasks)
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=20.0,
            verify=verify_ssl,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        self.client.close()

    def _raise(self, response: httpx.Response) -> None:
        status = response.status_code
        if status in (401, 403):
            raise VikunjaAuthError(response.text)
        if status == 404:
            raise VikunjaNotFoundError(response.text)
        if status in (409, 412):
            raise VikunjaConflictError(response.text)
        if status == 422:
            raise VikunjaValidationError(response.text)
        if status >= 500:
            raise VikunjaUnexpectedError(response.text)
        raise VikunjaValidationError(response.text)

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, VikunjaUnexpectedError)),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.client.request(method, path, **kwargs)
        if response.status_code >= 400:
            self._raise(response)
        if not response.text:
            return None
        if "application/json" in response.headers.get("content-type", ""):
            return response.json()
        return response.text

    def check_auth(self) -> dict[str, Any]:
        return self._request("GET", "/user")

    def get_project(self, project_id: int) -> dict[str, Any]:
        return self._request("GET", f"/projects/{project_id}")

    def list_tasks(
        self,
        *,
        project_id: int | None = None,
        filter_expression: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        max_items = max(1, min(limit, self.max_fetch_tasks))
        per_page = max(1, min(max_items, self.max_page_size))
        endpoints: list[str] = []
        if project_id is not None:
            endpoints.append(f"/projects/{project_id}/tasks")
        endpoints.extend(["/tasks/all", "/tasks"])

        last_error: Exception | None = None
        for endpoint in endpoints:
            page = 1
            items: list[dict[str, Any]] = []
            try:
                while len(items) < max_items:
                    params: dict[str, Any] = {"per_page": per_page, "page": page}
                    if endpoint.startswith("/projects/"):
                        pass
                    elif project_id is not None:
                        params["project_id"] = project_id
                    if filter_expression:
                        params["filter"] = filter_expression

                    data = self._request("GET", endpoint, params=params)
                    page_items = self._coerce_task_list(data)
                    items.extend(page_items)
                    if len(page_items) < per_page:
                        break
                    page += 1
                return items[:max_items]
            except (VikunjaNotFoundError, VikunjaValidationError) as exc:
                last_error = exc
                continue

        if last_error:
            raise last_error
        return []

    @staticmethod
    def _coerce_task_list(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, dict) and "tasks" in data:
            raw = data["tasks"]
            return raw if isinstance(raw, list) else []
        if isinstance(data, list):
            return data
        return []

    def get_task(self, task_id: int) -> dict[str, Any]:
        return self._request("GET", f"/tasks/{task_id}")

    def create_task(self, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PUT", f"/projects/{project_id}/tasks", json=payload)

    def update_task(self, task_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/tasks/{task_id}", json=payload)

    def get_task_comments(self, task_id: int) -> list[dict[str, Any]]:
        data = self._request("GET", f"/tasks/{task_id}/comments")
        return data if isinstance(data, list) else data.get("comments", [])

    def add_task_comment(self, task_id: int, comment: str) -> dict[str, Any]:
        return self._request("PUT", f"/tasks/{task_id}/comments", json={"comment": comment})

    def get_task_labels(self, task_id: int) -> list[dict[str, Any]]:
        data = self._request("GET", f"/tasks/{task_id}/labels")
        return data if isinstance(data, list) else data.get("labels", [])

    def get_labels(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/labels")
        return data if isinstance(data, list) else data.get("labels", [])

    def create_label(self, title: str) -> dict[str, Any]:
        return self._request("PUT", "/labels", json={"title": title})

    def ensure_labels(self, names: list[str]) -> list[dict[str, Any]]:
        if not names:
            return []
        existing = self.get_labels()
        by_name = {str(item.get("title", "")): item for item in existing}
        result: list[dict[str, Any]] = []
        for name in names:
            if name in by_name:
                result.append(by_name[name])
                continue
            created = self.create_label(name)
            result.append(created)
            by_name[name] = created
        return result

    def set_task_labels(self, task_id: int, labels: list[str]) -> list[dict[str, Any]]:
        desired = self.ensure_labels(labels)
        current = self.get_task_labels(task_id)
        current_ids = {int(item["id"]): item for item in current if "id" in item}
        desired_ids = {int(item["id"]): item for item in desired if "id" in item}

        for label_id in current_ids.keys() - desired_ids.keys():
            self._request("DELETE", f"/tasks/{task_id}/labels/{label_id}")
        for label_id in desired_ids.keys() - current_ids.keys():
            self._request("PUT", f"/tasks/{task_id}/labels", json={"label_id": label_id})
        return list(desired_ids.values())

    def get_task_assignees(self, task_id: int) -> list[dict[str, Any]]:
        data = self._request("GET", f"/tasks/{task_id}/assignees")
        return data if isinstance(data, list) else data.get("assignees", [])

    def set_task_assignees(self, task_id: int, assignees: list[str]) -> None:
        current = self.get_task_assignees(task_id)
        current_by_username = {
            str(item.get("username", "")): int(item.get("id", 0))
            for item in current
            if item.get("username") and item.get("id")
        }

        for username, user_id in current_by_username.items():
            if username not in assignees:
                self._request("DELETE", f"/tasks/{task_id}/assignees/{user_id}")

        for username in assignees:
            if username in current_by_username:
                continue
            self._request("PUT", f"/tasks/{task_id}/assignees", json={"username": username})

    @staticmethod
    def normalize_labels(task: dict[str, Any]) -> list[str]:
        labels = []
        for item in task.get("labels") or []:
            if isinstance(item, str):
                labels.append(item)
            elif isinstance(item, dict):
                title = item.get("title") or item.get("name")
                if isinstance(title, str):
                    labels.append(title)
        return labels

    @staticmethod
    def normalize_assignees(task: dict[str, Any]) -> list[str]:
        assignees = []
        for item in task.get("assignees") or []:
            if isinstance(item, str):
                assignees.append(item)
            elif isinstance(item, dict):
                username = item.get("username") or item.get("name")
                if isinstance(username, str):
                    assignees.append(username)
        return assignees
