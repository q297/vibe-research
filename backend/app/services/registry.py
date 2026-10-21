"""Wires real modules or stubs behind the ports; roles 2-4 plug their code in here"""

from dataclasses import dataclass, field
from functools import lru_cache

from app.config import get_settings
from app.services.jobs import JobManager
from app.services.ports import AgentPort, NewsPort, ProfilePort
from app.services.rate_limit import RateLimiter
from app.services.store import Store


@dataclass
class Services:
    news: NewsPort
    profiles: ProfilePort
    agent: AgentPort
    store: Store
    jobs: JobManager
    limiter: RateLimiter = field(default_factory=RateLimiter)


@lru_cache
def get_services() -> Services:
    settings = get_settings()
    if not settings.mock_mode:
        raise NotImplementedError("Real modules are not wired yet, set MOCK_MODE=true")

    from app.stubs.agent import StubAgent
    from app.stubs.news import StubNews
    from app.stubs.profiles import StubProfiles

    news = StubNews()
    agent = StubAgent(news, step_delay_s=settings.stub_step_delay_s)
    store = Store()
    return Services(
        news=news,
        profiles=StubProfiles(),
        agent=agent,
        store=store,
        jobs=JobManager(agent, store),
    )
