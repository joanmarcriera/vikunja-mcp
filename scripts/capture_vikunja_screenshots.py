#!/usr/bin/env python3
"""Capture reproducible Vikunja README screenshots using Playwright.

This script logs in with a test account, opens relevant project views,
and saves screenshots + a JSON manifest.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import typer
from dotenv import dotenv_values
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vikunja_mcp.vikunja_client import VikunjaClient  # noqa: E402

app = typer.Typer(add_completion=False)


def _strip_api_v1(base_url: str) -> str:
    value = base_url.rstrip("/")
    if value.endswith("/api/v1"):
        return value[: -len("/api/v1")]
    return value


def _wait_for_project_shell(page: Page) -> None:
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(800)
    selectors = [
        "button:has-text('FILTERS')",
        "button:has-text('Filters')",
        "text=List",
        "text=Kanban",
    ]
    for selector in selectors:
        locator = page.locator(selector).first
        if locator.count() == 0:
            continue
        try:
            locator.wait_for(timeout=8_000)
            return
        except PlaywrightTimeoutError:
            continue
    raise RuntimeError(f"project shell did not load as expected (url={page.url})")


def _maybe_login(page: Page, *, username: str, password: str) -> None:
    page.wait_for_timeout(500)
    if "/login" not in page.url and page.locator("input[type='password']").count() == 0:
        return
    page.locator("input[type='password']").first.wait_for(timeout=10_000)

    username_candidates = [
        "input[name='username']",
        "input[autocomplete='username']",
        "input[type='text']",
    ]
    password_candidates = [
        "input[name='password']",
        "input[autocomplete='current-password']",
        "input[type='password']",
    ]

    username_input = None
    for selector in username_candidates:
        locator = page.locator(selector).first
        if locator.count() > 0:
            username_input = locator
            break
    if username_input is None:
        raise RuntimeError("could not find username input")

    password_input = None
    for selector in password_candidates:
        locator = page.locator(selector).first
        if locator.count() > 0:
            password_input = locator
            break
    if password_input is None:
        raise RuntimeError("could not find password input")

    username_input.fill(username)
    password_input.fill(password)

    login_buttons = [
        page.get_by_role("button", name=re.compile("log in|login|sign in", re.IGNORECASE)).first,
        page.locator("button[type='submit']").first,
    ]
    clicked = False
    for button in login_buttons:
        if button.count() > 0:
            button.click()
            clicked = True
            break
    if not clicked:
        password_input.press("Enter")

    page.wait_for_timeout(1200)


def _discover_view_ids(
    *,
    base_api_url: str,
    token: str,
    project_id: int,
) -> dict[str, int]:
    client = VikunjaClient(base_api_url, token, verify_ssl=True)
    try:
        views = client.list_project_views(project_id)
        by_kind = {
            str(view.get("view_kind")): int(view.get("id"))
            for view in views
            if view.get("id")
        }
        required = {"list", "gantt", "table", "kanban"}
        missing = required - set(by_kind)
        if missing:
            raise RuntimeError(f"missing project view kinds: {sorted(missing)}")
        return by_kind
    finally:
        client.close()


def _discover_demo_task_ids(
    *,
    base_api_url: str,
    token: str,
    project_id: int,
) -> dict[str, int]:
    client = VikunjaClient(base_api_url, token, verify_ssl=True)
    try:
        tasks = client.list_tasks(project_id=project_id, limit=500)
        out: dict[str, int] = {}
        for task in tasks:
            labels = client.normalize_labels(task)
            for key in ("07", "10"):
                if f"demo:key:{key}" in labels:
                    out[key] = int(task["id"])
        return out
    finally:
        client.close()


def _capture(page: Page, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=True)


@app.command()
def main(
    output_dir: Path = typer.Option(
        ROOT / "docs" / "assets" / "screenshots",
        "--output-dir",
        help="Where PNG files and manifest are written.",
    ),
    username: str = typer.Option("mcp", "--username"),
    password: str = typer.Option("MCP12345", "--password"),
    headless: bool = typer.Option(True, "--headless/--headed"),
) -> None:
    env = dotenv_values(str(ROOT / ".env"))
    base_api_url = str(env.get("VIKUNJA_BASE_URL") or "").strip()
    token = str(env.get("VIKUNJA_TOKEN") or "").strip()
    project_id = int(env.get("VIKUNJA_DEFAULT_PROJECT_ID") or 0)

    if not base_api_url or not token or not project_id:
        raise typer.BadParameter(
            ".env requires VIKUNJA_BASE_URL, VIKUNJA_TOKEN, VIKUNJA_DEFAULT_PROJECT_ID"
        )

    base_web_url = _strip_api_v1(base_api_url)
    view_ids = _discover_view_ids(base_api_url=base_api_url, token=token, project_id=project_id)
    demo_task_ids = _discover_demo_task_ids(
        base_api_url=base_api_url,
        token=token,
        project_id=project_id,
    )

    manifest: dict[str, Any] = {
        "base_web_url": base_web_url,
        "project_id": project_id,
        "view_ids": view_ids,
        "task_ids": demo_task_ids,
        "screenshots": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        page = context.new_page()

        list_url = f"{base_web_url}/projects/{project_id}/{view_ids['list']}"
        page.goto(list_url, wait_until="domcontentloaded")
        _maybe_login(page, username=username, password=password)
        if "/login" in page.url:
            raise RuntimeError("login did not complete successfully")
        if "/projects/" not in page.url:
            page.goto(list_url, wait_until="domcontentloaded")
        _wait_for_project_shell(page)

        targets = {
            "01_list_view": list_url,
            "02_gantt_view": f"{base_web_url}/projects/{project_id}/{view_ids['gantt']}",
            "03_table_view": f"{base_web_url}/projects/{project_id}/{view_ids['table']}",
            "04_kanban_view": f"{base_web_url}/projects/{project_id}/{view_ids['kanban']}",
        }

        for name, url in targets.items():
            page.goto(url, wait_until="domcontentloaded")
            _wait_for_project_shell(page)
            out_path = output_dir / f"{name}.png"
            _capture(page, out_path)
            manifest["screenshots"][name] = str(out_path.relative_to(ROOT))

        # Capture filter dialog and filtered list state.
        page.goto(list_url, wait_until="domcontentloaded")
        _wait_for_project_shell(page)
        filters_button = page.get_by_role("button", name=re.compile("filters", re.IGNORECASE)).first
        filters_button.click()
        page.wait_for_timeout(400)
        filter_inputs = page.locator("input:visible, textarea:visible")
        if filter_inputs.count() > 0:
            filter_inputs.first.fill("labels = demo:readme")
        out_path = output_dir / "05_list_filter_dialog.png"
        _capture(page, out_path)
        manifest["screenshots"]["05_list_filter_dialog"] = str(out_path.relative_to(ROOT))

        show_results = page.get_by_role(
            "button",
            name=re.compile("show results", re.IGNORECASE),
        ).first
        if show_results.count() > 0:
            show_results.click()
            page.wait_for_timeout(500)
        out_path = output_dir / "06_list_filtered.png"
        _capture(page, out_path)
        manifest["screenshots"]["06_list_filtered"] = str(out_path.relative_to(ROOT))

        # Task details from demo workflow.
        for key, name in (("07", "07_task_done_detail"), ("10", "08_task_doing_detail")):
            task_id = demo_task_ids.get(key)
            if not task_id:
                continue
            url = f"{base_web_url}/tasks/{task_id}"
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(1000)
            out_path = output_dir / f"{name}.png"
            _capture(page, out_path)
            manifest["screenshots"][name] = str(out_path.relative_to(ROOT))

        browser.close()

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    typer.echo(f"Saved screenshots in: {output_dir}")
    typer.echo(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    app()
