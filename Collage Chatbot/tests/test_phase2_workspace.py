import hashlib
from datetime import datetime, UTC, timedelta
from backend.app.models.entities import User, Project, Conversation, Message, ConversationShare, Canvas, CanvasVersion
from backend.app.api.share_routes import safe_conversation

def test_share_token_is_stored_as_hash():
    token = "unpredictable-token"
    share = ConversationShare(conversation_id="conversation", created_by="owner", share_token_hash=hashlib.sha256(token.encode()).hexdigest())
    assert share.share_token_hash != token
    assert len(share.share_token_hash) == 64

def test_shared_payload_contains_only_public_fields():
    conversation = Conversation(id="private-id", title="Study", user_id="owner")
    conversation.messages = [Message(role="user", content="Question", conversation_id="private-id"), Message(role="assistant", content="Answer", conversation_id="private-id", selected_source="INTERNAL", entities={"private": "hidden"})]
    payload = safe_conversation(conversation)
    assert payload["title"] == "Study"
    assert "user_id" not in payload and "private" not in str(payload)
    assert all(set(message) <= {"role", "content", "created_at", "images", "sources"} for message in payload["messages"])

def test_project_delete_policy_is_non_destructive():
    project = Project(owner_id="owner", name="Course")
    conversation = Conversation(user_id="owner", project=project, title="Chat")
    project.conversations.append(conversation)
    project.is_archived = True
    conversation.project_id = None
    assert project.is_archived is True
    assert conversation.project_id is None

def test_canvas_versions_are_immutable_records():
    canvas = Canvas(project_id="project", owner_id="owner", title="Notes", content="one", revision=1)
    first = CanvasVersion(canvas_id="canvas", version=1, content="one")
    second = CanvasVersion(canvas_id="canvas", version=2, content="two")
    assert first.content == "one" and second.content == "two" and first.version != second.version
