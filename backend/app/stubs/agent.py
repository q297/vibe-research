import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from app.contracts.clients import ClientProfile, Product
from app.contracts.common import Citation, CitationKind, Claim, Provenance
from app.contracts.events import Event, EventOrigin
from app.contracts.insights import (
    Action,
    ChatMessage,
    ChatRole,
    ImpactItem,
    Insight,
    InsightStatus,
    Level,
    StepKind,
    StepStatus,
    TraceStep,
    UserRole,
)
from app.contracts.taxonomy import TAG_LABELS_RU, SensitivityTag
from app.services.ports import NewsPort

STUB = "[Заглушка агента]"

_PRODUCT_HINTS: list[tuple[SensitivityTag, Product | None, str, str]] = [
    (
        SensitivityTag.KEY_RATE,
        Product.CREDIT,
        "Оценить условия рефинансирования и фиксации ставки",
        "Кредитование",
    ),
    (
        SensitivityTag.KEY_RATE,
        Product.DEPOSITS,
        "Пересмотреть срок размещения свободной ликвидности",
        "Депозиты",
    ),
    (
        SensitivityTag.FX_RATE,
        None,
        "Рассмотреть хеджирование валютной выручки",
        "Валютный контроль и хеджирование",
    ),
    (
        SensitivityTag.EXPORT_IMPORT,
        Product.FACTORING,
        "Проверить лимит экспортного факторинга",
        "Факторинг",
    ),
]


def _client_citation(feature: str, label: str) -> Citation:
    # source_id is the feature key, it must also be listed in client_features_used
    return Citation(kind=CitationKind.CLIENT_DATA, source_id=feature, title=label)


