from collections import deque


class ConversationService:
    """
    Manage short-term conversation history.

    Each conversation stores the last 6 messages.
    """

    def __init__(self, max_messages: int = 6):
        self.max_messages = max_messages
        self.conversations = {}

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> None:
        """
        Add a user or assistant message to a session.
        """

        if role not in ("user", "assistant"):
            raise ValueError("Invalid message role")

        if session_id not in self.conversations:
            self.conversations[session_id] = deque(
                maxlen=self.max_messages
            )

        self.conversations[session_id].append({
            "role": role,
            "content": content
        })

    def get_history(self, session_id: str) -> list:
        """
        Return conversation history for a session.
        """

        return list(
            self.conversations.get(session_id, [])
        )

    def clear_history(self, session_id: str) -> None:
        """
        Clear conversation history for a session.
        """

        self.conversations.pop(session_id, None)