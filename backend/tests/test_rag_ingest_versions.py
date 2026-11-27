"""Ingestion : la nouvelle version d'un fichier remplace l'ancienne (même domaine et nom). Exige la base Docker."""

from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select

from gmix.db import get_sessionmaker
from gmix.db.models import Domain, KnowledgeChunk, KnowledgeDocument
from gmix.rag.ingest import ingest_bytes

DOMAIN = "test-versions"


class FakeLLM:
    catalog = SimpleNamespace(embedding_model=lambda: SimpleNamespace(name="fake"))

    async def embed_documents(self, texts: list[str], title: str | None = None) -> list[list[float]]:
        return [[1.0] + [0.0] * 767 for _ in texts]


async def _ingest(text: str, name: str = "fiche.md") -> dict:
    async with get_sessionmaker()() as session:
        report = await ingest_bytes(
            session, FakeLLM(), filename=name, data=text.encode(), domain=DOMAIN, store_original=False
        )  # type: ignore[arg-type]
        await session.commit()
    return report


@pytest.mark.integration
async def test_new_version_replaces_old_one() -> None:
    async with get_sessionmaker()() as session:
        await session.execute(delete(KnowledgeDocument).where(KnowledgeDocument.domain_slug == DOMAIN))
        await session.merge(Domain(slug=DOMAIN, name=DOMAIN, is_active=False))
        await session.commit()
    try:
        await _ingest("Version un du taux.")
        await _ingest("Autre fichier à garder.", name="autre.md")
        await _ingest("Version deux du taux.")
        assert (await _ingest("Version deux du taux."))["status"] == "skipped"
        async with get_sessionmaker()() as session:
            docs = (
                await session.scalars(select(KnowledgeDocument).where(KnowledgeDocument.domain_slug == DOMAIN))
            ).all()
            texts = (
                await session.scalars(select(KnowledgeChunk.content).where(KnowledgeChunk.domain_slug == DOMAIN))
            ).all()
        assert sorted(d.source_uri[len(DOMAIN) + 14 :] for d in docs) == ["autre.md", "fiche.md"]
        assert sorted(texts) == ["Autre fichier à garder.", "Version deux du taux."]
    finally:
        async with get_sessionmaker()() as session:
            await session.execute(delete(KnowledgeDocument).where(KnowledgeDocument.domain_slug == DOMAIN))
            await session.execute(delete(Domain).where(Domain.slug == DOMAIN))
            await session.commit()