class StubAgent:
    """Deterministic fake of the role 4 agent, emits the same step kinds as the real one"""

    def __init__(self, news: NewsPort, step_delay_s: float = 0.4) -> None:
        self._news = news
        self._delay = step_delay_s

    async def run(
        self, *, profile: ClientProfile, event: Event, role: UserRole, trace_id: str
    ) -> AsyncIterator[TraceStep | Insight]:
        index = 0

        def step(kind: StepKind, title: str, **kwargs) -> TraceStep:
            nonlocal index
            index += 1
            return TraceStep(
                index=index, kind=kind, title=title, started_at=datetime.now(UTC), **kwargs
            )

        matched = [s for s in profile.sensitivities if s.tag in event.tags]
        yield step(
            StepKind.PLAN,
            "План анализа",
            detail="Определить признаки клиента, найти позицию банка, оценить влияние, проверить вывод",
            model="stub",
        )
        await asyncio.sleep(self._delay)

        yield step(
            StepKind.TOOL_CALL,
            "Профиль клиента",
            tool="get_client_profile",
            input_summary=profile.client_id,
            output_summary=", ".join(s.reason for s in matched) or "Совпадений по тегам нет",
        )
        await asyncio.sleep(self._delay)

        topics = [t.value for t in event.tags]
        positions = await self._news.bank_positions(topics)
        yield step(
            StepKind.TOOL_CALL,
            "Поиск в аналитике банка",
            tool="search_bank_analytics",
            input_summary=", ".join(topics) or "—",
            output_summary=f"Найдено позиций: {len(positions)}",
            citations=[p.citation for p in positions],
        )
        await asyncio.sleep(self._delay)

        yield step(StepKind.DRAFT, "Черновик инсайта", model="stub", tokens_in=0, tokens_out=0)
        await asyncio.sleep(self._delay)

        data_gaps: list[str] = []
        critic_notes: list[str] = []
        if not positions:
            critic = step(
                StepKind.CRITIC,
                "Проверка критиком",
                detail="Нет позиции Альфа-Банка по теме события",
                status=StepStatus.WARNING,
            )
            yield critic
            await asyncio.sleep(self._delay)
            positions = await self._news.bank_positions([SensitivityTag.KEY_RATE.value])
            yield step(
                StepKind.RETRY,
                "Повторный поиск по смежной теме",
                tool="search_bank_analytics",
                input_summary=SensitivityTag.KEY_RATE.value,
                output_summary=f"Найдено позиций: {len(positions)}",
                retry_of=critic.index,
            )
            data_gaps.append("Нет прямой позиции банка по теме события")
            critic_notes.append("Позиция банка взята по смежной теме после повторного поиска")
        else:
            yield step(StepKind.CRITIC, "Проверка критиком", detail="Замечаний нет")
        await asyncio.sleep(self._delay)

        source_kind = (
            CitationKind.USER_INPUT
            if event.origin == EventOrigin.USER_INPUT
            else CitationKind.ARTICLE
        )
        article_citations = [
            Citation(
                kind=source_kind,
                source_id=a.article_id,
                title=a.title,
                url=a.url,
                snippet=a.snippet,
            )
            for a in event.articles
        ]
        why = [
            Claim(
                text=f"{STUB} Событие затрагивает фактор «{TAG_LABELS_RU[s.tag]}»: {s.reason.lower()}",
                provenance=Provenance.AI_INFERENCE,
                citations=[_client_citation(f"sensitivity.{s.tag.value}", s.reason)],
            )
            for s in matched
        ]
        if not why:
            data_gaps.append("Связь события с профилем клиента не найдена")
        if not article_citations:
            data_gaps.append("У события нет первоисточников")
        risks = [
            ImpactItem(
                claim=Claim(
                    text=f"{STUB} Возможное негативное влияние через «{TAG_LABELS_RU[s.tag]}»",
                    provenance=Provenance.AI_INFERENCE,
                ),
                severity=Level.HIGH if s.weight >= 0.8 else Level.MEDIUM,
            )
            for s in matched[:2]
        ]
        opportunities = [
            ImpactItem(
                claim=Claim(
                    text=f"{STUB} Возможность пересмотреть стратегию по фактору «{TAG_LABELS_RU[s.tag]}»",
                    provenance=Provenance.AI_INFERENCE,
                ),
                severity=Level.LOW,
            )
            for s in matched[2:3]
        ]
        actions = [
            Action(text=f"{STUB} {text}", product_hint=hint, priority=Level.MEDIUM, is_promo=True)
            for tag, product, text, hint in _PRODUCT_HINTS
            if tag in event.tags and (product is None or product in profile.products)
        ]

        insight = Insight(
            insight_id=f"ins-{uuid.uuid4().hex[:12]}",
            client_id=profile.client_id,
            event_id=event.event_id,
            event_version=event.version,
            role=role,
            status=InsightStatus.READY,
            headline=f"{event.title}: что это значит для вас",
            # Only source facts here, the generated event summary is not a fact (D6)
            what_happened=[
                Claim(text=c.title, provenance=Provenance.SOURCE_FACT, citations=[c])
                for c in article_citations
            ],
            why_it_matters=why,
            risks=risks,
            opportunities=opportunities,
            actions=actions,
            bank_positions=positions,
            sources=article_citations + [p.citation for p in positions],
            client_features_used=[f"sensitivity.{s.tag.value}" for s in matched],
            data_gaps=data_gaps,
            scenarios=[
                Claim(
                    text=f"{STUB} Что отслеживать дальше по теме «{TAG_LABELS_RU[s.tag]}»",
                    provenance=Provenance.AI_INFERENCE,
                )
                for s in matched[:1]
            ],
            relevance=round(min(1.0, sum(s.weight for s in matched) / 2), 2),
            confidence=Level.LOW if data_gaps else Level.MEDIUM,
            critic_passed=bool(positions) and bool(why),
            critic_notes=critic_notes,
            trace_id=trace_id,
            created_at=datetime.now(UTC),
        )
        yield step(StepKind.FINAL, "Инсайт готов", output_summary=insight.headline)
        yield insight

    async def chat(
        self, *, insight: Insight, history: list[ChatMessage], message: str, trace_id: str
    ) -> ChatMessage:
        await asyncio.sleep(self._delay)
        return ChatMessage(
            role=ChatRole.ASSISTANT,
            content=f"{STUB} Ответ на вопрос «{message[:200]}» появится, когда подключится агент",
            provenance=Provenance.AI_INFERENCE,
            citations=insight.sources[:2],
            created_at=datetime.now(UTC),
        )
