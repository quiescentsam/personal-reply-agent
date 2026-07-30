from __future__ import annotations

from personal_reply.browser.models import ThreadContext
from personal_reply.config import Config
from personal_reply.llm.ollama_client import OllamaChatClient
from personal_reply.rag.contact_list import list_contact_names
from personal_reply.rag.contact_resolve import ContactResolution, resolve_for_retrieval
from personal_reply.rag.context import build_reopen_retrieval_query, build_retrieval_query
from personal_reply.rag.embed import OllamaEmbedder
from personal_reply.rag.retrieve import RetrievedMessage, StyleRetriever
from personal_reply.rag.store import MessageStore
from personal_reply.reply.prompt import build_messages, build_opener_messages
from personal_reply.reply.thread_state import ConversationMode, ThreadAnalysis, analyze_thread_state
from personal_reply.research.subagent import ResearchBrief, run_research_subagent, should_invoke_research
from personal_reply.reply.verbose import SuggestResult


class ReplyGenerator:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._store = MessageStore(config.lancedb_uri)
        self._embedder = OllamaEmbedder(config)
        self._retriever = StyleRetriever(self._store, self._embedder)
        self._chat = OllamaChatClient(config)

    def suggest(
        self,
        incoming_text: str,
        *,
        thread_context: str | None = None,
        platform: str | None = None,
        contact: str | None = None,
        verbose: bool = False,
        thread_analysis: ThreadAnalysis | None = None,
        research: bool = False,
    ) -> str | SuggestResult:
        platform = platform or self._config.platform
        contact_resolution: ContactResolution | None = None
        stored_contact: str | None = None
        contact_label: str | None = None
        if contact:
            contact_resolution = resolve_for_retrieval(
                contact,
                list_contact_names(self._store, platform=platform),
                self._config.contact_attributes,
            )
            stored_contact = contact_resolution.stored_contact
            contact_label = contact_resolution.contact_label

        retrieval_scope = self._retrieval_scope(contact_resolution, platform)
        use_research = self._should_use_research(
            research=research,
            thread_context=thread_context,
            contact_label=contact_label,
            thread_analysis=thread_analysis,
            incoming_text=incoming_text,
        )
        research_brief = self._maybe_research(
            thread_context=thread_context,
            contact_label=contact_label,
            thread_analysis=thread_analysis,
            incoming_text=incoming_text,
            enabled=use_research,
        )
        research_context = research_brief.summary if research_brief else None

        if thread_analysis and thread_analysis.mode == "reopen":
            return self._suggest_reopen(
                thread_analysis=thread_analysis,
                platform=platform,
                contact_resolution=contact_resolution,
                contact_label=contact_label,
                verbose=verbose,
                research_brief=research_brief,
            )

        examples = self._retriever.retrieve(
            build_retrieval_query(incoming_text, thread_context),
            top_k=self._config.top_k,
            platform=platform,
            candidate_multiplier=self._config.candidate_multiplier,
            vector_weight=self._config.vector_weight,
            recency_weight=self._config.recency_weight,
            recency_half_life_days=self._config.recency_half_life_days,
            **retrieval_scope,
        )
        messages = build_messages(
            user_name=self._config.user_name,
            incoming_text=incoming_text,
            examples=examples,
            thread_context=thread_context,
            contact=contact_label,
            research_context=research_context,
        )
        suggestion = self._chat.chat(messages)
        if verbose:
            return SuggestResult(
                suggestion=suggestion,
                examples=examples,
                messages=messages,
                contact_label=contact_label,
                stored_contact=stored_contact,
                mode="respond",
                mode_reason=thread_analysis.reason if thread_analysis else None,
                hours_since_last=thread_analysis.hours_since_last if thread_analysis else None,
                research_queries=research_brief.queries if research_brief else (),
                research_summary=research_brief.summary if research_brief else None,
            )
        return suggestion

    def _retrieval_scope(
        self,
        contact_resolution: ContactResolution | None,
        platform: str,
    ) -> dict[str, object]:
        if contact_resolution is None:
            return {
                "contact": None,
                "peer_contacts": None,
                "contact_match_weight": self._config.contact_match_weight,
                "category_match_weight": self._config.category_match_weight,
            }
        return {
            "contact": contact_resolution.stored_contact,
            "peer_contacts": contact_resolution.peer_contacts,
            "contact_match_weight": self._config.contact_match_weight,
            "category_match_weight": self._config.category_match_weight,
        }

    def _should_use_research(
        self,
        *,
        research: bool,
        thread_context: str | None,
        contact_label: str | None,
        thread_analysis: ThreadAnalysis | None,
        incoming_text: str,
    ) -> bool:
        if not self._config.research_enabled:
            return False
        if research:
            return True
        if (
            thread_analysis is not None
            and thread_analysis.mode == "reopen"
            and self._config.research_auto_on_reopen
        ):
            return True
        if not self._config.research_auto:
            return False

        mode = thread_analysis.mode if thread_analysis else "respond"
        return should_invoke_research(
            self._chat,
            mode=mode,
            contact=contact_label,
            incoming_text=incoming_text if mode == "respond" else None,
            thread_context=thread_context or "",
            reopen_context=thread_analysis.reopen_context if thread_analysis else None,
            hours_since_last=thread_analysis.hours_since_last if thread_analysis else None,
        )

    def _maybe_research(
        self,
        *,
        thread_context: str | None,
        contact_label: str | None,
        thread_analysis: ThreadAnalysis | None,
        incoming_text: str,
        enabled: bool,
    ) -> ResearchBrief | None:
        if not enabled:
            return None
        mode = thread_analysis.mode if thread_analysis else "respond"
        return run_research_subagent(
            self._chat,
            config=self._config,
            thread_context=thread_context or "",
            contact=contact_label,
            mode=mode,
            incoming_text=incoming_text if mode == "respond" else None,
            reopen_context=thread_analysis.reopen_context if thread_analysis else None,
        )

    def _retrieve_opener_examples(
        self,
        *,
        query: str,
        platform: str,
        contact_resolution: ContactResolution | None,
    ) -> list[RetrievedMessage]:
        retrieval_scope = self._retrieval_scope(contact_resolution, platform)
        common_kwargs = {
            "top_k": self._config.top_k,
            "platform": platform,
            "candidate_multiplier": self._config.candidate_multiplier,
            "vector_weight": self._config.vector_weight,
            "recency_weight": self._config.recency_weight,
            "recency_half_life_days": self._config.recency_half_life_days,
            **retrieval_scope,
        }
        reopen_examples = self._retriever.retrieve(
            query,
            message_kind="reopen",
            **common_kwargs,
        )
        if len(reopen_examples) >= 2:
            return reopen_examples

        fallback_examples = self._retriever.retrieve(query, **common_kwargs)
        if not reopen_examples:
            return fallback_examples

        seen = {example.id for example in reopen_examples}
        merged = list(reopen_examples)
        for example in fallback_examples:
            if example.id not in seen:
                merged.append(example)
            if len(merged) >= self._config.top_k:
                break
        return merged[: self._config.top_k]

    def _suggest_reopen(
        self,
        *,
        thread_analysis: ThreadAnalysis,
        platform: str,
        contact_resolution: ContactResolution | None,
        contact_label: str | None,
        verbose: bool,
        research_brief: ResearchBrief | None = None,
    ) -> str | SuggestResult:
        query = build_reopen_retrieval_query(
            contact=contact_label,
            reopen_context=thread_analysis.reopen_context,
        )
        examples = self._retrieve_opener_examples(
            query=query,
            platform=platform,
            contact_resolution=contact_resolution,
        )
        messages = build_opener_messages(
            user_name=self._config.user_name,
            reopen_context=thread_analysis.reopen_context,
            examples=examples,
            contact=contact_label,
            research_context=research_brief.summary if research_brief else None,
        )
        suggestion = self._chat.chat(messages)
        if verbose:
            stored_contact = contact_resolution.stored_contact if contact_resolution else None
            return SuggestResult(
                suggestion=suggestion,
                examples=examples,
                messages=messages,
                contact_label=contact_label,
                stored_contact=stored_contact,
                mode="reopen",
                mode_reason=thread_analysis.reason,
                hours_since_last=thread_analysis.hours_since_last,
                research_queries=research_brief.queries if research_brief else (),
                research_summary=research_brief.summary if research_brief else None,
            )
        return suggestion

    def suggest_for_thread(
        self,
        thread: ThreadContext,
        *,
        verbose: bool = False,
        force_mode: ConversationMode | None = None,
        research: bool = False,
    ) -> str | SuggestResult:
        analysis = analyze_thread_state(thread, self._config, force_mode=force_mode)
        thread_context = thread.format_thread_context()
        incoming_text = analysis.incoming_text or thread.last_message().text.strip()
        return self.suggest(
            incoming_text,
            thread_context=thread_context,
            contact=thread.contact_or_subject,
            verbose=verbose,
            thread_analysis=analysis,
            research=research,
        )

    def suggest_from_browser(
        self,
        *,
        verbose: bool = False,
        insert_into_compose: bool | None = None,
        force_mode: ConversationMode | None = None,
        research: bool = False,
    ) -> str | SuggestResult:
        from personal_reply.browser.connector import connect_to_chrome
        from personal_reply.browser.whatsapp import read_whatsapp_thread, write_whatsapp_compose

        insert = (
            self._config.insert_into_compose
            if insert_into_compose is None
            else insert_into_compose
        )
        with connect_to_chrome(debug_url=self._config.chrome_debug_url) as page:
            thread = read_whatsapp_thread(page, sender_names=self._config.sender_names)
            result = self.suggest_for_thread(
                thread,
                verbose=verbose,
                force_mode=force_mode,
                research=research,
            )
            if insert:
                suggestion = result.suggestion if isinstance(result, SuggestResult) else result
                write_whatsapp_compose(
                    page,
                    compose_selector=thread.compose_selector,
                    text=suggestion.strip(),
                )
            return result

    def close(self) -> None:
        self._embedder.close()
        self._chat.close()

    def __enter__(self) -> ReplyGenerator:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
