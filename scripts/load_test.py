"""Locust load test for UNFYD.PIVOT.

Usage:
    pip install locust
    locust -f scripts/load_test.py --host http://localhost:8000

Scenario:
    - User registers a workspace
    - Lists conversations (empty)
    - Creates a conversation, sends 3 messages
    - Lists tickets

This profile is meant for soak / capacity testing.  For RAG-heavy load, point
some users at /api/v1/knowledge-base/search after seeding documents.
"""
from __future__ import annotations

import random
import string

from locust import HttpUser, between, task


def _email() -> str:
    return "load_" + "".join(random.choices(string.ascii_lowercase, k=10)) + "@test.dev"


class SupportUser(HttpUser):
    wait_time = between(1, 4)

    def on_start(self):
        email = _email()
        r = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "LoadTest123!",
                "full_name": "Load Test",
                "organization_name": "LoadTest Co",
            },
        )
        if r.status_code != 201:
            self.environment.runner.quit()
            return
        self.token = r.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def list_conversations(self):
        self.client.get("/api/v1/conversations", headers=self.headers, name="list conversations")

    @task(2)
    def chat_round(self):
        r = self.client.post(
            "/api/v1/conversations",
            json={"title": "load", "initial_message": "Hi, I need help."},
            headers=self.headers,
            name="create conversation",
        )
        if r.status_code != 201:
            return
        cid = r.json()["id"]
        for _ in range(2):
            self.client.post(
                f"/api/v1/conversations/{cid}/messages",
                json={"content": "Tell me more.", "role": "user"},
                headers=self.headers,
                name="send message",
            )

    @task(1)
    def list_tickets(self):
        self.client.get("/api/v1/tickets", headers=self.headers, name="list tickets")
