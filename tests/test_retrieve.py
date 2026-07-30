from datetime import datetime, timedelta

from personal_reply.rag.retrieve import StyleRetriever
from personal_reply.rag.store import MessageStore, StoredMessage


def test_retrieve_reranks_by_blended_score(tmp_path) -> None:
    store = MessageStore(tmp_path / "style.lance")
    now = datetime(2026, 7, 9, 12, 0)
    store.upsert(
        [
            StoredMessage(
                id="old",
                platform="whatsapp",
                contact="Papa",
                text="Old reply",
                context_before="Papa: old",
                context_after="",
                conversation_window="Papa: old\nSameer: Old reply",
                timestamp=now - timedelta(days=400),
                message_kind="reply",
                vector=[1.0, 0.0, 0.0],
            ),
            StoredMessage(
                id="new",
                platform="whatsapp",
                contact="Papa",
                text="New reply",
                context_before="Papa: new",
                context_after="",
                conversation_window="Papa: new\nSameer: New reply",
                timestamp=now - timedelta(days=2),
                message_kind="reply",
                vector=[0.9, 0.1, 0.0],
            ),
        ]
    )

    class FakeEmbedder:
        def embed(self, text: str) -> list[float]:
            return [1.0, 0.0, 0.0]

    retriever = StyleRetriever(store, FakeEmbedder())  # type: ignore[arg-type]
    results = retriever.retrieve(
        "Kahan ho?",
        top_k=1,
        platform="whatsapp",
        vector_weight=0.2,
        recency_weight=0.8,
        now=now,
    )

    assert len(results) == 1
    assert results[0].text == "New reply"
    assert results[0].formatted_timestamp == "07/07/26 12:00"


def test_retrieve_filters_message_kind_in_python(tmp_path) -> None:
    store = MessageStore(tmp_path / "style.lance")
    now = datetime(2026, 7, 9, 12, 0)
    store.upsert(
        [
            StoredMessage(
                id="reply",
                platform="whatsapp",
                contact="Papa",
                text="Reply text",
                context_before="",
                context_after="",
                conversation_window="Papa: hi\nSameer: Reply text",
                timestamp=now,
                message_kind="reply",
                vector=[1.0, 0.0, 0.0],
            ),
            StoredMessage(
                id="reopen",
                platform="whatsapp",
                contact="Papa",
                text="Opener text",
                context_before="",
                context_after="",
                conversation_window="Sameer: Opener text",
                timestamp=now,
                message_kind="reopen",
                vector=[1.0, 0.0, 0.0],
            ),
        ]
    )

    class FakeEmbedder:
        def embed(self, text: str) -> list[float]:
            return [1.0, 0.0, 0.0]

    retriever = StyleRetriever(store, FakeEmbedder())  # type: ignore[arg-type]
    results = retriever.retrieve("reopen", top_k=5, message_kind="reopen")
    assert len(results) == 1
    assert results[0].text == "Opener text"


def test_retrieve_blends_category_contacts_with_lower_affinity(tmp_path) -> None:
    store = MessageStore(tmp_path / "style.lance")
    now = datetime(2026, 7, 9, 12, 0)
    store.upsert(
        [
            StoredMessage(
                id="papa",
                platform="whatsapp",
                contact="WhatsAppChatwithPapaNew",
                text="Papa reply",
                context_before="",
                context_after="",
                conversation_window="Papa: hi\nSameer: Papa reply",
                timestamp=now,
                message_kind="reply",
                vector=[0.8, 0.2, 0.0],
            ),
            StoredMessage(
                id="mama",
                platform="whatsapp",
                contact="WhatsAppChatwithMamaNew",
                text="Mama reply",
                context_before="",
                context_after="",
                conversation_window="Mama: hi\nSameer: Mama reply",
                timestamp=now,
                message_kind="reply",
                vector=[1.0, 0.0, 0.0],
            ),
        ]
    )

    class FakeEmbedder:
        def embed(self, text: str) -> list[float]:
            return [1.0, 0.0, 0.0]

    retriever = StyleRetriever(store, FakeEmbedder())  # type: ignore[arg-type]
    results = retriever.retrieve(
        "family check in",
        top_k=2,
        contact="WhatsAppChatwithPapaNew",
        peer_contacts={"WhatsAppChatwithPapaNew", "WhatsAppChatwithMamaNew"},
        contact_match_weight=1.0,
        category_match_weight=0.65,
        vector_weight=1.0,
        recency_weight=0.0,
        now=now,
    )

    assert len(results) == 2
    assert results[0].contact == "WhatsAppChatwithPapaNew"
    assert results[0].affinity_weight == 1.0
    assert results[1].contact == "WhatsAppChatwithMamaNew"
    assert results[1].affinity_weight == 0.65
    assert results[0].score > results[1].score


def test_retrieve_tag_only_peers_use_category_weight(tmp_path) -> None:
    store = MessageStore(tmp_path / "style.lance")
    now = datetime(2026, 7, 9, 12, 0)
    store.upsert(
        [
            StoredMessage(
                id="papa",
                platform="whatsapp",
                contact="WhatsAppChatwithPapaNew",
                text="Papa reply",
                context_before="",
                context_after="",
                conversation_window="Papa: hi\nSameer: Papa reply",
                timestamp=now,
                message_kind="reply",
                vector=[1.0, 0.0, 0.0],
            ),
        ]
    )

    class FakeEmbedder:
        def embed(self, text: str) -> list[float]:
            return [1.0, 0.0, 0.0]

    retriever = StyleRetriever(store, FakeEmbedder())  # type: ignore[arg-type]
    results = retriever.retrieve(
        "salam",
        top_k=1,
        contact=None,
        peer_contacts={"WhatsAppChatwithPapaNew"},
        category_match_weight=0.65,
        vector_weight=1.0,
        recency_weight=0.0,
        now=now,
    )
    assert len(results) == 1
    assert results[0].affinity_weight == 0.65
